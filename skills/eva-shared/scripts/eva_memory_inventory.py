#!/usr/bin/env python3
"""Read-only inventory for the current project's Eva memory cards."""

from __future__ import annotations

import argparse
import os
import re
import stat
import unicodedata
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from eva_common import (
    VALID_ASSET_TYPES,
    add_common_arguments,
    print_result,
    read_frontmatter_metadata,
    result,
    sha256_file,
)


MEMORY_FOLDER = "eva-memory"
MAX_SCAN_LIMIT = 10_000
DEFAULT_RECENT_DAYS = 30
DEFAULT_TOP_KEYWORDS = 10
MAX_RECENT_DAYS = 3650
MAX_TOP_KEYWORDS = 100
MAX_KEYWORDS_PER_CARD = 100
MAX_KEYWORD_CHARS = 100
MAX_TYPE_CHARS = 128
MAX_PATH_CHARS = 1024
MAX_DUPLICATE_GROUPS = 10
MAX_PATHS_PER_GROUP = 10

DIRECTORY_TYPE_HINTS = {
    "idea-cards": "idea-card",
    "idea-card": "idea-card",
    "ideas": "idea-card",
    "idea": "idea-card",
    "点子卡": "idea-card",
    "persona": "persona-card",
    "persona-cards": "persona-card",
    "persona-card": "persona-card",
    "人设": "persona-card",
    "voice": "voice-card",
    "voice-cards": "voice-card",
    "voice-card": "voice-card",
    "文风": "voice-card",
    "product-service": "product-service-card",
    "product-service-cards": "product-service-card",
    "product-service-card": "product-service-card",
    "产品与服务": "product-service-card",
}

TYPE_BUCKETS = (
    "idea-card",
    "persona-card",
    "voice-card",
    "product-service-card",
    "other-recognized",
    "unrecognized",
)

HEALTH_KEYS = (
    "missing_frontmatter",
    "malformed_frontmatter",
    "unclosed_frontmatter",
    "oversized_frontmatter",
    "decode_error_frontmatter",
    "unreadable_files",
    "missing_type",
    "unknown_type",
    "inferred_type",
    "conflicting_type_fields",
    "missing_created",
    "invalid_created",
    "future_created",
    "missing_keywords",
    "invalid_keywords",
    "metadata_field_truncations",
    "cards_with_index_issues",
    "skipped_symlinks",
    "skipped_outside_root",
    "skipped_non_regular",
    "skipped_hidden",
    "skipped_temp",
    "excluded_index",
    "scan_errors",
)


def _absolute_lexical_path(raw: str) -> Path:
    return Path(os.path.abspath(os.path.expanduser(raw)))


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


def _safe_text(value: object, limit: int) -> tuple[str, bool]:
    if value is None:
        return "", False
    if isinstance(value, (dict, list, tuple, set)):
        return "", False
    text = str(value).replace("\ufeff", "")
    text = " ".join(text.split())
    text = "".join(character if character.isprintable() else " " for character in text)
    text = " ".join(text.split()).strip()
    if len(text) > limit:
        return text[:limit].rstrip(), True
    return text, False


