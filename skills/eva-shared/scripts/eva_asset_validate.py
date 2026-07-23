#!/usr/bin/env python3
"""Validate Eva Asset cards."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from eva_common import (
    CORE_ENTRIES,
    VALID_ASSET_TYPES,
    VALID_HANDOFF_TARGETS,
    VALID_LOW_CONFIDENCE_REASONS,
    add_common_arguments,
    canonical_handoff_target,
    coerce_asset_from_markdown,
    default_base_from_script,
    exit_with,
    is_blank_value,
    load_asset_types,
    normalize_path,
    parse_markdown_fields,
    read_frontmatter_metadata,
    read_json,
    required_fields_for_asset,
    result,
    simple_schema_validate,
)

CANONICAL_FRONTMATTER_JSON_PREFIX = "eva-json|"
STRUCTURED_FRONTMATTER_FIELDS = {
    "baseline",
    "baseline_distribution",
    "core_content",
    "evidence",
    "facts",
    "privacy",
}
def source_allowed_for_asset(source_module: object, allowed_sources: list) -> bool:
    if source_module in allowed_sources:
        return True
    if not isinstance(source_module, str):
        return False
    if "eva-link" in allowed_sources and source_module not in CORE_ENTRIES:
        return True
    return False


def _decode_canonical_frontmatter(metadata: dict[str, Any]) -> dict[str, Any]:
    """Decode values emitted by the canonical Eva Markdown serializer."""
    asset: dict[str, Any] = {}
    for key, value in metadata.items():
        if isinstance(value, str) and value.startswith(CANONICAL_FRONTMATTER_JSON_PREFIX):
            encoded = value[len(CANONICAL_FRONTMATTER_JSON_PREFIX) :]
            try:
                value = json.loads(encoded)
            except json.JSONDecodeError as exc:
                raise ValueError(f"canonical frontmatter field '{key}' has invalid encoded JSON") from exc
        elif (
            key in STRUCTURED_FRONTMATTER_FIELDS
            and isinstance(value, str)
            and value.startswith("{")
            and value.endswith("}")
        ):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                decoded = value
            if isinstance(decoded, dict):
                value = decoded
        asset[key] = value

    storage_type = asset.get("type")
    asset_type = asset.get("asset_type")
    if storage_type is not None and asset_type is not None and storage_type != asset_type:
        raise ValueError("canonical frontmatter fields 'type' and 'asset_type' conflict")
    if asset_type is None and isinstance(storage_type, str):
        asset["asset_type"] = storage_type
    return asset


def load_asset(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        payload = read_json(path)
        if not isinstance(payload, dict):
            raise ValueError("asset JSON must be an object")
        return payload

    frontmatter = read_frontmatter_metadata(path)
    status = frontmatter.get("status")
    metadata = frontmatter.get("metadata")
    if (
        status == "ok"
        and isinstance(metadata, dict)
        and "asset_type" in metadata
    ):
        return _decode_canonical_frontmatter(metadata)
    if status not in {"missing", "ok"}:
        details = frontmatter.get("errors")
        detail = "; ".join(str(item) for item in details) if isinstance(details, list) else str(status)
        raise ValueError(f"asset Markdown frontmatter is {status}: {detail}")

    fields = parse_markdown_fields(path)
    return coerce_asset_from_markdown(fields)


def validate_asset_payload(
    asset: dict[str, Any],
    schema: dict[str, Any],
    base: Path | None = None,
    downstream: str | None = None,
) -> dict[str, Any]:
    """Validate and normalize an in-memory Eva Asset without writing files."""
    root = base or default_base_from_script(__file__)
    errors: list[str] = []
    warnings: list[str] = []
    normalized_asset = copy.deepcopy(asset)

    errors.extend(simple_schema_validate(asset, schema))

    asset_type = asset.get("asset_type")
    asset_type_config: dict[str, Any] = {}
    required_fields: list[str] = []
    if not isinstance(asset_type, str) or asset_type not in VALID_ASSET_TYPES:
        errors.append(f"asset_type '{asset_type}' is not a valid Eva asset type")
    else:
        asset_type_config = load_asset_types(root)["assets"].get(asset_type, {})
        allowed_sources = asset_type_config.get("produced_by") or []
        source_module = asset.get("source_module")
        if allowed_sources and not source_allowed_for_asset(source_module, allowed_sources):
            errors.append(
                f"source_module '{source_module}' is not allowed to produce asset_type "
                f"'{asset_type}'; expected one of: " + ", ".join(map(str, allowed_sources))
            )
        required_fields = required_fields_for_asset(asset_type, root)
        missing_required = [
            field
            for field in required_fields
            if field not in asset or is_blank_value(asset.get(field))
        ]
        if missing_required:
            errors.append(
                f"asset_type '{asset_type}' missing required field(s): "
                + ", ".join(missing_required)
            )

    raw_valid_next = asset.get("valid_next")
    valid_next = raw_valid_next if isinstance(raw_valid_next, list) else []
    string_valid_next = [target for target in valid_next if isinstance(target, str)]
    invalid_next = sorted(
        {target for target in string_valid_next if target not in VALID_HANDOFF_TARGETS}
    )
    if invalid_next:
        errors.append("valid_next contains invalid handoff target(s): " + ", ".join(invalid_next))

    normalized_valid_next: list[str] = []
    seen_targets: set[str] = set()
    for target in string_valid_next:
        canonical = canonical_handoff_target(target, root)
        if canonical not in seen_targets:
            seen_targets.add(canonical)
            normalized_valid_next.append(canonical)
    if isinstance(raw_valid_next, list) and len(string_valid_next) == len(raw_valid_next):
        normalized_asset["valid_next"] = normalized_valid_next

    allowed_valid_next = [
        canonical_handoff_target(str(target), root)
        for target in (asset_type_config.get("valid_next") or [])
    ]
    disallowed_next = sorted(
        target
        for target in normalized_valid_next
        if allowed_valid_next and target not in allowed_valid_next
    )
    if disallowed_next:
        errors.append(
            f"asset_type '{asset_type}' does not allow valid_next target(s): "
            + ", ".join(disallowed_next)
            + "; expected only: "
            + ", ".join(allowed_valid_next)
        )

    compatibility_aliases = sorted(
        {
            target
            for target in string_valid_next
            if canonical_handoff_target(target, root) != target
        }
    )
    if compatibility_aliases:
        warnings.append(
            "valid_next uses compatibility alias(es); new assets should write canonical target names: "
            + ", ".join(compatibility_aliases)
        )

    if downstream:
        normalized_downstream = canonical_handoff_target(downstream, root)
        if normalized_downstream not in normalized_valid_next:
            errors.append(f"downstream '{downstream}' is not listed in valid_next")

    confidence = asset.get("confidence")
    raw_low_confidence_reason = asset.get("low_confidence_reason")
    if raw_low_confidence_reason is None:
        low_confidence_reason: list[object] = []
    elif isinstance(raw_low_confidence_reason, str):
        low_confidence_reason = [raw_low_confidence_reason]
    elif isinstance(raw_low_confidence_reason, list):
        low_confidence_reason = raw_low_confidence_reason
    else:
        low_confidence_reason = []
    string_reasons = [
        reason for reason in low_confidence_reason if isinstance(reason, str)
    ]
    invalid_reasons = sorted(
        {
            reason
            for reason in string_reasons
            if reason not in VALID_LOW_CONFIDENCE_REASONS
        }
    )
    if invalid_reasons:
        errors.append(
            "low_confidence_reason contains invalid reason(s): "
            + ", ".join(invalid_reasons)
        )
    if confidence == "low" and not low_confidence_reason:
        warnings.append("low confidence asset should declare low_confidence_reason")
    if confidence != "low" and low_confidence_reason:
        warnings.append("low_confidence_reason is set while confidence is not low")

    missing_fields = asset.get("missing_fields")
    if isinstance(missing_fields, list) and missing_fields:
        warnings.append(
            "asset declares missing_fields: "
            + ", ".join(str(item) for item in missing_fields)
        )
    elif missing_fields:
        warnings.append("asset declares malformed missing_fields")

    privacy_flags = asset.get("privacy_flags")
    if isinstance(privacy_flags, list) and privacy_flags:
        warnings.append("asset has privacy_flags; require user confirmation before saving")
    elif privacy_flags:
        warnings.append("asset declares malformed privacy_flags")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "asset_type": asset_type,
        "valid_next": valid_next,
        "normalized_valid_next": normalized_valid_next,
        "required_fields": required_fields,
        "low_confidence_reason": low_confidence_reason,
        "normalized_asset": normalized_asset,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an Eva Asset card.")
    parser.add_argument("--asset", required=True, help="Path to asset JSON or Markdown.")
    parser.add_argument("--schema", help="Path to asset-card.schema.json.")
    parser.add_argument("--downstream", help="Optional downstream module/link to check against valid_next.")
    add_common_arguments(parser)
    args = parser.parse_args()

    base = default_base_from_script(__file__)
    asset_path = normalize_path(args.asset)
    schema_path = normalize_path(args.schema) if args.schema else base / "schemas" / "asset-card.schema.json"

    if not asset_path.exists():
        exit_with(result(False, "asset_validate", "资产文件不存在", [str(asset_path)]))
    if not schema_path.exists():
        exit_with(result(False, "asset_validate", "Schema 文件不存在", [str(schema_path)]))

    try:
        asset = load_asset(asset_path)
    except Exception as exc:
        exit_with(result(False, "asset_validate", "资产读取失败", [str(exc)]))

    try:
        schema = read_json(schema_path)
        validation = validate_asset_payload(asset, schema, base, args.downstream)
    except Exception as exc:
        exit_with(result(False, "asset_validate", "资产校验器读取配置失败", [str(exc)]))

    ok = bool(validation["ok"])
    exit_with(
        result(
            ok,
            "asset_validate",
            "资产校验通过" if ok else "资产校验失败",
            validation["errors"],
            validation["warnings"],
            {
                "asset_path": str(asset_path),
                "schema_path": str(schema_path),
                "asset_type": validation["asset_type"],
                "valid_next": validation["valid_next"],
                "normalized_valid_next": validation["normalized_valid_next"],
                "required_fields": validation["required_fields"],
                "low_confidence_reason": validation["low_confidence_reason"],
            },
        )
    )


if __name__ == "__main__":
    main()
