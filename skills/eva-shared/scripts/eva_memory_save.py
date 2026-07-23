#!/usr/bin/env python3
"""Safely save canonical Eva Assets as current-project memory cards."""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import stat
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from eva_asset_validate import (
    CANONICAL_FRONTMATTER_JSON_PREFIX,
    load_asset,
    validate_asset_payload,
)
from eva_common import (
    add_common_arguments,
    default_base_from_script,
    exit_with,
    read_json,
    result,
    sha256_file,
)


MEMORY_FOLDER = "eva-memory"
SUPPORTED_MEMORY_TYPES = {
    "idea-card": {
        "directory": "idea-cards",
        "filename_label": "点子卡",
        "heading_label": "点子卡",
        "fallback_title": "未命名点子",
        "default_source": "conversation",
    },
    "persona-card": {
        "directory": "persona",
        "filename_label": "人设素材卡",
        "heading_label": "人设素材卡",
        "fallback_title": "未命名人设素材",
        "default_source": "conversation",
    },
    "voice-card": {
        "directory": "voice",
        "filename_label": "文风卡",
        "heading_label": "Voice-card",
        "fallback_title": "用户表达文风",
        "default_source": "user_samples",
    },
}

PREFERRED_FRONTMATTER_KEYS = (
    "type",
    "asset_type",
    "created",
    "source",
    "source_module",
    "keywords",
    "platform",
    "use_for",
    "confidence",
    "low_confidence_reason",
    "missing_fields",
    "privacy_flags",
    "valid_next",
    "saved",
    "title",
    "core_content",
    "user_question",
    "evidence",
)

PLAIN_STRING_FIELDS = {
    "type",
    "asset_type",
    "created",
    "source",
    "source_module",
    "confidence",
}
PLAIN_STRING_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")
SAFE_METADATA_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,127}\Z")
KEYWORD_SPLIT_PATTERN = re.compile(r"[,，、;；]")
MAX_KEYWORDS = 100
MAX_KEYWORD_CHARS = 100
MAX_TITLE_CHARS = 120
MAX_FILENAME_TITLE_CHARS = 40
MAX_COLLISION_ATTEMPTS = 9999


class MemorySaveError(Exception):
    """Expected, user-safe memory-save failure."""


def _absolute_lexical_path(raw: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(raw))))


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _looks_like_eva_source_repo(root: Path) -> bool:
    return all(
        (
            (root / "skills" / "eva" / "SKILL.md").is_file(),
            (root / "skills" / "eva-shared" / "SKILL.md").is_file(),
            (root / ".claude-plugin" / "marketplace.json").is_file(),
        )
    )


def _looks_like_eva_distribution_root(root: Path) -> bool:
    """Recognize Skill Hub and RedSkill all-in-one package roots."""
    return (
        (root / "SKILL.md").is_file()
        and (root / "modules" / "eva-shared" / "support.md").is_file()
    )


def _looks_like_skill_source_directory(root: Path) -> bool:
    """Reject split Skill installation/source roots before creating runtime data."""
    skill_file = root / "SKILL.md"
    try:
        skill_stat = os.lstat(skill_file)
    except OSError:
        return False
    if not stat.S_ISREG(skill_stat.st_mode):
        return False
    for child in ("agents", "references", "scripts", "assets", "modules"):
        try:
            child_stat = os.lstat(root / child)
        except OSError:
            continue
        if stat.S_ISDIR(child_stat.st_mode) and not stat.S_ISLNK(child_stat.st_mode):
            return True
    return False


def _existing_directory_without_symlink(path: Path, label: str) -> None:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError as exc:
        raise MemorySaveError(f"{label}不存在") from exc
    except Exception as exc:
        raise MemorySaveError(f"无法检查{label}: {exc.__class__.__name__}") from exc
    if stat.S_ISLNK(metadata.st_mode):
        raise MemorySaveError(f"{label}是符号链接，已拒绝写入")
    if not stat.S_ISDIR(metadata.st_mode):
        raise MemorySaveError(f"{label}不是目录")