def _normalized_key(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _safe_relative_path(path: Path, memory_root: Path) -> str:
    try:
        relative = path.relative_to(memory_root).as_posix()
    except ValueError:
        return "[outside-memory-root]"
    safe, _ = _safe_text(relative, MAX_PATH_CHARS)
    return safe or "[invalid-path]"


def _markdown_escape(value: object) -> str:
    text, _ = _safe_text(value, MAX_PATH_CHARS)
    replacements = {
        "\\": "\\\\",
        "`": "\\`",
        "*": "\\*",
        "_": "\\_",
        "[": "\\[",
        "]": "\\]",
        "<": "&lt;",
        ">": "&gt;",
        "#": "\\#",
        "|": "\\|",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _is_hidden(relative: Path) -> bool:
    return any(part.startswith(".") for part in relative.parts)


def _is_temp_file(name: str) -> bool:
    lowered = name.casefold()
    return (
        name.startswith(("~", ".#"))
        or name.endswith("~")
        or lowered.endswith((".tmp", ".temp", ".swp", ".swo", ".bak"))
    )


def _directory_hint(relative: Path) -> str | None:
    for part in relative.parts[:-1]:
        hint = DIRECTORY_TYPE_HINTS.get(_normalized_key(part))
        if hint:
            return hint
    return None


def _normalized_declared_type(value: object) -> tuple[str, bool]:
    text, truncated = _safe_text(value, MAX_TYPE_CHARS)
    return text.strip(), truncated


def _parse_created(value: object, today: date) -> tuple[str | None, str]:
    text, _ = _safe_text(value, 32)
    if not text:
        return None, "missing"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None, "invalid"
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return None, "invalid"
    if parsed > today:
        return None, "future"
    return parsed.isoformat(), "valid"


def _extract_keywords(value: object) -> tuple[list[str], str, int]:
    if value is None or value == "":
        return [], "missing", 0
    if isinstance(value, str):
        raw_values: list[object] = [item for item in re.split(r"[,，、;；]", value) if item.strip()]
    elif isinstance(value, (list, tuple)):
        raw_values = list(value)
    else:
        return [], "invalid", 0

    keywords: list[str] = []
    seen: set[str] = set()
    truncations = 0
    invalid_items = 0
    for raw in raw_values[:MAX_KEYWORDS_PER_CARD]:
        keyword, truncated = _safe_text(raw, MAX_KEYWORD_CHARS)
        if truncated:
            truncations += 1
        if not keyword:
            invalid_items += 1
            continue
        normalized = _normalized_key(keyword)
        if normalized in seen:
            continue
        seen.add(normalized)
        keywords.append(keyword)
    if len(raw_values) > MAX_KEYWORDS_PER_CARD:
        truncations += 1
    status = "invalid" if invalid_items or not keywords else "valid"
    return keywords, status, truncations


def _empty_data(recent_days: int, top_keywords: int, as_of: date, scan_limit: int) -> dict[str, Any]:
    return {
        "memory_root": MEMORY_FOLDER,
        "root_status": "missing",
        "status": "missing",
        "partial": False,
        "scan_limit": scan_limit,
        "scan_limit_reached": False,
        "scanned_cards": 0,
        "total_cards": 0,
        "total_cards_complete": True,
        "duplicate_check_complete": True,
        "recognized_cards": 0,
        "pending_validation_count": 0,
        "type_counts": {key: 0 for key in TYPE_BUCKETS},
        "recognized_type_counts": {},
        "declared_type_counts": {},
        "inferred_type_counts": {},
        "classification_counts": {
            "declared_recognized": 0,
            "declared_unrecognized": 0,
            "inferred_from_directory": 0,
            "unclassified": 0,
        },
        "created": {
            "earliest": None,
            "latest": None,
            "as_of": as_of.isoformat(),
            "recent_days": recent_days,
            "recent_count": 0,
        },
        "top_keywords_limit": top_keywords,
        "top_keywords": [],
        "health": {key: 0 for key in HEALTH_KEYS},
        "duplicates": {
            "same_name_group_count": 0,
            "same_name_groups": [],
            "same_name_groups_truncated": False,
            "exact_content_group_count": 0,
            "exact_content_groups": [],
            "exact_content_groups_truncated": False,
        },
        "duplicate_groups": {
            "same_name": [],
            "exact_content": [],
        },
        "skipped": {
            "symlinks": 0,
            "outside_root": 0,
            "non_regular": 0,
            "hidden": 0,
            "temporary": 0,
            "index": 0,
        },
        "cards_included": False,
        "cards": [],
        "next_action": "可以按类型或关键词展开卡片元数据列表。",
    }


def _blocked_payload(
    data: dict[str, Any],
    root_status: str,
    summary: str,
    error: str,
) -> dict[str, Any]:
    data["root_status"] = root_status
    data["status"] = root_status
    data["partial"] = True
    data["scanned_cards"] = 0
    data["total_cards"] = None
    data["total_cards_complete"] = False
    data["duplicate_check_complete"] = False
    health = data.get("health") or {}
    data["skipped"] = {
        "symlinks": int(health.get("skipped_symlinks") or 0),
        "outside_root": int(health.get("skipped_outside_root") or 0),
        "non_regular": int(health.get("skipped_non_regular") or 0),
        "hidden": int(health.get("skipped_hidden") or 0),
        "temporary": int(health.get("skipped_temp") or 0),
        "index": int(health.get("excluded_index") or 0),
    }
    return result(False, "memory-inventory", summary, [error], [], data)


def inventory_project(
    project_root: Path,
    *,
    recent_days: int = DEFAULT_RECENT_DAYS,
    top_keywords: int = DEFAULT_TOP_KEYWORDS,
    scan_limit: int = MAX_SCAN_LIMIT,
    include_cards: bool = False,
    filter_type: str | None = None,
    filter_keyword: str | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    today = as_of or date.today()
    data = _empty_data(recent_days, top_keywords, today, scan_limit)
    normalized_filter_type = (filter_type or "").strip()
    normalized_filter_keyword_text = (filter_keyword or "").strip()

    if include_cards and not (normalized_filter_type or normalized_filter_keyword_text):
        return _blocked_payload(
            data,
            "invalid-filter",
            "展开卡片元数据时必须提供非空类型或关键词筛选",
            "include_cards requires a non-blank filter_type or filter_keyword",
        )
    if not include_cards and (normalized_filter_type or normalized_filter_keyword_text):
        return _blocked_payload(
            data,
            "invalid-filter",
            "类型或关键词筛选只能用于卡片元数据展开",
            "filter_type and filter_keyword require include_cards",
        )

    if project_root.is_symlink():
        data["health"]["skipped_symlinks"] = 1
        return _blocked_payload(data, "blocked-project-symlink", "项目根目录为符号链接，已拒绝扫描", "project root symlinks are not followed")
    if not project_root.exists():
        return _blocked_payload(data, "missing-project-root", "项目根目录不存在", "project root does not exist")
    if not project_root.is_dir():
        return _blocked_payload(data, "invalid-project-root", "项目根路径不是目录", "project root must be a directory")
    if _looks_like_eva_source_repo(project_root):
        return _blocked_payload(
            data,
            "refused-eva-source-repo",
            "已拒绝把 Eva-skill 源码仓库当作运行项目扫描",
            "choose the creator project that contains ./eva-memory, not the Eva-skill source repository",
        )

    memory_root = project_root / MEMORY_FOLDER
    if memory_root.is_symlink():
        data["health"]["skipped_symlinks"] = 1
        try:
            project_real = project_root.resolve(strict=True)
            target_real = memory_root.resolve(strict=False)
            if not _is_relative_to(target_real, project_real):
                data["health"]["skipped_outside_root"] = 1
        except OSError:
            pass
        return _blocked_payload(data, "blocked-memory-symlink", "记忆库根目录为符号链接，已拒绝扫描", "eva-memory root symlinks are not followed")
    if not memory_root.exists():
        return result(True, "memory-inventory", "当前项目尚未建立 eva-memory 记忆库", [], [], data)
    if not memory_root.is_dir():
        return _blocked_payload(data, "invalid-memory-root", "eva-memory 不是目录，无法扫描", "eva-memory must be a directory")

    try:
        memory_root_real = memory_root.resolve(strict=True)
        project_root_real = project_root.resolve(strict=True)
    except OSError:
        return _blocked_payload(data, "unreadable-memory-root", "无法读取 eva-memory 目录", "cannot resolve the memory root safely")
    if not _is_relative_to(memory_root_real, project_root_real):
        data["health"]["skipped_outside_root"] = 1
        return _blocked_payload(data, "outside-project-root", "eva-memory 越出当前项目，已拒绝扫描", "memory root must stay inside project root")

    type_buckets: Counter[str] = Counter()
    recognized_type_counts: Counter[str] = Counter()
    declared_type_counts: Counter[str] = Counter()
    inferred_type_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    keyword_counts: Counter[str] = Counter()
    keyword_labels: dict[str, str] = {}
    valid_dates: list[date] = []
    same_name_paths: defaultdict[str, list[str]] = defaultdict(list)
    exact_hash_paths: defaultdict[str, list[str]] = defaultdict(list)
    card_records: list[dict[str, Any]] = []
    health: Counter[str] = Counter()
    warnings: list[str] = []
    total_cards = 0
    recognized_cards = 0
    pending_validation_count = 0
    walk_errors = 0

    def on_walk_error(_: OSError) -> None:
        nonlocal walk_errors
        walk_errors += 1

    stop_scan = False
    for current_raw, directory_names, file_names in os.walk(
        memory_root,
        topdown=True,
        followlinks=False,
        onerror=on_walk_error,
    ):
        current = Path(current_raw)
        safe_directories: list[str] = []
        for directory_name in sorted(directory_names, key=str.casefold):
            candidate = current / directory_name
            relative = candidate.relative_to(memory_root)
            if _is_hidden(relative):
                health["skipped_hidden"] += 1
                continue
            if candidate.is_symlink():
                health["skipped_symlinks"] += 1
                try:
                    if not _is_relative_to(candidate.resolve(strict=False), memory_root_real):
                        health["skipped_outside_root"] += 1
                except OSError:
                    pass
                continue
            try:
                resolved = candidate.resolve(strict=True)
            except OSError:
                health["scan_errors"] += 1
                continue
            if not _is_relative_to(resolved, memory_root_real):
                health["skipped_outside_root"] += 1
                continue
            safe_directories.append(directory_name)
        directory_names[:] = safe_directories

        for file_name in sorted(file_names, key=str.casefold):
            candidate = current / file_name
            relative = candidate.relative_to(memory_root)
            if _is_hidden(relative):
                health["skipped_hidden"] += 1
                continue
            if file_name.casefold() == "index.md":
                health["excluded_index"] += 1
                continue
            if _is_temp_file(file_name):
                health["skipped_temp"] += 1
                continue
            if candidate.suffix.casefold() != ".md":
                continue
            try:
                candidate_stat = candidate.lstat()
            except OSError:
                health["unreadable_files"] += 1
                health["scan_errors"] += 1
                continue
            if stat.S_ISLNK(candidate_stat.st_mode):
                health["skipped_symlinks"] += 1
                try:
                    if not _is_relative_to(candidate.resolve(strict=False), memory_root_real):
                        health["skipped_outside_root"] += 1
                except OSError:
                    pass
                continue
            if not stat.S_ISREG(candidate_stat.st_mode):
                health["skipped_non_regular"] += 1
                continue
            try:
                resolved = candidate.resolve(strict=True)
            except OSError:
                health["unreadable_files"] += 1
                health["scan_errors"] += 1
                continue
            if not _is_relative_to(resolved, memory_root_real):
                health["skipped_outside_root"] += 1
                continue

            if total_cards >= scan_limit:
                data["scan_limit_reached"] = True
                stop_scan = True
                break
            total_cards += 1
            relative_text = _safe_relative_path(candidate, memory_root)
            same_name_paths[_normalized_key(file_name)].append(relative_text)

            metadata_result = read_frontmatter_metadata(candidate)
            metadata_status = str(metadata_result.get("status") or "malformed")
            metadata = metadata_result.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
                metadata_status = "malformed"

            issue = False
            if metadata_status == "missing":
                health["missing_frontmatter"] += 1
                issue = True
            elif metadata_status == "malformed":
                health["malformed_frontmatter"] += 1
                issue = True
            elif metadata_status == "unclosed":
                health["unclosed_frontmatter"] += 1
                issue = True
            elif metadata_status == "too-large":
                health["oversized_frontmatter"] += 1
                issue = True
            elif metadata_status == "decode-error":
                health["decode_error_frontmatter"] += 1
                issue = True
            elif metadata_status == "unreadable":
                health["unreadable_files"] += 1
                issue = True
            elif metadata_status != "ok":
                health["malformed_frontmatter"] += 1
                issue = True
            if any("truncated" in str(item) for item in metadata_result.get("errors") or []):
                health["metadata_field_truncations"] += 1

            type_value, type_truncated = _normalized_declared_type(metadata.get("type"))
            asset_type_value, asset_type_truncated = _normalized_declared_type(metadata.get("asset_type"))
            if type_truncated or asset_type_truncated:
                health["metadata_field_truncations"] += 1
                issue = True
            if type_value and asset_type_value and type_value != asset_type_value:
                health["conflicting_type_fields"] += 1
                issue = True
            declared_type = type_value or asset_type_value
            inferred_type: str | None = None
            effective_type: str | None = None
            type_source = "unclassified"

            if declared_type:
                if declared_type in VALID_ASSET_TYPES:
                    declared_type_counts[declared_type] += 1
                    effective_type = declared_type
                    type_source = "declared"
                    classification_counts["declared_recognized"] += 1
                else:
                    type_source = "declared-unrecognized"
                    classification_counts["declared_unrecognized"] += 1
                    health["unknown_type"] += 1
                    issue = True
            else:
                health["missing_type"] += 1
                inferred_type = _directory_hint(relative)
                if inferred_type:
                    effective_type = inferred_type
                    type_source = "inferred-directory"
                    inferred_type_counts[inferred_type] += 1
                    classification_counts["inferred_from_directory"] += 1
                    health["inferred_type"] += 1
                else:
                    classification_counts["unclassified"] += 1
                issue = True

            if effective_type:
                recognized_cards += 1
                recognized_type_counts[effective_type] += 1
                if effective_type in {
                    "idea-card",
                    "persona-card",
                    "voice-card",
                    "product-service-card",
                }:
                    type_buckets[effective_type] += 1
                else:
                    type_buckets["other-recognized"] += 1
            else:
                type_buckets["unrecognized"] += 1

            created_text, created_status = _parse_created(metadata.get("created"), today)
            if created_status == "missing":
                health["missing_created"] += 1
                issue = True
            elif created_status == "invalid":
                health["invalid_created"] += 1
                issue = True
            elif created_status == "future":
                health["future_created"] += 1
                issue = True
            elif created_text:
                valid_dates.append(date.fromisoformat(created_text))

            keywords, keyword_status, keyword_truncations = _extract_keywords(metadata.get("keywords"))
            if keyword_truncations:
                health["metadata_field_truncations"] += keyword_truncations
                issue = True
            if keyword_status == "missing":
                health["missing_keywords"] += 1
                issue = True
            elif keyword_status == "invalid":
                health["invalid_keywords"] += 1
                issue = True
            for keyword in keywords:
                normalized_keyword = _normalized_key(keyword)
                keyword_counts[normalized_keyword] += 1
                keyword_labels.setdefault(normalized_keyword, keyword)

            if issue:
                health["cards_with_index_issues"] += 1
                pending_validation_count += 1

            try:
                digest = sha256_file(candidate)
            except (OSError, PermissionError):
                if metadata_status != "unreadable":
                    health["unreadable_files"] += 1
            else:
                exact_hash_paths[digest].append(relative_text)

            card_records.append(
                {
                    "path": relative_text,
                    "type": effective_type,
                    "type_source": type_source,
                    "declared_type": declared_type or None,
                    "inferred_type": inferred_type,
                    "created": created_text,
                    "keywords": keywords,
                    "frontmatter_status": metadata_status,
                    "needs_validation": issue,
                }
            )
        if stop_scan:
            break

    if walk_errors:
        health["scan_errors"] += walk_errors

    cutoff = today - timedelta(days=recent_days - 1)
    recent_count = sum(1 for item in valid_dates if cutoff <= item <= today)
    sorted_keywords = sorted(keyword_counts.items(), key=lambda item: (-item[1], keyword_labels[item[0]].casefold()))
    top_keyword_rows = [
        {"keyword": keyword_labels[normalized], "count": count}
        for normalized, count in sorted_keywords[:top_keywords]
    ]

    def limited_duplicate_groups(groups: list[list[str]]) -> tuple[list[dict[str, list[str]]], bool]:
        rows: list[dict[str, list[str]]] = []
        for paths in groups[:MAX_DUPLICATE_GROUPS]:
            rows.append({"paths": sorted(paths, key=str.casefold)[:MAX_PATHS_PER_GROUP]})
        truncated = len(groups) > MAX_DUPLICATE_GROUPS or any(len(paths) > MAX_PATHS_PER_GROUP for paths in groups)
        return rows, truncated

    same_name_groups_raw = [paths for paths in same_name_paths.values() if len(paths) > 1]
    same_name_groups_raw.sort(key=lambda paths: [item.casefold() for item in sorted(paths, key=str.casefold)])
    exact_groups_raw = [paths for paths in exact_hash_paths.values() if len(paths) > 1]
    exact_groups_raw.sort(key=lambda paths: [item.casefold() for item in sorted(paths, key=str.casefold)])
    same_name_groups, same_name_truncated = limited_duplicate_groups(same_name_groups_raw)
    exact_groups, exact_truncated = limited_duplicate_groups(exact_groups_raw)

    total_cards_complete = not data["scan_limit_reached"] and not health["scan_errors"]
    duplicate_check_complete = not bool(
        data["scan_limit_reached"]
        or health["unreadable_files"]
        or health["scan_errors"]
        or health["skipped_symlinks"]
        or health["skipped_outside_root"]
    )
    partial = not duplicate_check_complete
    root_status = "partial" if partial else ("empty" if total_cards == 0 else "available")
    data.update(
        {
            "root_status": root_status,
            "status": root_status,
            "partial": partial,
            "scanned_cards": total_cards,
            "total_cards": total_cards if total_cards_complete else None,
            "total_cards_complete": total_cards_complete,
            "duplicate_check_complete": duplicate_check_complete,
            "recognized_cards": recognized_cards,
            "pending_validation_count": pending_validation_count,
            "type_counts": {key: type_buckets[key] for key in TYPE_BUCKETS},
            "recognized_type_counts": dict(sorted(recognized_type_counts.items())),
            "declared_type_counts": dict(sorted(declared_type_counts.items())),
            "inferred_type_counts": dict(sorted(inferred_type_counts.items())),
            "classification_counts": {
                key: classification_counts[key]
                for key in ("declared_recognized", "declared_unrecognized", "inferred_from_directory", "unclassified")
            },
            "created": {
                "earliest": min(valid_dates).isoformat() if valid_dates else None,
                "latest": max(valid_dates).isoformat() if valid_dates else None,
                "as_of": today.isoformat(),
                "recent_days": recent_days,
                "recent_count": recent_count,
            },
            "top_keywords": top_keyword_rows,
            "health": {key: health[key] for key in HEALTH_KEYS},
            "duplicates": {
                "same_name_group_count": len(same_name_groups_raw),
                "same_name_groups": same_name_groups,
                "same_name_groups_truncated": same_name_truncated,
                "exact_content_group_count": len(exact_groups_raw),
                "exact_content_groups": exact_groups,
                "exact_content_groups_truncated": exact_truncated,
            },
            "duplicate_groups": {
                "same_name": same_name_groups,
                "exact_content": exact_groups,
            },
            "skipped": {
                "symlinks": health["skipped_symlinks"],
                "outside_root": health["skipped_outside_root"],
                "non_regular": health["skipped_non_regular"],
                "hidden": health["skipped_hidden"],
                "temporary": health["skipped_temp"],
                "index": health["excluded_index"],
            },
        }
    )

    if include_cards:
        normalized_filter_keyword = _normalized_key(normalized_filter_keyword_text)
        selected_cards = []
        for record in card_records:
            if normalized_filter_type and record["type"] != normalized_filter_type:
                continue
            if normalized_filter_keyword and normalized_filter_keyword not in {
                _normalized_key(item) for item in record["keywords"]
            }:
                continue
            selected_cards.append(record)
        data["cards_included"] = True
        data["cards"] = sorted(selected_cards, key=lambda item: item["path"].casefold())

    if data["scan_limit_reached"]:
        warnings.append(f"扫描达到 {scan_limit} 张上限，本次结果为部分盘点。")
    if health["unreadable_files"]:
        warnings.append(f"{health['unreadable_files']} 个文件无法完整读取，其余统计已继续。")
    if health["skipped_symlinks"]:
        warnings.append(f"已跳过 {health['skipped_symlinks']} 个符号链接，未跟随。")
    if health["skipped_non_regular"]:
        warnings.append(f"已跳过 {health['skipped_non_regular']} 个非普通 Markdown 文件，未读取。")
    if health["scan_errors"]:
        warnings.append(f"扫描期间出现 {health['scan_errors']} 个目录读取错误。")
    if same_name_truncated or exact_truncated:
        if duplicate_check_complete:
            warnings.append("疑似重复列表已截断；组数统计覆盖本次完整扫描，可按需进一步展开。")
        else:
            warnings.append("疑似重复列表已截断；组数只代表本次部分检查中已发现的结果。")

    if partial:
        summary = f"已完成部分记忆盘点：已扫描 {total_cards} 张卡，有路径或文件被安全跳过。"
    elif total_cards == 0:
        summary = "当前 eva-memory 目录为空，共 0 张卡。"
    else:
        summary = f"记忆盘点完成：共 {total_cards} 张卡，识别 {recognized_cards} 张。"
    return result(True, "memory-inventory", summary, [], warnings, data)


def run_inventory(
    project_root: str | Path,
    recent_days: int = DEFAULT_RECENT_DAYS,
    today: date | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Compatibility entry for deterministic tests and other Eva scripts."""
    root = project_root if isinstance(project_root, Path) else _absolute_lexical_path(project_root)
    if not root.is_absolute():
        root = _absolute_lexical_path(str(root))
    return inventory_project(root, recent_days=recent_days, as_of=today, **kwargs)


def render_markdown(payload: dict[str, Any]) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    health = data.get("health") if isinstance(data.get("health"), dict) else {}
    duplicates = data.get("duplicates") if isinstance(data.get("duplicates"), dict) else {}
    created = data.get("created") if isinstance(data.get("created"), dict) else {}
    type_counts = data.get("type_counts") if isinstance(data.get("type_counts"), dict) else {}
    declared_type_counts = (
        data.get("declared_type_counts") if isinstance(data.get("declared_type_counts"), dict) else {}
    )
    scan_started = bool(payload.get("ok"))
    total_cards_complete = bool(data.get("total_cards_complete"))
    duplicate_check_complete = bool(data.get("duplicate_check_complete"))
    inferred_type_counts = (
        data.get("inferred_type_counts") if isinstance(data.get("inferred_type_counts"), dict) else {}
    )

    if total_cards_complete:
        card_count_line = f"- 卡片总数：{int(data.get('total_cards') or 0)}"
    else:
        card_count_line = f"- 已扫描卡片数（非全量）：{int(data.get('scanned_cards') or 0)}"

    if not scan_started:
        same_name_line = "- 同名：未检查（扫描未完成）"
        exact_content_line = "- 内容完全相同：未检查（扫描未完成）"
    elif duplicate_check_complete:
        same_name_line = f"- 同名组：{int(duplicates.get('same_name_group_count') or 0)}"
        exact_content_line = f"- 内容完全相同组：{int(duplicates.get('exact_content_group_count') or 0)}"
    else:
        same_name_line = (
            f"- 同名：部分检查中发现 {int(duplicates.get('same_name_group_count') or 0)} 组（未完整检查）"
        )
        exact_content_line = (
            "- 内容完全相同：部分检查中发现 "
            f"{int(duplicates.get('exact_content_group_count') or 0)} 组（未完整检查）"
        )

    lines = [
        "# Eva Memory 记忆盘点",
        "",
        f"> {_markdown_escape(payload.get('summary', ''))}",
        "",
        f"- 扫描状态：`{_markdown_escape(data.get('root_status', 'unknown'))}`",
        card_count_line,
        f"- 可归类卡片（含目录推断）：{int(data.get('recognized_cards') or 0)}",
        f"- 待校验：{int(data.get('pending_validation_count') or 0)}",
        "",
        "## 正式声明类型",
        "",
        f"- idea-card：{int(declared_type_counts.get('idea-card') or 0)}",
        f"- persona-card：{int(declared_type_counts.get('persona-card') or 0)}",
        f"- voice-card：{int(declared_type_counts.get('voice-card') or 0)}",
        f"- product-service-card：{int(declared_type_counts.get('product-service-card') or 0)}",
        "- 其他已识别类型："
        + str(
            sum(
                int(count or 0)
                for asset_type, count in declared_type_counts.items()
                if asset_type in VALID_ASSET_TYPES
                and asset_type
                not in {
                    "idea-card",
                    "persona-card",
                    "voice-card",
                    "product-service-card",
                }
            )
        ),
        f"- 无法识别类型：{int(type_counts.get('unrecognized') or 0)}",
        "",
        "## 目录推断、待校验",
        "",
        f"- idea-card：{int(inferred_type_counts.get('idea-card') or 0)}",
        f"- persona-card：{int(inferred_type_counts.get('persona-card') or 0)}",
        f"- voice-card：{int(inferred_type_counts.get('voice-card') or 0)}",
        f"- product-service-card：{int(inferred_type_counts.get('product-service-card') or 0)}",
        "",
        "## 时间与关键词",
        "",
        f"- 创建日期范围：{_markdown_escape(created.get('earliest') or '暂无有效日期')} 至 {_markdown_escape(created.get('latest') or '暂无有效日期')}",
        f"- 最近 {int(created.get('recent_days') or DEFAULT_RECENT_DAYS)} 天新增：{int(created.get('recent_count') or 0)}",
    ]
    keywords = data.get("top_keywords") if isinstance(data.get("top_keywords"), list) else []
    if keywords:
        keyword_text = "、".join(
            f"{_markdown_escape(item.get('keyword', ''))}（{int(item.get('count') or 0)}）"
            for item in keywords
            if isinstance(item, dict)
        )
        lines.append(f"- 高频关键词：{keyword_text}")
    else:
        lines.append("- 高频关键词：暂无")

    lines.extend(
        [
            "",
            "## 索引健康",
            "",
            f"- 缺少或无效 type：{int(health.get('missing_type') or 0) + int(health.get('unknown_type') or 0)}",
            f"- 缺少或无效 created：{int(health.get('missing_created') or 0) + int(health.get('invalid_created') or 0) + int(health.get('future_created') or 0)}",
            f"- 缺少或无效 keywords：{int(health.get('missing_keywords') or 0) + int(health.get('invalid_keywords') or 0)}",
            f"- 缺少、损坏或过大 frontmatter：{int(health.get('missing_frontmatter') or 0) + int(health.get('malformed_frontmatter') or 0) + int(health.get('unclosed_frontmatter') or 0) + int(health.get('oversized_frontmatter') or 0) + int(health.get('decode_error_frontmatter') or 0)}",
            f"- 无法读取文件：{int(health.get('unreadable_files') or 0)}",
            f"- 非普通文件跳过：{int(health.get('skipped_non_regular') or 0)}",
            "",
            "## 疑似重复",
            "",
            same_name_line,
            exact_content_line,
        ]
    )

    exact_groups = duplicates.get("exact_content_groups") if isinstance(duplicates.get("exact_content_groups"), list) else []
    same_name_groups = duplicates.get("same_name_groups") if isinstance(duplicates.get("same_name_groups"), list) else []
    for label, groups in (("内容完全相同", exact_groups), ("同名", same_name_groups)):
        for index, group in enumerate(groups[:10], start=1):
            if not isinstance(group, dict) or not isinstance(group.get("paths"), list):
                continue
            paths = "、".join(f"`{_markdown_escape(item)}`" for item in group["paths"])
            lines.append(f"- {label} {index}：{paths}")

    if data.get("cards_included") is True:
        cards = data.get("cards") if isinstance(data.get("cards"), list) else []
        lines.extend(["", "## 筛选结果", ""])
        if not cards:
            lines.append("- 没有命中当前类型或关键词的卡片。")
        for card in cards:
            if not isinstance(card, dict):
                continue
            type_source = str(card.get("type_source") or "unclassified")
            if type_source == "declared":
                type_text = f"正式声明类型：{_markdown_escape(card.get('type') or '未知')}"
            elif type_source == "inferred-directory":
                type_text = f"目录推断类型：{_markdown_escape(card.get('inferred_type') or '未知')}（待校验）"
            elif type_source == "declared-unrecognized":
                type_text = f"无法识别的声明类型：{_markdown_escape(card.get('declared_type') or '未知')}"
            else:
                type_text = "类型：未识别"
            card_keywords = card.get("keywords") if isinstance(card.get("keywords"), list) else []
            keyword_text = "、".join(_markdown_escape(item) for item in card_keywords) or "暂无"
            validation_text = "待校验" if card.get("needs_validation") else "正常"
            lines.append(
                f"- `{_markdown_escape(card.get('path') or '[invalid-path]')}`｜{type_text}｜"
                f"日期：{_markdown_escape(card.get('created') or '暂无合法日期')}｜"
                f"关键词：{keyword_text}｜校验：{validation_text}"
            )

    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    if warnings:
        lines.extend(["", "## 扫描提示", ""])
        lines.extend(f"- {_markdown_escape(item)}" for item in warnings)

    lines.extend(
        [
            "",
            "## 下一步",
            "",
            "可以按类型或关键词展开对应卡片的元数据列表。默认不展示正文，也不写入 `INDEX.md`。",
        ]
    )
    return "\n".join(lines) + "\n"


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return value


def _scan_limit(raw: str) -> int:
    value = _positive_int(raw)
    if value > MAX_SCAN_LIMIT:
        raise argparse.ArgumentTypeError(f"must not exceed {MAX_SCAN_LIMIT}")
    return value


def _recent_days(raw: str) -> int:
    value = _positive_int(raw)
    if value > MAX_RECENT_DAYS:
        raise argparse.ArgumentTypeError(f"must not exceed {MAX_RECENT_DAYS}")
    return value


def _top_keywords(raw: str) -> int:
    value = _positive_int(raw)
    if value > MAX_TOP_KEYWORDS:
        raise argparse.ArgumentTypeError(f"must not exceed {MAX_TOP_KEYWORDS}")
    return value


def _as_of(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be YYYY-MM-DD") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only inventory of ./eva-memory in the current creator project.")
    parser.add_argument("--project-root", default=".", help="Creator project root; ./eva-memory is derived from it.")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--recent-days", type=_recent_days, default=DEFAULT_RECENT_DAYS)
    parser.add_argument("--top-keywords", type=_top_keywords, default=DEFAULT_TOP_KEYWORDS)
    parser.add_argument("--scan-limit", type=_scan_limit, default=MAX_SCAN_LIMIT)
    parser.add_argument(
        "--include-cards",
        action="store_true",
        help="Include filtered metadata-only card rows; requires a type or keyword filter and never includes body text.",
    )
    parser.add_argument("--filter-type", help="With --include-cards, include only this recognized effective type.")
    parser.add_argument("--filter-keyword", help="With --include-cards, include only cards with this exact keyword.")
    parser.add_argument("--as-of", type=_as_of, help="Override today's date for deterministic checks (YYYY-MM-DD).")
    add_common_arguments(parser)
    args = parser.parse_args()

    normalized_cli_filter_type = (args.filter_type or "").strip()
    normalized_cli_filter_keyword = (args.filter_keyword or "").strip()
    if (normalized_cli_filter_type or normalized_cli_filter_keyword) and not args.include_cards:
        parser.error("--filter-type and --filter-keyword require --include-cards")
    if args.include_cards and not (normalized_cli_filter_type or normalized_cli_filter_keyword):
        parser.error("--include-cards requires --filter-type or --filter-keyword")

    project_root = _absolute_lexical_path(args.project_root)
    payload = inventory_project(
        project_root,
        recent_days=args.recent_days,
        top_keywords=args.top_keywords,
        scan_limit=args.scan_limit,
        include_cards=args.include_cards,
        filter_type=normalized_cli_filter_type,
        filter_keyword=normalized_cli_filter_keyword,
        as_of=args.as_of,
    )
    if args.format == "markdown":
        print(render_markdown(payload), end="")
    else:
        print_result(payload)
    raise SystemExit(0 if payload.get("ok") else 1)


if __name__ == "__main__":
    main()
