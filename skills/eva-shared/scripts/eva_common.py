#!/usr/bin/env python3
"""Common helpers for Eva Shared 2.2.5 scripts."""

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

VERSION = "eva-shared-2.2.5"

FRONTMATTER_MAX_BYTES = 64 * 1024
FRONTMATTER_MAX_KEY_CHARS = 128
FRONTMATTER_MAX_SCALAR_CHARS = 4096
FRONTMATTER_MAX_COLLECTION_ITEMS = 256


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


def read_frontmatter_metadata(
    path: Path,
    max_bytes: int = FRONTMATTER_MAX_BYTES,
) -> dict[str, Any]:
    """Read bounded YAML-like frontmatter without loading the Markdown body.

    This intentionally supports only the metadata shapes used by Eva cards:
    top-level scalars, block lists and one-level nested maps. The return value
    always contains ``status``, ``metadata``, ``errors`` and ``bytes_read``.
    Existing ``parse_frontmatter`` remains unchanged for compatibility.
    """
    response: dict[str, Any] = {
        "status": "missing",
        "metadata": {},
        "errors": [],
        "bytes_read": 0,
    }
    if max_bytes <= 0:
        response["status"] = "invalid-limit"
        response["errors"] = ["frontmatter byte limit must be positive"]
        return response

    try:
        with path.open("rb") as handle:
            first = handle.readline(max_bytes + 1)
            response["bytes_read"] = len(first)
            first_without_bom = first[3:] if first.startswith(b"\xef\xbb\xbf") else first
            if first_without_bom.strip() != b"---":
                return response
            if len(first) > max_bytes:
                response["status"] = "too-large"
                response["errors"] = [f"frontmatter exceeds {max_bytes} bytes"]
                return response
            try:
                opening = first_without_bom.decode("utf-8").strip()
            except UnicodeDecodeError:
                response["status"] = "decode-error"
                response["errors"] = ["frontmatter opening line is not valid UTF-8"]
                return response
            if opening != "---":
                return response

            raw_lines: list[bytes] = []
            while True:
                remaining = max_bytes - int(response["bytes_read"])
                if remaining <= 0:
                    response["status"] = "too-large"
                    response["errors"] = [f"frontmatter exceeds {max_bytes} bytes"]
                    return response
                raw_line = handle.readline(remaining + 1)
                response["bytes_read"] = int(response["bytes_read"]) + len(raw_line)
                if not raw_line:
                    response["status"] = "unclosed"
                    response["errors"] = ["frontmatter has no closing ---"]
                    return response
                if int(response["bytes_read"]) > max_bytes:
                    response["status"] = "too-large"
                    response["errors"] = [f"frontmatter exceeds {max_bytes} bytes"]
                    return response
                try:
                    decoded_line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    response["status"] = "decode-error"
                    response["errors"] = ["frontmatter is not valid UTF-8"]
                    return response
                if decoded_line.strip() == "---":
                    break
                raw_lines.append(raw_line)
    except (OSError, PermissionError) as exc:
        response["status"] = "unreadable"
        response["errors"] = [f"cannot read frontmatter: {exc.__class__.__name__}"]
        return response

    try:
        lines = b"".join(raw_lines).decode("utf-8").splitlines()
    except UnicodeDecodeError:
        response["status"] = "decode-error"
        response["errors"] = ["frontmatter is not valid UTF-8"]
        return response

    metadata, parse_errors = _parse_safe_frontmatter_lines(lines)
    response["metadata"] = metadata
    response["errors"] = parse_errors
    response["status"] = "malformed" if parse_errors else "ok"
    return response


