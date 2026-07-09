#!/usr/bin/env python3
"""Minimal Eva Harness 2.0.4 regression checks."""

from __future__ import annotations

import argparse
import json
import tempfile

from eva_link_check import validate_expected_asset as validate_link_expected_asset
from eva_common import (
    CORE_ENTRIES,
    VALID_ASSET_TYPES,
    VALID_HANDOFF_TARGETS,
    add_common_arguments,
    default_base_from_script,
    exit_with,
    is_blank_value,
    load_asset_types,
    normalize_path,
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


REQUIRED_REGRESSION_CASES = {
    "default-start",
    "ordinary-learning-no-auto-learn",
    "explicit-eva-learn",
    "semantic-eva-learn",
    "learn-restore-without-path",
    "material-to-create",
    "explicit-brief",
    "commercial-content-not-brief-entry",
    "title-candidate-check",
    "title-promise-check",
    "opening-only",
    "full-script-needs-route-map",
    "ai-check-default-diagnose",
    "voice-needs-user-sample",
    "moments-voice-extraction-not-create",
    "persona-credibility-diagnosis",
    "explicit-save",
    "review-pending-no-auto-route",
    "review-data-pending-no-auto-route",
    "review-comment-pending-no-auto-route",
    "external-skill-not-2-0-mainline",
    "explicit-link-still-available",
    "custom-eva-skill-means-link-builder",
    "ordinary-moments-writing-not-link-builder",
    "explicit-local-link-call",
    "link-default-needs-confirmation",
    "expression-preload-create-hit",
    "expression-preload-think-no-noise",
    "expression-preload-learn-stays-light",
    "link-doctor-uses-shared-script-path",
    "expression-preload-create-reuse",
    "expression-preload-create-rescan-on-change",
    "expression-preload-specific-detail-notice",
    "voice-current-instruction-priority",
}

REQUIRED_ROUTER_MARKERS = {
    "eva-think": "Router must expose eva-think as the default light entry",
    "eva-create": "Router must route creation and ordinary writing to eva-create",
    "eva-learn": "Router must route explicit Eva Learn requests to eva-learn",
    "eva-brief": "Router must route Brief and sponsored-content constraints to eva-brief",
    "eva-link": "Router must route explicit Link requests to eva-link",
    "带我系统学": "Router must route semantic learning requests to eva-learn",
    "提取我朋友圈的语气": "Router must disambiguate moments voice extraction from creation",
    "人设立不住": "Router must expose persona credibility diagnosis through eva-think",
    "不读取 Harness / Asset / schema": "Router must stay thin and not load shared heavy protocols",
}

REQUIRED_ARCHITECTURE_PATHS = (
    "../eva/SKILL.md",
    "../eva-think/SKILL.md",
    "../eva-think/references/think/00_eva-think_思考助理.md",
    "../eva-create/SKILL.md",
    "../eva-create/references/create/00_eva-create_创作主入口.md",
    "../eva-learn/SKILL.md",
    "../eva-brief/SKILL.md",
    "../eva-link/SKILL.md",
    "../eva-link/references/link/00_eva-link_本地模块连接.md",
    "references/audience/00_eva-audience-finder_话题人群识别器.md",
    "references/learn/00_eva-learn.md",
    "references/commerce/00_eva-commerce_商单主入口.md",
    "references/shared/04_light-interaction_轻交互协议.md",
    "references/shared/05_expression-asset-preload_表达资产轻量预加载协议.md",
    "references/harness/00_eva-harness_状态与交接校验.md",
)

ENTRY_SHARED_GUARD_PATHS = (
    "../eva-think/SKILL.md",
    "../eva-create/SKILL.md",
    "../eva-link/SKILL.md",
)

EXPRESSION_PRELOAD_REQUIRED_ENTRIES = (
    "../eva-think/SKILL.md",
    "../eva-create/SKILL.md",
    "../eva-link/SKILL.md",
    "../eva-learn/SKILL.md",
)

def validate_asset(asset: dict, schema: dict, base) -> list[str]:
    errors = simple_schema_validate(asset, schema)
    asset_type = asset.get("asset_type")
    if asset_type not in VALID_ASSET_TYPES:
        errors.append(f"asset_type {asset_type!r} is invalid")
    else:
        asset_type_config = load_asset_types(base)["assets"].get(str(asset_type), {})
        allowed_sources = asset_type_config.get("produced_by") or []
        source_module = asset.get("source_module")
        if allowed_sources and not source_allowed_for_asset(source_module, allowed_sources):
            errors.append(
                f"source_module {source_module!r} is not allowed to produce asset_type "
                f"{asset_type!r}; expected one of: " + ", ".join(map(str, allowed_sources))
            )
        missing_required = [
            field for field in required_fields_for_asset(str(asset_type), base)
            if field not in asset or is_blank_value(asset.get(field))
        ]
        if missing_required:
            errors.append("missing required field(s): " + ", ".join(missing_required))
    invalid_next = sorted(set(asset.get("valid_next") or []) - VALID_HANDOFF_TARGETS)
    if invalid_next:
        errors.append("valid_next contains invalid target(s): " + ", ".join(invalid_next))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Run minimal Eva Harness regression checks.")
    parser.add_argument("--base", default=None, help="Base folder containing schemas/ and examples/.")
    add_common_arguments(parser)
    args = parser.parse_args()

    base = normalize_path(args.base) if args.base else default_base_from_script(__file__)
    errors: list[str] = []
    warnings: list[str] = []

    schema = read_json(base / "schemas" / "asset-card.schema.json")
    example_asset = read_json(base / "examples" / "asset-card.example.json")

    positive_errors = validate_asset(example_asset, schema, base)
    if positive_errors:
        errors.append("positive asset example failed: " + "; ".join(positive_errors))

    link_config = {
        "id": "local.selftest",
        "produces": ["content-asset-card"],
        "handoff_to": ["eva-memory"],
    }
    strict_link_examples = [
        (
            "asset_type",
            {"asset_type": "idea-card", "source_module": "local.selftest", "valid_next": ["eva-memory"]},
            "not declared in Link produces",
        ),
        (
            "source_module",
            {"asset_type": "content-asset-card", "source_module": "wrong.link", "valid_next": ["eva-memory"]},
            "must equal Link id",
        ),
        (
            "valid_next",
            {"asset_type": "content-asset-card", "source_module": "local.selftest", "valid_next": ["eva-create"]},
            "not declared in Link handoff_to",
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="eva-link-selftest-") as tmp_dir:
        for label, overrides, expected_marker in strict_link_examples:
            strict_asset = dict(example_asset)
            strict_asset.update(overrides)
            strict_asset_path = normalize_path(tmp_dir) / f"{label}.json"
            strict_asset_path.write_text(json.dumps(strict_asset, ensure_ascii=False), encoding="utf-8")
            strict_asset_errors = validate_link_expected_asset(strict_asset_path, base, link_config)
            if not any(expected_marker in item for item in strict_asset_errors):
                errors.append(f"strict Link expected_asset binding failed to catch {label} mismatch")

    bad_asset = dict(example_asset)
    bad_asset["asset_type"] = "fake-card"
    if not validate_asset(bad_asset, schema, base):
        errors.append("negative asset example unexpectedly passed invalid asset_type")

    bad_next = dict(example_asset)
    bad_next["valid_next"] = ["eva-create", "fake-downstream"]
    if not validate_asset(bad_next, schema, base):
        errors.append("negative asset example unexpectedly passed invalid valid_next")

    bad_required = dict(example_asset)
    bad_required.pop("evidence", None)
    if not validate_asset(bad_required, schema, base):
        errors.append("negative asset example unexpectedly passed missing asset-type required field")

    bad_review_source = {
        "asset_type": "review-card",
        "source_module": "eva-create",
        "core_content": "selftest",
        "user_question": "selftest",
        "evidence": ["selftest"],
        "valid_next": ["eva-memory"],
        "saved": False,
        "confidence": "medium",
        "low_confidence_reason": [],
        "missing_fields": [],
        "privacy_flags": [],
        "evidence_level": "L1",
        "path_bottleneck": "unknown",
        "design_type": "single_observation",
        "treatment_variable": "selftest",
        "outcome_variable": "selftest",
        "control_plan": "selftest",
        "adjustment_variables": ["selftest"],
        "hypothesis": "selftest",
        "confounders": ["selftest"],
        "metric_spec": [
            {
                "name": "selftest",
                "role": "primary",
                "numerator": "selftest",
                "denominator": "selftest",
                "window": "selftest",
            }
        ],
        "next_test_action": "selftest",
        "metrics_to_watch": ["selftest"],
        "success_criteria": "selftest",
        "observation_window": "selftest",
        "result_backfill_required": True,
    }
    if not validate_asset(bad_review_source, schema, base):
        errors.append("negative review-card example unexpectedly passed active source_module")

    regression_path = base / "examples" / "prompt-regression-matrix.json"
    if not regression_path.exists():
        errors.append("missing examples/prompt-regression-matrix.json")
    else:
        regression = read_json(regression_path)
        cases = regression.get("cases") or []
        case_ids = {case.get("id") for case in cases if isinstance(case, dict)}
        duplicate_ids = sorted({case_id for case_id in case_ids if sum(1 for case in cases if isinstance(case, dict) and case.get("id") == case_id) > 1})
        if duplicate_ids:
            errors.append("prompt regression matrix contains duplicate id(s): " + ", ".join(str(item) for item in duplicate_ids))
        missing_cases = sorted(REQUIRED_REGRESSION_CASES - case_ids)
        if missing_cases:
            errors.append("prompt regression matrix missing required case(s): " + ", ".join(missing_cases))
        if len(cases) < 10:
            errors.append("prompt regression matrix must keep at least 10 cases")
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                errors.append(f"prompt regression case #{index} must be an object")
                continue
            missing = [field for field in ["id", "input", "expected_route", "forbid", "expected_terminal"] if field not in case]
            if missing:
                errors.append(f"prompt regression case {case.get('id', index)!r} missing field(s): " + ", ".join(missing))
            for field in ["id", "input", "expected_route", "expected_terminal"]:
                if field in case and not isinstance(case[field], str):
                    errors.append(f"prompt regression case {case.get('id', index)!r} field {field} must be a string")
            if "forbid" in case and not isinstance(case["forbid"], list):
                errors.append(f"prompt regression case {case.get('id', index)!r} forbid must be an array")

    if (base / "SKILL.md").exists():
        errors.append("eva-shared must not have SKILL.md; shared layer must not be directly triggerable")

    for relative in REQUIRED_ARCHITECTURE_PATHS:
        if not (base / relative).resolve().exists():
            errors.append(f"missing architecture path: {relative}")

    preload_relative = "references/shared/05_expression-asset-preload_表达资产轻量预加载协议.md"
    asset_state_relative = "references/shared/01_asset-state_资产状态归一表.md"
    preload_path = (base / preload_relative).resolve()
    if preload_path.exists():
        preload_text = preload_path.read_text(encoding="utf-8")
        for marker in ("./eva-memory/persona/", "./eva-memory/voice/", "只读", "不保存", "不推断", "不编造"):
            if marker not in preload_text:
                errors.append(f"expression preload protocol missing marker: {marker}")
        for marker in ("01_asset-state_资产状态归一表.md", "不新增状态体系", "本文件不维护第二套状态解释"):
            if marker not in preload_text:
                errors.append(f"expression preload protocol missing asset-state delegation marker: {marker}")
        for marker in ("具体个人经历", "具体素材提示", "当前指令与 voice-card 优先级", "更新我的语气卡", "不得覆盖 `voice-card`"):
            if marker not in preload_text:
                errors.append(f"expression preload protocol missing privacy/voice-priority marker: {marker}")

    asset_state_path = (base / asset_state_relative).resolve()
    if asset_state_path.exists():
        asset_state_text = asset_state_path.read_text(encoding="utf-8")
        for marker in ("预加载与主动回捞优先级", "不能替代检查点本身", "复用该命中结果", "重新扫描", "覆盖预加载状态", "更靠近当前产物阶段"):
            if marker not in asset_state_text:
                errors.append(f"asset state protocol missing preload priority marker: {marker}")

    for relative in ENTRY_SHARED_GUARD_PATHS:
        entry_path = (base / relative).resolve()
        if not entry_path.exists():
            continue
        entry_text = entry_path.read_text(encoding="utf-8")
        for marker in ("../eva-shared/schemas/asset-types.json", "version", "2.0.x", "缺少同系列 Eva 2.0 shared 真源"):
            if marker not in entry_text:
                errors.append(f"{relative} missing shared guard marker: {marker}")

    for relative in EXPRESSION_PRELOAD_REQUIRED_ENTRIES:
        entry_path = (base / relative).resolve()
        if not entry_path.exists():
            continue
        entry_text = entry_path.read_text(encoding="utf-8")
        if "05_expression-asset-preload_表达资产轻量预加载协议.md" not in entry_text:
            errors.append(f"{relative} must reference expression asset preload protocol")

    brief_path = (base / "../eva-brief/SKILL.md").resolve()
    if brief_path.exists():
        brief_text = brief_path.read_text(encoding="utf-8")
        if "首轮不默认读取" not in brief_text or "05_expression-asset-preload_表达资产轻量预加载协议.md" not in brief_text:
            errors.append("eva-brief must explicitly say expression preload is not default")

    link_root = (base / "../eva-link/references/link").resolve()
    if link_root.exists():
        for link_doc in sorted(link_root.rglob("*.md")):
            link_text = link_doc.read_text(encoding="utf-8")
            if "python3 scripts/eva_" in link_text:
                errors.append(f"eva-link doc still uses stale local scripts path: {link_doc}")
            if "examples/eva.link.example.json" in link_text and "../eva-shared/examples/eva.link.example.json" not in link_text:
                errors.append(f"eva-link doc still uses stale examples path: {link_doc}")

    router_path = (base / "../eva/SKILL.md").resolve()
    if router_path.exists():
        router_text = router_path.read_text(encoding="utf-8")
        missing_markers = [
            description for marker, description in REQUIRED_ROUTER_MARKERS.items()
            if marker not in router_text
        ]
        errors.extend(missing_markers)

    learn_entry_path = (base / "../eva-learn/SKILL.md").resolve()
    learn_source_path = (base / "references/learn/00_eva-learn.md").resolve()
    for learn_path in (learn_entry_path, learn_source_path):
        if not learn_path.exists():
            continue
        learn_text = learn_path.read_text(encoding="utf-8")
        for marker in ("带我学懂", "带我系统学", "带我读", "主题式阅读", "继续上次学习"):
            if marker not in learn_text:
                errors.append(f"{learn_path.name} missing semantic Learn trigger marker: {marker}")
        if "请对我说“eva-learn”" in learn_text or "请说 eva-learn" in learn_text:
            errors.append(f"{learn_path.name} still requires eva-learn incantation for semantic learning")

    think_path = (base / "../eva-think/references/think/00_eva-think_思考助理.md").resolve()
    if think_path.exists():
        think_text = think_path.read_text(encoding="utf-8")
        for marker in ("Memory 转接消歧", "提取我朋友圈的语气", "人设立不住", "朋友圈 Link / 用我的朋友圈 Link"):
            if marker not in think_text:
                errors.append(f"eva-think missing disambiguation marker: {marker}")

    persona_path = (base / "references/memory/01_eva-persona-memory_人设记忆采集.md").resolve()
    if persona_path.exists():
        persona_text = persona_path.read_text(encoding="utf-8")
        for marker in ("人设资格诊断模式", "具体经历", "选择代价", "反复模式", "公开边界", "默认只输出诊断，不保存"):
            if marker not in persona_text:
                errors.append(f"persona-memory missing credibility diagnosis marker: {marker}")

    live_review_dir = base / "references" / "review"
    if live_review_dir.exists():
        errors.append("references/review must not exist in Eva 2.0.4; keep inactive drafts outside this skill")

    internal_pending_dir = base / "references" / "internal-pending"
    if internal_pending_dir.exists():
        errors.append("references/internal-pending must not exist in Eva 2.0.4; move upgrade drafts outside this skill")

    chain = [
        ("audience-card", "eva-create"),
        ("title-handoff-card", "eva-create"),
        ("content-task-card", "eva-create"),
        ("review-card", "eva-memory"),
    ]
    for asset_type, downstream in chain:
        test_asset = {
            "asset_type": asset_type,
            "source_module": "eva-create",
            "core_content": "selftest",
            "user_question": "selftest",
            "evidence": ["selftest"],
            "valid_next": [downstream],
            "saved": False,
            "confidence": "medium",
            "low_confidence_reason": [],
            "missing_fields": [],
            "privacy_flags": [],
        }
        if asset_type == "review-card":
            test_asset["source_module"] = "upgrade-pending-review"
            test_asset.update(
                {
                    "evidence_level": "L1",
                    "path_bottleneck": "unknown",
                    "design_type": "single_observation",
                    "treatment_variable": "selftest",
                    "outcome_variable": "selftest",
                    "control_plan": "selftest",
                    "adjustment_variables": ["selftest"],
                    "hypothesis": "selftest",
                    "confounders": ["selftest"],
                    "metric_spec": [
                        {
                            "name": "selftest",
                            "role": "primary",
                            "numerator": "selftest",
                            "denominator": "selftest",
                            "window": "selftest",
                        }
                    ],
                    "next_test_action": "selftest",
                    "metrics_to_watch": ["selftest"],
                    "success_criteria": "selftest",
                    "observation_window": "selftest",
                    "result_backfill_required": True,
                }
            )
        chain_errors = validate_asset(test_asset, schema, base)
        if chain_errors:
            errors.append(f"chain asset {asset_type} -> {downstream} failed: " + "; ".join(chain_errors))

    ok = not errors
    exit_with(
        result(
            ok,
            "selftest",
            "Eva Harness 2.0.4自检通过" if ok else "Eva Harness 2.0.4自检失败",
            errors,
            warnings,
            {
                "base": str(base),
                "positive_example": "examples/asset-card.example.json",
                "prompt_regression_matrix": "examples/prompt-regression-matrix.json",
                "required_regression_cases": sorted(REQUIRED_REGRESSION_CASES),
                "required_architecture_paths": list(REQUIRED_ARCHITECTURE_PATHS),
                "chain": [f"{left}->{right}" for left, right in chain],
            },
        )
    )


if __name__ == "__main__":
    main()
