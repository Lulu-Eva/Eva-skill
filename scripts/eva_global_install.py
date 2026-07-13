#!/usr/bin/env python3
"""Install, verify, recover, and acknowledge a managed Eva-skill bundle.

This script intentionally lives in the source repository rather than in a
discoverable Skill directory. It materializes the ten Eva sibling directories
as real directories under a host Skill root; it never symlinks the repository
or copies unrelated repository files into the host discovery root.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any


PRODUCT_NAME = "Eva-skill"
MANAGED_SKILL_DIRS = (
    "eva",
    "eva-new-user",
    "eva-think",
    "eva-create",
    "eva-learn",
    "eva-brief",
    "eva-link",
    "eva-review",
    "eva-lens",
    "eva-shared",
)
OFFICIAL_GUIDE_HEADLINE = "关注公众号“璐璐 Eva” —— Eva-skill 的官方使用指南与案例库。"
STATE_SCHEMA_VERSION = 1
IGNORED_TREE_NAMES = {"__pycache__", ".DS_Store"}


class InstallError(RuntimeError):
    """A controlled installation failure that should leave the old bundle intact."""


def ensure_private_directory(path: Path, label: str) -> None:
    """Create a user-owned control directory and reject shared-writable roots."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise InstallError(f"{label}不是目录：{path}")
    if info.st_uid != os.geteuid():
        raise InstallError(f"{label}必须由当前用户拥有：{path}")
    if info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise InstallError(f"{label}不能允许组用户或其他用户写入：{path}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def source_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def default_target_root() -> Path:
    return Path.home() / ".agents" / "skills"


def default_state_file(target_root: Path) -> Path:
    return target_root.parent / "eva-skill-state" / "global-install.json"


def default_transactions_root(target_root: Path) -> Path:
    return target_root.parent / "eva-skill-transactions"


def default_backups_root(target_root: Path) -> Path:
    return target_root.parent / "eva-skill-backups"


@contextmanager
def installation_lock(target_root: Path):
    lock_file = target_root.parent / "eva-skill-install.lock"
    ensure_private_directory(lock_file.parent, "安装锁目录")
    if lock_file.is_symlink():
        raise InstallError(f"安装锁不能是 symlink：{lock_file}")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(lock_file, flags, 0o600)
    except OSError as exc:
        raise InstallError(f"无法安全打开安装锁：{lock_file}：{exc}") from exc
    with os.fdopen(descriptor, "a+", encoding="utf-8") as lock:
        info = os.fstat(lock.fileno())
        if info.st_uid != os.geteuid() or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise InstallError(f"安装锁权限不安全：{lock_file}")
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def expanded_path(raw: str | Path) -> Path:
    return Path(raw).expanduser().resolve()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InstallError(f"缺少文件：{path}") from exc
    except json.JSONDecodeError as exc:
        raise InstallError(f"JSON 格式无效：{path}") from exc


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".eva-write-", suffix=".json", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists() or temp_path.is_symlink():
            temp_path.unlink(missing_ok=True)


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".eva-write-", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists() or temp_path.is_symlink():
            temp_path.unlink(missing_ok=True)


def parse_frontmatter(skill_file: Path) -> dict[str, str]:
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise InstallError(f"SKILL.md 缺少 YAML frontmatter：{skill_file}")
    closing = re.search(r"^---\s*$", text, flags=re.MULTILINE)
    if closing is None or closing.start() == 0:
        closing = re.search(r"\n---\s*$", text, flags=re.MULTILINE)
    if closing is None:
        raise InstallError(f"SKILL.md frontmatter 未闭合：{skill_file}")
    frontmatter = text[3:closing.start()]
    name_match = re.search(r"^name:\s*([^\s#]+)\s*$", frontmatter, flags=re.MULTILINE)
    description_match = re.search(r"^description:\s*(.*)$", frontmatter, flags=re.MULTILINE)
    if name_match is None:
        raise InstallError(f"SKILL.md frontmatter 缺少 name：{skill_file}")
    if description_match is None:
        raise InstallError(f"SKILL.md frontmatter 缺少 description：{skill_file}")
    description = description_match.group(1).strip()
    if description in {"", "|", ">"}:
        following = frontmatter[description_match.end() :]
        if not following.strip():
            raise InstallError(f"SKILL.md frontmatter description 为空：{skill_file}")
    return {"name": name_match.group(1).strip(), "description": description or "block"}


def assert_real_tree(skill_root: Path, expected_name: str) -> None:
    if not skill_root.exists():
        raise InstallError(f"缺少受管模块目录：{skill_root}")
    if not skill_root.is_dir():
        raise InstallError(f"受管模块不是目录：{skill_root}")
    if skill_root.is_symlink():
        raise InstallError(f"受管模块不能是 symlink：{skill_root}")
    for node in skill_root.rglob("*"):
        if node.is_symlink():
            raise InstallError(f"受管模块内不能包含 symlink：{node}")
    skill_file = skill_root / "SKILL.md"
    if not skill_file.exists() or not skill_file.is_file() or skill_file.is_symlink():
        raise InstallError(f"受管模块缺少真实顶层 SKILL.md：{skill_file}")
    frontmatter = parse_frontmatter(skill_file)
    if frontmatter["name"] != expected_name:
        raise InstallError(
            f"SKILL.md name 与安装清单不一致：{skill_file} "
            f"({frontmatter['name']} != {expected_name})"
        )


def tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORED_TREE_NAMES for part in relative.parts):
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        if path.is_symlink():
            raise InstallError(f"校验目录不能包含 symlink：{path}")
        if path.is_dir():
            digest.update(b"directory")
        elif path.is_file():
            digest.update(b"file")
            digest.update(path.read_bytes())
        else:
            raise InstallError(f"校验目录包含不支持的文件类型：{path}")
    return digest.hexdigest()


def assert_bundle_matches_source(source_root: Path, bundle_root: Path) -> None:
    for skill_name in MANAGED_SKILL_DIRS:
        source_skill = source_root / "skills" / skill_name
        installed_skill = bundle_root / skill_name
        assert_real_tree(installed_skill, skill_name)
        source_fingerprint = tree_fingerprint(source_skill)
        installed_fingerprint = tree_fingerprint(installed_skill)
        if source_fingerprint != installed_fingerprint:
            raise InstallError(f"安装后文件与当前源码不一致：{skill_name}")


