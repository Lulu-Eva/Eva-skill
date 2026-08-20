#!/usr/bin/env python3
"""Preview, export, and verify local Eva data backups.

The script is intentionally non-interactive. The calling Eva workflow must show
the preview to the user and obtain confirmation before invoking ``export``.
Only Python's standard library is used.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import time
from typing import Any, Iterable
import unicodedata
import zipfile


SCRIPT_VERSION = "2.3.0"
BACKUP_FORMAT_VERSION = 1
MANIFEST_NAME = "MANIFEST.json"
README_NAME = "README.md"
DEFAULT_ARCHIVE_PREFIX = "Eva-data-backup"
DEFAULT_MAX_FILES = 50_000
DEFAULT_MAX_BYTES = 10 * 1024 * 1024 * 1024
DEFAULT_MAX_MANIFEST_BYTES = 16 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
SOURCE_KINDS = ("memory", "learn", "review")
TEMP_SUFFIXES = (
    ".tmp",
    ".temp",
    ".swp",
    ".swo",
    ".bak",
    ".part",
    ".crdownload",
)


@dataclass(frozen=True)
class SourceSpec:
    kind: str
    label: str
    root: Path
    real_root: Path
    archive_prefix: str
    identity: str
    learn_shape: str | None = None


@dataclass(frozen=True)
class FileEntry:
    kind: str
    source_label: str
    source_path: Path
    relative_path: str
    archive_path: str
    size: int
    mtime_ns: int
    device: int
    inode: int


@dataclass
class ScanReport:
    files: list[FileEntry]
    skipped: dict[str, int]
    errors: list[str]
    memory_card_count: int = 0
    learn_projects: int = 0
    learn_raw_source_files: int = 0
    learn_raw_source_bytes: int = 0
    review_accounts: int = 0
    review_record_files: int = 0


def _result(
    ok: bool,
    kind: str,
    summary: str,
    *,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "kind": kind,
        "summary": summary,
        "errors": errors or [],
        "warnings": warnings or [],
        "data": data or {},
    }


def _print_payload(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))


def _render_markdown(payload: dict[str, Any]) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    lines = [
        "# Eva 数据备份",
        "",
        f"> {payload.get('summary') or ''}",
        "",
        f"- 状态：{'通过' if payload.get('ok') else '未通过'}",
    ]
    if data.get("scope"):
        lines.append(f"- 导出范围：{data.get('scope')}")
    included = data.get("included_kinds")
    if isinstance(included, list):
        lines.append(f"- 包含模块：{'、'.join(str(item) for item in included) or '无'}")
    if data.get("proposed_output_dir"):
        lines.append(f"- 拟输出目录：`{data.get('proposed_output_dir')}`")
    if data.get("plan_id"):
        lines.append(f"- 预检 ID：`{data.get('plan_id')}`")
    if data.get("archive_path"):
        lines.append(f"- 压缩包：`{data.get('archive_path')}`")
    if data.get("archive_sha256"):
        lines.append(f"- 压缩包 SHA-256：`{data.get('archive_sha256')}`")
    if isinstance(data.get("file_count"), int):
        lines.append(f"- 文件：{data.get('file_count')}")
    if isinstance(data.get("total_bytes"), int):
        lines.append(f"- 大小：{data.get('total_bytes')} 字节")

    memory = data.get("memory") if isinstance(data.get("memory"), dict) else None
    learn = data.get("learn") if isinstance(data.get("learn"), dict) else None
    review = data.get("review") if isinstance(data.get("review"), dict) else None
    if memory is not None:
        lines.extend(
            [
                "",
                "## Eva Memory",
                "",
                f"- 卡片：{int(memory.get('card_count') or 0)}",
                f"- 文件：{int(memory.get('files') or 0)}",
                f"- 大小：{int(memory.get('bytes') or 0)} 字节",
            ]
        )
    if learn is not None:
        lines.extend(
            [
                "",
                "## Eva Learn",
                "",
                f"- 学习项目：{int(learn.get('project_count') or 0)}",
                f"- 拟导出文件：{int(learn.get('files') or 0)}",
                f"- 拟导出大小：{int(learn.get('bytes') or 0)} 字节",
                f"- 原始资料文件：{int(learn.get('raw_source_files') or 0)}",
                f"- 原始资料大小：{int(learn.get('raw_source_bytes') or 0)} 字节",
                f"- 是否包含原始资料：{'否' if learn.get('raw_sources_excluded') else '是'}",
            ]
        )
    if review is not None:
        lines.extend(
            [
                "",
                "## Eva Review",
                "",
                f"- 账号：{int(review.get('account_count') or 0)}",
                f"- 复盘记录文件：{int(review.get('record_files') or 0)}",
                f"- 文件：{int(review.get('files') or 0)}",
                f"- 大小：{int(review.get('bytes') or 0)} 字节",
            ]
        )

    skipped = data.get("skipped") if isinstance(data.get("skipped"), dict) else {}
    nonzero_skipped = {
        str(key): int(value)
        for key, value in skipped.items()
        if isinstance(value, int) and value > 0
    }
    if nonzero_skipped:
        lines.extend(["", "## 安全跳过", ""])
        lines.extend(f"- {key}：{value}" for key, value in nonzero_skipped.items())

    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    if errors:
        lines.extend(["", "## 错误", ""])
        lines.extend(f"- {item}" for item in errors)
    if warnings:
        lines.extend(["", "## 提示", ""])
        lines.extend(f"- {item}" for item in warnings)
    if data.get("archive_path"):
        lines.extend(["", "这是未加密的本地备份，请自行妥善保管。"])
    return "\n".join(lines) + "\n"


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "markdown":
        print(_render_markdown(payload), end="")
    else:
        _print_payload(payload)


def _absolute_lexical_path(raw: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(raw))))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _normalized_collision_key(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def _safe_archive_path(value: str) -> str:
    if not value or "\x00" in value or "\\" in value:
        raise ValueError("archive path is empty or contains an unsafe character")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError("archive path must be a safe relative POSIX path")
    normalized = pure.as_posix()
    if normalized.startswith("/") or ":" in pure.parts[0]:
        raise ValueError("archive path must not be absolute")
    return normalized


def _safe_segment(value: str, fallback: str) -> str:
    text = unicodedata.normalize("NFC", value).strip()
    text = "".join(character if character.isprintable() else "-" for character in text)
    text = text.replace("/", "-").replace("\\", "-").replace("\x00", "-")
    text = text.strip(" .")
    if text in ("", ".", ".."):
        return fallback
    return text[:120]


def _is_hidden_name(name: str) -> bool:
    return name.startswith(".")


def _is_git_name(name: str) -> bool:
    return name.casefold() == ".git"


def _is_temp_name(name: str) -> bool:
    lowered = name.casefold()
    return (
        name.startswith(("~", ".#"))
        or name.endswith("~")
        or lowered.endswith(TEMP_SUFFIXES)
    )


def _is_log_name(name: str) -> bool:
    return name.casefold().endswith(".log")


def _is_log_directory_name(name: str) -> bool:
    return name.casefold() in {"log", "logs"}


def _is_cache_directory_name(name: str) -> bool:
    return name.casefold() in {
        "__pycache__",
        ".cache",
        "cache",
        "caches",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }


def _is_existing_backup_name(name: str) -> bool:
    lowered = name.casefold()
    return lowered.startswith("eva-data-backup-") and lowered.endswith(".zip")


def _looks_like_eva_source_repo(root: Path) -> bool:
    return all(
        (
            (root / "skills" / "eva" / "SKILL.md").is_file(),
            (root / "skills" / "eva-shared" / "SKILL.md").is_file(),
            (root / ".claude-plugin" / "marketplace.json").is_file(),
        )
    )


def _looks_like_distribution_bundle(root: Path) -> bool:
    return _is_regular_no_follow(root / "SKILL.md") and _is_regular_no_follow(
        root / "modules" / "eva-shared" / "support.md"
    )


def _looks_like_skill_source_directory(root: Path) -> bool:
    if not _is_regular_no_follow(root / "SKILL.md"):
        return False
    return any(
        _is_directory_no_follow(root / child)
        for child in ("agents", "references", "scripts", "assets", "modules")
    )


def _path_lstat(path: Path) -> os.stat_result:
    return path.lstat()


def _is_regular_no_follow(path: Path) -> bool:
    try:
        return stat.S_ISREG(_path_lstat(path).st_mode)
    except OSError:
        return False


def _is_directory_no_follow(path: Path) -> bool:
    try:
        return stat.S_ISDIR(_path_lstat(path).st_mode)
    except OSError:
        return False


def _learn_root_shape(root: Path) -> str | None:
    """Return ``project`` or ``container`` for a narrowly recognizable Learn root."""
    if _is_regular_no_follow(root / "00-学习进度.md"):
        return "project"
    if root.name.casefold() == "eva-learn":
        return "container"
    try:
        with os.scandir(root) as iterator:
            entries = sorted(iterator, key=lambda item: item.name.casefold())
    except OSError:
        return None
    for entry in entries:
        try:
            entry_stat = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if not stat.S_ISDIR(entry_stat.st_mode) or stat.S_ISLNK(entry_stat.st_mode):
            continue
        if _is_regular_no_follow(Path(entry.path) / "00-学习进度.md"):
            return "container"
    return None


def _scope_kinds(scope: str, custom_includes: Iterable[str]) -> tuple[str, ...]:
    if scope == "memory":
        return ("memory",)
    if scope == "complete":
        return SOURCE_KINDS
    selected = tuple(dict.fromkeys(custom_includes))
    return selected


def _source_identity(real_root: Path) -> str:
    return hashlib.sha256(os.fsencode(str(real_root))).hexdigest()[:20]


def _discover_sources(
    *,
    project_root: Path,
    included_kinds: tuple[str, ...],
    extra_learn_paths: list[Path],
) -> tuple[list[SourceSpec], list[str], list[str]]:
    sources: list[SourceSpec] = []
    warnings: list[str] = []
    errors: list[str] = []
    seen_real_roots: list[Path] = []

    def add_source(
        *,
        kind: str,
        label: str,
        root: Path,
        archive_prefix: str,
        explicit: bool,
        learn_shape: str | None = None,
    ) -> None:
        try:
            root_stat = _path_lstat(root)
        except FileNotFoundError:
            message = f"{kind}:{label} 不存在，未纳入备份。"
            if explicit:
                errors.append(message)
            else:
                warnings.append(message)
            return
        except OSError as exc:
            errors.append(f"{kind}:{label} 无法读取目录状态：{exc.__class__.__name__}")
            return
        if stat.S_ISLNK(root_stat.st_mode):
            message = f"{kind}:{label} 是符号链接，已拒绝跟随。"
            if explicit:
                errors.append(message)
            else:
                warnings.append(message)
            return
        if not stat.S_ISDIR(root_stat.st_mode):
            errors.append(f"{kind}:{label} 不是目录。")
            return
        if _is_hidden_name(root.name):
            errors.append(f"{kind}:{label} 是隐藏目录，不能作为备份根。")
            return
        if _looks_like_skill_source_directory(root):
            message = f"{kind}:{label} 看起来是 Skill 源码目录，已拒绝纳入数据备份。"
            if explicit:
                errors.append(message)
            else:
                warnings.append(message)
            return
        try:
            real_root = root.resolve(strict=True)
        except OSError as exc:
            errors.append(f"{kind}:{label} 无法解析真实路径：{exc.__class__.__name__}")
            return
        for previous in seen_real_roots:
            if real_root == previous or _is_relative_to(real_root, previous):
                warnings.append(f"{kind}:{label} 与已发现目录重复，已去重。")
                return
            if _is_relative_to(previous, real_root):
                errors.append(f"{kind}:{label} 包含已发现的数据根，已拒绝扩大扫描范围。")
                return
        seen_real_roots.append(real_root)
        sources.append(
            SourceSpec(
                kind=kind,
                label=label,
                root=root,
                real_root=real_root,
                archive_prefix=_safe_archive_path(archive_prefix),
                identity=_source_identity(real_root),
                learn_shape=learn_shape,
            )
        )

    def add_learn_root(
        *,
        label: str,
        root: Path,
        archive_prefix: str,
        explicit: bool,
    ) -> None:
        try:
            root_stat = _path_lstat(root)
        except FileNotFoundError:
            message = f"learn:{label} 不存在，未纳入备份。"
            if explicit:
                errors.append(message)
            else:
                warnings.append(message)
            return
        except OSError as exc:
            errors.append(f"learn:{label} 无法读取目录状态：{exc.__class__.__name__}")
            return
        if stat.S_ISLNK(root_stat.st_mode):
            message = f"learn:{label} 是符号链接，已拒绝跟随。"
            if explicit:
                errors.append(message)
            else:
                warnings.append(message)
            return
        if not stat.S_ISDIR(root_stat.st_mode):
            errors.append(f"learn:{label} 不是目录。")
            return
        shape = _learn_root_shape(root)
        if shape is None:
            message = f"learn:{label} 不是可识别的 Eva Learn 项目或容器。"
            if explicit:
                errors.append(message)
            else:
                warnings.append(message)
            return
        if shape == "project":
            project_name = _safe_segment(root.name, "learn-project")
            add_source(
                kind="learn",
                label=f"{label}/{project_name}",
                root=root,
                archive_prefix=f"{archive_prefix}/{project_name}",
                explicit=explicit,
                learn_shape="project",
            )
            return

        valid_projects: list[Path] = []
        try:
            with os.scandir(root) as iterator:
                entries = sorted(iterator, key=lambda item: item.name.casefold())
        except OSError as exc:
            errors.append(f"learn:{label} 无法枚举学习项目：{exc.__class__.__name__}")
            return
        for entry in entries:
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                errors.append(
                    f"learn:{label} 无法读取直接子项目 {entry.name}：{exc.__class__.__name__}"
                )
                return
            if stat.S_ISLNK(entry_stat.st_mode):
                warnings.append(f"learn:{label}/{entry.name} 是符号链接，已跳过。")
                continue
            if not stat.S_ISDIR(entry_stat.st_mode):
                continue
            if _is_hidden_name(entry.name) or _is_temp_name(entry.name):
                continue
            project_root = Path(entry.path)
            if _is_regular_no_follow(project_root / "00-学习进度.md"):
                valid_projects.append(project_root)
        if not valid_projects:
            warnings.append(f"learn:{label} 没有包含 00-学习进度.md 的有效直接子项目。")
            return
        for project_root in valid_projects:
            project_name = _safe_segment(project_root.name, "learn-project")
            add_source(
                kind="learn",
                label=f"{label}/{project_name}",
                root=project_root,
                archive_prefix=f"{archive_prefix}/{project_name}",
                explicit=explicit,
                learn_shape="project",
            )

    if "memory" in included_kinds:
        add_source(
            kind="memory",
            label="current-project",
            root=project_root / "eva-memory",
            archive_prefix="eva-memory",
            explicit=False,
        )

    if "review" in included_kinds:
        review_root = project_root / "eva-review"
        try:
            review_stat = _path_lstat(review_root)
        except FileNotFoundError:
            add_source(
                kind="review",
                label="current-project",
                root=review_root,
                archive_prefix="eva-review",
                explicit=False,
            )
        except OSError as exc:
            errors.append(
                f"review:current-project 无法读取目录状态：{exc.__class__.__name__}"
            )
        else:
            settings_path = review_root / "00_review-settings.md"
            if not stat.S_ISDIR(review_stat.st_mode) or stat.S_ISLNK(review_stat.st_mode):
                add_source(
                    kind="review",
                    label="current-project",
                    root=review_root,
                    archive_prefix="eva-review",
                    explicit=False,
                )
            elif not _is_regular_no_follow(settings_path):
                warnings.append(
                    "review:current-project 缺少正式授权设置 00_review-settings.md，"
                    "未纳入数据备份。"
                )
            else:
                add_source(
                    kind="review",
                    label="current-project",
                    root=review_root,
                    archive_prefix="eva-review",
                    explicit=False,
                )

    if "learn" in included_kinds:
        current_learn = project_root / "eva-learn"
        add_learn_root(
            label="current-project",
            root=current_learn,
            archive_prefix="eva-learn/current-project",
            explicit=False,
        )
        documents_learn = _absolute_lexical_path(Path.home() / "Documents" / "eva-learn")
        add_learn_root(
            label="documents-default",
            root=documents_learn,
            archive_prefix="eva-learn/documents-default",
            explicit=False,
        )
        for index, extra_root in enumerate(extra_learn_paths, start=1):
            label = f"user-selected-{index:02d}"
            prefix = f"eva-learn/{label}"
            add_learn_root(
                label=label,
                root=extra_root,
                archive_prefix=prefix,
                explicit=True,
            )

    return sources, warnings, errors


def _empty_skipped() -> dict[str, int]:
    return {
        "symlinks": 0,
        "hidden": 0,
        "temporary": 0,
        "logs": 0,
        "cache_directories": 0,
        "existing_backups": 0,
        "skill_source_directories": 0,
        "git": 0,
        "special": 0,
        "outside_root": 0,
    }


def _open_readonly_no_follow(path: Path) -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(path, flags)


def _probe_readable(path: Path, planned: os.stat_result) -> str | None:
    try:
        descriptor = _open_readonly_no_follow(path)
    except OSError as exc:
        return f"{exc.__class__.__name__}"
    try:
        current = os.fstat(descriptor)
        if not stat.S_ISREG(current.st_mode):
            return "not-regular-after-open"
        if (current.st_dev, current.st_ino) != (planned.st_dev, planned.st_ino):
            return "file-changed-during-scan"
    finally:
        os.close(descriptor)
    return None


def _scan_source(
    source: SourceSpec,
    *,
    max_files: int,
    max_bytes: int,
    exclude_learn_sources: bool,
) -> ScanReport:
    files: list[FileEntry] = []
    skipped = _empty_skipped()
    errors: list[str] = []
    archive_collision_keys: set[str] = set()
    total_bytes = 0
    scanned_regular_files = 0
    scanned_regular_bytes = 0
    memory_card_count = 0
    learn_raw_source_files = 0
    learn_raw_source_bytes = 0
    review_accounts: set[str] = set()
    review_record_files = 0

    def is_learn_raw_source(parts: tuple[str, ...]) -> bool:
        return (
            source.kind == "learn"
            and source.learn_shape == "project"
            and len(parts) >= 3
            and parts[0] == "sources"
            and parts[1] == "原始资料"
        )

    def walk(current: Path, relative_parts: tuple[str, ...]) -> None:
        nonlocal total_bytes
        nonlocal scanned_regular_files, scanned_regular_bytes
        nonlocal memory_card_count
        nonlocal learn_raw_source_files, learn_raw_source_bytes
        nonlocal review_record_files
        if errors:
            return
        try:
            with os.scandir(current) as iterator:
                entries = sorted(iterator, key=lambda item: item.name.casefold())
        except OSError as exc:
            errors.append(
                f"{source.kind}:{source.label} 无法读取目录 {PurePosixPath(*relative_parts).as_posix() or '.'}："
                f"{exc.__class__.__name__}"
            )
            return

        for entry in entries:
            name = entry.name
            next_parts = relative_parts + (name,)
            relative_posix = PurePosixPath(*next_parts).as_posix()
            if _is_git_name(name):
                skipped["git"] += 1
                continue
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError as exc:
                errors.append(
                    f"{source.kind}:{source.label} 无法读取 {relative_posix}：{exc.__class__.__name__}"
                )
                return
            mode = entry_stat.st_mode
            if stat.S_ISLNK(mode):
                skipped["symlinks"] += 1
                continue
            path = Path(entry.path)
            if stat.S_ISDIR(mode):
                if _is_log_directory_name(name):
                    skipped["logs"] += 1
                    continue
                if _is_cache_directory_name(name):
                    skipped["cache_directories"] += 1
                    continue
                if _is_hidden_name(name):
                    skipped["hidden"] += 1
                    continue
                if _is_temp_name(name):
                    skipped["temporary"] += 1
                    continue
                if _looks_like_skill_source_directory(path):
                    skipped["skill_source_directories"] += 1
                    continue
                try:
                    real_directory = path.resolve(strict=True)
                except OSError as exc:
                    errors.append(
                        f"{source.kind}:{source.label} 无法解析目录 {relative_posix}：{exc.__class__.__name__}"
                    )
                    return
                if not _is_relative_to(real_directory, source.real_root):
                    skipped["outside_root"] += 1
                    continue
                if (
                    source.kind == "review"
                    and len(next_parts) == 2
                    and next_parts[0] == "accounts"
                ):
                    review_accounts.add(next_parts[1])
                walk(path, next_parts)
                if errors:
                    return
                continue
            if _is_hidden_name(name):
                skipped["hidden"] += 1
                continue
            if _is_temp_name(name):
                skipped["temporary"] += 1
                continue
            if _is_log_name(name):
                skipped["logs"] += 1
                continue
            if _is_existing_backup_name(name):
                skipped["existing_backups"] += 1
                continue
            if not stat.S_ISREG(mode):
                skipped["special"] += 1
                continue

            try:
                real_file = path.resolve(strict=True)
            except OSError as exc:
                errors.append(
                    f"{source.kind}:{source.label} 无法解析文件 {relative_posix}：{exc.__class__.__name__}"
                )
                return
            if not _is_relative_to(real_file, source.real_root):
                skipped["outside_root"] += 1
                continue

            raw_source = is_learn_raw_source(next_parts)
            if raw_source:
                learn_raw_source_files += 1
                learn_raw_source_bytes += int(entry_stat.st_size)
                if exclude_learn_sources:
                    continue

            read_error = _probe_readable(path, entry_stat)
            if read_error:
                errors.append(
                    f"{source.kind}:{source.label} 普通文件 {relative_posix} 无法安全读取：{read_error}"
                )
                return

            scanned_regular_files += 1
            scanned_regular_bytes += int(entry_stat.st_size)
            if scanned_regular_files > max_files:
                errors.append(f"{source.kind}:{source.label} 扫描文件数量超过上限 {max_files}。")
                return
            if scanned_regular_bytes > max_bytes:
                errors.append(f"{source.kind}:{source.label} 扫描数据量超过上限 {max_bytes} 字节。")
                return

            try:
                archive_path = _safe_archive_path(
                    PurePosixPath(source.archive_prefix, *next_parts).as_posix()
                )
            except ValueError as exc:
                errors.append(
                    f"{source.kind}:{source.label} 路径无法安全写入 ZIP "
                    f"{relative_posix}：{exc}"
                )
                return
            collision_key = _normalized_collision_key(archive_path)
            if collision_key in archive_collision_keys:
                errors.append(
                    f"{source.kind}:{source.label} 存在大小写或 Unicode 冲突路径：{relative_posix}"
                )
                return
            archive_collision_keys.add(collision_key)
            files.append(
                FileEntry(
                    kind=source.kind,
                    source_label=source.label,
                    source_path=path,
                    relative_path=relative_posix,
                    archive_path=archive_path,
                    size=int(entry_stat.st_size),
                    mtime_ns=int(entry_stat.st_mtime_ns),
                    device=int(entry_stat.st_dev),
                    inode=int(entry_stat.st_ino),
                )
            )
            total_bytes += int(entry_stat.st_size)
            if (
                source.kind == "memory"
                and path.suffix.casefold() == ".md"
                and path.name.casefold() != "index.md"
            ):
                memory_card_count += 1
            if (
                source.kind == "review"
                and len(next_parts) >= 4
                and next_parts[0] == "accounts"
                and next_parts[2] == "records"
            ):
                review_record_files += 1
            if len(files) > max_files:
                errors.append(f"{source.kind}:{source.label} 文件数量超过上限 {max_files}。")
                return
            if total_bytes > max_bytes:
                errors.append(f"{source.kind}:{source.label} 数据量超过上限 {max_bytes} 字节。")
                return

    walk(source.root, ())
    return ScanReport(
        files=sorted(files, key=lambda item: _normalized_collision_key(item.archive_path)),
        skipped=skipped,
        errors=errors,
        memory_card_count=memory_card_count,
        learn_projects=1 if source.kind == "learn" else 0,
        learn_raw_source_files=learn_raw_source_files,
        learn_raw_source_bytes=learn_raw_source_bytes,
        review_accounts=len(review_accounts),
        review_record_files=review_record_files,
    )


def _plan_id(
    *,
    scope: str,
    included_kinds: tuple[str, ...],
    sources: list[SourceSpec],
    files: list[FileEntry],
    exclude_learn_sources: bool,
    proposed_output_dir: Path,
) -> str:
    payload = {
        "format": BACKUP_FORMAT_VERSION,
        "scope": scope,
        "included_kinds": list(included_kinds),
        "exclude_learn_sources": exclude_learn_sources,
        "proposed_output_dir": str(proposed_output_dir),
        "sources": [
            {
                "kind": source.kind,
                "label": source.label,
                "identity": source.identity,
                "archive_prefix": source.archive_prefix,
            }
            for source in sources
        ],
        "files": [
            {
                "path": entry.archive_path,
                "size": entry.size,
                "mtime_ns": entry.mtime_ns,
                "device": entry.device,
                "inode": entry.inode,
            }
            for entry in files
        ],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _build_plan(
    *,
    project_root: Path,
    scope: str,
    custom_includes: list[str],
    extra_learn_paths: list[Path],
    exclude_learn_sources: bool,
    proposed_output_dir: Path,
    max_files: int,
    max_bytes: int,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        project_stat = _path_lstat(project_root)
    except FileNotFoundError:
        return _result(False, "data-export-preview", "当前项目目录不存在。", errors=["project root does not exist"])
    except OSError as exc:
        return _result(
            False,
            "data-export-preview",
            "无法读取当前项目目录。",
            errors=[f"project root: {exc.__class__.__name__}"],
        )
    if stat.S_ISLNK(project_stat.st_mode):
        return _result(False, "data-export-preview", "当前项目目录是符号链接，已拒绝扫描。")
    if not stat.S_ISDIR(project_stat.st_mode):
        return _result(False, "data-export-preview", "当前项目路径不是目录。")
    if _looks_like_eva_source_repo(project_root):
        return _result(
            False,
            "data-export-preview",
            "已拒绝把 Eva-skill 源码仓库当作用户运行项目。",
        )
    if _looks_like_distribution_bundle(project_root):
        return _result(
            False,
            "data-export-preview",
            "已拒绝把 SkillHub 或 RedSkill 发行包当作用户运行项目。",
        )
    if _looks_like_skill_source_directory(project_root):
        return _result(
            False,
            "data-export-preview",
            "已拒绝把 Skill 安装或源码目录当作用户运行项目。",
        )

    if scope != "custom" and custom_includes:
        errors.append("--include 只能和 --scope custom 一起使用")
    included_kinds = _scope_kinds(scope, custom_includes)
    if scope == "custom" and not included_kinds:
        errors.append("custom scope 至少需要一个 --include")
    if len(set(custom_includes)) != len(custom_includes):
        errors.append("include scope contains duplicate values")
    if any(kind not in SOURCE_KINDS for kind in included_kinds):
        errors.append("include scope contains an unsupported value")
    if extra_learn_paths and "learn" not in included_kinds:
        errors.append("--learn-path 只能在导出范围包含 learn 时使用")
    if exclude_learn_sources and scope != "custom":
        errors.append("--exclude-learn-sources 只能和 --scope custom 一起使用")
    if exclude_learn_sources and "learn" not in included_kinds:
        errors.append("--exclude-learn-sources 要求自定义范围包含 learn")
    if errors:
        return _result(False, "data-export-preview", "导出范围无效。", errors=errors)

    selection = {
        "scope": scope,
        "included_kinds": list(included_kinds),
        "exclude_learn_sources": bool(exclude_learn_sources),
    }
    output_error = _proposed_output_directory_error(proposed_output_dir)
    if output_error:
        return _result(
            False,
            "data-export-preview",
            "目标目录当前不可用于备份，请先选择一个可写目录。",
            errors=[output_error],
            data={
                "scope": scope,
                "included_kinds": list(included_kinds),
                "selection": selection,
                "proposed_output_dir": str(proposed_output_dir),
                "will_write": False,
            },
        )

    sources, discovery_warnings, discovery_errors = _discover_sources(
        project_root=project_root,
        included_kinds=included_kinds,
        extra_learn_paths=extra_learn_paths,
    )
    warnings.extend(discovery_warnings)
    errors.extend(discovery_errors)
    if sources and _output_is_inside_source(proposed_output_dir, sources):
        errors.append("目标目录位于备份源内部，请选择其他目录")

    all_files: list[FileEntry] = []
    source_rows: list[dict[str, Any]] = []
    aggregate_skipped = _empty_skipped()
    global_archive_keys: set[str] = set()
    total_bytes = 0
    memory_stats = {"card_count": 0, "files": 0, "bytes": 0}
    learn_stats = {
        "project_count": 0,
        "files": 0,
        "bytes": 0,
        "raw_source_files": 0,
        "raw_source_bytes": 0,
        "raw_sources_excluded": bool(exclude_learn_sources),
    }
    review_stats = {
        "account_count": 0,
        "record_files": 0,
        "files": 0,
        "bytes": 0,
    }

    for source in sources:
        remaining_files = max_files - len(all_files)
        remaining_bytes = max_bytes - total_bytes
        if remaining_files <= 0 or remaining_bytes < 0:
            errors.append("备份总量超过安全上限。")
            break
        report = _scan_source(
            source,
            max_files=remaining_files,
            max_bytes=remaining_bytes,
            exclude_learn_sources=exclude_learn_sources,
        )
        errors.extend(report.errors)
        for key, count in report.skipped.items():
            aggregate_skipped[key] += count
        if report.errors:
            continue
        source_bytes = sum(entry.size for entry in report.files)
        if source.kind == "memory":
            memory_stats["card_count"] += report.memory_card_count
            memory_stats["files"] += len(report.files)
            memory_stats["bytes"] += source_bytes
        elif source.kind == "learn":
            learn_stats["project_count"] += report.learn_projects
            learn_stats["files"] += len(report.files)
            learn_stats["bytes"] += source_bytes
            learn_stats["raw_source_files"] += report.learn_raw_source_files
            learn_stats["raw_source_bytes"] += report.learn_raw_source_bytes
        elif source.kind == "review":
            review_stats["account_count"] += report.review_accounts
            review_stats["record_files"] += report.review_record_files
            review_stats["files"] += len(report.files)
            review_stats["bytes"] += source_bytes
        for entry in report.files:
            collision_key = _normalized_collision_key(entry.archive_path)
            if collision_key in global_archive_keys:
                errors.append(f"不同数据源产生了冲突归档路径：{entry.archive_path}")
                break
            global_archive_keys.add(collision_key)
            all_files.append(entry)
        source_rows.append(
            {
                "kind": source.kind,
                "label": source.label,
                "archive_prefix": source.archive_prefix,
                "file_count": len(report.files),
                "total_bytes": source_bytes,
                "learn_shape": source.learn_shape,
            }
        )
        total_bytes += source_bytes

    all_files.sort(key=lambda item: _normalized_collision_key(item.archive_path))
    if len(all_files) > max_files:
        errors.append(f"备份总文件数超过上限 {max_files}。")
    if total_bytes > max_bytes:
        errors.append(f"备份总数据量超过上限 {max_bytes} 字节。")
    if errors:
        return _result(
            False,
            "data-export-preview",
            "备份预检未通过，没有生成压缩包。",
            errors=errors,
            warnings=warnings,
            data={
                "scope": scope,
                "included_kinds": list(included_kinds),
                "selection": selection,
                "sources": source_rows,
                "file_count": len(all_files),
                "total_bytes": total_bytes,
                "memory": memory_stats,
                "learn": learn_stats,
                "review": review_stats,
                "proposed_output_dir": str(proposed_output_dir),
                "skipped": aggregate_skipped,
                "will_write": False,
            },
        )
    if not all_files:
        return _result(
            False,
            "data-export-preview",
            "所选范围没有可导出的已保存文件，没有生成压缩包。",
            warnings=warnings,
            data={
                "scope": scope,
                "included_kinds": list(included_kinds),
                "selection": selection,
                "sources": source_rows,
                "file_count": 0,
                "total_bytes": 0,
                "memory": memory_stats,
                "learn": learn_stats,
                "review": review_stats,
                "proposed_output_dir": str(proposed_output_dir),
                "skipped": aggregate_skipped,
                "will_write": False,
            },
        )

    plan_id = _plan_id(
        scope=scope,
        included_kinds=included_kinds,
        sources=sources,
        files=all_files,
        exclude_learn_sources=exclude_learn_sources,
        proposed_output_dir=proposed_output_dir,
    )
    return _result(
        True,
        "data-export-preview",
        f"备份预检完成：{len(all_files)} 个文件，共 {total_bytes} 字节。",
        warnings=warnings,
        data={
            "scope": scope,
            "included_kinds": list(included_kinds),
            "selection": selection,
            "sources": source_rows,
            "file_count": len(all_files),
            "total_bytes": total_bytes,
            "memory": memory_stats,
            "learn": learn_stats,
            "review": review_stats,
            "proposed_output_dir": str(proposed_output_dir),
            "skipped": aggregate_skipped,
            "plan_id": plan_id,
            "will_write": False,
            "_sources": sources,
            "_files": all_files,
        },
    )


def _public_plan(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload.get("data") or {})
    data.pop("_sources", None)
    data.pop("_files", None)
    return {
        **payload,
        "data": data,
    }


def _zip_datetime(timestamp: float) -> tuple[int, int, int, int, int, int]:
    parts = time.localtime(timestamp)
    year = min(max(parts.tm_year, 1980), 2107)
    return (year, parts.tm_mon, parts.tm_mday, parts.tm_hour, parts.tm_min, parts.tm_sec)


def _zip_info(archive_path: str, timestamp: float) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(_safe_archive_path(archive_path), date_time=_zip_datetime(timestamp))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    return info


def _write_bytes_entry(
    archive: zipfile.ZipFile,
    archive_path: str,
    content: bytes,
    *,
    timestamp: float,
) -> dict[str, Any]:
    digest = hashlib.sha256(content).hexdigest()
    archive.writestr(_zip_info(archive_path, timestamp), content)
    return {
        "path": _safe_archive_path(archive_path),
        "kind": "metadata",
        "source_label": "generated",
        "size": len(content),
        "sha256": digest,
    }


def _write_source_entry(
    archive: zipfile.ZipFile,
    entry: FileEntry,
    *,
    backup_root: str,
) -> dict[str, Any]:
    try:
        descriptor = _open_readonly_no_follow(entry.source_path)
    except OSError as exc:
        raise OSError(
            f"cannot safely open {entry.kind}:{entry.source_label}/{entry.relative_path}: "
            f"{exc.__class__.__name__}"
        ) from exc
    digest = hashlib.sha256()
    copied = 0
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise OSError("source is no longer a regular file")
        expected_identity = (entry.device, entry.inode, entry.size, entry.mtime_ns)
        current_identity = (
            int(opened_stat.st_dev),
            int(opened_stat.st_ino),
            int(opened_stat.st_size),
            int(opened_stat.st_mtime_ns),
        )
        if current_identity != expected_identity:
            raise OSError("source changed after preview")
        with os.fdopen(descriptor, "rb", closefd=True) as source_handle:
            descriptor = -1
            rooted_archive_path = _safe_archive_path(
                PurePosixPath(backup_root, entry.archive_path).as_posix()
            )
            with archive.open(
                _zip_info(rooted_archive_path, opened_stat.st_mtime),
                mode="w",
                force_zip64=True,
            ) as destination:
                while True:
                    chunk = source_handle.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    destination.write(chunk)
                    digest.update(chunk)
                    copied += len(chunk)
            closed_stat = os.fstat(source_handle.fileno())
            if (
                int(closed_stat.st_size) != entry.size
                or int(closed_stat.st_mtime_ns) != entry.mtime_ns
            ):
                raise OSError("source changed while being archived")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if copied != entry.size:
        raise OSError("source byte count changed while being archived")
    return {
        "path": rooted_archive_path,
        "kind": entry.kind,
        "source_label": entry.source_label,
        "size": copied,
        "sha256": digest.hexdigest(),
    }


def _readme_bytes(
    *,
    created_at: str,
    scope: str,
    included_kinds: tuple[str, ...],
) -> bytes:
    kinds = "、".join(included_kinds)
    text = f"""# Eva 数据备份

