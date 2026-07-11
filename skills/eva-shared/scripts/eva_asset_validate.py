#!/usr/bin/env python3
"""Validate Eva Asset cards."""

from __future__ import annotations

import argparse
from pathlib import Path

from eva_common import (
    CORE_ENTRIES,
    VALID_ASSET_TYPES,
    VALID_HANDOFF_TARGETS,
    VALID_LOW_CONFIDENCE_REASONS,
    add_common_arguments,
    canonical_handoff_target,
    canonicalize_handoff_targets,
    coerce_asset_from_markdown,
    default_base_from_script,
    exit_with,
    is_blank_value,
    load_asset_types,
    normalize_path,
    parse_markdown_fields,
    read_json,
    required_fields_for_asset,
    result,
    simple_schema_validate,
)


def source_allowed_for_asset(source_module: object, allowed_sources: list) -> bool:
    if source_module in allowed_sources:
        return True
    if not isinstance(source_module, str):
        return False
    if "eva-link" in allowed_sources and source_module not in CORE_ENTRIES:
        return True
    return False


def load_asset(path: Path) -> dict:
    if path.suffix.lower() == ".json":
        payload = read_json(path)
        if not isinstance(payload, dict):
            raise ValueError("asset JSON must be an object")
        return payload
    fields = parse_markdown_fields(path)
    return coerce_asset_from_markdown(fields)


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

    errors: list[str] = []
    warnings: list[str] = []

    if not asset_path.exists():
        exit_with(result(False, "asset_validate", "资产文件不存在", [str(asset_path)]))
    if not schema_path.exists():
        exit_with(result(False, "asset_validate", "Schema 文件不存在", [str(schema_path)]))

    try:
        asset = load_asset(asset_path)
    except Exception as exc:
        exit_with(result(False, "asset_validate", "资产读取失败", [str(exc)]))

    schema = read_json(schema_path)
    errors.extend(simple_schema_validate(asset, schema))

    asset_type = asset.get("asset_type")
    if asset_type not in VALID_ASSET_TYPES:
        errors.append(f"asset_type '{asset_type}' is not a valid Eva asset type")
    else:
        asset_type_config = load_asset_types(base)["assets"].get(str(asset_type), {})
        allowed_sources = asset_type_config.get("produced_by") or []
        source_module = asset.get("source_module")
        if allowed_sources and not source_allowed_for_asset(source_module, allowed_sources):
            errors.append(
                f"source_module '{source_module}' is not allowed to produce asset_type "
                f"'{asset_type}'; expected one of: " + ", ".join(map(str, allowed_sources))
            )
        missing_required = [
            field for field in required_fields_for_asset(str(asset_type), base)
            if field not in asset or is_blank_value(asset.get(field))
        ]
        if missing_required:
            errors.append(
                f"asset_type '{asset_type}' missing required field(s): "
                + ", ".join(missing_required)
            )

    valid_next = asset.get("valid_next") or []
    invalid_next = sorted(set(valid_next) - VALID_HANDOFF_TARGETS)
    if invalid_next:
        errors.append("valid_next contains invalid handoff target(s): " + ", ".join(invalid_next))

    normalized_valid_next = canonicalize_handoff_targets(valid_next, base)
    compatibility_aliases = sorted(
        str(target) for target in valid_next
        if canonical_handoff_target(target, base) != str(target)
    )
    if compatibility_aliases:
        warnings.append(
            "valid_next uses compatibility alias(es); new assets should write canonical target names: "
            + ", ".join(compatibility_aliases)
        )

    if args.downstream:
        normalized_downstream = canonical_handoff_target(args.downstream, base)
        if normalized_downstream not in normalized_valid_next:
            errors.append(f"downstream '{args.downstream}' is not listed in valid_next")

    confidence = asset.get("confidence")
    low_confidence_reason = asset.get("low_confidence_reason") or []
    if isinstance(low_confidence_reason, str):
        low_confidence_reason = [low_confidence_reason]
    invalid_reasons = sorted(set(low_confidence_reason) - VALID_LOW_CONFIDENCE_REASONS)
    if invalid_reasons:
        errors.append("low_confidence_reason contains invalid reason(s): " + ", ".join(invalid_reasons))
    if confidence == "low" and not low_confidence_reason:
        warnings.append("low confidence asset should declare low_confidence_reason")
    if confidence != "low" and low_confidence_reason:
        warnings.append("low_confidence_reason is set while confidence is not low")

    missing_fields = asset.get("missing_fields") or []
    if missing_fields:
        warnings.append("asset declares missing_fields: " + ", ".join(map(str, missing_fields)))

    privacy_flags = asset.get("privacy_flags") or []
    if privacy_flags:
        warnings.append("asset has privacy_flags; require user confirmation before saving")

    ok = not errors
    exit_with(
        result(
            ok,
            "asset_validate",
            "资产校验通过" if ok else "资产校验失败",
            errors,
            warnings,
            {
                "asset_path": str(asset_path),
                "schema_path": str(schema_path),
                "asset_type": asset_type,
                "valid_next": valid_next,
                "normalized_valid_next": normalized_valid_next,
                "required_fields": required_fields_for_asset(str(asset_type), base) if asset_type in VALID_ASSET_TYPES else [],
                "low_confidence_reason": low_confidence_reason,
            },
        )
    )


if __name__ == "__main__":
    main()