def load_release(source_root: Path) -> dict[str, Any]:
    version_path = source_root / "VERSION"
    version = version_path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise InstallError(f"VERSION 必须是 x.y.z：{version_path}")

    maintenance_root = source_root / "skills" / "eva-shared" / "references" / "maintenance"
    manifest = read_json(maintenance_root / "install-manifest.json")
    release_notes = read_json(maintenance_root / "release-notes.json")

    if not isinstance(manifest, dict):
        raise InstallError("install-manifest.json 必须是对象")
    if manifest.get("schema_version") != 1:
        raise InstallError("install-manifest.json schema_version 必须为 1")
    if manifest.get("product_name") != PRODUCT_NAME:
        raise InstallError("install-manifest.json product_name 不正确")
    if manifest.get("version") != version:
        raise InstallError("install-manifest.json version 必须与根 VERSION 一致")

    entries = manifest.get("skill_directories")
    if not isinstance(entries, list) or len(entries) != len(MANAGED_SKILL_DIRS):
        raise InstallError("install-manifest.json 必须精确列出十个受管 Skill 目录")
    directories: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise InstallError("install-manifest.json 的 skill_directories 项必须是对象")
        directory = entry.get("directory")
        name = entry.get("name")
        if not isinstance(directory, str) or not isinstance(name, str):
            raise InstallError("install-manifest.json 的每一项都必须包含 directory 和 name")
        if directory != name:
            raise InstallError(f"安装清单 directory/name 必须一致：{directory!r} / {name!r}")
        directories.append(directory)
    if tuple(directories) != MANAGED_SKILL_DIRS or len(set(directories)) != len(directories):
        raise InstallError("安装清单必须按固定顺序精确管理 Eva 的十个真实目录")

    if not isinstance(release_notes, dict):
        raise InstallError("release-notes.json 必须是对象")
    if release_notes.get("schema_version") != 1:
        raise InstallError("release-notes.json schema_version 必须为 1")
    if release_notes.get("product_name") != PRODUCT_NAME:
        raise InstallError("release-notes.json product_name 不正确")
    if release_notes.get("version") != version:
        raise InstallError("release-notes.json version 必须与根 VERSION 一致")
    highlights = release_notes.get("release_highlights")
    if not isinstance(highlights, list) or len(highlights) < 3:
        raise InstallError("release-notes.json 至少需要三条 release_highlights")
    official_guide = release_notes.get("official_guide")
    if not isinstance(official_guide, dict):
        raise InstallError("release-notes.json 缺少 official_guide")
    if official_guide.get("headline") != OFFICIAL_GUIDE_HEADLINE:
        raise InstallError("官方指南文案与发布真源不一致")
    for key in ("maintainer", "public_account", "headline", "body"):
        if not isinstance(official_guide.get(key), str) or not official_guide[key].strip():
            raise InstallError(f"official_guide.{key} 必须是非空字符串")
    install_help = release_notes.get("install_help")
    expected_install_help = {
        "source_directory_note": "请在 Eva-skill 源码根目录手动执行；安装和更新使用同一命令。",
        "install_or_update_command": "python3 scripts/eva_global_install.py install",
        "verify_command": "python3 scripts/eva_global_install.py verify",
        "recover_command": "python3 scripts/eva_global_install.py recover",
    }
    if not isinstance(install_help, dict):
        raise InstallError("release-notes.json 缺少 install_help")
    for key, expected_value in expected_install_help.items():
        if install_help.get(key) != expected_value:
            raise InstallError(f"install_help.{key} 与受管安装命令不一致")

    return {
        "version": version,
        "manifest": manifest,
        "release_notes": release_notes,
        "directories": tuple(directories),
    }


def validate_source_bundle(source_root: Path, release: dict[str, Any]) -> None:
    skills_root = source_root / "skills"
    if not skills_root.is_dir():
        raise InstallError(f"缺少 skills 目录：{skills_root}")
    for skill_name in release["directories"]:
        assert_real_tree(skills_root / skill_name, skill_name)
    required_shared_paths = (
        "scripts/eva_doctor.py",
        "scripts/eva_prompt_lint.py",
        "scripts/eva_selftest.py",
        "references/maintenance/install-manifest.json",
        "references/maintenance/release-notes.json",
        "references/maintenance/00_eva-maintenance-notice.md",
    )
    for relative in required_shared_paths:
        path = skills_root / "eva-shared" / relative
        if not path.exists():
            raise InstallError(f"eva-shared 缺少安装所需文件：{relative}")


def copy_skill_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        symlinks=False,
        ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"),
    )


def stage_bundle(source_root: Path, transaction_root: Path, release: dict[str, Any]) -> Path:
    staged_root = transaction_root / "stage"
    if staged_root.exists():
        raise InstallError(f"安装暂存目录已存在：{staged_root}")
    staged_root.mkdir(parents=True)
    for skill_name in release["directories"]:
        source = source_root / "skills" / skill_name
        destination = staged_root / skill_name
        copy_skill_tree(source, destination)
        assert_real_tree(destination, skill_name)
    return staged_root


def command_output(process: subprocess.CompletedProcess[str]) -> str:
    parts = [part.strip() for part in (process.stdout, process.stderr) if part and part.strip()]
    return "\n".join(parts)


def run_bundle_checks(bundle_root: Path) -> None:
    shared_root = bundle_root / "eva-shared"
    doctor = shared_root / "scripts" / "eva_doctor.py"
    prompt_lint = shared_root / "scripts" / "eva_prompt_lint.py"
    selftest = shared_root / "scripts" / "eva_selftest.py"
    for skill_name in MANAGED_SKILL_DIRS:
        assert_real_tree(bundle_root / skill_name, skill_name)
    with tempfile.TemporaryDirectory(prefix="eva-global-install-check-") as cache_dir:
        env = os.environ.copy()
        env["PYTHONPYCACHEPREFIX"] = cache_dir
        for label, script in (
            ("doctor", doctor),
            ("prompt lint", prompt_lint),
            ("selftest", selftest),
        ):
            try:
                process = subprocess.run(
                    [sys.executable, str(script), "--base", str(shared_root)],
                    cwd=str(bundle_root),
                    text=True,
                    capture_output=True,
                    env=env,
                    check=False,
                    timeout=120,
                )
            except subprocess.TimeoutExpired as exc:
                raise InstallError(f"暂存包 {label} 校验超时") from exc
            if process.returncode != 0:
                output = command_output(process)
                raise InstallError(f"暂存包 {label} 校验失败：{output or '无输出'}")


