#!/usr/bin/env python3
"""Eva 2.1.2 structural checks and prompt scenario-contract validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from eva_link_check import validate_expected_asset as validate_link_expected_asset
from eva_common import (
    CORE_ENTRIES,
    VERSION,
    VALID_ASSET_TYPES,
    VALID_HANDOFF_TARGETS,
    add_common_arguments,
    canonical_handoff_target,
    canonicalize_handoff_targets,
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


REQUIRED_SCENARIO_CASES = {
    "default-start",
    "explicit-eva-new-user",
    "new-user-minimum-success-loop",
    "eva-new-user-skip",
    "eva-new-user-to-real-task",
    "direct-think-luckin",
    "think-companion-continuity",
    "think-deep-sorting",
    "ordinary-learning-no-auto-learn",
    "explicit-eva-learn",
    "learn-minimum-archive",
    "semantic-eva-learn",
    "learn-archive-write-failure",
    "learn-restore-without-path",
    "material-to-create",
    "explicit-brief",
    "commercial-content-not-brief-entry",
    "title-candidate-check",
    "title-promise-check",
    "opening-only",
    "full-script-needs-route",
    "ai-check-default-diagnose",
    "voice-needs-user-sample",
    "moments-voice-extraction-not-create",
    "persona-credibility-diagnosis",
    "explicit-save",
    "external-skill-not-eva-mainline",
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
    "compatibility-reframe-alias",
    "compatibility-audience-alias",
    "compatibility-benchmark-alias",
    "compatibility-memory-alias",
    "compatibility-persona-alias",
    "compatibility-user-voice-alias",
    "compatibility-ai-check-alias",
    "general-ai-check-longform",
    "general-benchmark-analysis",
    "ai-check-rewrite-combination",
    "ai-check-rewrite-no-scope-or-form",
    "long-material-final-verb",
    "low-confidence-draft-not-publishable",
    "explicit-eva-review-single",
    "review-batch-comparability",
    "review-prepublish-not-review",
    "review-store-write-failure",
    "explicit-eva-lens-quick",
    "eva-lens-single-view",
    "eva-lens-deep-review",
    "eva-lens-evidence-handoff",
    "eva-lens-zero-save",
    "harness-reverse-review-to-lens",
    "information-complete-direct-draft",
    "douyin-information-complete-direct-draft",
    "shipinhao-information-complete-direct-draft",
    "second-explicit-draft-request",
}

REQUIRED_ARTICLE_CASE_CONTRACTS = {
    "article-information-complete-direct-draft": {
        "expected_route": "eva-create-article-direct-draft",
        "expected_terminal": "complete-nonfiction-article-with-post-draft-title",
        "forbid": {"short-video-title-gate", "outline-only", "fixed-word-count", "invent-facts"},
        "must_include": {"same-turn-complete-article", "body-first-title-after", "dynamic-length"},
    },
    "article-critical-gap-one-question": {
        "expected_route": "eva-create-article-one-critical-question",
        "expected_terminal": "ask-one-question-that-changes-the-article-direction",
        "forbid": {"multiple-questions", "invent-author-experience", "short-video-title-search"},
        "must_include": {"one-critical-question"},
    },
    "article-short-topic-dynamic-length": {
        "expected_route": "eva-create-article-dynamic-short",
        "expected_terminal": "concise-complete-article-without-padding",
        "forbid": {"pad-to-800", "repeat-same-point", "fixed-word-count"},
        "must_include": {"stop-at-argument-closure", "shorter-than-default-when-warranted"},
    },
    "article-long-topic-dynamic-length": {
        "expected_route": "eva-create-article-dynamic-long",
        "expected_terminal": "longer-complete-article-when-complexity-requires",
        "forbid": {"compress-to-1200", "drop-counterargument", "fixed-word-count"},
        "must_include": {"allow-over-default-length", "complete-argument-chain"},
    },
    "article-fact-judgment-separation": {
        "expected_route": "eva-create-article-fact-layering",
        "expected_terminal": "article-draft-with-unverified-claim-clearly-marked-or-removed",
        "forbid": {"invent-source", "present-hearsay-as-fact"},
        "must_include": {"fact-experience-inference-rhetoric-separation", "pending-verification-marker"},
    },
    "article-cta-missing-details": {
        "expected_route": "eva-create-article-cta-safe-draft",
        "expected_terminal": "article-with-truthful-cta-or-clearly-marked-missing-details",
        "forbid": {"invent-price", "invent-quota", "invent-deadline", "invent-join-method"},
        "must_include": {"one-question-or-pending-placeholder", "first-party-cta-only"},
    },
    "article-local-edit-scope": {
        "expected_route": "eva-create-article-local-edit",
        "expected_terminal": "return-only-the-revised-second-paragraph",
        "forbid": {"rewrite-full-article", "change-title", "change-cta", "expand-edit-scope"},
        "must_include": {"authorized-section-only"},
    },
    "article-long-material-final-verb": {
        "expected_route": "eva-create-material-to-article",
        "expected_terminal": "article-route-before-writing",
        "forbid": {"eva-learn", "eva-create-short-video", "route-by-material-type-only"},
        "must_include": {"route-by-final-output-form"},
    },
    "learn-to-article-direct-handoff": {
        "expected_route": "eva-learn-to-eva-create-article-same-turn",
        "expected_terminal": "same-turn-complete-article-without-short-video-gates",
        "forbid": {
            "force-thought-seed-card",
            "short-video-audience-gate",
            "short-video-title-gate",
            "short-video-first-line-gate",
            "short-video-route-map",
        },
        "must_include": {
            "judgment-evidence-counterevidence-uncertainty-handoff",
            "same-turn-article-handoff",
        },
    },
    "article-professional-writing-exclusion": {
        "expected_route": "professional-technical-writing-not-eva-article",
        "expected_terminal": "professional-technical-documentation-path",
        "forbid": {"eva-create-article", "nonfiction-media-article-template", "invent-api-behavior"},
        "must_include": set(),
    },
    "article-single-sample-current-task-only": {
        "expected_route": "eva-create-article-current-sample",
        "expected_terminal": "article-draft-with-current-sample-rhythm-and-zero-persistence",
        "forbid": {"save-voice-card", "claim-stable-user-style", "copy-sample-wording"},
        "must_include": {"current-task-style-reference-only"},
    },
    "article-sponsored-brief-exclusion": {
        "expected_route": "eva-brief-or-commerce-constraint-only-for-sponsored-article",
        "expected_terminal": "brief-constraint-only-no-article-draft-in-2.1.2",
        "forbid": {
            "direct-article-before-constraint-card",
            "article-draft-after-constraint-card",
            "continue-to-article-after-brief",
            "invent-brand-claim",
            "ignore-brand-prohibition",
        },
        "must_include": set(),
    },
}

REQUIRED_SCENARIO_CASES.update(REQUIRED_ARTICLE_CASE_CONTRACTS)

REQUIRED_ROUTER_MARKERS = {
    "eva-new-user": "Router must expose the adaptive new-user tutorial",
    "eva-think": "Router must expose eva-think as the default light entry",
    "eva-create": "Router must expose content creation through eva-create",
    "非虚构自媒体文章": "Router must expose nonfiction article creation through eva-create",
    "eva-learn": "Router must route explicit Eva Learn requests to eva-learn",
    "eva-brief": "Router must route Brief and sponsored-content constraints to eva-brief",
    "eva-link": "Router must route explicit Link requests to eva-link",
    "eva-review": "Router must route published-content review requests to eva-review",
    "eva-lens": "Router must route multi-perspective requests to eva-lens",
    "带我系统学": "Router must route semantic learning requests to eva-learn",
    "提取我朋友圈的语气": "Router must disambiguate moments voice extraction from creation",
    "人设立不住": "Router must expose persona credibility diagnosis through eva-think",
    "不读取 Harness / Asset / schema": "Router must stay thin and not load shared heavy protocols",
    "立即读取目标入口": "Router must load the target sibling entry immediately",
    "同一轮": "Router must continue in the same turn",
    "基础模型": "Router must pass ordinary non-video writing to the base model",
    "不得只输出“这个交给某入口处理”后停止": "Router must not stop at a routing announcement",
    "/eva-reframe": "Router must preserve the reframe compatibility alias",
    "/eva-audience-finder": "Router must preserve the audience compatibility alias",
    "/eva-benchmark-copy": "Router must preserve the benchmark compatibility alias",
    "/eva-memory": "Router must preserve the memory compatibility alias",
    "/eva-persona-memory": "Router must preserve the persona compatibility alias",
    "/eva-user-voice": "Router must preserve the user-voice compatibility alias",
    "/eva-ai-check": "Router must preserve the AI-check compatibility alias",
    "长文档按最终动词": "Router must resolve long material by the user's final verb",
    "AI Check + 改稿": "Router must resolve combined AI-check and rewrite intent",
    "Review + 改下一篇": "Router must keep Review separate from content production",
    "Review + 补盲区": "Router must hand Review conclusions to Lens without redoing attribution",
}

REQUIRED_ARCHITECTURE_PATHS = (
    "../eva/SKILL.md",
    "../eva-new-user/SKILL.md",
    "../eva-think/SKILL.md",
    "../eva-think/references/think/00_eva-think_思考助理.md",
    "../eva-create/SKILL.md",
    "../eva-create/references/create/00_eva-create_创作主入口.md",
    "../eva-create/references/create/article/00_eva-article_文章主入口.md",
    "../eva-create/references/create/article/01_eva-article-argument_观点与论证路线.md",
    "../eva-create/references/create/article/02_eva-article-writing_文章撰写与长度调节.md",
    "../eva-create/references/create/shortvideo/script/03_eva-script-runtime_普通正文简版路线.md",
    "../eva-learn/SKILL.md",
    "../eva-brief/SKILL.md",
    "../eva-link/SKILL.md",
    "../eva-link/references/link/00_eva-link_本地模块连接.md",
    "../eva-review/SKILL.md",
    "../eva-review/references/review/00_entry_入口与模式路由.md",
    "../eva-review/references/review/06_store_记录库与保存协议.md",
    "../eva-lens/SKILL.md",
    "../eva-lens/references/lens/01_quick_快速补光.md",
    "../eva-lens/references/lens/02_deep_深度审视.md",
    "references/audience/00_eva-audience-finder_话题人群识别器.md",
    "references/benchmark/00_eva-benchmark-copy_对标文案拆解.md",
    "references/quality/00_eva-ai-check_表达真实性审查.md",
    "references/learn/00_eva-learn.md",
    "references/learn/05_eva-learn-project_分级建档与恢复.md",
    "references/commerce/00_eva-commerce_商单主入口.md",
    "references/shared/04_light-interaction_轻交互协议.md",
    "references/shared/05_expression-asset-preload_表达资产轻量预加载协议.md",
    "references/harness/00_eva-harness_状态与交接校验.md",
)

RUNTIME_VERSION_FREE_PATHS = (
    "../eva-think/SKILL.md",
    "../eva-create/SKILL.md",
    "../eva-learn/SKILL.md",
    "../eva-brief/SKILL.md",
    "../eva-link/SKILL.md",
    "../eva-review/SKILL.md",
    "../eva-lens/SKILL.md",
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
    parser = argparse.ArgumentParser(description="Run Eva structural checks and validate the prompt scenario contract.")
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

    expected_aliases = {
        "learn": "eva-learn",
        "think": "eva-think",
        "create": "eva-create",
        "memory": "eva-memory",
        "link": "eva-link",
        "review": "eva-review",
        "lens": "eva-lens",
    }
    for alias, canonical in expected_aliases.items():
        if canonical_handoff_target(alias, base) != canonical:
            errors.append(f"handoff alias {alias!r} must normalize to {canonical!r}")
    if canonicalize_handoff_targets(["review", "title", "eva-create"], base) != ["eva-review", "title", "eva-create"]:
        errors.append("handoff canonicalization must preserve internal stages and canonical targets")

    compatibility_asset = dict(example_asset)
    compatibility_asset["valid_next"] = ["create", "memory"]
    if validate_asset(compatibility_asset, schema, base):
        errors.append("compatibility handoff aliases must remain readable during the 2.1 cycle")

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
        "alternative_explanations": ["selftest"],
        "falsification_condition": "selftest",
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

    valid_review = dict(bad_review_source)
    valid_review["source_module"] = "eva-review"
    valid_review["valid_next"] = ["eva-lens", "eva-create"]
    valid_review_errors = validate_asset(valid_review, schema, base)
    if valid_review_errors:
        errors.append("valid eva-review review-card failed: " + "; ".join(valid_review_errors))

    review_common = {
        "asset_type": "review-card",
        "source_module": "eva-review",
        "core_content": "selftest review conclusion",
        "user_question": "What should the next review action be?",
        "evidence": ["user-provided review evidence"],
        "valid_next": ["eva-think", "eva-create", "eva-lens"],
        "saved": False,
        "confidence": "medium",
        "low_confidence_reason": [],
        "missing_fields": [],
        "privacy_flags": [],
    }
    review_mode_examples = {
        "single": {
            "hypothesis": "The opening may not fully carry the title promise.",
            "alternative_explanations": ["The observation window may be too short."],
            "next_test_action": "Change only the opening in the next comparable post.",
            "observation_window": "24 hours after publishing",
            "falsification_condition": "The primary metric does not improve while controls remain stable.",
        },
        "batch": {
            "hypothesis": "Comparable posts with concrete conflict openings may retain better.",
            "alternative_explanations": ["Traffic source differs across the supporting records."],
            "next_test_action": "Run one comparable post with only the opening mechanism changed.",
            "observation_window": "the next three comparable posts",
            "falsification_condition": "The candidate pattern disappears after grouping by traffic source.",
        },
        "backfill": {
            "hypothesis": "Original hypothesis: a clearer promise improves qualified engagement.",
            "alternative_explanations": ["The backfill changed more than one variable."],
            "next_test_action": "Repeat the test with the original control items restored.",
            "observation_window": "same window as the original record",
            "falsification_condition": "The repeated controlled result does not support the original direction.",
        },
    }
    for mode, fields in review_mode_examples.items():
        review_asset = {**review_common, **fields}
        mode_errors = validate_asset(review_asset, schema, base)
        if mode_errors:
            errors.append(f"valid {mode} review-card failed: " + "; ".join(mode_errors))

    incomplete_review = {**review_common, **review_mode_examples["single"]}
    incomplete_review.pop("falsification_condition")
    if not validate_asset(incomplete_review, schema, base):
        errors.append("review-card without falsification_condition unexpectedly passed")

    initializer_schema = read_json(base / "schemas" / "initializer-card.schema.json")
    valid_initializer = {
        "user_goal": "restore a failed learning task",
        "task_type": "eva-learn-recovery",
        "definition_of_done": ["state is readable"],
        "assets_to_generate": [],
        "required_fields": ["project_path"],
        "next_step": "ask for the project path",
    }
    if simple_schema_validate(valid_initializer, initializer_schema):
        errors.append("valid initializer-card failed schema validation")
    invalid_initializer = dict(valid_initializer)
    invalid_initializer.pop("next_step")
    if not simple_schema_validate(invalid_initializer, initializer_schema):
        errors.append("initializer-card without next_step unexpectedly passed")

    failure_schema = read_json(base / "schemas" / "failure-record.schema.json")
    valid_failure = {
        "failure_type": "script_or_tool_failed",
        "summary": "link validation script could not run",
        "recommended_action": "repair the script before saving the Link",
    }
    if simple_schema_validate(valid_failure, failure_schema):
        errors.append("valid failure-record failed schema validation")
    invalid_failure = dict(valid_failure)
    invalid_failure["failure_type"] = "unknown_failure"
    if not simple_schema_validate(invalid_failure, failure_schema):
        errors.append("failure-record with unknown failure_type unexpectedly passed")

    scenario_contract_path = base / "examples" / "prompt-regression-matrix.json"
    if not scenario_contract_path.exists():
        errors.append("missing examples/prompt-regression-matrix.json")
    else:
        scenario_contract = read_json(scenario_contract_path)
        expected_version = VERSION.rsplit("-", 1)[-1]
        if str(scenario_contract.get("version", "")) != expected_version:
            errors.append(
                "prompt scenario contract version must match "
                f"{expected_version}, got {scenario_contract.get('version', '<missing>')}"
            )
        cases = scenario_contract.get("cases") or []
        case_ids = {case.get("id") for case in cases if isinstance(case, dict)}
        duplicate_ids = sorted({case_id for case_id in case_ids if sum(1 for case in cases if isinstance(case, dict) and case.get("id") == case_id) > 1})
        if duplicate_ids:
            errors.append("prompt scenario contract contains duplicate id(s): " + ", ".join(str(item) for item in duplicate_ids))
        missing_cases = sorted(REQUIRED_SCENARIO_CASES - case_ids)
        if missing_cases:
            errors.append("prompt scenario contract missing required case(s): " + ", ".join(missing_cases))
        if len(cases) < 10:
            errors.append("prompt scenario contract must keep at least 10 cases")
        for index, case in enumerate(cases, start=1):
            if not isinstance(case, dict):
                errors.append(f"prompt scenario case #{index} must be an object")
                continue
            missing = [field for field in ["id", "input", "expected_route", "forbid", "expected_terminal"] if field not in case]
            if missing:
                errors.append(f"prompt scenario case {case.get('id', index)!r} missing field(s): " + ", ".join(missing))
            for field in ["id", "input", "expected_route", "expected_terminal"]:
                if field in case and not isinstance(case[field], str):
                    errors.append(f"prompt scenario case {case.get('id', index)!r} field {field} must be a string")
            if "forbid" in case and not isinstance(case["forbid"], list):
                errors.append(f"prompt scenario case {case.get('id', index)!r} forbid must be an array")
            if "must_include" in case and not isinstance(case["must_include"], list):
                errors.append(f"prompt scenario case {case.get('id', index)!r} must_include must be an array")

        case_by_id = {
            case.get("id"): case
            for case in cases
            if isinstance(case, dict) and isinstance(case.get("id"), str)
        }
        required_case_markers = {
            "new-user-minimum-success-loop": ("one-minimum-demo", "one-user-practice-prompt"),
            "information-complete-direct-draft": ("tailored-search-terms", "observation-criteria"),
            "douyin-information-complete-direct-draft": ("first-line-content-entry", "complete-draft"),
            "shipinhao-information-complete-direct-draft": ("first-line-content-entry", "complete-draft"),
            "second-explicit-draft-request": ("【未验证结构草案｜不可直接发布】", "one-upgrade-action"),
        }
        for case_id, markers in required_case_markers.items():
            must_include = case_by_id.get(case_id, {}).get("must_include") or []
            missing_markers = [marker for marker in markers if marker not in must_include]
            if missing_markers:
                errors.append(
                    f"prompt scenario case {case_id!r} missing must_include marker(s): "
                    + ", ".join(missing_markers)
                )

        for case_id, contract in REQUIRED_ARTICLE_CASE_CONTRACTS.items():
            case = case_by_id.get(case_id) or {}
            for scalar_field in ("expected_route", "expected_terminal"):
                if case.get(scalar_field) != contract[scalar_field]:
                    errors.append(
                        f"prompt scenario case {case_id!r} {scalar_field} must be "
                        f"{contract[scalar_field]!r}"
                    )
            for list_field in ("forbid", "must_include"):
                actual = set(case.get(list_field) or [])
                missing_markers = sorted(contract[list_field] - actual)
                if missing_markers:
                    errors.append(
                        f"prompt scenario case {case_id!r} missing {list_field} marker(s): "
                        + ", ".join(missing_markers)
                    )

    shared_skill_path = base / "SKILL.md"
    if not shared_skill_path.exists():
        errors.append("eva-shared must have SKILL.md so GitHub skill installers copy the shared package")
    else:
        shared_skill_text = shared_skill_path.read_text(encoding="utf-8")
        for marker in ("name: eva-shared", "Do not use directly", "not a user-facing Eva entry", "Direct Invocation Response"):
            if marker not in shared_skill_text:
                errors.append(f"eva-shared SKILL.md missing support-only marker: {marker}")
    shared_openai_path = base / "agents" / "openai.yaml"
    if not shared_openai_path.exists():
        errors.append("eva-shared must have agents/openai.yaml")
    elif "allow_implicit_invocation: false" not in shared_openai_path.read_text(encoding="utf-8"):
        errors.append("eva-shared must disable implicit invocation in agents/openai.yaml")

    for relative in REQUIRED_ARCHITECTURE_PATHS:
        if not (base / relative).resolve().exists():
            errors.append(f"missing architecture path: {relative}")

    expected_version = VERSION.rsplit("-", 1)[-1]
    repo_root = base.parent.parent
    version_path = repo_root / "VERSION"
    source_checkout = (repo_root / ".git").exists() or (repo_root / ".claude-plugin" / "marketplace.json").exists()
    layout = "source-checkout" if source_checkout else "installed-skill-bundle"
    if version_path.exists():
        actual_version = version_path.read_text(encoding="utf-8").strip()
        if actual_version != expected_version:
            errors.append(f"root VERSION must be {expected_version}, got {actual_version or '<empty>'}")
    elif source_checkout:
        errors.append(f"missing root VERSION: {version_path}")

    readme_path = repo_root / "README.md"
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        for marker in (
            "# Eva Skill v2.1.2",
            "## 按你想完成的事使用 Eva",
            "## 一个短视频从想法到成稿",
            "## 一篇文章从判断到成稿",
            "## 常见问题",
            "## 2.1.2 新增",
        ):
            if marker not in readme_text:
                errors.append(f"README missing 2.1.2 user-guide marker: {marker}")
    elif source_checkout:
        errors.append(f"missing root README: {readme_path}")

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

    for relative in RUNTIME_VERSION_FREE_PATHS:
        entry_path = (base / relative).resolve()
        if not entry_path.exists():
            continue
        entry_text = entry_path.read_text(encoding="utf-8")
        if "../eva-shared/VERSION" in entry_text:
            errors.append(f"{relative} still contains runtime version gate")

    staged_asset_gate_markers = {
        "../eva-think/SKILL.md": "生成资产、保存或跨模块交接前",
        "../eva-create/SKILL.md": "生成交接卡、资产卡、保存或跨模块交接前",
        "../eva-learn/SKILL.md": "需要生成、保存或交接正式 Eva Asset",
        "../eva-brief/SKILL.md": "生成正式商单约束卡、保存或交回创作链路前",
        "../eva-link/SKILL.md": "Link 生成资产或交接前",
        "../eva-review/SKILL.md": "只有把复盘结论交给",
    }
    for relative, gate_marker in staged_asset_gate_markers.items():
        entry_path = (base / relative).resolve()
        if not entry_path.exists():
            continue
        entry_text = entry_path.read_text(encoding="utf-8")
        for marker in ("../eva-shared/schemas/asset-types.json", gate_marker):
            if marker not in entry_text:
                errors.append(f"{relative} missing staged Asset hard gate marker: {marker}")

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
            for stale_command in ("python3 scripts/eva_", "python3 ../eva-shared/scripts/eva_"):
                if stale_command in link_text:
                    errors.append(f"eva-link doc still uses a cwd-dependent script path: {link_doc}")
            if "python3 " in link_text:
                for marker in ("<EVA_SHARED_ROOT>", "<PROJECT_ROOT>"):
                    if marker not in link_text:
                        errors.append(f"eva-link command doc missing absolute path placeholder {marker}: {link_doc}")

        link_main_path = link_root / "00_eva-link_本地模块连接.md"
        if link_main_path.exists():
            link_main_text = link_main_path.read_text(encoding="utf-8")
            for marker in (
                "EVA_SHARED_ROOT =",
                "PROJECT_ROOT =",
                "../eva-shared/schemas/eva-link.schema.json",
                "../eva-shared/schemas/link-registry.schema.json",
                "../eva-shared/schemas/asset-card.schema.json",
            ):
                if marker not in link_main_text:
                    errors.append(f"eva-link main protocol missing separated path marker: {marker}")

        link_script = base / "scripts" / "eva_link_check.py"
        link_fixture = base / "examples" / "local.weibo-copy"
        if link_script.exists() and link_fixture.exists():
            with tempfile.TemporaryDirectory(prefix="eva-link-path-selftest-") as temp_dir:
                project_root = Path(temp_dir) / "user-project"
                link_target = project_root / "local-modules" / "local.weibo-copy"
                registry_path = project_root / ".eva" / "links.json"
                link_target.parent.mkdir(parents=True)
                registry_path.parent.mkdir(parents=True)
                shutil.copytree(link_fixture, link_target)
                registry_path.write_text(
                    json.dumps(
                        {
                            "version": "1.0.0",
                            "links": [
                                {
                                    "id": "local.weibo-copy",
                                    "path": "local-modules/local.weibo-copy",
                                    "enabled": True,
                                }
                            ],
                            "defaults": [],
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                link_check = subprocess.run(
                    [
                        sys.executable,
                        str(link_script.resolve()),
                        "--link",
                        str(link_target.resolve()),
                        "--strict",
                        "--registry",
                        str(registry_path.resolve()),
                    ],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if link_check.returncode != 0:
                    errors.append(
                        "eva-link separated install/project path check failed: "
                        + (link_check.stdout.strip() or link_check.stderr.strip() or "unknown error")
                    )

    router_path = (base / "../eva/SKILL.md").resolve()
    if router_path.exists():
        router_text = router_path.read_text(encoding="utf-8")
        missing_markers = [
            description for marker, description in REQUIRED_ROUTER_MARKERS.items()
            if marker not in router_text
        ]
        errors.extend(missing_markers)

    think_entry_path = (base / "../eva-think/SKILL.md").resolve()
    if think_entry_path.exists():
        think_entry_text = think_entry_path.read_text(encoding="utf-8")
        if "## 默认读取" not in think_entry_text or "按需读取" not in think_entry_text:
            errors.append("eva-think must separate default reads from conditional reads")
        else:
            think_default_reads = think_entry_text.split("## 默认读取", 1)[1].split("按需读取", 1)[0]
            for marker in (
                "asset-types.json",
                "00_eva-harness",
                "00_eva-asset",
                "00_eva-memory",
                "05_expression-asset-preload",
            ):
                if marker in think_default_reads:
                    errors.append(f"eva-think default reads must stay light; found: {marker}")

    create_entry_path = (base / "../eva-create/SKILL.md").resolve()
    create_openai_path = (base / "../eva-create/agents/openai.yaml").resolve()
    if create_entry_path.exists():
        create_entry_text = create_entry_path.read_text(encoding="utf-8")
        create_frontmatter = create_entry_text.split("---", 2)[1] if create_entry_text.startswith("---") else ""
        for marker in ("普通图文", "图文创作入口", "普通内容创作"):
            if marker in create_frontmatter:
                errors.append(f"eva-create frontmatter claims unsupported generic creation: {marker}")
        for marker in ("短视频", "非虚构自媒体文章", "公众号文章", "不处理朋友圈、微博"):
            if marker not in create_frontmatter:
                errors.append(f"eva-create frontmatter missing supported-content boundary: {marker}")
        for stale_marker in ("独立短视频生产入口", "只处理短视频", "不处理朋友圈、微博、公众号"):
            if stale_marker in create_frontmatter:
                errors.append(f"eva-create frontmatter keeps stale short-video-only boundary: {stale_marker}")
        for marker in (
            "references/create/article/00_eva-article_文章主入口.md",
            "references/create/article/01_eva-article-argument_观点与论证路线.md",
            "references/create/article/02_eva-article-writing_文章撰写与长度调节.md",
        ):
            if marker not in create_entry_text:
                errors.append(f"eva-create missing conditional Article read: {marker}")
        for marker in ("第一次要求", "标题搜索方案", "第二次明确", "不能包装成可直接发布的终稿"):
            if marker not in create_entry_text:
                errors.append(f"eva-create missing two-turn draft boundary marker: {marker}")
        for marker in ("依赖封面或标题点击", "抖音、视频号", "不强制搜索平台标题"):
            if marker not in create_entry_text:
                errors.append(f"eva-create missing platform-specific title boundary marker: {marker}")
    if create_openai_path.exists():
        create_openai_text = create_openai_path.read_text(encoding="utf-8")
        for marker in ("图文创作入口", "普通内容创作"):
            if marker in create_openai_text:
                errors.append(f"eva-create agents/openai.yaml claims unsupported generic creation: {marker}")
        for marker in ("$eva-create", "非虚构自媒体文章"):
            if marker not in create_openai_text:
                errors.append(f"eva-create agents/openai.yaml missing Article marker: {marker}")

    create_router_path = (base / "../eva-create/references/create/00_eva-create_创作主入口.md").resolve()
    if create_router_path.exists():
        create_router_text = create_router_path.read_text(encoding="utf-8")
        for marker in (
            "references/create/shortvideo/00_eva-shortvideo_主入口.md",
            "references/create/article/00_eva-article_文章主入口.md",
            "最终输出形式优先于输入材料形式",
        ):
            if marker not in create_router_text:
                errors.append(f"eva-create router missing content-form split marker: {marker}")

    article_paths = {
        "entry": (base / "../eva-create/references/create/article/00_eva-article_文章主入口.md").resolve(),
        "argument": (base / "../eva-create/references/create/article/01_eva-article-argument_观点与论证路线.md").resolve(),
        "writing": (base / "../eva-create/references/create/article/02_eva-article-writing_文章撰写与长度调节.md").resolve(),
    }
    article_markers = {
        "entry": (
            "信息充分",
            "同一轮直接交付完整文章",
            "最多只问一个关键问题",
            "宽泛主题",
            "不得由 Article 自行挑一个泛化观点",
            "正式品牌商单",
        ),
        "argument": ("事实", "亲历", "推论", "修辞", "最短闭环论证路径"),
        "writing": ("800–1200", "论证闭环", "先写正文，后定标题", "[待核验]", "[待补]", "CTA"),
    }
    for label, path in article_paths.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in article_markers[label]:
            if marker not in text:
                errors.append(f"Article {label} protocol missing marker: {marker}")
        for forbidden_coupling in ("shortvideo/title/", "shortvideo/opening/", "/eva-title", "/eva-script"):
            if forbidden_coupling in text:
                errors.append(f"Article {label} protocol must not couple to short-video gate: {forbidden_coupling}")

    forbidden_article_skill = (repo_root / "skills" / "eva-article").resolve()
    if forbidden_article_skill.exists():
        errors.append(f"Eva 2.1.2 must not expose a top-level Article skill: {forbidden_article_skill}")
    asset_registry = read_json(base / "schemas" / "asset-types.json")
    registered_assets = set((asset_registry.get("assets") or {}).keys())
    if "article-card" in registered_assets:
        errors.append("Article must reuse content-task-card/content-asset-card; article-card is forbidden")
    for required_asset in ("content-task-card", "content-asset-card"):
        if required_asset not in registered_assets:
            errors.append(f"Article requires existing shared asset type to remain available: {required_asset}")
    handoff_registry = read_json(base / "schemas" / "handoff-targets.json")
    if "eva-article" in set(handoff_registry.get("targets") or []):
        errors.append("Article must remain an internal eva-create branch; eva-article handoff target is forbidden")

    direct_draft_paths = {
        "script router": (base / "../eva-create/references/create/shortvideo/script/00_eva-script_思维流爆款内容创作.md").resolve(),
        "compact route": (base / "../eva-create/references/create/shortvideo/script/03_eva-script-runtime_普通正文简版路线.md").resolve(),
        "route map": (base / "../eva-create/references/create/shortvideo/script/04_eva-script-route-map_正文路线图.md").resolve(),
        "script writing": (base / "../eva-create/references/create/shortvideo/script/05_eva-script-writing_正文撰写.md").resolve(),
    }
    for label, path in direct_draft_paths.items():
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in ("固定发布条数", "测试周期"):
            if marker not in text:
                errors.append(f"{label} missing direct-draft numeric-threshold boundary: {marker}")
    script_writing_path = direct_draft_paths["script writing"]
    if script_writing_path.exists():
        script_writing_text = script_writing_path.read_text(encoding="utf-8")
        for marker in (
            "二次坚持后的未验证草稿",
            "前台只输出完整内容稿",
            "不能替用户发明新的处方",
            "连续发十条",
            "【未验证结构草案｜不可直接发布】",
        ):
            if marker not in script_writing_text:
                errors.append(f"script writing missing direct-draft scope marker: {marker}")
        if "只允许在完整稿件之后追加一句事实说明" in script_writing_text:
            errors.append("script writing must place the unverified-draft warning before the draft body")

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

    learn_project_path = (base / "references/learn/05_eva-learn-project_分级建档与恢复.md").resolve()
    if learn_project_path.exists():
        learn_project_text = learn_project_path.read_text(encoding="utf-8")
        for marker in (
            "所有明确进入 Eva Learn 的任务都必须先建立或恢复可追溯档案",
            "最小档案",
            "完整档案",
            "项目锚点、资料保存、进度更新或问答原稿追加失败时立即停止",
            "同轮进入教学",
            "第一讲前的项目锚点",
            "建档状态: 初始化",
            "07-学习问答原稿.md",
        ):
            if marker not in learn_project_text:
                errors.append(f"Learn graded archive protocol missing marker: {marker}")

    learn_journey_markers = {
        "references/learn/01_探索式学习.md": ("第一讲前只创建", "展示给用户前创建", "创建或写入失败"),
        "references/learn/02_资料带学.md": ("第一讲前只创建", "展示给用户前", "创建、资料保存或写入失败"),
        "references/learn/03_主题式阅读.md": ("完整建档", "写入失败"),
        "references/learn/04_思想种子卡与内容链路交接.md": (
            "先创建",
            "写入失败",
            "Article 交接优先",
            "不强制生成思想种子卡",
            "短视频成熟度判断",
            "短视频交接禁止",
        ),
    }
    for relative, markers in learn_journey_markers.items():
        journey_path = (base / relative).resolve()
        if not journey_path.exists():
            continue
        journey_text = journey_path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in journey_text:
                errors.append(f"{relative} missing graded archive marker: {marker}")

    think_path = (base / "../eva-think/references/think/00_eva-think_思考助理.md").resolve()
    if think_path.exists():
        think_text = think_path.read_text(encoding="utf-8")
        for marker in ("Memory 转接消歧", "提取我朋友圈的语气", "人设立不住", "朋友圈 Link / 用我的朋友圈 Link"):
            if marker not in think_text:
                errors.append(f"eva-think missing disambiguation marker: {marker}")
        for marker in (
            "轻量”只表示少读取外部协议",
            "不能每一轮重新开始",
            "区分事实、感受、判断和目标",
            "阶段性梳理",
            "轻量思考视角",
        ):
            if marker not in think_text:
                errors.append(f"eva-think missing deep-thinking marker: {marker}")
        for marker in ("专项诊断转接", "shared Benchmark", "shared AI Check", "通用表达诊断"):
            if marker not in think_text:
                errors.append(f"eva-think missing compatibility diagnostic routing marker: {marker}")

    persona_path = (base / "references/memory/01_eva-persona-memory_人设记忆采集.md").resolve()
    if persona_path.exists():
        persona_text = persona_path.read_text(encoding="utf-8")
        for marker in ("人设资格诊断模式", "具体经历", "选择代价", "反复模式", "公开边界", "默认只输出诊断，不保存"):
            if marker not in persona_text:
                errors.append(f"persona-memory missing credibility diagnosis marker: {marker}")

    internal_pending_dir = base / "references" / "internal-pending"
    if internal_pending_dir.exists():
        errors.append("references/internal-pending must not exist in Eva 2.1.2; move upgrade drafts outside this skill")

    new_user_path = (base / "../eva-new-user/SKILL.md").resolve()
    if new_user_path.exists():
        new_user_text = new_user_path.read_text(encoding="utf-8")
        for marker in (
            "开始前扫描",
            "跳过",
            "指定提前学习的功能",
            "正式处理",
            "不先判断或记录用户是不是新手",
            "三分钟最小闭环",
            "演示",
            "跟做",
            "独立",
        ):
            if marker not in new_user_text:
                errors.append(f"eva-new-user missing adaptive tutorial marker: {marker}")

    light_interaction_path = (base / "references/shared/04_light-interaction_轻交互协议.md").resolve()
    if light_interaction_path.exists():
        light_interaction_text = light_interaction_path.read_text(encoding="utf-8")
        for marker in (
            "价值优先响应",
            "一次只暴露一个决策点",
            "不得只复述规则",
            "【未验证结构草案｜不可直接发布】",
            "不新增资产类型、状态字段或 schema",
        ):
            if marker not in light_interaction_text:
                errors.append(f"light-interaction protocol missing 2.1.2 marker: {marker}")

    low_confidence_path = (base / "references/shared/02_low-confidence_低置信度授权协议.md").resolve()
    if low_confidence_path.exists():
        low_confidence_text = low_confidence_path.read_text(encoding="utf-8")
        for marker in (
            "【未验证结构草案｜不可直接发布】",
            "当前缺失：",
            "升级动作：",
            "草案正文之前",
        ):
            if marker not in low_confidence_text:
                errors.append(f"low-confidence protocol missing visible draft boundary marker: {marker}")

    review_path = (base / "../eva-review/SKILL.md").resolve()
    if review_path.exists():
        review_text = review_path.read_text(encoding="utf-8")
        for marker in (
            "单篇检查、批量回溯和结果回填都是本 Skill 的内部模式",
            "少于 10 条可比记录",
            "./eva-review/",
            "不等于 shared `review-card`",
            "发布前短视频改稿交给 Create",
        ):
            if marker not in review_text:
                errors.append(f"eva-review missing product-boundary marker: {marker}")
        single_review_text = (base / "../eva-review/references/review/02_single_单篇复盘.md").resolve().read_text(encoding="utf-8")
        if "不得自行用点赞、评论或其他互动数充当分母" not in single_review_text:
            errors.append("eva-review must forbid invented proxy ratios without an exposure denominator")
        pattern_review_text = (base / "../eva-review/references/review/03_pattern_批量规律回溯.md").resolve().read_text(encoding="utf-8")
        if "不能给出“押注某类内容、减少某类内容、分配发布比例”" not in pattern_review_text:
            errors.append("eva-review must forbid allocation recommendations below ten comparable records")
        record_review_text = (base / "../eva-review/references/review/05_record_记录字段真源.md").resolve().read_text(encoding="utf-8")
        for marker in ("字段表是持久化规范", "Markdown 记录模板是人读映射", "不得只更新其中一处"):
            if marker not in record_review_text:
                errors.append(f"eva-review record/template mapping missing marker: {marker}")
    for forbidden_peer in (base / "../eva-review-check", base / "../eva-review-pattern"):
        if forbidden_peer.resolve().exists():
            errors.append(f"Eva 2.1 must not expose Review sub-skill: {forbidden_peer.name}")

    lens_path = (base / "../eva-lens/SKILL.md").resolve()
    if lens_path.exists():
        lens_text = lens_path.read_text(encoding="utf-8")
        for marker in (
            "快速补光",
            "单视角点射",
            "深度审视",
            "不创建 `lens-card`",
            "不模拟历史人物、专家圆桌或聊天室",
            "不自动联网搜索",
        ):
            if marker not in lens_text:
                errors.append(f"eva-lens missing product-boundary marker: {marker}")
        for forbidden in ("人物智慧讨论", "推荐人物", "多 Agent"):
            if forbidden in lens_text:
                errors.append(f"eva-lens still contains removed discussion mode: {forbidden}")
        quick_lens_text = (base / "../eva-lens/references/lens/01_quick_快速补光.md").resolve().read_text(encoding="utf-8")
        if "不得把推测写成某家公司、平台或行业已经采用的真实策略" not in quick_lens_text:
            errors.append("eva-lens quick mode must separate mechanism inference from verified facts")
        deep_lens_text = (base / "../eva-lens/references/lens/02_deep_深度审视.md").resolve().read_text(encoding="utf-8")
        for marker in ("800-1200 个中文字符", "不得用“逻辑上必然成立 / 不成立”", "Harness 交接输入", "交回原入口继续校验"):
            if marker not in deep_lens_text:
                errors.append(f"eva-lens deep mode missing calibrated-depth marker: {marker}")
    harness_path = (base / "references/harness/00_eva-harness_状态与交接校验.md").resolve()
    if harness_path.exists():
        harness_text = harness_path.read_text(encoding="utf-8")
        for marker in ("认知反向审查交接", "交给 `eva-lens` 的深度审视模式", "Lens 结果不能绕过 Harness 闸门"):
            if marker not in harness_text:
                errors.append(f"Harness missing Lens handoff marker: {marker}")
        for removed_marker in ("## Eva Doubt", "反向审查卡：", "启动 Doubt"):
            if removed_marker in harness_text:
                errors.append(f"Harness still maintains duplicate Eva Doubt protocol: {removed_marker}")
    if "lens-card" in VALID_ASSET_TYPES:
        errors.append("Eva Lens must not add lens-card to shared asset types")

    chain = [
        ("audience-card", "eva-create"),
        ("title-handoff-card", "eva-create"),
        ("content-task-card", "eva-create"),
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
        chain_errors = validate_asset(test_asset, schema, base)
        if chain_errors:
            errors.append(f"chain asset {asset_type} -> {downstream} failed: " + "; ".join(chain_errors))

    ok = not errors
    exit_with(
        result(
            ok,
            "selftest",
            "Eva 2.1.2结构自检与场景契约检查通过" if ok else "Eva 2.1.2结构自检与场景契约检查失败",
            errors,
            warnings,
            {
                "base": str(base),
                "layout": layout,
                "positive_example": "examples/asset-card.example.json",
                "prompt_scenario_contract": "examples/prompt-regression-matrix.json",
                "required_scenario_cases": sorted(REQUIRED_SCENARIO_CASES),
                "required_architecture_paths": list(REQUIRED_ARCHITECTURE_PATHS),
                "chain": [f"{left}->{right}" for left, right in chain],
            },
        )
    )


if __name__ == "__main__":
    main()