def _parse_safe_frontmatter_lines(lines: list[str]) -> tuple[dict[str, Any], list[str]]:
    metadata: dict[str, Any] = {}
    errors: list[str] = []
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if raw_line.startswith((" ", "\t")) or ":" not in raw_line:
            errors.append(f"line {index + 2}: expected a top-level key")
            index += 1
            continue

        raw_key, raw_value = raw_line.split(":", 1)
        key = raw_key.strip()
        if not key or len(key) > FRONTMATTER_MAX_KEY_CHARS:
            errors.append(f"line {index + 2}: invalid or oversized key")
            index += 1
            continue
        if key in metadata:
            errors.append(f"line {index + 2}: duplicate key '{key}'")

        value = raw_value.strip()
        if value and value not in {"|", ">"}:
            parsed, value_error = _parse_safe_metadata_scalar(value)
            metadata[key] = parsed
            if value_error:
                errors.append(f"line {index + 2}: {value_error}")
            index += 1
            continue

        block_start = index + 1
        block: list[tuple[int, str]] = []
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip() and not candidate.startswith((" ", "\t")):
                break
            block.append((index + 2, candidate))
            index += 1

        if value in {"|", ">"}:
            block_text = [item.strip() for _, item in block]
            joined = ("\n" if value == "|" else " ").join(block_text).strip()
            if len(joined) > FRONTMATTER_MAX_SCALAR_CHARS:
                joined = joined[:FRONTMATTER_MAX_SCALAR_CHARS]
                errors.append(f"line {block_start + 1}: block scalar was truncated")
            metadata[key] = joined
            continue

        meaningful = [(line_no, item.strip()) for line_no, item in block if item.strip() and not item.strip().startswith("#")]
        if not meaningful:
            metadata[key] = None
            continue

        is_list = [item.startswith("-") for _, item in meaningful]
        is_map = [(not item.startswith("-")) and ":" in item for _, item in meaningful]
        if all(is_list):
            values: list[Any] = []
            for line_no, item in meaningful[:FRONTMATTER_MAX_COLLECTION_ITEMS]:
                raw_item = item[1:].strip()
                parsed, value_error = _parse_safe_metadata_scalar(raw_item)
                values.append(parsed)
                if value_error:
                    errors.append(f"line {line_no}: {value_error}")
            if len(meaningful) > FRONTMATTER_MAX_COLLECTION_ITEMS:
                errors.append(f"line {block_start + 1}: list exceeded item limit and was truncated")
            metadata[key] = values
        elif all(is_map):
            nested: dict[str, Any] = {}
            for line_no, item in meaningful[:FRONTMATTER_MAX_COLLECTION_ITEMS]:
                nested_key_raw, nested_value_raw = item.split(":", 1)
                nested_key = nested_key_raw.strip()
                if not nested_key or len(nested_key) > FRONTMATTER_MAX_KEY_CHARS:
                    errors.append(f"line {line_no}: invalid or oversized nested key")
                    continue
                if nested_key in nested:
                    errors.append(f"line {line_no}: duplicate nested key '{nested_key}'")
                parsed, value_error = _parse_safe_metadata_scalar(nested_value_raw.strip())
                nested[nested_key] = parsed
                if value_error:
                    errors.append(f"line {line_no}: {value_error}")
            if len(meaningful) > FRONTMATTER_MAX_COLLECTION_ITEMS:
                errors.append(f"line {block_start + 1}: map exceeded item limit and was truncated")
            metadata[key] = nested
        else:
            metadata[key] = None
            errors.append(f"line {block_start + 1}: mixed or unsupported block for '{key}'")

    return metadata, errors


def _parse_safe_metadata_scalar(value: str) -> tuple[Any, str | None]:
    cleaned = value.strip()
    if not cleaned:
        return "", None
    if len(cleaned) > FRONTMATTER_MAX_SCALAR_CHARS:
        return cleaned[:FRONTMATTER_MAX_SCALAR_CHARS], "scalar was truncated"
    if cleaned in {"true", "True", "TRUE"}:
        return True, None
    if cleaned in {"false", "False", "FALSE"}:
        return False, None
    if cleaned in {"null", "Null", "NULL", "~"}:
        return None, None
    if cleaned.startswith("[") and cleaned.endswith("]"):
        inner = cleaned[1:-1].strip()
        if not inner:
            return [], None
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                if len(parsed) > FRONTMATTER_MAX_COLLECTION_ITEMS:
                    return parsed[:FRONTMATTER_MAX_COLLECTION_ITEMS], "inline list was truncated"
                return parsed, None
        except json.JSONDecodeError:
            items = [item.strip().strip("\"'") for item in inner.split(",")]
            if len(items) > FRONTMATTER_MAX_COLLECTION_ITEMS:
                return items[:FRONTMATTER_MAX_COLLECTION_ITEMS], "inline list was truncated"
            return items, None
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (
        cleaned.startswith("'") and cleaned.endswith("'")
    ):
        return cleaned[1:-1], None
    if re.fullmatch(r"[-+]?\d+", cleaned):
        try:
            return int(cleaned), None
        except ValueError:
            pass
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)", cleaned):
        try:
            return float(cleaned), None
        except ValueError:
            pass
    return cleaned, None


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