def detected_bundle_version(bundle_root: Path) -> str | None:
    common = bundle_root / "eva-shared" / "scripts" / "eva_common.py"
    if not common.exists():
        return None
    match = re.search(
        r"^VERSION\s*=\s*['\"]eva-shared-(\d+\.\d+\.\d+)['\"]\s*$",
        common.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    return match.group(1) if match else None


def inspect_installed_bundle(target_root: Path) -> dict[str, Any]:
    existing = [
        name
        for name in MANAGED_SKILL_DIRS
        if (target_root / name).exists() or (target_root / name).is_symlink()
    ]
    if not existing:
        return {"present": False, "valid": False, "version": None, "errors": []}
    errors: list[str] = []
    missing = [name for name in MANAGED_SKILL_DIRS if name not in existing]
    if missing:
        errors.append("缺少受管 Skill 目录：" + "、".join(missing))
    for skill_name in MANAGED_SKILL_DIRS:
        if skill_name not in existing:
            continue
        try:
            assert_real_tree(target_root / skill_name, skill_name)
        except InstallError as exc:
            errors.append(str(exc))
    detected_version = detected_bundle_version(target_root)
    if detected_version is None:
        errors.append("无法从 eva-shared/scripts/eva_common.py 识别已安装版本")
    return {
        "present": True,
        "valid": not errors,
        "version": detected_version,
        "errors": errors,
    }


def parse_version(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", value):
        raise InstallError(f"无法比较非标准版本号：{value!r}")
    return tuple(int(piece) for piece in value.split("."))  # type: ignore[return-value]


def read_state(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, None
    try:
        payload = read_json(path)
    except InstallError as exc:
        return None, str(exc)
    if not isinstance(payload, dict):
        return None, "安装状态不是对象"
    return payload, None


def state_is_managed(state: dict[str, Any] | None, target_root: Path) -> bool:
    if not state or state.get("schema_version") != STATE_SCHEMA_VERSION:
        return False
    if state.get("product_name") != PRODUCT_NAME:
        return False
    if state.get("target_root") != str(target_root):
        return False
    return state.get("managed_directories") == list(MANAGED_SKILL_DIRS)


def new_notice(release: dict[str, Any], action: str) -> dict[str, str]:
    return {
        "id": uuid.uuid4().hex,
        "action": action,
        "version": release["version"],
        "created_at": utc_now(),
    }


def build_state(
    release: dict[str, Any],
    target_root: Path,
    action: str,
    transaction_id: str,
    notice: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "product_name": PRODUCT_NAME,
        "installed_version": release["version"],
        "target_root": str(target_root),
        "managed_directories": list(MANAGED_SKILL_DIRS),
        "installed_at": utc_now(),
        "transaction_id": transaction_id,
        "last_action": action,
        "notice_pending": True,
        "pending_notice": notice,
    }


def compare_or_reject_downgrade(current_version: str | None, target_version: str, allow: bool) -> None:
    if current_version and parse_version(current_version) > parse_version(target_version) and not allow:
        raise InstallError(
            f"拒绝从 {current_version} 降级到 {target_version}；如确有需要，请显式传入 --allow-downgrade"
        )


def classify_install(
    current: dict[str, Any],
    state: dict[str, Any] | None,
    target_root: Path,
    release: dict[str, Any],
    allow_downgrade: bool,
    force: bool,
) -> str:
    current_version = current.get("version")
    protected_versions: list[str] = []
    if isinstance(current_version, str) and current_version:
        protected_versions.append(current_version)
    if state_is_managed(state, target_root) and state is not None:
        managed_version = state.get("installed_version")
        if isinstance(managed_version, str) and managed_version and managed_version not in protected_versions:
            protected_versions.append(managed_version)
    for protected_version in protected_versions:
        compare_or_reject_downgrade(protected_version, release["version"], allow_downgrade)
    if current.get("valid"):
        if (
            current_version == release["version"]
            and state_is_managed(state, target_root)
            and state is not None
            and state.get("installed_version") == release["version"]
            and not force
        ):
            return "unchanged"
        if current_version == release["version"]:
            return "migrated"
        return "updated" if state_is_managed(state, target_root) else "migrated"
    if current.get("present"):
        return "repaired"
    return "installed"


def ensure_same_filesystem(target_root: Path, paths: tuple[Path, ...]) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    device = target_root.stat().st_dev
    for path in paths:
        ensure_private_directory(path, "安装控制目录")
        if path.stat().st_dev != device:
            raise InstallError(f"事务目录必须与目标 Skill 根目录在同一文件系统：{path}")


def move_path(source: Path, destination: Path) -> None:
    if not source.exists() and not source.is_symlink():
        raise InstallError(f"无法移动不存在的路径：{source}")
    if destination.exists() or destination.is_symlink():
        raise InstallError(f"移动目标已存在，拒绝覆盖：{destination}")
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)
    except OSError as exc:
        raise InstallError(f"无法移动 {source} -> {destination}：{exc}") from exc


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def paths_overlap(left: Path, right: Path) -> bool:
    return is_within(left, right) or is_within(right, left)


def validate_path_topology(
    target_root: Path,
    state_file: Path,
    transactions_root: Path,
    backups_root: Path,
    source_root: Path | None = None,
) -> None:
    """Keep source, active Skills, state, transactions, and backups disjoint."""
    if state_file.exists() and state_file.is_dir():
        raise InstallError(f"安装状态路径不能是目录：{state_file}")

    directories = (
        ("目标 Skill 根目录", target_root),
        ("事务根目录", transactions_root),
        ("备份根目录", backups_root),
    )
    for index, (left_label, left_path) in enumerate(directories):
        for right_label, right_path in directories[index + 1 :]:
            if paths_overlap(left_path, right_path):
                raise InstallError(f"{left_label}与{right_label}不能重叠：{left_path} / {right_path}")

    protected_roots = list(directories)
    if source_root is not None:
        if paths_overlap(source_root, target_root):
            raise InstallError("目标 Skill 根目录不能与 Eva-skill 源码目录重叠")
        for label, path in directories[1:]:
            if paths_overlap(source_root, path):
                raise InstallError(f"{label}不能与 Eva-skill 源码目录重叠：{path}")
        protected_roots.append(("Eva-skill 源码目录", source_root))

    for label, root in protected_roots:
        if is_within(state_file, root):
            raise InstallError(f"安装状态文件必须位于{label}之外：{state_file}")
    lock_file = target_root.parent / "eva-skill-install.lock"
    if state_file == lock_file:
        raise InstallError(f"安装状态文件不能覆盖安装锁：{state_file}")


def path_kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "missing"


def journal_path(transaction_root: Path) -> Path:
    return transaction_root / "transaction.json"


def save_journal(transaction_root: Path, payload: dict[str, Any]) -> None:
    write_json_atomic(journal_path(transaction_root), payload)


def reserve_previous_state(state_file: Path, transaction_root: Path) -> dict[str, Any]:
    snapshot = {"existed": state_file.exists(), "path": str(state_file)}
    if state_file.exists():
        prior = transaction_root / "previous-state.json"
        shutil.copy2(state_file, prior)
        snapshot["backup"] = str(prior)
    return snapshot


def restore_previous_state(snapshot: dict[str, Any], state_file: Path) -> None:
    if snapshot.get("existed"):
        backup = Path(str(snapshot.get("backup", "")))
        if not backup.exists():
            raise InstallError("无法恢复原安装状态：缺少 previous-state.json")
        write_text_atomic(state_file, backup.read_text(encoding="utf-8"))
    elif state_file.exists() or state_file.is_symlink():
        state_file.unlink()


def rollback_transaction(
    target_root: Path,
    transaction_root: Path,
    backup_root: Path,
    journal: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    failed_root = transaction_root / "failed-install"
    installed_names = list(journal.get("installed_names") or [])
    original_names = set(journal.get("original_names") or [])
    original_entry_types = dict(journal.get("original_entry_types") or {})
    backed_up_names = set(journal.get("backed_up_names") or [])
    restored_names = set(journal.get("restored_names") or [])

    def persist_progress() -> bool:
        try:
            save_journal(transaction_root, journal)
            return True
        except Exception as exc:
            errors.append(f"无法持久化回滚进度：{exc}")
            return False

    backing_up_name = journal.get("backing_up_name")
    if isinstance(backing_up_name, str):
        backup = backup_root / backing_up_name
        current = target_root / backing_up_name
        backup_exists = backup.exists() or backup.is_symlink()
        current_exists = current.exists() or current.is_symlink()
        if backup_exists and not current_exists:
            backed_up_names.add(backing_up_name)
            if backing_up_name not in journal["backed_up_names"]:
                journal["backed_up_names"].append(backing_up_name)
            journal["backing_up_name"] = None
            if not persist_progress():
                return errors
        elif current_exists and not backup_exists:
            journal["backing_up_name"] = None
            if not persist_progress():
                return errors
        elif backup_exists == current_exists:
            errors.append(
                f"无法判断备份中断点：{backing_up_name} "
                f"(target={current_exists}, backup={backup_exists})"
            )

    restoring_name = journal.get("restoring_name")
    if isinstance(restoring_name, str):
        backup = backup_root / restoring_name
        current = target_root / restoring_name
        backup_exists = backup.exists() or backup.is_symlink()
        current_exists = current.exists() or current.is_symlink()
        if current_exists and not backup_exists:
            if path_kind(current) != original_entry_types.get(restoring_name):
                errors.append(f"恢复后的旧模块类型与事务记录不一致：{restoring_name}")
            else:
                restored_names.add(restoring_name)
                if restoring_name not in journal["restored_names"]:
                    journal["restored_names"].append(restoring_name)
                journal["restoring_name"] = None
                if not persist_progress():
                    return errors
        elif backup_exists and not current_exists:
            pass
        else:
            errors.append(
                f"无法判断恢复中断点：{restoring_name} "
                f"(target={current_exists}, backup={backup_exists})"
            )

    activating_name = journal.get("activating_name")
    if isinstance(activating_name, str) and activating_name not in installed_names:
        current = target_root / activating_name
        staged = transaction_root / "stage" / activating_name
        failed = failed_root / activating_name
        current_exists = current.exists() or current.is_symlink()
        staged_exists = staged.exists() or staged.is_symlink()
        failed_exists = failed.exists() or failed.is_symlink()
        if (current_exists and not staged_exists) or (failed_exists and not current_exists):
            installed_names.append(activating_name)
        elif staged_exists and not current_exists:
            pass
        else:
            errors.append(
                f"无法判断激活中断点：{activating_name} "
                f"(target={current_exists}, stage={staged_exists}, failed={failed_exists})"
            )
    installed_names = [name for name in installed_names if name in MANAGED_SKILL_DIRS]

    for name in backed_up_names - restored_names:
        backup = backup_root / name
        if not (backup.exists() or backup.is_symlink()):
            errors.append(f"无法回滚：已记录的旧模块备份缺失：{backup}")
    for name in restored_names:
        current = target_root / name
        if not (current.exists() or current.is_symlink()):
            errors.append(f"无法回滚：已记录恢复完成的旧模块不在目标目录：{current}")
        elif path_kind(current) != original_entry_types.get(name):
            errors.append(f"恢复后的旧模块类型与事务记录不一致：{name}")
    for name in original_names - backed_up_names:
        current = target_root / name
        if not (current.exists() or current.is_symlink()):
            errors.append(f"无法回滚：未备份的旧模块也不在目标目录：{current}")
    if errors:
        return errors

    for name in reversed(installed_names):
        if name in restored_names:
            continue
        current = target_root / name
        failed = failed_root / name
        current_exists = current.exists() or current.is_symlink()
        failed_exists = failed.exists() or failed.is_symlink()
        if current_exists and failed_exists:
            errors.append(f"回滚冲突：目标与失败副本同时存在：{name}")
        elif current_exists:
            try:
                move_path(current, failed)
            except InstallError as exc:
                errors.append(str(exc))
        elif not failed_exists and not (transaction_root / "stage" / name).exists():
            errors.append(f"回滚时找不到已激活模块及其失败副本：{name}")
    if errors:
        return errors

    for name in MANAGED_SKILL_DIRS:
        backup = backup_root / name
        target = target_root / name
        if name not in backed_up_names or name in restored_names:
            continue
        displaced = failed_root / f"pre-restore-{name}"
        target_exists = target.exists() or target.is_symlink()
        displaced_exists = displaced.exists() or displaced.is_symlink()
        if target_exists and displaced_exists:
            errors.append(f"恢复冲突：目标与待恢复前副本同时存在：{name}")
            continue
        if target_exists:
            try:
                move_path(target, displaced)
            except InstallError as exc:
                errors.append(str(exc))
                continue
        journal["restoring_name"] = name
        if not persist_progress():
            return errors
        try:
            move_path(backup, target)
        except InstallError as exc:
            errors.append(str(exc))
            continue
        journal["restored_names"].append(name)
        journal["restoring_name"] = None
        if not persist_progress():
            return errors
    return errors


def restore_state_from_journal(transaction_root: Path, journal: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    state_file_raw = journal.get("state_file")
    snapshot = journal.get("previous_state")
    if state_file_raw is None and snapshot is None:
        return errors
    if not isinstance(state_file_raw, str) or not isinstance(snapshot, dict):
        return ["恢复事务缺少有效的旧状态快照信息"]
    state_file = expanded_path(state_file_raw)
    if snapshot.get("path") != str(state_file):
        return ["恢复事务的状态路径与旧状态快照不一致"]
    backup_raw = snapshot.get("backup")
    if backup_raw is not None:
        if not isinstance(backup_raw, str) or not is_within(Path(backup_raw), transaction_root):
            return ["恢复事务的旧状态快照不在当前事务目录内"]
    try:
        restore_previous_state(snapshot, state_file)
    except (InstallError, OSError) as exc:
        errors.append(str(exc))
    return errors


def validate_recovery_journal(
    transaction_root: Path,
    journal: dict[str, Any],
    target_root: Path,
    transactions_root: Path,
    backups_root: Path,
    expected_state_file: Path | None,
) -> tuple[str, Path]:
    if transaction_root.is_symlink() or transaction_root.parent.resolve() != transactions_root.resolve():
        raise InstallError(f"事务目录必须是事务根目录下的真实一级目录：{transaction_root}")
    if journal.get("schema_version") != 1 or journal.get("product_name") != PRODUCT_NAME:
        raise InstallError(f"事务日志身份无效：{transaction_root.name}")
    if journal.get("transaction_id") != transaction_root.name:
        raise InstallError(f"事务日志 ID 与目录名不一致：{transaction_root.name}")
    if journal.get("target_root") != str(target_root):
        raise InstallError(f"事务日志目标目录与本次恢复不一致：{transaction_root.name}")
    if journal.get("managed_directories") != list(MANAGED_SKILL_DIRS):
        raise InstallError(f"事务日志受管目录清单无效：{transaction_root.name}")

    status = journal.get("status")
    allowed_statuses = {
        "staged",
        "activating",
        "postcheck",
        "committed",
        "rolled-back",
        "rollback-failed",
    }
    if status not in allowed_statuses:
        raise InstallError(f"事务日志状态无效：{transaction_root.name} / {status!r}")

    backup_root_raw = journal.get("backup_root")
    if not isinstance(backup_root_raw, str):
        raise InstallError(f"事务日志缺少备份目录：{transaction_root.name}")
    raw_backup_root = Path(backup_root_raw).expanduser()
    if raw_backup_root.is_symlink():
        raise InstallError(f"事务备份目录不能是 symlink：{transaction_root.name}")
    backup_root = expanded_path(backup_root_raw)
    expected_backup_root = (backups_root / transaction_root.name).resolve()
    if backup_root != expected_backup_root or backup_root.is_symlink():
        raise InstallError(f"事务备份目录与事务 ID 不一致：{transaction_root.name}")

    state_file_raw = journal.get("state_file")
    snapshot = journal.get("previous_state")
    if not isinstance(state_file_raw, str) or not isinstance(snapshot, dict):
        raise InstallError(f"事务日志缺少状态快照：{transaction_root.name}")
    state_file = expanded_path(state_file_raw)
    if expected_state_file is not None and state_file != expected_state_file:
        raise InstallError("恢复事务的状态文件与本次 recover 参数不一致")
    if snapshot.get("path") != str(state_file) or not isinstance(snapshot.get("existed"), bool):
        raise InstallError(f"事务日志状态快照无效：{transaction_root.name}")
    backup_state_raw = snapshot.get("backup")
    if snapshot.get("existed"):
        expected_state_backup = (transaction_root / "previous-state.json").resolve()
        if not isinstance(backup_state_raw, str) or expanded_path(backup_state_raw) != expected_state_backup:
            raise InstallError(f"事务日志旧状态备份无效：{transaction_root.name}")
        state_backup_path = transaction_root / "previous-state.json"
        if state_backup_path.is_symlink() or not state_backup_path.is_file():
            raise InstallError(f"事务日志旧状态备份必须是真实文件：{transaction_root.name}")
    elif backup_state_raw is not None:
        raise InstallError(f"不存在旧状态时不得声明状态备份：{transaction_root.name}")

    def checked_names(field: str) -> list[str]:
        raw = journal.get(field)
        if not isinstance(raw, list) or any(not isinstance(name, str) for name in raw):
            raise InstallError(f"事务日志 {field} 无效：{transaction_root.name}")
        if len(raw) != len(set(raw)) or any(name not in MANAGED_SKILL_DIRS for name in raw):
            raise InstallError(f"事务日志 {field} 超出受管目录：{transaction_root.name}")
        return raw

    original_names = checked_names("original_names")
    checked_names("installed_names")
    backed_up_names = checked_names("backed_up_names")
    if any(name not in original_names for name in backed_up_names):
        raise InstallError(f"事务日志 backed_up_names 超出原目录：{transaction_root.name}")
    backing_up_name = journal.get("backing_up_name")
    if backing_up_name is not None and (
        backing_up_name not in original_names or backing_up_name in backed_up_names
    ):
        raise InstallError(f"事务日志 backing_up_name 无效：{transaction_root.name}")
    restored_names = checked_names("restored_names")
    if any(name not in backed_up_names for name in restored_names):
        raise InstallError(f"事务日志 restored_names 超出已备份目录：{transaction_root.name}")
    restoring_name = journal.get("restoring_name")
    if restoring_name is not None and (
        restoring_name not in backed_up_names or restoring_name in restored_names
    ):
        raise InstallError(f"事务日志 restoring_name 无效：{transaction_root.name}")
    activating_name = journal.get("activating_name")
    if activating_name is not None and activating_name not in MANAGED_SKILL_DIRS:
        raise InstallError(f"事务日志 activating_name 无效：{transaction_root.name}")

    original_entry_types = journal.get("original_entry_types")
    if not isinstance(original_entry_types, dict) or set(original_entry_types) != set(original_names):
        raise InstallError(f"事务日志缺少原目录类型清单：{transaction_root.name}")
    if any(kind not in {"directory", "file", "symlink"} for kind in original_entry_types.values()):
        raise InstallError(f"事务日志原目录类型无效：{transaction_root.name}")
    installed_names = journal.get("installed_names") or []
    if (installed_names or activating_name is not None or status == "postcheck") and (
        set(backed_up_names) != set(original_names) or backing_up_name is not None
    ):
        raise InstallError(f"事务已进入激活阶段但旧目录备份记录不完整：{transaction_root.name}")
    for name in original_names:
        backup = backup_root / name
        if backup.exists() or backup.is_symlink():
            if path_kind(backup) != original_entry_types[name]:
                raise InstallError(f"事务备份类型与日志不一致：{transaction_root.name} / {name}")

    validate_path_topology(
        target_root,
        state_file,
        transactions_root,
        backups_root,
    )
    return status, backup_root


def finalize_rollback(
    transaction_root: Path,
    journal: dict[str, Any],
    errors: list[str],
) -> list[str]:
    journal["status"] = "rolled-back" if not errors else "rollback-failed"
    journal["rolled_back_at"] = utc_now()
    journal["rollback_errors"] = errors
    journal["activating_name"] = None
    journal["backing_up_name"] = None
    journal["restoring_name"] = None
    try:
        save_journal(transaction_root, journal)
    except Exception as exc:
        errors.append(f"无法写入回滚事务状态：{exc}")
    return errors


def cleanup_proven_pre_activation_orphan(
    transaction_root: Path,
    backups_root: Path,
) -> bool:
    """Remove only an orphan that cannot have started target activation."""
    allowed_files = {"previous-state.json"}
    for child in transaction_root.iterdir():
        if child.is_symlink() or not child.is_file():
            return False
        if child.name not in allowed_files and not child.name.startswith(".eva-write-"):
            return False

    backup_root = backups_root / transaction_root.name
    if backup_root.is_symlink():
        return False
    if backup_root.exists():
        if not backup_root.is_dir() or any(backup_root.iterdir()):
            return False

    shutil.rmtree(transaction_root)
    if backup_root.exists():
        shutil.rmtree(backup_root)
    return True


def recover_pending_transactions(
    target_root: Path,
    transactions_root: Path,
    backups_root: Path,
    expected_state_file: Path | None = None,
    requested: bool = False,
) -> list[str]:
    notices: list[str] = []
    if not transactions_root.exists():
        return notices
    for transaction_root in sorted(transactions_root.iterdir()):
        if transaction_root.is_symlink():
            raise InstallError(f"事务根目录中不能包含 symlink：{transaction_root}")
        if not transaction_root.is_dir():
            continue
        journal_file = journal_path(transaction_root)
        if not journal_file.exists():
            if cleanup_proven_pre_activation_orphan(transaction_root, backups_root):
                notices.append(f"已清理未开始替换的孤立事务：{transaction_root.name}")
                continue
            raise InstallError(f"发现无法证明安全的无日志事务目录：{transaction_root}")
        if journal_file.is_symlink() or not journal_file.is_file():
            raise InstallError(f"transaction.json 必须是真实文件：{journal_file}")
        try:
            journal = read_json(journal_file)
        except InstallError as exc:
            raise InstallError(f"无法读取事务日志，拒绝假装恢复成功：{transaction_root}：{exc}") from exc
        if not isinstance(journal, dict):
            raise InstallError(f"事务日志必须是对象：{transaction_root}")
        if journal.get("target_root") != str(target_root):
            continue
        if journal.get("status") in {"committed", "rolled-back"}:
            continue
        status, backup_root = validate_recovery_journal(
            transaction_root,
            journal,
            target_root,
            transactions_root,
            backups_root,
            expected_state_file,
        )
        if status == "staged":
            rollback_errors: list[str] = []
            finalize_rollback(transaction_root, journal, rollback_errors)
            if rollback_errors:
                raise InstallError("恢复未完成事务失败：" + "；".join(rollback_errors))
            notices.append(f"已清理未激活的暂存事务：{transaction_root.name}")
            continue
        rollback_errors = rollback_transaction(target_root, transaction_root, backup_root, journal)
        if not rollback_errors:
            rollback_errors.extend(restore_state_from_journal(transaction_root, journal))
        finalize_rollback(transaction_root, journal, rollback_errors)
        if rollback_errors:
            raise InstallError("恢复未完成事务失败：" + "；".join(rollback_errors))
        notices.append(f"已恢复未完成事务：{transaction_root.name}")
    if requested and not notices:
        notices.append("没有需要恢复的未完成事务")
    return notices


def render_notice(release: dict[str, Any], notice: dict[str, str]) -> str:
    action_label = {
        "installed": "已完成安装",
        "updated": "已完成升级",
        "migrated": "已完成受管安装迁移",
        "repaired": "已完成修复安装",
    }.get(notice["action"], "已完成安装")
    highlights = release["release_notes"]["release_highlights"]
    guide = release["release_notes"]["official_guide"]
    lines = [
        f"Eva-skill v{notice['version']} {action_label}",
        "",
        "本次变化：",
        *[f"- {item}" for item in highlights],
        "",
        guide["headline"],
        guide["body"],
    ]
    return "\n".join(lines)


def serialize_result(ok: bool, summary: str, **data: Any) -> dict[str, Any]:
    return {"ok": ok, "summary": summary, **data}


def install(args: argparse.Namespace) -> dict[str, Any]:
    source_root = expanded_path(args.source_root)
    target_root = expanded_path(args.target_root)
    state_file = expanded_path(args.state_file) if args.state_file else default_state_file(target_root)
    transactions_root = (
        expanded_path(args.transactions_root)
        if args.transactions_root
        else default_transactions_root(target_root)
    )
    backups_root = (
        expanded_path(args.backups_root)
        if args.backups_root
        else default_backups_root(target_root)
    )
    validate_path_topology(
        target_root,
        state_file,
        transactions_root,
        backups_root,
        source_root,
    )
    release = load_release(source_root)
    validate_source_bundle(source_root, release)
    ensure_same_filesystem(target_root, (transactions_root, backups_root, state_file.parent))

    with installation_lock(target_root):
        recovered = recover_pending_transactions(
            target_root,
            transactions_root,
            backups_root,
            expected_state_file=state_file,
        )
        prior_state, state_error = read_state(state_file)
        current = inspect_installed_bundle(target_root)
        if current.get("valid") and current.get("version") == release["version"]:
            try:
                assert_bundle_matches_source(source_root, target_root)
            except InstallError as exc:
                current["valid"] = False
                current["errors"].append(str(exc))
        action = classify_install(
            current,
            prior_state,
            target_root,
            release,
            args.allow_downgrade,
            args.force,
        )
        if action == "unchanged":
            pending_notice = (
                prior_state.get("pending_notice")
                if prior_state and prior_state.get("notice_pending")
                else None
            )
            rendered_notice = (
                render_notice(release, pending_notice)
                if isinstance(pending_notice, dict)
                and pending_notice.get("version") == release["version"]
                and pending_notice.get("action")
                else None
            )
            return serialize_result(
                True,
                f"Eva-skill v{release['version']} 已是受管且有效的当前版本",
                action=action,
                version=release["version"],
                target_root=str(target_root),
                notice=pending_notice,
                rendered_notice=rendered_notice,
                recovered=recovered,
            )

        transaction_id = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:10]}"
        transaction_root = transactions_root / transaction_id
        backup_root = backups_root / transaction_id
        transaction_root.mkdir(mode=0o700, parents=True)
        backup_root.mkdir(mode=0o700, parents=True)
        try:
            original_names = [
                name
                for name in MANAGED_SKILL_DIRS
                if (target_root / name).exists() or (target_root / name).is_symlink()
            ]
            original_entry_types = {
                name: path_kind(target_root / name)
                for name in original_names
            }
            prior_state_snapshot = reserve_previous_state(state_file, transaction_root)
            journal: dict[str, Any] = {
                "schema_version": 1,
                "product_name": PRODUCT_NAME,
                "transaction_id": transaction_id,
                "target_root": str(target_root),
                "backup_root": str(backup_root),
                "source_root": str(source_root),
                "version": release["version"],
                "managed_directories": list(MANAGED_SKILL_DIRS),
                "original_names": original_names,
                "original_entry_types": original_entry_types,
                "backed_up_names": [],
                "backing_up_name": None,
                "restored_names": [],
                "restoring_name": None,
                "installed_names": [],
                "activating_name": None,
                "state_file": str(state_file),
                "previous_state": prior_state_snapshot,
                "status": "staged",
                "created_at": utc_now(),
            }
            save_journal(transaction_root, journal)
            staged_root = stage_bundle(source_root, transaction_root, release)
            run_bundle_checks(staged_root)
        except Exception:
            shutil.rmtree(transaction_root, ignore_errors=True)
            shutil.rmtree(backup_root, ignore_errors=True)
            raise

        try:
            journal["status"] = "activating"
            save_journal(transaction_root, journal)
            for name in original_names:
                journal["backing_up_name"] = name
                save_journal(transaction_root, journal)
                move_path(target_root / name, backup_root / name)
                journal["backed_up_names"].append(name)
                journal["backing_up_name"] = None
                save_journal(transaction_root, journal)
            for name in MANAGED_SKILL_DIRS:
                journal["activating_name"] = name
                save_journal(transaction_root, journal)
                move_path(staged_root / name, target_root / name)
                journal["installed_names"].append(name)
                journal["activating_name"] = None
                save_journal(transaction_root, journal)
            journal["status"] = "postcheck"
            save_journal(transaction_root, journal)
            assert_bundle_matches_source(source_root, target_root)

            notice = new_notice(release, action)
            state = build_state(release, target_root, action, transaction_id, notice)
            write_json_atomic(state_file, state)
            journal["status"] = "committed"
            journal["committed_at"] = utc_now()
            save_journal(transaction_root, journal)
        except Exception as exc:
            rollback_errors = rollback_transaction(target_root, transaction_root, backup_root, journal)
            if not rollback_errors:
                try:
                    restore_previous_state(prior_state_snapshot, state_file)
                except (InstallError, OSError) as restore_exc:
                    rollback_errors.append(str(restore_exc))
            finalize_rollback(transaction_root, journal, rollback_errors)
            detail = str(exc)
            if rollback_errors:
                detail += "；回滚异常：" + "；".join(rollback_errors)
            raise InstallError(f"安装失败，已尝试恢复旧版本：{detail}") from exc

    action_summary = {
        "installed": "安装完成",
        "updated": "升级完成",
        "migrated": "受管安装迁移完成",
        "repaired": "修复安装完成",
    }.get(action, "安装完成")
    return serialize_result(
        True,
        f"Eva-skill v{release['version']} {action_summary}",
        action=action,
        version=release["version"],
        target_root=str(target_root),
        transaction_id=transaction_id,
        state_file=str(state_file),
        backup_root=str(backup_root),
        recovered=recovered,
        state_warning=state_error,
        notice=notice,
        rendered_notice=render_notice(release, notice),
    )


def verify(args: argparse.Namespace) -> dict[str, Any]:
    source_root = expanded_path(args.source_root)
    target_root = expanded_path(args.target_root)
    release = load_release(source_root)
    validate_source_bundle(source_root, release)
    if paths_overlap(source_root, target_root):
        raise InstallError("目标 Skill 根目录不能与 Eva-skill 源码目录重叠")
    if not target_root.exists():
        raise InstallError(f"尚未检测到 Eva-skill 安装目录：{target_root}")
    with installation_lock(target_root):
        current = inspect_installed_bundle(target_root)
        if not current["valid"]:
            detail = "；".join(current["errors"]) or "未检测到十个 Eva-skill 受管模块"
            raise InstallError("当前安装包校验失败：" + detail)
        assert_bundle_matches_source(source_root, target_root)
    return serialize_result(
        True,
        f"Eva-skill v{current['version'] or release['version']} 安装包校验通过",
        action="verified",
        target_root=str(target_root),
        detected_version=current["version"],
        managed_directories=list(MANAGED_SKILL_DIRS),
    )


def recover(args: argparse.Namespace) -> dict[str, Any]:
    target_root = expanded_path(args.target_root)
    state_file = expanded_path(args.state_file) if args.state_file else default_state_file(target_root)
    transactions_root = (
        expanded_path(args.transactions_root)
        if args.transactions_root
        else default_transactions_root(target_root)
    )
    backups_root = (
        expanded_path(args.backups_root)
        if args.backups_root
        else default_backups_root(target_root)
    )
    validate_path_topology(target_root, state_file, transactions_root, backups_root)
    ensure_same_filesystem(target_root, (transactions_root, backups_root, state_file.parent))
    with installation_lock(target_root):
        messages = recover_pending_transactions(
            target_root,
            transactions_root,
            backups_root,
            expected_state_file=state_file,
            requested=True,
        )
    return serialize_result(
        True,
        "；".join(messages),
        action="recovered",
        target_root=str(target_root),
        messages=messages,
    )


def acknowledge(args: argparse.Namespace) -> dict[str, Any]:
    state_file = expanded_path(args.state_file)
    state, error = read_state(state_file)
    if error or state is None:
        raise InstallError(f"没有可确认的安装状态：{error or state_file}")
    target_root_raw = state.get("target_root")
    if not isinstance(target_root_raw, str) or not target_root_raw:
        raise InstallError("安装状态缺少 target_root，无法安全确认提示")
    target_root = expanded_path(target_root_raw)
    if is_within(state_file, target_root):
        raise InstallError("安装状态文件必须位于目标 Skill 根目录之外")
    with installation_lock(target_root):
        state, error = read_state(state_file)
        if error or state is None:
            raise InstallError(f"没有可确认的安装状态：{error or state_file}")
        pending = state.get("pending_notice")
        if not state.get("notice_pending") or not isinstance(pending, dict):
            return serialize_result(
                True,
                "当前没有待展示的安装提示",
                action="acknowledged",
                notice_pending=False,
            )
        if pending.get("id") != args.notice_id:
            raise InstallError("notice_id 与待展示安装提示不一致，拒绝确认")
        state["notice_pending"] = False
        state["acknowledged_notice_id"] = args.notice_id
        state["acknowledged_at"] = utc_now()
        state.pop("pending_notice", None)
        write_json_atomic(state_file, state)
    return serialize_result(True, "已确认安装提示已展示", action="acknowledged", notice_pending=False)


def parser() -> argparse.ArgumentParser:
    root = source_root_from_script()
    target = default_target_root()
    command_parser = argparse.ArgumentParser(
        description="Managed installer for the ten real Eva-skill directories."
    )
    subcommands = command_parser.add_subparsers(dest="command", required=True)

    def shared_options(subparser: argparse.ArgumentParser, include_state: bool = True) -> None:
        subparser.add_argument("--source-root", default=str(root), help="Eva-skill source repository root")
        subparser.add_argument("--target-root", default=str(target), help="Host Skill discovery root")
        if include_state:
            subparser.add_argument("--state-file", default=None)
        subparser.add_argument("--transactions-root", default=None)
        subparser.add_argument("--backups-root", default=None)
        subparser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only")

    install_parser = subcommands.add_parser("install", help="Stage, validate, and install Eva-skill")
    shared_options(install_parser)
    install_parser.add_argument("--allow-downgrade", action="store_true")
    install_parser.add_argument("--force", action="store_true", help="Reinstall a valid managed same-version bundle")

    verify_parser = subcommands.add_parser(
        "verify",
        help="Validate the existing managed bundle without changing installed Skills or installation state",
    )
    shared_options(verify_parser, include_state=False)

    recover_parser = subcommands.add_parser("recover", help="Recover an interrupted managed installation")
    shared_options(recover_parser)

    ack_parser = subcommands.add_parser("ack", help="Mark a displayed installation notice as acknowledged")
    ack_parser.add_argument("--state-file", default=str(default_state_file(target)))
    ack_parser.add_argument("--notice-id", required=True)
    ack_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only")
    return command_parser


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            payload = install(args)
        elif args.command == "verify":
            payload = verify(args)
        elif args.command == "recover":
            payload = recover(args)
        elif args.command == "ack":
            payload = acknowledge(args)
        else:
            raise InstallError(f"未知命令：{args.command}")
    except (InstallError, OSError) as exc:
        payload = serialize_result(False, str(exc), action="failed")
        if not getattr(args, "json", False):
            print(payload["summary"], file=sys.stderr)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print(payload["summary"])
    if payload.get("rendered_notice"):
        print()
        print(payload["rendered_notice"])
        ack_args = argparse.Namespace(
            state_file=(
                expanded_path(args.state_file)
                if getattr(args, "state_file", None)
                else default_state_file(expanded_path(args.target_root))
            ),
            notice_id=payload["notice"]["id"],
        )
        acknowledge(ack_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
