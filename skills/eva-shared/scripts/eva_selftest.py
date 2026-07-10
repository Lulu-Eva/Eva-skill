#!/usr/bin/env python3
"""Eva 2.0.5 structural checks and prompt scenario-contract validation."""

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
    "full-script-needs-route-map",
    "ai-check-default-diagnose",
    "voice-needs-user-sample",
    "moments-voice-extraction-not-create",
    "persona-credibility-diagnosis",
    "explicit-save",
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
    "legacy-reframe-alias",
    "legacy-audience-alias",
    "legacy-benchmark-alias",
    "legacy-memory-alias",
    "legacy-persona-alias",
    "legacy-user-voice-alias",
    "legacy-ai-check-alias",
    "general-ai-check-longform",
    "general-benchmark-analysis",
    "ai-check-rewrite-combination",
    "long-material-final-verb",
    "low-confidence-draft-not-publishable",
}

REQUIRED_ROUTER_MARKERS = {
    "eva-think": "Router must expose eva-think as the default light entry",
    "eva-create": "Router must expose short-video creation through eva-create",
    "eva-learn": "Router must route explicit Eva Learn requests to eva-learn",
    "eva-brief": "Router must route Brief and sponsored-content constraints to eva-brief",
    "eva-link": "Router must route explicit Link requests to eva-link",
    "带我系统学": "Router must route semantic learning requests to eva-learn",
    "提取我朋友圈的语气": "Router must disambiguate moments voice extraction from creation",
    "人设立不住": "Router must expose persona credibility diagnosis through eva-think",
    "不读取 Harness / Asset / schema": "Router must stay thin and not load shared heavy protocols",
    "立即读取目标入口": "Router must load the target sibling entry immediately",
    "同一轮": "Router must continue in the same turn",
    "基础模型": "Router must pass ordinary non-video writing to the base model",
    "不得只输出“这个交给某入口处理”后停止": "Router must not stop at a routing announcement",
    "/eva-reframe": "Router must preserve the 1.7.4 reframe alias",
    "/eva-audience-finder": "Router must preserve the 1.7.4 audience alias",
    "/eva-benchmark-copy": "Router must preserve the 1.7.4 benchmark alias",
    "/eva-memory": "Router must preserve the 1.7.4 memory alias",
    "/eva-persona-memory": "Router must preserve the 1.7.4 persona alias",
    "/eva-user-voice": "Router must preserve the 1.7.4 user-voice alias",
    "/eva-ai-check": "Router must preserve the 1.7.4 AI-check alias",
    "长文档按最终动词": "Router must resolve long material by the user's final verb",
    "AI Check + 改稿": "Router must resolve combined AI-check and rewrite intent",
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
    version_paths = {"root VERSION": base.parent.parent / "VERSION"}
    for label, version_path in version_paths.items():
        if not version_path.exists():
            errors.append(f"missing {label}: {version_path}")
            continue
        actual_version = version_path.read_text(encoding="utf-8").strip()
        if actual_version != expected_version:
            errors.append(f"{label} must be {expected_version}, got {actual_version or '<empty>'}")

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
                errors.append(f"eva-create frontmatter still claims non-video creation: {marker}")
        for marker in ("只处理短视频", "不处理朋友圈、微博、公众号"):
            if marker not in create_frontmatter:
                errors.append(f"eva-create frontmatter missing short-video boundary: {marker}")
    if create_openai_path.exists():
        create_openai_text = create_openai_path.read_text(encoding="utf-8")
        for marker in ("图文创作入口", "普通内容创作"):
            if marker in create_openai_text:
                errors.append(f"eva-create agents/openai.yaml still claims non-video creation: {marker}")

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
            "建档、资料保存、进度更新或问答原稿追加失败时立即停止",
            "同轮进入教学",
            "07-学习问答原稿.md",
        ):
            if marker not in learn_project_text:
                errors.append(f"Learn graded archive protocol missing marker: {marker}")

    learn_journey_markers = {
        "references/learn/01_探索式学习.md": ("首次写入前创建", "创建或写入失败"),
        "references/learn/02_资料带学.md": ("在首次写入前创建", "创建、资料保存或写入失败"),
        "references/learn/03_主题式阅读.md": ("完整建档", "写入失败"),
        "references/learn/04_思想种子卡与内容链路交接.md": ("先创建", "写入失败"),
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
                errors.append(f"eva-think missing legacy diagnostic routing marker: {marker}")

    persona_path = (base / "references/memory/01_eva-persona-memory_人设记忆采集.md").resolve()
    if persona_path.exists():
        persona_text = persona_path.read_text(encoding="utf-8")
        for marker in ("人设资格诊断模式", "具体经历", "选择代价", "反复模式", "公开边界", "默认只输出诊断，不保存"):
            if marker not in persona_text:
                errors.append(f"persona-memory missing credibility diagnosis marker: {marker}")

    live_review_dir = base / "references" / "review"
    if live_review_dir.exists():
        errors.append("references/review must not exist in Eva 2.0.5; keep inactive drafts outside this skill")

    internal_pending_dir = base / "references" / "internal-pending"
    if internal_pending_dir.exists():
        errors.append("references/internal-pending must not exist in Eva 2.0.5; move upgrade drafts outside this skill")

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
            "Eva 2.0.5结构自检与场景契约检查通过" if ok else "Eva 2.0.5结构自检与场景契约检查失败",
            errors,
            warnings,
            {
                "base": str(base),
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
