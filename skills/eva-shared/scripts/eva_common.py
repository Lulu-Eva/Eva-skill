#!/usr/bin/env python3
"""Common helpers for Eva Shared 2.2.1 scripts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


CORE_ENTRIES = {
    "eva",
    "eva-new-user",
    "eva-learn",
    "eva-brief",
    "eva-think",
    "eva-audience-finder",
    "eva-create",
    "eva-memory",
    "eva-link",
    "eva-review",
    "eva-lens",
    "eva-preflight",
}

VALID_LOW_CONFIDENCE_REASONS = {
    "title-unverified",
    "brief-incomplete",
    "missing-audience",
    "missing-user-question",
    "missing-source-material",
    "user-requested-draft-before-evidence",
    "link-output-schema-failed",
    "missing-title-or-content",
    "missing-data",
    "small-comment-sample",
    "unclear-data-window",
    "missing-user-goal",
    "unverified-causality",
}

VERSION = "eva-shared-2.2.1"


def default_base_from_script(script_path: str) -> Path:
    return Path(script_path).resolve().parents[1]


def load_asset_types(base: Path | None = None) -> dict[str, Any]:
    """Load the machine-readable Eva asset type registry."""
    root = base or default_base_from_script(__file__)
    with (root / "schemas" / "asset-types.json").open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    assets = payload.get("assets")
    if not isinstance(assets, dict):
        raise ValueError("schemas/asset-types.json must contain an assets object")
    return payload


def asset_type_names(base: Path | None = None) -> set[str]:
    return set(load_asset_types(base)["assets"].keys())


def load_handoff_targets(base: Path | None = None) -> dict[str, Any]:
    """Load the independent Eva handoff target registry."""
    root = base or default_base_from_script(__file__)
    with (root / "schemas" / "handoff-targets.json").open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    targets = payload.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ValueError("schemas/handoff-targets.json must contain a non-empty targets array")
    return payload


def handoff_targets(base: Path | None = None) -> set[str]:
    return set(load_handoff_targets(base)["targets"])


def handoff_aliases(base: Path | None = None) -> dict[str, str]:
    aliases = load_handoff_targets(base).get("aliases") or {}
    if not isinstance(aliases, dict):
        raise ValueError("schemas/handoff-targets.json aliases must be an object")
    return {str(alias): str(target) for alias, target in aliases.items()}


def handoff_internal_stages(base: Path | None = None) -> set[str]:
    stages = load_handoff_targets(base).get("internal_stages") or []
    if not isinstance(stages, list):
        raise ValueError("schemas/handoff-targets.json internal_stages must be an array")
    return {str(stage) for stage in stages}


def canonical_handoff_target(target: object, base: Path | None = None) -> str:
    value = str(target)
    return handoff_aliases(base).get(value, value)


def canonicalize_handoff_targets(targets: object, base: Path | None = None) -> list[str]:
    if not isinstance(targets, (list, tuple, set)):
        return []
    aliases = handoff_aliases(base)
    return [aliases.get(str(target), str(target)) for target in targets]


def required_fields_for_asset(asset_type: str, base: Path | None = None) -> list[str]:
    assets = load_asset_types(base)["assets"]
    config = assets.get(asset_type)
    if not isinstance(config, dict):
        return []
    required_fields = config.get("required_fields") or []
    if not isinstance(required_fields, list):
        raise ValueError(f"asset type {asset_type} required_fields must be an array")
    return [str(item) for item in required_fields]


def is_blank_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


VALID_ASSET_TYPES = asset_type_names()
VALID_HANDOFF_TARGETS = handoff_targets()
HANDOFF_ALIASES = handoff_aliases()
HANDOFF_INTERNAL_STAGES = handoff_internal_stages()


def result(
    ok: bool,
    kind: str,
    summary: str,
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


def print_result(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def exit_with(payload: dict[str, Any]) -> None:
    print_result(payload)
    raise SystemExit(0 if payload.get("ok") else 1)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str, secret: str = "") -> str:
    digest = hashlib.sha256()
    digest.update(secret.encode("utf-8"))
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def simple_schema_validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Small JSON-schema subset validator using only the Python standard library."""
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type and not _matches_type(instance, expected_type):
        errors.append(f"{path}: expected {expected_type}, got {type(instance).__name__}")
        return errors

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required field '{key}'")
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in instance:
                errors.extend(simple_schema_validate(instance[key], subschema, f"{path}.{key}"))
    elif isinstance(instance, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(instance) < min_items:
            errors.append(f"{path}: expected at least {min_items} items")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                errors.extend(simple_schema_validate(item, item_schema, f"{path}[{index}]"))

    if "minLength" in schema and isinstance(instance, str) and len(instance) < schema["minLength"]:
        errors.append(f"{path}: expected length >= {schema['minLength']}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: value {instance!r} is not in enum {schema['enum']}")
    if "pattern" in schema and isinstance(instance, str):
        if not re.search(schema["pattern"], instance):
            errors.append(f"{path}: value {instance!r} does not match pattern {schema['pattern']}")

    return errors


def _matches_type(value: Any, expected: str | list[str]) -> bool:
    expected_types = expected if isinstance(expected, list) else [expected]
    for item in expected_types:
        if item == "object" and isinstance(value, dict):
            return True
        if item == "array" and isinstance(value, list):
            return True
        if item == "string" and isinstance(value, str):
            return True
        if item == "boolean" and isinstance(value, bool):
            return True
        if item == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if item == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if item == "null" and value is None:
            return True
    return False


def parse_markdown_fields(path: Path) -> dict[str, str]:
    """Parse simple Chinese/English field labels from a Markdown asset card."""
    fields: dict[str, str] = {}
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "：" in line:
            key, value = line.split("：", 1)
        elif ":" in line:
            key, value = line.split(":", 1)
        else:
            continue
        key = key.strip().strip("-* ")
        value = value.strip()
        if key:
            fields[key] = value
    return fields


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = read_text(path)
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    raw_meta = parts[1].strip()
    body = parts[2]
    meta: dict[str, Any] = {}
    lines = raw_meta.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.startswith((" ", "\t")) or ":" not in line:
            index += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value in {"|", ">"}:
            block_lines: list[str] = []
            index += 1
            while index < len(lines):
                next_line = lines[index]
                if next_line and not next_line.startswith((" ", "\t")) and ":" in next_line:
                    break
                block_lines.append(next_line.strip())
                index += 1
            meta[key] = "\n".join(item for item in block_lines if item).strip()
            continue
        meta[key] = _parse_scalar(value)
        index += 1
    return meta, body


def _parse_scalar(value: str) -> Any:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value.strip("\"'")


def coerce_asset_from_markdown(fields: dict[str, str]) -> dict[str, Any]:
    mapping = {
        "资产类型": "asset_type",
        "来源模块": "source_module",
        "核心内容": "core_content",
        "用户问题": "user_question",
        "关键证据或材料": "evidence",
        "适合交给哪个下游": "valid_next",
        "是否已保存": "saved",
    }
    asset: dict[str, Any] = {}
    for cn_key, en_key in mapping.items():
        if cn_key in fields:
            asset[en_key] = fields[cn_key]
    if isinstance(asset.get("valid_next"), str):
        asset["valid_next"] = [item.strip() for item in re.split(r"[,，/、]", asset["valid_next"]) if item.strip()]
    if isinstance(asset.get("saved"), str):
        asset["saved"] = asset["saved"].lower() in {"true", "yes", "y", "已保存", "是"}
    return asset


def find_skill_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("SKILL.md"))


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pretty", action="store_true", help="Accepted for compatibility; JSON output is always pretty.")
    parser.add_argument("--version", action="version", version=VERSION)


def normalize_path(raw: str) -> Path:
    return Path(os.path.expanduser(raw)).resolve()