def _ensure_child_directory(path: Path, label: str) -> None:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        try:
            os.mkdir(path, 0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            raise MemorySaveError(f"无法创建{label}: {exc.__class__.__name__}") from exc
        try:
            metadata = os.lstat(path)
        except OSError as exc:
            raise MemorySaveError(f"无法确认{label}: {exc.__class__.__name__}") from exc
    except OSError as exc:
        raise MemorySaveError(f"无法检查{label}: {exc.__class__.__name__}") from exc

    if stat.S_ISLNK(metadata.st_mode):
        raise MemorySaveError(f"{label}是符号链接，已拒绝写入")
    if not stat.S_ISDIR(metadata.st_mode):
        raise MemorySaveError(f"{label}不是目录")


def _prepare_target_directory(project_root: Path, asset_type: str) -> Path:
    _existing_directory_without_symlink(project_root, "项目根目录")
    if _looks_like_eva_source_repo(project_root):
        raise MemorySaveError("已拒绝把 Eva-skill 源码仓库当作记忆卡运行项目")
    if _looks_like_eva_distribution_root(project_root):
        raise MemorySaveError("已拒绝把 Eva-skill 一体化发行包当作记忆卡运行项目")
    if _looks_like_skill_source_directory(project_root):
        raise MemorySaveError("已拒绝把 Skill 安装或源码目录当作记忆卡运行项目")

    try:
        project_real = project_root.resolve(strict=True)
    except OSError as exc:
        raise MemorySaveError("无法安全解析项目根目录") from exc

    memory_root = project_root / MEMORY_FOLDER
    _ensure_child_directory(memory_root, "eva-memory 目录")
    target = memory_root / str(SUPPORTED_MEMORY_TYPES[asset_type]["directory"])
    _ensure_child_directory(target, "记忆卡类型目录")

    try:
        memory_real = memory_root.resolve(strict=True)
        target_real = target.resolve(strict=True)
    except OSError as exc:
        raise MemorySaveError("无法安全解析记忆卡目录") from exc
    if not _is_relative_to(memory_real, project_real):
        raise MemorySaveError("eva-memory 目录越出当前项目，已拒绝写入")
    if not _is_relative_to(target_real, memory_real):
        raise MemorySaveError("记忆卡类型目录越出 eva-memory，已拒绝写入")

    _existing_directory_without_symlink(memory_root, "eva-memory 目录")
    _existing_directory_without_symlink(target, "记忆卡类型目录")
    return target


def _normalize_keywords(raw_value: object) -> list[str]:
    if isinstance(raw_value, str):
        raw_keywords: list[object] = [
            item for item in KEYWORD_SPLIT_PATTERN.split(raw_value) if item.strip()
        ]
    elif isinstance(raw_value, list):
        raw_keywords = raw_value
    else:
        raise MemorySaveError("keywords 必须是非空字符串数组或分隔字符串")

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_keyword in raw_keywords:
        if not isinstance(raw_keyword, str):
            raise MemorySaveError("keywords 只能包含字符串")
        keyword = " ".join(raw_keyword.replace("\ufeff", "").split()).strip()
        if not keyword:
            raise MemorySaveError("keywords 不能包含空值")
        if len(keyword) > MAX_KEYWORD_CHARS:
            raise MemorySaveError(
                f"单个 keyword 不能超过 {MAX_KEYWORD_CHARS} 个字符"
            )
        if not all(character.isprintable() for character in keyword):
            raise MemorySaveError("keywords 不能包含控制字符")
        identity = unicodedata.normalize("NFKC", keyword).casefold()
        if identity in seen:
            continue
        seen.add(identity)
        normalized.append(keyword)
        if len(normalized) > MAX_KEYWORDS:
            raise MemorySaveError(f"keywords 不能超过 {MAX_KEYWORDS} 项")
    if not normalized:
        raise MemorySaveError("保存记忆卡至少需要一个 keyword")
    return normalized


def _keywords_from_cli_or_asset(cli_values: list[str], asset: dict[str, Any]) -> list[str]:
    if cli_values:
        flattened: list[str] = []
        for raw in cli_values:
            flattened.extend(
                item for item in KEYWORD_SPLIT_PATTERN.split(raw) if item.strip()
            )
        return _normalize_keywords(flattened)
    return _normalize_keywords(asset.get("keywords"))


def _privacy_confirmation_required(asset: dict[str, Any]) -> bool:
    flags = asset.get("privacy_flags")
    if isinstance(flags, list) and bool(flags):
        return True

    privacy = asset.get("privacy")
    if isinstance(privacy, dict):
        private_value = privacy.get("private")
        if private_value not in (None, "", False, [], {}):
            return True
        if privacy.get("public") is False:
            return True
        return any(
            key not in {"public", "private"}
            and value not in (None, "", False, [], {})
            for key, value in privacy.items()
        )
    return privacy not in (None, "", False, [], {})


def _display_title(asset: dict[str, Any], asset_type: str, override: str | None) -> str:
    raw_title: object = override if override is not None else asset.get("title")
    if raw_title is not None and not isinstance(raw_title, str):
        raise MemorySaveError("title 必须是字符串")

    title = " ".join(str(raw_title or "").replace("\ufeff", "").split()).strip()
    if not title:
        title = str(SUPPORTED_MEMORY_TYPES[asset_type]["fallback_title"])
    return title[:MAX_TITLE_CHARS].rstrip()


def _filename_slug(title: str, asset_type: str) -> str:
    normalized = unicodedata.normalize("NFKC", title)
    normalized = "".join(
        character if character.isprintable() else " " for character in normalized
    )
    normalized = re.sub(r"[/\\:*?\"<>|]", " ", normalized)
    normalized = re.sub(r"\s+", "_", normalized)
    normalized = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", normalized, flags=re.UNICODE)
    normalized = normalized.strip("._-")[:MAX_FILENAME_TITLE_CHARS].strip("._-")
    if normalized in {"", ".", ".."}:
        normalized = str(SUPPORTED_MEMORY_TYPES[asset_type]["fallback_title"])
    return normalized


def _safe_source(raw_value: object, asset_type: str) -> str:
    if raw_value is None:
        return str(SUPPORTED_MEMORY_TYPES[asset_type]["default_source"])
    if not isinstance(raw_value, str):
        raise MemorySaveError("source 必须是字符串")
    source = raw_value.strip()
    if not source or len(source) > 128 or not all(
        character.isprintable() for character in source
    ):
        raise MemorySaveError("source 必须是 1-128 个可打印字符")
    return source


def _frontmatter_value(key: str, value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (list, dict)):
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if isinstance(value, list):
            return encoded
        return CANONICAL_FRONTMATTER_JSON_PREFIX + encoded
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return json.dumps(value, ensure_ascii=False)
    if (
        isinstance(value, str)
        and key in PLAIN_STRING_FIELDS
        and PLAIN_STRING_PATTERN.fullmatch(value)
        and value.lower() not in {"true", "false", "null"}
        and not re.fullmatch(r"[-+]?\d+(?:\.\d*)?", value)
    ):
        return value
    return CANONICAL_FRONTMATTER_JSON_PREFIX + json.dumps(
        value, ensure_ascii=False, separators=(",", ":")
    )


def _ordered_metadata_items(asset: dict[str, Any]) -> list[tuple[str, Any]]:
    for key in asset:
        if not isinstance(key, str) or not SAFE_METADATA_KEY_PATTERN.fullmatch(key):
            raise MemorySaveError("资产包含无法安全写入 frontmatter 的字段名")

    items: list[tuple[str, Any]] = []
    added: set[str] = set()
    for key in PREFERRED_FRONTMATTER_KEYS:
        if key in asset:
            items.append((key, asset[key]))
            added.add(key)
    for key in sorted((key for key in asset if key not in added), key=str.casefold):
        items.append((key, asset[key]))
    return items


def _human_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip() or "（空）"
    if isinstance(value, list):
        if not value:
            return "- （无）"
        lines: list[str] = []
        for item in value:
            if isinstance(item, str):
                lines.append(f"- {item}")
            else:
                lines.append(
                    "- "
                    + json.dumps(item, ensure_ascii=False, sort_keys=True)
                )
        return "\n".join(lines)
    if isinstance(value, dict):
        if not value:
            return "- （无）"
        return "\n".join(
            f"- {key}："
            + (
                item
                if isinstance(item, str)
                else json.dumps(item, ensure_ascii=False, sort_keys=True)
            )
            for key, item in value.items()
        )
    return str(value)


def render_memory_markdown(asset: dict[str, Any], display_title: str) -> str:
    asset_type = str(asset["asset_type"])
    heading_label = str(SUPPORTED_MEMORY_TYPES[asset_type]["heading_label"])
    frontmatter = ["---"]
    for key, value in _ordered_metadata_items(asset):
        frontmatter.append(f"{key}: {_frontmatter_value(key, value)}")
    frontmatter.extend(
        [
            "---",
            "",
            f"# {heading_label}：{display_title}",
            "",
            "## 核心内容",
            "",
            _human_value(asset.get("core_content")),
            "",
            "## 用户问题",
            "",
            _human_value(asset.get("user_question")),
            "",
            "## 关键证据或材料",
            "",
            _human_value(asset.get("evidence")),
            "",
            "## 可交接下游",
            "",
            _human_value(asset.get("valid_next")),
            "",
        ]
    )
    return "\n".join(frontmatter)


def _roundtrip_errors(expected: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, expected_value in expected.items():
        if key not in actual:
            errors.append(f"rendered Markdown lost frontmatter field '{key}'")
        elif actual[key] != expected_value:
            errors.append(f"rendered Markdown changed frontmatter field '{key}'")
    unexpected = sorted(key for key in actual if key not in expected)
    if unexpected:
        errors.append(
            "rendered Markdown added unexpected frontmatter field(s): "
            + ", ".join(unexpected)
        )
    return errors


def _public_validation_warnings(warnings: list[str]) -> list[str]:
    public: list[str] = []
    for warning in warnings:
        if warning.startswith("asset declares missing_fields:"):
            sanitized = "asset declares missing_fields"
        elif warning.startswith("valid_next uses compatibility alias(es)"):
            sanitized = "valid_next compatibility aliases were normalized before saving"
        elif warning == "asset has privacy_flags; require user confirmation before saving":
            sanitized = "asset has privacy_flags; privacy confirmation was recorded"
        else:
            sanitized = warning
        if sanitized not in public:
            public.append(sanitized)
    return public


def _write_temp_card(target_directory: Path, markdown: str) -> Path:
    descriptor = -1
    temp_path: Path | None = None
    try:
        descriptor, raw_path = tempfile.mkstemp(
            prefix=".eva-memory-save-",
            suffix=".md.tmp",
            dir=target_directory,
            text=True,
        )
        temp_path = Path(raw_path)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(markdown)
            handle.flush()
            os.fsync(handle.fileno())
        return temp_path
    except (OSError, UnicodeError) as exc:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise MemorySaveError(
            f"无法在记忆卡目录创建临时文件: {exc.__class__.__name__}"
        ) from exc


def _publish_without_overwrite(
    temp_path: Path,
    target_directory: Path,
    base_filename: str,
) -> tuple[Path, int, bool]:
    stem = Path(base_filename).stem
    suffix = Path(base_filename).suffix
    for attempt in range(1, MAX_COLLISION_ATTEMPTS + 1):
        filename = (
            base_filename if attempt == 1 else f"{stem}-{attempt:02d}{suffix}"
        )
        candidate = target_directory / filename
        try:
            os.link(temp_path, candidate, follow_symlinks=False)
        except FileExistsError:
            continue
        except (OSError, NotImplementedError, TypeError) as link_exc:
            if isinstance(link_exc, OSError) and link_exc.errno == errno.EEXIST:
                continue
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
                raise MemorySaveError(
                    "无法原子预留记忆卡文件名: "
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
                raise MemorySaveError(
                    f"无法原子发布记忆卡: {replace_exc.__class__.__name__}"
                ) from replace_exc
            return candidate, attempt, True
        return candidate, attempt, False
    raise MemorySaveError("同名记忆卡过多，无法分配安全文件名")


def _fsync_directory(path: Path) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        return
    finally:
        if descriptor is not None:
            os.close(descriptor)


def save_memory_asset(
    *,
    asset_path: Path,
    project_root: Path,
    confirm_save: bool,
    confirm_privacy: bool,
    title_override: str | None = None,
    keyword_overrides: list[str] | None = None,
    source_override: str | None = None,
    today: date | None = None,
) -> dict[str, Any]:
    if not confirm_save:
        return result(
            False,
            "memory-save",
            "尚未获得保存确认",
            ["saving requires --confirm-save"],
        )
    if asset_path.suffix.lower() != ".json":
        return result(
            False,
            "memory-save",
            "只接受 canonical Asset JSON",
            ["--asset must point to a .json file"],
        )
    if not asset_path.exists() or not asset_path.is_file():
        return result(
            False,
            "memory-save",
            "资产 JSON 不存在或不是普通文件",
            [str(asset_path)],
        )

    base = default_base_from_script(__file__)
    schema_path = base / "schemas" / "asset-card.schema.json"
    try:
        asset = read_json(asset_path)
        schema = read_json(schema_path)
    except Exception as exc:
        return result(
            False,
            "memory-save",
            "资产或 Schema 读取失败",
            [exc.__class__.__name__],
        )
    if not isinstance(asset, dict):
        return result(
            False,
            "memory-save",
            "资产 JSON 必须是对象",
            ["asset JSON must be an object"],
        )

    initial_validation = validate_asset_payload(asset, schema, base)
    if not initial_validation["ok"]:
        return result(
            False,
            "memory-save",
            "canonical Asset 校验失败，未写入",
            initial_validation["errors"],
            _public_validation_warnings(initial_validation["warnings"]),
        )

    asset_type = initial_validation["asset_type"]
    if asset_type not in SUPPORTED_MEMORY_TYPES:
        return result(
            False,
            "memory-save",
            "该资产类型不能保存到 Eva Memory",
            ["only idea-card, persona-card and voice-card are supported"],
        )

    if _privacy_confirmation_required(asset) and not confirm_privacy:
        return result(
            False,
            "memory-save",
            "资产含隐私标记或私密字段，尚未获得隐私保存确认",
            ["privacy markers require --confirm-privacy"],
        )

    normalized_asset = initial_validation["normalized_asset"]
    storage_type = normalized_asset.get("type")
    if storage_type is not None and storage_type != asset_type:
        return result(
            False,
            "memory-save",
            "type 与 asset_type 冲突，未写入",
            ["type must equal asset_type when both are present"],
        )

    try:
        keywords = _keywords_from_cli_or_asset(
            keyword_overrides or [], normalized_asset
        )
        display_title = _display_title(
            normalized_asset, str(asset_type), title_override
        )
        source = _safe_source(
            source_override
            if source_override is not None
            else normalized_asset.get("source"),
            str(asset_type),
        )
    except MemorySaveError as exc:
        return result(False, "memory-save", "记忆卡存储元数据无效", [str(exc)])

    created = (today or date.today()).isoformat()
    final_asset = dict(normalized_asset)
    final_asset.update(
        {
            "type": asset_type,
            "asset_type": asset_type,
            "created": created,
            "source": source,
            "keywords": keywords,
            "title": display_title,
            "saved": True,
            "valid_next": initial_validation["normalized_valid_next"],
        }
    )

    final_validation = validate_asset_payload(final_asset, schema, base)
    if not final_validation["ok"]:
        return result(
            False,
            "memory-save",
            "最终 canonical Asset 校验失败，未写入",
            final_validation["errors"],
            _public_validation_warnings(final_validation["warnings"]),
        )
    final_asset = final_validation["normalized_asset"]

    try:
        markdown = render_memory_markdown(final_asset, display_title)
        target_directory = _prepare_target_directory(project_root, str(asset_type))
    except MemorySaveError as exc:
        return result(False, "memory-save", "无法准备安全保存位置", [str(exc)])
    except Exception as exc:
        return result(
            False,
            "memory-save",
            "记忆卡渲染失败，未写入",
            [exc.__class__.__name__],
        )

    filename_label = str(SUPPORTED_MEMORY_TYPES[str(asset_type)]["filename_label"])
    base_filename = (
        f"{created.replace('-', '')}_{_filename_slug(display_title, str(asset_type))}_"
        f"{filename_label}.md"
    )

    temp_path: Path | None = None
    final_path: Path | None = None
    cleanup_warning: str | None = None
    try:
        _existing_directory_without_symlink(
            target_directory, "记忆卡类型目录"
        )
        temp_path = _write_temp_card(target_directory, markdown)

        parsed_asset = load_asset(temp_path)
        roundtrip_failures = _roundtrip_errors(final_asset, parsed_asset)
        if roundtrip_failures:
            raise MemorySaveError("; ".join(roundtrip_failures))
        roundtrip_validation = validate_asset_payload(parsed_asset, schema, base)
        if not roundtrip_validation["ok"]:
            raise MemorySaveError(
                "rendered Markdown failed canonical validation: "
                + "; ".join(roundtrip_validation["errors"])
            )

        _existing_directory_without_symlink(
            target_directory, "记忆卡类型目录"
        )
        final_path, collision_index, temp_consumed = _publish_without_overwrite(
            temp_path, target_directory, base_filename
        )
        if temp_consumed:
            temp_path = None
        else:
            try:
                temp_path.unlink()
                temp_path = None
            except OSError:
                cleanup_warning = "保存成功，但隐藏临时硬链接清理失败"
        _fsync_directory(target_directory)

        digest = sha256_file(final_path)
        size = final_path.stat().st_size
    except MemorySaveError as exc:
        if final_path is not None:
            try:
                final_path.unlink()
            except OSError:
                pass
        return result(
            False,
            "memory-save",
            "记忆卡回读或原子写入失败",
            [str(exc)],
        )
    except Exception as exc:
        if final_path is not None:
            try:
                final_path.unlink()
            except OSError:
                pass
        return result(
            False,
            "memory-save",
            "记忆卡写入失败",
            [exc.__class__.__name__],
        )
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass

    warnings = _public_validation_warnings(final_validation["warnings"])
    if cleanup_warning:
        warnings.append(cleanup_warning)
    return result(
        True,
        "memory-save",
        "Eva Memory 记忆卡已保存",
        [],
        warnings,
        {
            "asset_type": asset_type,
            "path": str(final_path),
            "relative_path": final_path.relative_to(project_root).as_posix(),
            "created": created,
            "sha256": digest,
            "bytes": size,
            "collision_index": collision_index,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Save a canonical Eva Asset JSON into ./eva-memory."
    )
    parser.add_argument("--asset", required=True, help="Canonical Eva Asset JSON.")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Current creator project; ./eva-memory is derived from it.",
    )
    parser.add_argument("--title", help="Optional human-readable card title.")
    parser.add_argument(
        "--keyword",
        "--keywords",
        dest="keywords",
        action="append",
        default=[],
        help="Keyword; repeat the option or use Chinese/English separators.",
    )
    parser.add_argument("--source", help="Optional storage source label.")
    parser.add_argument(
        "--confirm-save",
        action="store_true",
        help="Required confirmation that the user approved saving.",
    )
    parser.add_argument(
        "--confirm-privacy",
        action="store_true",
        help="Additional confirmation required when privacy_flags is non-empty.",
    )
    add_common_arguments(parser)
    args = parser.parse_args()

    payload = save_memory_asset(
        asset_path=_absolute_lexical_path(args.asset),
        project_root=_absolute_lexical_path(args.project_root),
        confirm_save=args.confirm_save,
        confirm_privacy=args.confirm_privacy,
        title_override=args.title,
        keyword_overrides=args.keywords,
        source_override=args.source,
    )
    exit_with(payload)


if __name__ == "__main__":
    main()