- 备份格式版本：{BACKUP_FORMAT_VERSION}
- Eva-skill 版本：{SCRIPT_VERSION}
- 生成时间：{created_at}
- 导出范围：{scope}
- 包含数据：{kinds}

本压缩包是用户主动确认后生成的本地备份，不会联网上传。
它没有加密，请妥善保管。`MANIFEST.json` 保存相对路径、文件大小和 SHA-256，
不包含电脑上的绝对来源路径。解压或迁移前可再次运行 Eva 的备份校验。
"""
    return text.encode("utf-8")


def _manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")


def _archive_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_info_is_regular(info: zipfile.ZipInfo) -> bool:
    """Accept only regular Unix file entries produced by this backup format."""
    if info.is_dir() or info.create_system != 3:
        return False
    unix_mode = (int(info.external_attr) >> 16) & 0xFFFF
    return stat.S_ISREG(unix_mode)


def _validate_zip(path: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if path.is_symlink():
        return _result(False, "data-export-verify", "压缩包是符号链接，已拒绝验证。")
    try:
        path_stat = path.lstat()
    except FileNotFoundError:
        return _result(False, "data-export-verify", "压缩包不存在。")
    except OSError as exc:
        return _result(
            False,
            "data-export-verify",
            "无法读取压缩包。",
            errors=[exc.__class__.__name__],
        )
    if not stat.S_ISREG(path_stat.st_mode):
        return _result(False, "data-export-verify", "待验证路径不是普通文件。")
    if not zipfile.is_zipfile(path):
        return _result(False, "data-export-verify", "文件不是有效 ZIP。")

    manifest: dict[str, Any] | None = None
    actual_names: list[str] = []
    archive_root: str | None = None
    manifest_path: str | None = None
    readme_path: str | None = None
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            if len(infos) > DEFAULT_MAX_FILES:
                errors.append(
                    f"ZIP entry 数量超过安全上限 {DEFAULT_MAX_FILES}"
                )
            declared_uncompressed = 0
            for info in infos:
                if info.file_size < 0 or info.compress_size < 0:
                    errors.append(f"ZIP entry 大小元数据无效：{info.filename!r}")
                    continue
                declared_uncompressed += int(info.file_size)
                if info.file_size > DEFAULT_MAX_BYTES:
                    errors.append(f"ZIP entry 超过单包字节上限：{info.filename!r}")
                if (
                    info.file_size > CHUNK_SIZE
                    and info.compress_size > 0
                    and info.file_size > info.compress_size * 1000
                ):
                    errors.append(f"ZIP entry 压缩比异常：{info.filename!r}")
            if declared_uncompressed > DEFAULT_MAX_BYTES:
                errors.append(
                    f"ZIP 解压后总量超过安全上限 {DEFAULT_MAX_BYTES} 字节"
                )
            if errors:
                return _result(
                    False,
                    "data-export-verify",
                    "压缩包验证失败。",
                    errors=errors,
                    warnings=warnings,
                )

            exact_names: set[str] = set()
            collision_keys: set[str] = set()
            for info in infos:
                try:
                    safe_name = _safe_archive_path(info.filename)
                except ValueError as exc:
                    errors.append(f"ZIP entry 路径不安全：{info.filename!r}（{exc}）")
                    continue
                collision_key = _normalized_collision_key(safe_name)
                if not _zip_info_is_regular(info):
                    errors.append(
                        f"ZIP entry 不是普通文件或缺少受支持的文件类型：{safe_name}"
                    )
                if safe_name in exact_names:
                    errors.append(f"ZIP 包含重复 entry：{safe_name}")
                if collision_key in collision_keys:
                    errors.append(f"ZIP 包含大小写或 Unicode 冲突 entry：{safe_name}")
                exact_names.add(safe_name)
                collision_keys.add(collision_key)
                actual_names.append(safe_name)
            if errors:
                return _result(
                    False,
                    "data-export-verify",
                    "压缩包验证失败。",
                    errors=errors,
                    warnings=warnings,
                )
            top_levels = {
                PurePosixPath(name).parts[0]
                for name in exact_names
                if PurePosixPath(name).parts
            }
            if len(top_levels) != 1:
                errors.append("ZIP 必须只有一个顶层备份目录")
            else:
                archive_root = next(iter(top_levels))
                if not archive_root.startswith(f"{DEFAULT_ARCHIVE_PREFIX}-"):
                    errors.append("ZIP 顶层目录名称不是 Eva 数据备份目录")
                manifest_path = _safe_archive_path(
                    PurePosixPath(archive_root, MANIFEST_NAME).as_posix()
                )
                readme_path = _safe_archive_path(
                    PurePosixPath(archive_root, README_NAME).as_posix()
                )
            if manifest_path is None or manifest_path not in exact_names:
                errors.append(f"ZIP 缺少顶层目录内的 {MANIFEST_NAME}")
            else:
                try:
                    manifest_info = archive.getinfo(manifest_path)
                    if manifest_info.file_size > DEFAULT_MAX_MANIFEST_BYTES:
                        errors.append(
                            "Manifest 超过安全读取上限 "
                            f"{DEFAULT_MAX_MANIFEST_BYTES} 字节"
                        )
                    else:
                        raw_manifest = archive.read(manifest_info)
                        loaded = json.loads(raw_manifest.decode("utf-8"))
                        if isinstance(loaded, dict):
                            manifest = loaded
                        else:
                            errors.append("Manifest 不是 JSON 对象")
                except (
                    OSError,
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                    KeyError,
                    RuntimeError,
                    zipfile.BadZipFile,
                ) as exc:
                    errors.append(f"Manifest 无法读取：{exc.__class__.__name__}")
            if readme_path is None or readme_path not in exact_names:
                errors.append(f"ZIP 缺少顶层目录内的 {README_NAME}")

            if manifest is not None:
                if manifest.get("format_version") != BACKUP_FORMAT_VERSION:
                    errors.append("Manifest 格式版本不受支持")
                manifest_eva_version = manifest.get("eva_skill_version")
                if (
                    not isinstance(manifest_eva_version, str)
                    or re.fullmatch(
                        r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?",
                        manifest_eva_version,
                    )
                    is None
                ):
                    errors.append("Manifest eva_skill_version 无效")
                if manifest.get("archive_root") != archive_root:
                    errors.append("Manifest archive_root 与 ZIP 顶层目录不一致")
                manifest_scope = manifest.get("scope")
                manifest_kinds = manifest.get("included_kinds")
                if manifest_scope not in {"memory", "complete", "custom"}:
                    errors.append("Manifest scope 无效")
                if (
                    not isinstance(manifest_kinds, list)
                    or not manifest_kinds
                    or any(
                        not isinstance(kind, str) or kind not in SOURCE_KINDS
                        for kind in manifest_kinds
                    )
                    or len(set(manifest_kinds)) != len(manifest_kinds)
                ):
                    errors.append("Manifest included_kinds 无效")
                    normalized_manifest_kinds: list[str] = []
                else:
                    normalized_manifest_kinds = list(manifest_kinds)
                    if manifest_scope == "memory" and normalized_manifest_kinds != ["memory"]:
                        errors.append("memory 范围只能包含 memory")
                    if (
                        manifest_scope == "complete"
                        and normalized_manifest_kinds != list(SOURCE_KINDS)
                    ):
                        errors.append(
                            "complete 范围必须声明 memory、learn、review"
                        )
                selection = manifest.get("selection")
                exclude_learn_sources = False
                if not isinstance(selection, dict):
                    errors.append("Manifest selection 必须是对象")
                else:
                    if selection.get("scope") != manifest.get("scope"):
                        errors.append("Manifest selection.scope 与 scope 不一致")
                    if selection.get("included_kinds") != manifest.get("included_kinds"):
                        errors.append(
                            "Manifest selection.included_kinds 与 included_kinds 不一致"
                        )
                    if not isinstance(selection.get("exclude_learn_sources"), bool):
                        errors.append(
                            "Manifest selection.exclude_learn_sources 必须是布尔值"
                        )
                    else:
                        exclude_learn_sources = bool(
                            selection.get("exclude_learn_sources")
                        )
                    if exclude_learn_sources and (
                        manifest_scope != "custom"
                        or "learn" not in normalized_manifest_kinds
                    ):
                        errors.append(
                            "排除 Learn 原始资料只适用于包含 learn 的 custom 范围"
                        )
                rows = manifest.get("files")
                if not isinstance(rows, list):
                    errors.append("Manifest files 必须是数组")
                    rows = []
                expected_names: set[str] = {str(manifest_path)}
                expected_total = 0
                data_row_count = 0
                for index, row in enumerate(rows):
                    if not isinstance(row, dict):
                        errors.append(f"Manifest files[{index}] 不是对象")
                        continue
                    row_path = row.get("path")
                    row_size = row.get("size")
                    row_digest = row.get("sha256")
                    if not isinstance(row_path, str):
                        errors.append(f"Manifest files[{index}] 缺少路径")
                        continue
                    try:
                        safe_row_path = _safe_archive_path(row_path)
                    except ValueError:
                        errors.append(f"Manifest files[{index}] 路径不安全")
                        continue
                    if archive_root is not None and not safe_row_path.startswith(
                        f"{archive_root}/"
                    ):
                        errors.append(f"Manifest 文件不在顶层备份目录内：{safe_row_path}")
                        continue
                    if safe_row_path == manifest_path:
                        errors.append("Manifest 不能把自身列入逐文件哈希")
                        continue
                    parts = PurePosixPath(safe_row_path).parts
                    row_kind = row.get("kind")
                    if readme_path is not None and safe_row_path == readme_path:
                        if row_kind != "metadata":
                            errors.append("README.md 的 Manifest kind 必须是 metadata")
                    else:
                        allowed_prefixes = {
                            "memory": "eva-memory",
                            "learn": "eva-learn",
                            "review": "eva-review",
                        }
                        expected_prefix = allowed_prefixes.get(str(row_kind))
                        if (
                            expected_prefix is None
                            or len(parts) < 3
                            or parts[1] != expected_prefix
                        ):
                            errors.append(
                                f"Manifest 文件不属于允许的数据域：{safe_row_path}"
                            )
                            continue
                        data_row_count += 1
                        if str(row_kind) not in normalized_manifest_kinds:
                            errors.append(
                                f"Manifest 文件类型不在当前选择范围内：{safe_row_path}"
                            )
                        if (
                            exclude_learn_sources
                            and row_kind == "learn"
                            and "/sources/原始资料/" in f"/{safe_row_path}/"
                        ):
                            errors.append(
                                f"Manifest 声明排除 Learn 原始资料但仍包含：{safe_row_path}"
                            )
                    if safe_row_path in expected_names:
                        errors.append(f"Manifest 包含重复路径：{safe_row_path}")
                        continue
                    expected_names.add(safe_row_path)
                    try:
                        info = archive.getinfo(safe_row_path)
                    except KeyError:
                        errors.append(f"Manifest 文件在 ZIP 中不存在：{safe_row_path}")
                        continue
                    if not isinstance(row_size, int) or row_size < 0:
                        errors.append(f"Manifest 文件大小无效：{safe_row_path}")
                        continue
                    if info.file_size != row_size:
                        errors.append(f"文件大小不匹配：{safe_row_path}")
                    expected_total += row_size
                    if (
                        not isinstance(row_digest, str)
                        or len(row_digest) != 64
                        or any(character not in "0123456789abcdef" for character in row_digest)
                    ):
                        errors.append(f"SHA-256 格式无效：{safe_row_path}")
                        continue
                    digest = hashlib.sha256()
                    try:
                        with archive.open(info, "r") as handle:
                            for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
                                digest.update(chunk)
                    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                        errors.append(f"无法读取 ZIP entry {safe_row_path}：{exc.__class__.__name__}")
                        continue
                    if digest.hexdigest() != row_digest:
                        errors.append(f"SHA-256 不匹配：{safe_row_path}")
                if set(actual_names) != expected_names:
                    extras = sorted(set(actual_names) - expected_names)
                    missing = sorted(expected_names - set(actual_names))
                    if extras:
                        errors.append("ZIP 含 Manifest 未登记文件：" + "、".join(extras[:10]))
                    if missing:
                        errors.append("ZIP 缺少 Manifest 登记文件：" + "、".join(missing[:10]))
                if manifest.get("file_count") != len(rows):
                    errors.append("Manifest file_count 与 files 数量不一致")
                if manifest.get("total_bytes") != expected_total:
                    errors.append("Manifest total_bytes 与逐文件大小不一致")
                if data_row_count == 0:
                    errors.append("ZIP 不包含任何用户正式存档数据")
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        errors.append(f"ZIP 验证失败：{exc.__class__.__name__}")

    if errors:
        return _result(
            False,
            "data-export-verify",
            "压缩包验证失败。",
            errors=errors,
            warnings=warnings,
        )
    try:
        digest = _archive_sha256(path)
    except OSError as exc:
        return _result(
            False,
            "data-export-verify",
            "压缩包内容通过，但无法计算压缩包 SHA-256。",
            errors=[exc.__class__.__name__],
        )
    return _result(
        True,
        "data-export-verify",
        "压缩包 CRC、路径、清单和逐文件 SHA-256 均通过。",
        data={
            "archive_sha256": digest,
            "file_count": int((manifest or {}).get("file_count") or 0),
            "total_bytes": int((manifest or {}).get("total_bytes") or 0),
            "scope": (manifest or {}).get("scope"),
            "included_kinds": (manifest or {}).get("included_kinds") or [],
            "archive_root": (manifest or {}).get("archive_root"),
        },
    )


def _output_is_inside_source(output_dir: Path, sources: list[SourceSpec]) -> bool:
    try:
        output_real = output_dir.resolve(strict=True)
    except OSError:
        return True
    return any(_is_relative_to(output_real, source.real_root) for source in sources)


def _proposed_output_directory_error(output_dir: Path) -> str | None:
    """Read-only target check used before asking the user to confirm export."""
    try:
        output_stat = _path_lstat(output_dir)
    except FileNotFoundError:
        return "output directory does not exist"
    except OSError as exc:
        return f"cannot inspect output directory: {exc.__class__.__name__}"
    if stat.S_ISLNK(output_stat.st_mode):
        return "output directory is a symbolic link"
    if not stat.S_ISDIR(output_stat.st_mode):
        return "output path is not a directory"
    try:
        output_dir.resolve(strict=True)
    except OSError as exc:
        return f"cannot resolve output directory: {exc.__class__.__name__}"
    if not os.access(output_dir, os.W_OK | os.X_OK):
        return "output directory is not writable"
    return None


def _atomic_publish(temp_path: Path, output_dir: Path, stem: str) -> Path:
    for index in range(1, 1000):
        suffix = "" if index == 1 else f"-{index:02d}"
        candidate = output_dir / f"{stem}{suffix}.zip"
        try:
            os.link(temp_path, candidate)
        except FileExistsError:
            continue
        except OSError as exc:
            reserve_descriptor = -1
            try:
                reserve_descriptor = os.open(
                    candidate,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError:
                continue
            except OSError as reserve_exc:
                raise OSError(
                    "cannot atomically reserve archive name: "
                    f"{reserve_exc.__class__.__name__}"
                ) from reserve_exc
            finally:
                if reserve_descriptor >= 0:
                    os.close(reserve_descriptor)
            try:
                os.replace(temp_path, candidate)
            except OSError as replace_exc:
                try:
                    candidate.unlink()
                except OSError:
                    pass
                raise OSError(
                    f"cannot atomically publish archive: {replace_exc.__class__.__name__}"
                ) from replace_exc
        else:
            try:
                temp_path.unlink()
            except OSError as cleanup_exc:
                try:
                    candidate.unlink()
                except OSError as rollback_exc:
                    raise OSError(
                        "cannot clean temporary archive or roll back published archive: "
                        f"{rollback_exc.__class__.__name__}"
                    ) from rollback_exc
                raise OSError(
                    "cannot clean temporary archive after publication: "
                    f"{cleanup_exc.__class__.__name__}"
                ) from cleanup_exc
        try:
            directory_fd = os.open(output_dir, os.O_RDONLY)
        except OSError:
            directory_fd = -1
        if directory_fd >= 0:
            try:
                os.fsync(directory_fd)
            except OSError:
                pass
            finally:
                os.close(directory_fd)
        return candidate
    raise OSError("too many archive name collisions")


def _export_plan(
    plan_payload: dict[str, Any],
    *,
    output_dir: Path,
    expected_plan_id: str | None,
) -> dict[str, Any]:
    data = plan_payload.get("data") or {}
    sources = data.get("_sources")
    entries = data.get("_files")
    if not isinstance(sources, list) or not all(isinstance(item, SourceSpec) for item in sources):
        return _result(False, "data-export", "内部预检结果缺少来源信息。")
    if not isinstance(entries, list) or not all(isinstance(item, FileEntry) for item in entries):
        return _result(False, "data-export", "内部预检结果缺少文件信息。")
    if not entries:
        return _result(False, "data-export", "所选范围为空，没有生成压缩包。")
    plan_id = str(data.get("plan_id") or "")
    if not expected_plan_id:
        return _result(
            False,
            "data-export",
            "缺少用户确认的预检 ID，请先重新预检。",
            errors=["export requires --expected-plan-id"],
        )
    if expected_plan_id != plan_id:
        return _result(
            False,
            "data-export",
            "当前数据范围与用户确认的预检不一致，请重新预检。",
            errors=["expected plan_id does not match the current plan"],
        )

    try:
        output_stat = _path_lstat(output_dir)
    except FileNotFoundError:
        return _result(False, "data-export", "输出目录不存在。")
    except OSError as exc:
        return _result(
            False,
            "data-export",
            "无法读取输出目录。",
            errors=[exc.__class__.__name__],
        )
    if stat.S_ISLNK(output_stat.st_mode):
        return _result(False, "data-export", "输出目录是符号链接，已拒绝写入。")
    if not stat.S_ISDIR(output_stat.st_mode):
        return _result(False, "data-export", "输出路径不是目录。")
    if _output_is_inside_source(output_dir, sources):
        return _result(False, "data-export", "输出目录位于备份源内部，已拒绝写入。")

    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{DEFAULT_ARCHIVE_PREFIX}-{timestamp}"
    backup_root = _safe_segment(stem, DEFAULT_ARCHIVE_PREFIX)
    descriptor = -1
    temp_path: Path | None = None
    final_path: Path | None = None
    try:
        descriptor, temp_name = tempfile.mkstemp(
            prefix=".eva-data-export-",
            suffix=".tmp",
            dir=output_dir,
        )
        temp_path = Path(temp_name)
        try:
            os.fchmod(descriptor, 0o600)
        except (AttributeError, OSError):
            os.chmod(temp_path, 0o600)
        os.close(descriptor)
        descriptor = -1

        file_rows: list[dict[str, Any]] = []
        with zipfile.ZipFile(
            temp_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as archive:
            readme_row = _write_bytes_entry(
                archive,
                PurePosixPath(backup_root, README_NAME).as_posix(),
                _readme_bytes(
                    created_at=created_at,
                    scope=str(data.get("scope")),
                    included_kinds=tuple(data.get("included_kinds") or []),
                ),
                timestamp=time.time(),
            )
            file_rows.append(readme_row)
            for entry in entries:
                file_rows.append(
                    _write_source_entry(
                        archive,
                        entry,
                        backup_root=backup_root,
                    )
                )
            manifest = {
                "format_version": BACKUP_FORMAT_VERSION,
                "eva_skill_version": SCRIPT_VERSION,
                "created_at": created_at,
                "archive_root": backup_root,
                "scope": data.get("scope"),
                "included_kinds": data.get("included_kinds") or [],
                "selection": data.get("selection") or {},
                "plan_id": plan_id,
                "sources": data.get("sources") or [],
                "skipped": data.get("skipped") or {},
                "file_count": len(file_rows),
                "total_bytes": sum(int(row["size"]) for row in file_rows),
                "files": file_rows,
                "notes": {
                    "absolute_source_paths_included": False,
                    "encrypted": False,
                    "manifest_self_hash_excluded": True,
                },
            }
            archive.writestr(
                _zip_info(
                    PurePosixPath(backup_root, MANIFEST_NAME).as_posix(),
                    time.time(),
                ),
                _manifest_bytes(manifest),
            )

        with temp_path.open("rb") as handle:
            os.fsync(handle.fileno())
        verification = _validate_zip(temp_path)
        if not verification.get("ok"):
            return _result(
                False,
                "data-export",
                "临时压缩包校验失败，没有发布备份。",
                errors=list(verification.get("errors") or []),
                warnings=list(verification.get("warnings") or []),
            )
        final_path = _atomic_publish(temp_path, output_dir, stem)
        temp_path = None
        final_verification = _validate_zip(final_path)
        if not final_verification.get("ok"):
            try:
                final_path.unlink()
            except OSError:
                pass
            return _result(
                False,
                "data-export",
                "最终压缩包校验失败，已尝试移除。",
                errors=list(final_verification.get("errors") or []),
            )
        verify_data = final_verification.get("data") or {}
        return _result(
            True,
            "data-export",
            f"Eva 数据备份已生成：{final_path.name}",
            warnings=list(plan_payload.get("warnings") or []),
            data={
                "archive_path": str(final_path),
                "archive_name": final_path.name,
                "archive_sha256": verify_data.get("archive_sha256"),
                "file_count": int(data.get("file_count") or 0),
                "total_bytes": int(data.get("total_bytes") or 0),
                "verified_manifest_file_count": verify_data.get("file_count"),
                "verified_manifest_total_bytes": verify_data.get("total_bytes"),
                "scope": data.get("scope"),
                "included_kinds": data.get("included_kinds") or [],
                "plan_id": plan_id,
                "memory": data.get("memory") or {},
                "learn": data.get("learn") or {},
                "review": data.get("review") or {},
                "skipped": data.get("skipped") or {},
                "verified": True,
            },
        )
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        return _result(
            False,
            "data-export",
            "备份创建失败，没有发布压缩包。",
            errors=[str(exc) or exc.__class__.__name__],
        )
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temp_path is not None:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview, export, or verify a local Eva data backup."
    )
    parser.add_argument("--version", action="version", version=SCRIPT_VERSION)
    subparsers = parser.add_subparsers(dest="mode", required=True)

    def add_scope_arguments(target: argparse.ArgumentParser) -> None:
        target.add_argument(
            "--project-root",
            default=".",
            help="Current creator project root.",
        )
        target.add_argument(
            "--scope",
            choices=("memory", "complete", "custom"),
            default="memory",
            help="memory=cards only; complete=Memory+Learn+Review; custom uses --include.",
        )
        target.add_argument(
            "--include",
            action="append",
            choices=SOURCE_KINDS,
            default=[],
            help="Repeatable; only valid with --scope custom.",
        )
        target.add_argument(
            "--learn-path",
            action="append",
            default=[],
            help="Additional explicit Eva Learn project or container path.",
        )
        target.add_argument(
            "--exclude-learn-sources",
            action="store_true",
            help=(
                "Only with custom scope including learn: exclude files under each "
                "Learn project's sources/原始资料 directory."
            ),
        )
        target.add_argument(
            "--output-dir",
            default=str(Path.home() / "Desktop"),
            help=(
                "Proposed destination for preview and actual destination for export; "
                "defaults to the current user's Desktop."
            ),
        )
        target.add_argument(
            "--format",
            choices=("json", "markdown"),
            default="json",
            help="Output format for preview or export status.",
        )
        target.add_argument("--max-files", type=_positive_int, default=DEFAULT_MAX_FILES)
        target.add_argument("--max-bytes", type=_positive_int, default=DEFAULT_MAX_BYTES)

    preview_parser = subparsers.add_parser(
        "preview",
        help="Read-only discovery and size preview. Never creates output.",
    )
    add_scope_arguments(preview_parser)

    export_parser = subparsers.add_parser(
        "export",
        help="Create a verified local ZIP after explicit confirmation.",
    )
    add_scope_arguments(export_parser)
    export_parser.add_argument(
        "--confirm-export",
        "--confirm",
        dest="confirm_export",
        action="store_true",
        help="Required explicit confirmation that the user approved this export scope.",
    )
    export_parser.add_argument(
        "--expected-plan-id",
        required=True,
        help="Required preview plan_id; export stops if the current plan differs.",
    )

    verify_parser = subparsers.add_parser(
        "verify",
        help="Verify CRC, safe paths, manifest, and every file SHA-256.",
    )
    verify_parser.add_argument("--archive", required=True, help="ZIP archive to verify.")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.mode == "verify":
        payload = _validate_zip(_absolute_lexical_path(args.archive))
        _print_payload(payload)
        return 0 if payload.get("ok") else 1

    if args.mode == "export" and not args.confirm_export:
        payload = _result(
            False,
            "data-export",
            "没有显式确认，未生成压缩包。",
            errors=["export requires --confirm-export"],
        )
        _emit(payload, args.format)
        return 1

    project_root = _absolute_lexical_path(args.project_root)
    extra_learn_paths = [_absolute_lexical_path(item) for item in args.learn_path]
    output_dir = _absolute_lexical_path(args.output_dir)
    plan = _build_plan(
        project_root=project_root,
        scope=args.scope,
        custom_includes=list(args.include),
        extra_learn_paths=extra_learn_paths,
        exclude_learn_sources=bool(args.exclude_learn_sources),
        proposed_output_dir=output_dir,
        max_files=args.max_files,
        max_bytes=args.max_bytes,
    )
    if args.mode == "preview":
        public = _public_plan(plan)
        _emit(public, args.format)
        return 0 if public.get("ok") else 1

    if not plan.get("ok"):
        public = _public_plan(plan)
        public["kind"] = "data-export"
        _emit(public, args.format)
        return 1
    payload = _export_plan(
        plan,
        output_dir=output_dir,
        expected_plan_id=args.expected_plan_id,
    )
    _emit(payload, args.format)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
