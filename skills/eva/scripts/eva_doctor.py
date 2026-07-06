#!/usr/bin/env python3
"""Check Eva Harness 2.0 local health."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from eva_common import (
    VALID_ASSET_TYPES,
    VALID_LOW_CONFIDENCE_REASONS,
    VERSION,
    add_common_arguments,
    asset_type_names,
    exit_with,
    handoff_targets,
    normalize_path,
    read_json,
    result,
)


REQUIRED_SCHEMAS = [
    "asset-types.json",
    "handoff-targets.json",
    "asset-card.schema.json",
    "eva-link.schema.json",
    "link-registry.schema.json",
    "initializer-card.schema.json",
    "failure-record.schema.json",
]

REQUIRED_SCRIPTS = [
    "eva_common.py",
    "eva_asset_validate.py",
    "eva_link_check.py",
    "eva_doctor.py",
    "eva_selftest.py",
]

OPTIONAL_SCRIPTS = []

REQUIRED_SIBLING_SKILLS = {
    "eva-brief": [
        "../eva/schemas/asset-types.json",
        "../eva/references/create/commerce/00_eva-commerce_商单主入口.md",
        "../eva/references/shared/03_commercial-constraint-card_商单约束卡真源.md",
        "../eva/references/shared/01_asset-state_资产状态归一表.md",
        "../eva/references/shared/02_low-confidence_低置信度授权协议.md",
        "../eva/references/asset/00_eva-asset_资产卡协议.md",
        "../eva/references/create/commerce/01_brief-parse_Brief基础解析.md",
        "../eva/references/create/commerce/02_constraint-card_商单约束卡生成.md",
        "../eva/references/create/commerce/03_draft-check_已有商单稿检查.md",
        "../eva/references/create/commerce/04_sample-transfer_对标样本迁移.md",
    ],
    "eva-learn": [
        "../eva/schemas/asset-types.json",
        "../eva/references/learn/00_eva-learn.md",
        "../eva/references/shared/04_light-interaction_轻交互协议.md",
        "../eva/references/asset/00_eva-asset_资产卡协议.md",
        "../eva/references/harness/00_eva-harness_状态与交接校验.md",
    ],
}


def check_files(base: Path, folder: str, names: list[str]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    present: list[str] = []
    for name in names:
        path = base / folder / name
        if path.exists():
            present.append(str(path))
        else:
            errors.append(f"missing {folder}/{name}")
    return errors, present


def check_asset_type_truth(base: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    data: dict = {}

    registry_path = base / "schemas" / "asset-types.json"
    handoff_path = base / "schemas" / "handoff-targets.json"
    schema_path = base / "schemas" / "asset-card.schema.json"
    asset_doc_path = base / "references" / "asset" / "00_eva-asset_资产卡协议.md"

    if not registry_path.exists() or not schema_path.exists() or not handoff_path.exists():
        return errors, warnings, data

    registry = read_json(registry_path)
    handoff_registry = read_json(handoff_path)
    registry_assets = set((registry.get("assets") or {}).keys())
    raw_handoff_targets = handoff_registry.get("targets") or []
    handoff_registry_targets = set(raw_handoff_targets)
    schema = read_json(schema_path)
    schema_assets = set(schema.get("properties", {}).get("asset_type", {}).get("enum") or [])
    schema_low_confidence_reasons = set(
        schema.get("properties", {})
        .get("low_confidence_reason", {})
        .get("items", {})
        .get("enum")
        or []
    )
    schema_fields = set(schema.get("properties", {}).keys())
    common_assets = asset_type_names(base)
    common_handoff_targets = handoff_targets(base)

    data["asset_types_count"] = len(registry_assets)
    data["asset_types"] = sorted(registry_assets)
    data["handoff_targets_count"] = len(handoff_registry_targets)
    data["handoff_targets"] = sorted(handoff_registry_targets)

    expected_version = VERSION.rsplit("-", 1)[-1]
    registry_version = str(registry.get("version", ""))
    handoff_version = str(handoff_registry.get("version", ""))
    data["eva_common_version"] = VERSION
    data["expected_schema_version"] = expected_version
    if registry_version != expected_version:
        errors.append(
            f"version drift: schemas/asset-types.json version {registry_version or '<missing>'} "
            f"does not match {expected_version}"
        )
    if handoff_version != expected_version:
        errors.append(
            f"version drift: schemas/handoff-targets.json version {handoff_version or '<missing>'} "
            f"does not match {expected_version}"
        )

    if registry_assets != schema_assets:
        errors.append(
            "asset type drift: schemas/asset-types.json and schemas/asset-card.schema.json enum differ"
        )
        data["asset_type_registry_minus_schema"] = sorted(registry_assets - schema_assets)
        data["asset_type_schema_minus_registry"] = sorted(schema_assets - registry_assets)

    if registry_assets != common_assets:
        errors.append("asset type drift: eva_common VALID_ASSET_TYPES differs from asset-types.json")
        data["asset_type_registry_minus_common"] = sorted(registry_assets - common_assets)
        data["asset_type_common_minus_registry"] = sorted(common_assets - registry_assets)

    if handoff_registry_targets != common_handoff_targets:
        errors.append("handoff target drift: eva_common VALID_HANDOFF_TARGETS differs from handoff-targets.json")
        data["handoff_registry_minus_common"] = sorted(handoff_registry_targets - common_handoff_targets)
        data["handoff_common_minus_registry"] = sorted(common_handoff_targets - handoff_registry_targets)

    if schema_low_confidence_reasons != VALID_LOW_CONFIDENCE_REASONS:
        errors.append(
            "low_confidence_reason drift: eva_common VALID_LOW_CONFIDENCE_REASONS differs from asset-card.schema.json"
        )
        data["low_confidence_schema_minus_common"] = sorted(schema_low_confidence_reasons - VALID_LOW_CONFIDENCE_REASONS)
        data["low_confidence_common_minus_schema"] = sorted(VALID_LOW_CONFIDENCE_REASONS - schema_low_confidence_reasons)

    duplicated_targets = sorted({item for item in raw_handoff_targets if raw_handoff_targets.count(item) > 1})
    if duplicated_targets:
        errors.append("handoff-targets.json contains duplicate target(s): " + ", ".join(duplicated_targets))

    missing_core_targets = sorted(set(["eva-create", "eva-memory", "eva-link"]) - handoff_registry_targets)
    if missing_core_targets:
        errors.append("handoff-targets.json missing core target(s): " + ", ".join(missing_core_targets))

    visibility_values = set((registry.get("visibility_values") or {}).keys())
    for name, config in (registry.get("assets") or {}).items():
        visibility = config.get("visibility")
        if visibility not in visibility_values:
            errors.append(f"asset type {name} has invalid visibility: {visibility}")
        missing = [field for field in ["produced_by", "valid_next", "required_fields", "is_handoff", "visibility"] if field not in config]
        if missing:
            errors.append(f"asset type {name} missing config field(s): {', '.join(missing)}")
        required_fields = config.get("required_fields") or []
        if not isinstance(required_fields, list) or not required_fields:
            errors.append(f"asset type {name} required_fields must be a non-empty array")
        else:
            invalid_required = set(required_fields) - schema_fields
            if invalid_required:
                errors.append(f"asset type {name} required_fields contains unknown field(s): {', '.join(sorted(invalid_required))}")
        invalid_next = set(config.get("valid_next") or []) - handoff_registry_targets
        if invalid_next:
            errors.append(f"asset type {name} has invalid valid_next target(s): {', '.join(sorted(invalid_next))}")

    if asset_doc_path.exists():
        text = asset_doc_path.read_text(encoding="utf-8")
        doc_assets = set(re.findall(r"\|\s*([a-z][a-z0-9-]*-card)\s*\|", text))
        missing_in_registry = doc_assets - registry_assets
        if missing_in_registry:
            errors.append("asset type drift: asset protocol doc contains type(s) absent from asset-types.json")
            data["asset_type_doc_minus_registry"] = sorted(missing_in_registry)
        missing_in_doc = registry_assets - doc_assets
        if missing_in_doc:
            warnings.append("asset protocol doc matrix omits asset type(s): " + ", ".join(sorted(missing_in_doc)))

    return errors, warnings, data


def check_sibling_skills(base: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    data: dict = {}

    if base.name != "eva":
        warnings.append("sibling skill checks skipped because --base is not the eva skill folder")
        return errors, warnings, data

    skills_root = base.parent
    schema_path = base / "schemas" / "asset-types.json"
    if schema_path.exists():
        version = str(read_json(schema_path).get("version", ""))
        data["eva_asset_types_version"] = version
        if not version.startswith("2.0."):
            errors.append(f"schemas/asset-types.json version must be 2.0.x, got {version or '<missing>'}")

    sibling_status: dict[str, dict] = {}
    for skill_name, referenced_paths in REQUIRED_SIBLING_SKILLS.items():
        skill_root = skills_root / skill_name
        skill_file = skill_root / "SKILL.md"
        status = {
            "skill_file": str(skill_file),
            "present": skill_file.exists(),
            "references_checked": referenced_paths,
        }
        sibling_status[skill_name] = status
        if not skill_file.exists():
            errors.append(f"missing sibling skill: ../{skill_name}/SKILL.md")
            continue
        skill_text = skill_file.read_text(encoding="utf-8")
        if "2.0.x" not in skill_text:
            warnings.append(f"../{skill_name}/SKILL.md does not explicitly guard sibling eva version 2.0.x")
        for relative in referenced_paths:
            target = (skill_root / relative).resolve()
            if not target.exists():
                errors.append(f"../{skill_name}/SKILL.md referenced missing sibling source: {relative}")
    data["sibling_skills"] = sibling_status
    return errors, warnings, data


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Eva Harness 2.0 health.")
    parser.add_argument("--base", default=".", help="Base folder containing schemas/ and scripts/.")
    parser.add_argument("--link", action="append", help="Optional Link config path to note in report.")
    add_common_arguments(parser)
    args = parser.parse_args()

    base = normalize_path(args.base)
    errors: list[str] = []
    warnings: list[str] = []
    data: dict = {"base": str(base)}

    if not base.exists():
        exit_with(result(False, "doctor", "Base 路径不存在", [str(base)]))

    schema_errors, schemas = check_files(base, "schemas", REQUIRED_SCHEMAS)
    script_errors, scripts = check_files(base, "scripts", REQUIRED_SCRIPTS)
    optional_script_errors, optional_scripts = check_files(base, "scripts", OPTIONAL_SCRIPTS)
    errors.extend(schema_errors)
    errors.extend(script_errors)
    if optional_script_errors:
        warnings.extend(optional_script_errors)
    data["schemas"] = schemas
    data["scripts"] = scripts
    data["optional_scripts"] = optional_scripts

    truth_errors, truth_warnings, truth_data = check_asset_type_truth(base)
    errors.extend(truth_errors)
    warnings.extend(truth_warnings)
    data.update(truth_data)

    sibling_errors, sibling_warnings, sibling_data = check_sibling_skills(base)
    errors.extend(sibling_errors)
    warnings.extend(sibling_warnings)
    data.update(sibling_data)

    if args.link:
        data["links"] = [str(normalize_path(item)) for item in args.link]
        for raw in args.link:
            path = normalize_path(raw)
            if not path.exists():
                warnings.append(f"link path does not exist: {path}")

    ok = not errors
    exit_with(
        result(
            ok,
            "doctor",
            "Eva Harness 2.0状态正常" if ok else "Eva Harness 2.0状态异常",
            errors,
            warnings,
            data,
        )
    )


if __name__ == "__main__":
    main()
