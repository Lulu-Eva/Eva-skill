#!/usr/bin/env python3
"""Validate Eva Asset cards."""

from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import date
from pathlib import Path, PurePosixPath
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

PRODUCT_SERVICE_ASSET_TYPE = "product-service-card"
PRODUCT_SERVICE_CORE_FIELDS = (
    "offering_form",
    "can_help_with",
    "fit_situations",
    "help_method",
    "responsible_outcome",
    "boundaries",
    "lifecycle_status",
)
PRODUCT_SERVICE_OFFERING_FORMS = {
    "product",
    "standardized_service",
    "consulting",
    "project_collaboration",
    "professional_capability",
}
PRODUCT_SERVICE_LIFECYCLE_STATUSES = {"active", "paused", "retired"}
PRODUCT_SERVICE_EVIDENCE_STATUSES = {
    "user_confirmed",
    "material_supported_inference",
    "pending_validation",
}
PRODUCT_SERVICE_PROFILE_ID_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z"
)


def _has_meaningful_product_service_value(value: object) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value) and any(
            _has_meaningful_product_service_value(item) for item in value
        )
    if isinstance(value, dict):
        return bool(value) and any(
            _has_meaningful_product_service_value(item) for item in value.values()
        )
    return value is not None and not isinstance(value, bool)


def _safe_product_service_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return False
    if "\\" in value or "\x00" in value or re.match(r"^[A-Za-z]:", value):
        return False
    candidate = PurePosixPath(value)
    return bool(
        not candidate.is_absolute()
        and candidate.as_posix() not in {"", "."}
        and candidate.as_posix() == value
        and ".." not in candidate.parts
        and all(part not in {"", "."} for part in candidate.parts)
    )


def validate_product_service_asset(asset: dict[str, Any]) -> list[str]:
    """Validate fields that apply only to product-service-card assets."""
    if asset.get("asset_type") != PRODUCT_SERVICE_ASSET_TYPE:
        return []

    errors: list[str] = []
    profile_id = asset.get("profile_id")
    if not isinstance(profile_id, str) or not PRODUCT_SERVICE_PROFILE_ID_PATTERN.fullmatch(
        profile_id
    ):
        errors.append(
            "product-service-card profile_id must be 1-128 ASCII letters, digits, dots, underscores or hyphens and start with a letter or digit"
        )

    revision = asset.get("revision")
    valid_revision = (
        isinstance(revision, int) and not isinstance(revision, bool) and revision > 0
    )
    if not valid_revision:
        errors.append("product-service-card revision must be a positive integer")

    facts_confirmed_at = asset.get("facts_confirmed_at")
    valid_facts_confirmed_at = False
    if isinstance(facts_confirmed_at, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}", facts_confirmed_at
    ):
        try:
            date.fromisoformat(facts_confirmed_at)
        except ValueError:
            pass
        else:
            valid_facts_confirmed_at = True
    if not valid_facts_confirmed_at:
        errors.append(
            "product-service-card facts_confirmed_at must be a valid YYYY-MM-DD calendar date"
        )

    lifecycle_status = asset.get("lifecycle_status")
    if not isinstance(lifecycle_status, str) or (
        lifecycle_status not in PRODUCT_SERVICE_LIFECYCLE_STATUSES
    ):
        errors.append(
            "product-service-card lifecycle_status must be active, paused or retired"
        )

    core_content = asset.get("core_content")
    if not isinstance(core_content, dict):
        errors.append("product-service-card core_content must be an object")
        core_content = {}
    missing_core_fields = [
        field
        for field in PRODUCT_SERVICE_CORE_FIELDS
        if field not in core_content
        or not _has_meaningful_product_service_value(core_content.get(field))
    ]
    if missing_core_fields:
        errors.append(
            "product-service-card core_content missing non-blank field(s): "
            + ", ".join(missing_core_fields)
        )

    offering_form = core_content.get("offering_form")
    if not isinstance(offering_form, str) or (
        offering_form not in PRODUCT_SERVICE_OFFERING_FORMS
    ):
        errors.append(
            "product-service-card core_content.offering_form must be one of: "
            + ", ".join(sorted(PRODUCT_SERVICE_OFFERING_FORMS))
        )
    core_lifecycle_status = core_content.get("lifecycle_status")
    if not isinstance(core_lifecycle_status, str) or (
        core_lifecycle_status not in PRODUCT_SERVICE_LIFECYCLE_STATUSES
    ):
        errors.append(
            "product-service-card core_content.lifecycle_status must be active, paused or retired"
        )
    elif isinstance(lifecycle_status, str) and (
        lifecycle_status in PRODUCT_SERVICE_LIFECYCLE_STATUSES
    ) and (
        core_lifecycle_status != lifecycle_status
    ):
        errors.append(
            "product-service-card top-level lifecycle_status must equal core_content.lifecycle_status"
        )

    for field in PRODUCT_SERVICE_CORE_FIELDS:
        if field in {"offering_form", "lifecycle_status"} or field not in core_content:
            continue
        value = core_content.get(field)
        if not isinstance(value, (str, list, dict)):
            errors.append(
                f"product-service-card core_content.{field} must be a string, array or object"
            )

    evidence = asset.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("product-service-card evidence must be a non-empty array")
    else:
        for index, item in enumerate(evidence):
            prefix = f"product-service-card evidence[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            content = item.get("content")
            if not isinstance(content, str) or not content.strip():
                errors.append(f"{prefix}.content must be a non-blank string")
            status = item.get("status")
            if not isinstance(status, str) or (
                status not in PRODUCT_SERVICE_EVIDENCE_STATUSES
            ):
                errors.append(
                    f"{prefix}.status must be one of: "
                    + ", ".join(sorted(PRODUCT_SERVICE_EVIDENCE_STATUSES))
                )
            if "source" in item:
                source = item.get("source")
                if not isinstance(source, str) or not source.strip():
                    errors.append(f"{prefix}.source must be a non-blank string when set")

    supersedes = asset.get("supersedes")
    declares_supersedes = "supersedes" in asset
    has_supersedes = declares_supersedes and not is_blank_value(supersedes)
    if declares_supersedes and not _safe_product_service_relative_path(supersedes):
        errors.append(
            "product-service-card supersedes must be a safe project-relative POSIX path without traversal"
        )
    if valid_revision:
        if revision == 1 and declares_supersedes:
            errors.append("product-service-card revision 1 must not declare supersedes")
        elif revision > 1 and not has_supersedes:
            errors.append("product-service-card revision greater than 1 requires supersedes")

    return errors


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
    errors.extend(validate_product_service_asset(asset))

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
