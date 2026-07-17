#!/usr/bin/env python3
"""Check Eva Shared 2.2.2 local structure and dependencies."""

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
    handoff_aliases,
    handoff_internal_stages,
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
    "eva_prompt_lint.py",
    "eva_selftest.py",
    "eva_memory_inventory.py",
]

OPTIONAL_SCRIPTS = []

REQUIRED_PEER_SKILLS = {
    "eva": [
        "references/project/00_project-info_项目身份与许可.md",
        "references/project/01_project-license-routing_项目许可问答路由.md",
    ],
    "eva-new-user": [],
    "eva-audience-finder": [
        "../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md",
    ],
    "eva-think": [
        "references/think/00_eva-think_思考助理.md",
        "references/think/01_eva-reframe_表象问题归位.md",
        "../eva-shared/references/shared/04_light-interaction_轻交互协议.md",
        "../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md",
        "../eva-shared/references/benchmark/00_eva-benchmark-copy_对标文案拆解.md",
        "../eva-shared/references/quality/00_eva-ai-check_表达真实性审查.md",
        "../eva-shared/references/shared/06_external-material-safety_外部材料安全边界.md",
        "../eva-shared/references/lens/00_eva-lens-discipline-divergence_学科发散.md",
    ],
    "eva-create": [
        "references/create/00_eva-create_创作主入口.md",
        "references/create/article/00_eva-article_文章主入口.md",
        "references/create/article/01_eva-article-argument_观点与论证路线.md",
        "references/create/article/02_eva-article-writing_文章撰写与长度调节.md",
        "../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md",
        "../eva-shared/references/benchmark/00_eva-benchmark-copy_对标文案拆解.md",
        "../eva-shared/references/quality/00_eva-ai-check_表达真实性审查.md",
        "../eva-shared/references/commerce/00_eva-commerce_商单主入口.md",
        "../eva-shared/references/shared/00_handoff-cards_交接卡字段真源.md",
        "../eva-shared/references/shared/02_low-confidence_低置信度授权协议.md",
        "../eva-shared/references/shared/03_commercial-constraint-card_商单约束卡真源.md",
        "../eva-shared/references/shared/06_external-material-safety_外部材料安全边界.md",
    ],
    "eva-brief": [
        "../eva-shared/schemas/asset-types.json",
        "../eva-shared/references/commerce/00_eva-commerce_商单主入口.md",
        "../eva-shared/references/shared/03_commercial-constraint-card_商单约束卡真源.md",
        "../eva-shared/references/shared/01_asset-state_资产状态归一表.md",
        "../eva-shared/references/shared/02_low-confidence_低置信度授权协议.md",
        "../eva-shared/references/asset/00_eva-asset_资产卡协议.md",
        "../eva-shared/references/commerce/01_brief-parse_Brief基础解析.md",
        "../eva-shared/references/commerce/02_constraint-card_商单约束卡生成.md",
        "../eva-shared/references/commerce/03_draft-check_已有商单稿检查.md",
        "../eva-shared/references/commerce/04_sample-transfer_对标样本迁移.md",
        "../eva-shared/references/shared/06_external-material-safety_外部材料安全边界.md",
    ],
    "eva-learn": [
        "../eva-shared/schemas/asset-types.json",
        "../eva-shared/references/learn/00_eva-learn.md",
        "../eva-shared/references/learn/05_eva-learn-project_分级建档与恢复.md",
        "../eva-shared/references/shared/04_light-interaction_轻交互协议.md",
        "../eva-shared/references/asset/00_eva-asset_资产卡协议.md",
        "../eva-shared/references/harness/00_eva-harness_状态与交接校验.md",
        "../eva-shared/references/shared/06_external-material-safety_外部材料安全边界.md",
    ],
    "eva-link": [
        "references/link/00_eva-link_本地模块连接.md",
        "references/link/01_eva-link-builder_自定义Link生成.md",
        "references/link/02_eva-link-doctor_Link健康检查.md",
        "references/link/03_eva-link-builder-templates_生成模板.md",
        "../eva-shared/references/asset/00_eva-asset_资产卡协议.md",
        "../eva-shared/references/harness/00_eva-harness_状态与交接校验.md",
        "../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md",
        "../eva-shared/references/shared/06_external-material-safety_外部材料安全边界.md",
    ],
    "eva-review": [
        "references/review/00_entry_入口与模式路由.md",
        "references/review/01_frontstage_前台语言.md",
        "references/review/02_single_单篇复盘.md",
        "references/review/03_pattern_批量规律回溯.md",
        "references/review/04_backfill_结果回填.md",
        "references/review/05_record_记录字段真源.md",
        "references/review/06_store_记录库与保存协议.md",
        "../eva-shared/schemas/asset-types.json",
        "../eva-shared/references/asset/00_eva-asset_资产卡协议.md",
        "../eva-shared/references/shared/06_external-material-safety_外部材料安全边界.md",
    ],
    "eva-lens": [
        "references/lens/00_entry_入口与模式.md",
        "references/lens/01_quick_快速补光.md",
        "references/lens/02_deep_深度审视.md",
        "references/lens/03_evidence_证据与出口边界.md",
        "../eva-shared/references/lens/00_eva-lens-discipline-divergence_学科发散.md",
        "../eva-shared/references/shared/06_external-material-safety_外部材料安全边界.md",
    ],
    "eva-preflight": [
        "references/preflight/00_eva-preflight_发布前审核主控.md",
        "references/preflight/01_eva-preflight-shortvideo_短视频审核.md",
        "references/preflight/02_eva-preflight-article_文章审核.md",
        "references/preflight/03_eva-preflight-social_图文与一般社媒内容审核.md",
        "references/preflight/04_eva-preflight-expression-assets_表达资产增强.md",
        "references/preflight/05_eva-preflight-truth-source-call_真源只读调用.md",
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
    common_handoff_aliases = handoff_aliases(base)
    common_internal_stages = handoff_internal_stages(base)
    raw_aliases = handoff_registry.get("aliases") or {}
    raw_canonical_targets = handoff_registry.get("canonical_targets") or []
    raw_internal_stages = handoff_registry.get("internal_stages") or []
    canonical_targets = set(raw_canonical_targets) if isinstance(raw_canonical_targets, list) else set()
    internal_stages = set(raw_internal_stages) if isinstance(raw_internal_stages, list) else set()

    data["asset_types_count"] = len(registry_assets)
    data["asset_types"] = sorted(registry_assets)
    data["handoff_targets_count"] = len(handoff_registry_targets)
    data["handoff_targets"] = sorted(handoff_registry_targets)
    data["handoff_aliases"] = raw_aliases
    data["handoff_internal_stages"] = sorted(internal_stages)

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

    if not isinstance(raw_aliases, dict):
        errors.append("handoff-targets.json aliases must be an object")
        raw_aliases = {}
    if not isinstance(raw_canonical_targets, list) or not raw_canonical_targets:
        errors.append("handoff-targets.json canonical_targets must be a non-empty array")
    if not isinstance(raw_internal_stages, list):
        errors.append("handoff-targets.json internal_stages must be an array")
    if raw_aliases != common_handoff_aliases:
        errors.append("handoff alias drift: eva_common differs from handoff-targets.json")
    if internal_stages != common_internal_stages:
        errors.append("handoff internal-stage drift: eva_common differs from handoff-targets.json")

    invalid_alias_names = sorted(set(raw_aliases) - handoff_registry_targets)
    invalid_alias_targets = sorted(set(raw_aliases.values()) - handoff_registry_targets)
    if invalid_alias_names:
        errors.append("handoff alias name(s) missing from targets: " + ", ".join(invalid_alias_names))
    if invalid_alias_targets:
        errors.append("handoff alias canonical target(s) missing from targets: " + ", ".join(invalid_alias_targets))
    invalid_canonical_targets = sorted(canonical_targets - handoff_registry_targets)
    if invalid_canonical_targets:
        errors.append("canonical handoff target(s) missing from targets: " + ", ".join(invalid_canonical_targets))
    required_canonical_targets = {
        "eva",
        "eva-learn",
        "eva-brief",
        "eva-think",
        "eva-create",
        "eva-memory",
        "eva-link",
        "eva-review",
        "eva-lens",
    }
    missing_canonical_targets = sorted(required_canonical_targets - canonical_targets)
    if missing_canonical_targets:
        errors.append("canonical_targets missing Eva entry/module name(s): " + ", ".join(missing_canonical_targets))
    invalid_internal_stages = sorted(internal_stages - handoff_registry_targets)
    if invalid_internal_stages:
        errors.append("internal handoff stage(s) missing from targets: " + ", ".join(invalid_internal_stages))
    classified_targets = canonical_targets | set(raw_aliases) | internal_stages
    unclassified_targets = sorted(handoff_registry_targets - classified_targets)
    if unclassified_targets:
        errors.append("handoff target(s) lack canonical/alias/internal classification: " + ", ".join(unclassified_targets))

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
        alias_targets = sorted(set(config.get("valid_next") or []) & set(raw_aliases))
        if alias_targets:
            errors.append(
                f"asset type {name} uses compatibility alias(es) in valid_next; new registry entries must use canonical names: "
                + ", ".join(alias_targets)
            )
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


def check_peer_skills(base: Path) -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    data: dict = {}

    if base.name != "eva-shared":
        warnings.append("peer skill checks skipped because --base is not the eva-shared folder")
        return errors, warnings, data

    skills_root = base.parent
    package_root = skills_root.parent
    skillhub_bundle = skills_root.name == "modules" and (package_root / "SKILL.md").exists()
    source_checkout = (package_root / ".git").exists() or (package_root / ".claude-plugin" / "marketplace.json").exists()
    data["skillhub_bundle"] = skillhub_bundle
    if skillhub_bundle:
        package_readme = package_root / "README.md"
        package_version = package_root / "VERSION"
        data["skillhub_root_readme"] = str(package_readme) if package_readme.exists() else None
        data["skillhub_root_version"] = str(package_version) if package_version.exists() else None
        if not package_readme.exists():
            errors.append("missing SkillHub package root README.md")
        if not package_version.exists():
            errors.append("missing SkillHub package root VERSION")
    if source_checkout or skillhub_bundle:
        required_legal_files = ("LICENSE", "LEGAL_NOTICE.md", "TRADEMARKS.md", "THIRD_PARTY_NOTICES.md")
        missing_legal_files = [name for name in required_legal_files if not (package_root / name).exists()]
        data["root_legal_files"] = {
            name: str(package_root / name) if (package_root / name).exists() else None
            for name in required_legal_files
        }
        if missing_legal_files:
            errors.append("missing package root legal file(s): " + ", ".join(missing_legal_files))
    schema_path = base / "schemas" / "asset-types.json"
    shared_skill_md = base / "SKILL.md"
    data["eva_shared_has_skill_md"] = shared_skill_md.exists()
    if not shared_skill_md.exists():
        errors.append("eva-shared must contain SKILL.md so GitHub skill installers copy the shared package")
    else:
        shared_skill_text = shared_skill_md.read_text(encoding="utf-8")
        for marker in ("name: eva-shared", "Do not use directly", "not a user-facing Eva entry", "Direct Invocation Response"):
            if marker not in shared_skill_text:
                errors.append(f"eva-shared SKILL.md missing support-only marker: {marker}")
    shared_openai_yaml = base / "agents" / "openai.yaml"
    if not shared_openai_yaml.exists():
        errors.append("eva-shared must include agents/openai.yaml with implicit invocation disabled")
    else:
        shared_openai_text = shared_openai_yaml.read_text(encoding="utf-8")
        if "allow_implicit_invocation: false" not in shared_openai_text:
            errors.append("eva-shared agents/openai.yaml must set allow_implicit_invocation: false")

    if schema_path.exists():
        version = str(read_json(schema_path).get("version", ""))
        data["eva_shared_asset_types_version"] = version
        expected_version = VERSION.rsplit("-", 1)[-1]
        if version != expected_version:
            errors.append(
                "schemas/asset-types.json version must match eva_common "
                f"{expected_version}, got {version or '<missing>'}"
            )

    peer_status: dict[str, dict] = {}
    for skill_name, referenced_paths in REQUIRED_PEER_SKILLS.items():
        skill_root = skills_root / skill_name
        skill_file = skill_root / "SKILL.md"
        status = {
            "skill_file": str(skill_file),
            "present": skill_file.exists(),
            "references_checked": referenced_paths,
        }
        peer_status[skill_name] = status
        if not skill_file.exists():
            errors.append(f"missing peer skill: ../{skill_name}/SKILL.md")
            continue
        skill_text = skill_file.read_text(encoding="utf-8")
        if skill_name not in ("eva", "eva-new-user", "eva-lens") and "../eva-shared" not in skill_text:
            warnings.append(f"../{skill_name}/SKILL.md does not reference ../eva-shared")
        for relative in referenced_paths:
            target = (skill_root / relative).resolve()
            if not target.exists():
                errors.append(f"../{skill_name}/SKILL.md referenced missing source: {relative}")
        if skill_name in ("eva-think", "eva-lens"):
            discipline_reference = "../eva-shared/references/lens/00_eva-lens-discipline-divergence_学科发散.md"
            if discipline_reference not in skill_text:
                errors.append(
                    f"../{skill_name}/SKILL.md must reference the shared Lens discipline-divergence truth source"
                )
    data["peer_skills"] = peer_status
    return errors, warnings, data


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Eva Shared structure and dependencies.")
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

    peer_errors, peer_warnings, peer_data = check_peer_skills(base)
    errors.extend(peer_errors)
    warnings.extend(peer_warnings)
    data.update(peer_data)

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
            f"Eva Shared {VERSION.rsplit('-', 1)[-1]}结构正常"
            if ok
            else f"Eva Shared {VERSION.rsplit('-', 1)[-1]}结构异常",
            errors,
            warnings,
            data,
        )
    )


if __name__ == "__main__":
    main()
