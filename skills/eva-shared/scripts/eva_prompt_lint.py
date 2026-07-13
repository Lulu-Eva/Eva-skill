#!/usr/bin/env python3
"""Prompt-level lint checks for Eva 2.1 source-of-truth boundaries."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


BACKSTAGE_TERMS = (
    "Harness",
    "schema",
    "valid_next",
    "DoD",
    "failure-record",
)

REMOVED_CAPABILITY_PATTERNS = (
    "Link" + " " + "Trace",
    "link" + "-" + "trace",
    "eva" + "_" + "link" + "_" + "trace",
    "EVA" + "_" + "TRACE" + "_" + "SECRET",
)

TITLE_CARD_FIELDS = (
    "- 标题谜面：",
    "- 标题来源：",
    "- 标题验证状态：",
    "- 人群状态：",
    "- 成稿置信度上限：",
)

TITLE_CARD_ALIASES = (
    "- 标题承诺：",
    "- 标题验证：",
    "- 标题置信度：",
    "- 成稿上限：",
)

OPENING_CARD_FIELDS = (
    "- 第一句话：",
    "- 停留理由：",
    "- 人群状态：",
    "- 用户继续看最想知道：",
)

OPENING_CARD_ALIASES = (
    "- 开头第一句：",
    "- 继续看理由：",
    "- 观看理由：",
    "- 第一反应：",
)

COMMERCIAL_CARD_FIELDS = (
    "- 产品：",
    "- 目标用户：",
    "- 推荐主讲卖点：",
    "- 必须保留：",
    "- 禁止触碰：",
    "- 不可承诺内容：",
    "- 学员可用素材：",
)

COMMERCIAL_CARD_ALIASES = (
    "- 主讲产品：",
    "- 主讲卖点：",
    "- 品牌必提：",
    "- 必带卖点：",
    "- 禁区：",
    "- 品牌禁区：",
    "- 不可写内容：",
    "- 真实体验素材：",
)

ASSET_FIELD_MARKERS = (
    "asset_type",
    "source_module",
    "core_content",
    "user_question",
    "valid_next",
    "saved",
    "confidence",
)

FRONTSTAGE_TEMPLATE_HEADINGS = (
    "## 默认启动",
    "## 输出格式",
    "## 输出收束",
    "## 第一轮输出",
    "## 内容稿",
    "## 改后版本",
    "## 我先判断",
    "## 下一步",
)

DEFAULT_STARTUP_UNIQUE_PHRASES = (
    "先把脑子里的东西丢给我。目前默认是创作模式",
    "如果你想单独拆商单 Brief 或品牌合作需求，请说 eva-brief",
)

DEFAULT_STARTUP_ALLOWED = (
    "../eva/SKILL.md",
)

OFFICIAL_GUIDE_HEADLINE = "关注公众号“璐璐 Eva” —— Eva-skill 的官方使用指南与案例库。"
OFFICIAL_GUIDE_PUBLIC_ACCOUNT_FRAGMENT = "公众号“璐璐 Eva”"
DEFAULT_STARTUP_MAINTENANCE_NUDGE_TERMS = (
    OFFICIAL_GUIDE_PUBLIC_ACCOUNT_FRAGMENT,
    "官方使用指南与案例库",
    "版本动态",
)

LIGHT_INTERACTION_CONDITION_MARKERS = (
    "用户明确启动 eva-learn",
    "用户提供多份资料，要求主题式阅读、研究或比较",
    "用户要求创建、接入、检查 Link",
    "用户要求保存为长期资产、项目档案或下次继续",
    "用户任务涉及商业战略、产品设计、内部方法论",
    "脚本、schema、Link 或资产保存校验失败",
)

LIGHT_INTERACTION_CONDITIONS_ALLOWED = (
    "../eva-shared/references/shared/04_light-interaction_轻交互协议.md",
)

ARTICLE_FORBIDDEN_SHORTVIDEO_COUPLINGS = (
    "shortvideo/title/",
    "shortvideo/opening/",
    "/eva-title",
    "/eva-script",
)

SHORTVIDEO_FORBIDDEN_ARTICLE_COUPLINGS = (
    "references/create/article/",
    "/eva-article",
)

SEMANTIC_DUPLICATE_PATTERNS = (
    {
        "name": "commercial full-draft boundary",
        "patterns": ("不直接写完整商单稿", "禁止直接写完整商单稿"),
        "match": "any",
        "threshold": 3,
        "hint": "入口级可留短句，执行边界应留在 Commerce / eva-brief；不要重复字段表。",
    },
    {
        "name": "frontstage asset fields hidden by default",
        "patterns": ("不得默认输出", "valid_next", "confidence"),
        "match": "all",
        "threshold": 3,
        "hint": "前台外显条件应以 shared/04 为准，其他文件只引用。",
    },
    {
        "name": "route-map gate",
        "patterns": ("正文路线图", "不得直接写稿", "禁止跳过正文路线图"),
        "match": "all",
        "threshold": 5,
        "hint": "正文入口门槛可在 script 总入口保留，本地子模块只保留必要退回条件。",
    },
    {
        "name": "commercial constraint card is not content entry",
        "patterns": ("商单约束卡不是标题交接卡", "商单约束卡当成正文入口", "商单约束卡才可以转换"),
        "match": "any",
        "threshold": 3,
        "hint": "商单约束字段和转换规则应集中在 shared/03。",
    },
    {
        "name": "explicit save confirmation",
        "patterns": ("保存必须由用户明确触发", "保存 Memory 必须由用户明确触发", "不自动保存隐私"),
        "match": "all",
        "threshold": 3,
        "hint": "保存边界是全局闸门，但隐私和资产字段规则应由 Asset / Memory 执行。",
    },
)

SOURCE_OF_TRUTH_RULES = (
    {
        "name": "title handoff card fields",
        "allowed": ("../eva-shared/references/shared/00_handoff-cards_交接卡字段真源.md",),
        "fields": TITLE_CARD_FIELDS + TITLE_CARD_ALIASES,
        "min_hits": 4,
    },
    {
        "name": "opening handoff card fields",
        "allowed": ("../eva-shared/references/shared/00_handoff-cards_交接卡字段真源.md",),
        "fields": OPENING_CARD_FIELDS + OPENING_CARD_ALIASES,
        "min_hits": 4,
    },
    {
        "name": "commercial constraint card fields",
        "allowed": ("../eva-shared/references/shared/03_commercial-constraint-card_商单约束卡真源.md",),
        "fields": COMMERCIAL_CARD_FIELDS + COMMERCIAL_CARD_ALIASES,
        "min_hits": 5,
    },
    {
        "name": "asset card field table",
        "allowed": (
            "../eva-shared/references/asset/00_eva-asset_资产卡协议.md",
            "references/link/03_eva-link-builder-templates_生成模板.md",
        ),
        "fields": ASSET_FIELD_MARKERS,
        "min_hits": 5,
    },
)


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return "../" + str(path.relative_to(base.parent))


def md_files(base: Path) -> list[Path]:
    candidates = list(base.rglob("*.md"))
    for peer in (
        "eva",
        "eva-new-user",
        "eva-think",
        "eva-create",
        "eva-learn",
        "eva-brief",
        "eva-link",
        "eva-review",
        "eva-lens",
    ):
        peer_root = base.parent / peer
        if peer_root.exists():
            candidates.extend(peer_root.rglob("*.md"))
    return sorted({path.resolve() for path in candidates})


def count_fields(text: str, fields: tuple[str, ...]) -> int:
    return sum(1 for field in fields if field in text)


def in_allowed(path: Path, allowed_suffixes: tuple[str, ...]) -> bool:
    normalized = str(path).replace("\\", "/")
    for suffix in allowed_suffixes:
        clean_suffix = suffix.replace("\\", "/")
        if normalized.endswith(clean_suffix):
            return True
        if clean_suffix.startswith("../") and normalized.endswith(clean_suffix[3:]):
            return True
    return False


def extract_section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start == -1:
        return ""
    next_heading = re.search(r"\n## ", text[start + len(heading) :])
    if not next_heading:
        return text[start:]
    end = start + len(heading) + next_heading.start()
    return text[start:end]


def lint(base: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    default_phrase_hits: dict[str, list[str]] = {phrase: [] for phrase in DEFAULT_STARTUP_UNIQUE_PHRASES}
    semantic_hits: dict[str, list[str]] = {rule["name"]: [] for rule in SEMANTIC_DUPLICATE_PATTERNS}

    for path in md_files(base):
        text = path.read_text(encoding="utf-8")
        path_rel = rel(path, base)

        for rule in SOURCE_OF_TRUTH_RULES:
            hit_count = count_fields(text, rule["fields"])
            if hit_count >= rule["min_hits"] and not in_allowed(path, rule["allowed"]):
                errors.append(f"{path_rel}: duplicates {rule['name']} ({hit_count} markers)")

        for phrase in DEFAULT_STARTUP_UNIQUE_PHRASES:
            if phrase in text:
                default_phrase_hits[phrase].append(path_rel)
                if not in_allowed(path, DEFAULT_STARTUP_ALLOWED):
                    errors.append(f"{path_rel}: duplicates default startup phrase; keep startup copy only in eva router")

        light_condition_hits = count_fields(text, LIGHT_INTERACTION_CONDITION_MARKERS)
        if light_condition_hits >= 3 and not in_allowed(path, LIGHT_INTERACTION_CONDITIONS_ALLOWED):
            errors.append(
                f"{path_rel}: duplicates light-interaction visibility conditions "
                f"({light_condition_hits} markers); keep condition list only in shared/04"
            )

        for pattern in REMOVED_CAPABILITY_PATTERNS:
            if pattern in text:
                errors.append(f"{path_rel}: contains removed internal-pending marker: {pattern}")

        if OFFICIAL_GUIDE_HEADLINE in text or OFFICIAL_GUIDE_PUBLIC_ACCOUNT_FRAGMENT in text:
            errors.append(
                f"{path_rel}: duplicates official public-account copy; "
                "keep it only in maintenance/release-notes.json"
            )

        normalized_path = path.as_posix()
        if "/eva-create/references/create/article/" in normalized_path:
            for coupling in ARTICLE_FORBIDDEN_SHORTVIDEO_COUPLINGS:
                if coupling in text:
                    errors.append(f"{path_rel}: Article protocol couples to short-video gate: {coupling}")
        if "/eva-create/references/create/shortvideo/" in normalized_path:
            for coupling in SHORTVIDEO_FORBIDDEN_ARTICLE_COUPLINGS:
                if coupling in text:
                    errors.append(f"{path_rel}: short-video protocol couples to Article branch: {coupling}")

        for rule in SEMANTIC_DUPLICATE_PATTERNS:
            patterns = rule["patterns"]
            match_mode = rule.get("match", "any")
            if match_mode == "all":
                matched = all(pattern in text for pattern in patterns)
            else:
                matched = any(pattern in text for pattern in patterns)
            if matched:
                semantic_hits[rule["name"]].append(path_rel)

        for heading in FRONTSTAGE_TEMPLATE_HEADINGS:
            section = extract_section(text, heading)
            if not section:
                continue
            found = [term for term in BACKSTAGE_TERMS if term in section]
            if found and "shared/04_light-interaction" not in path_rel:
                warnings.append(f"{path_rel}: backstage term(s) in frontstage-like section {heading}: {', '.join(found)}")

    skill = (base / "../eva/SKILL.md").resolve()
    if skill.exists():
        text = skill.read_text(encoding="utf-8")
        default = extract_section(text, "## 默认启动")
        for forbidden in ("Link", "Synchro", "Asset", "Harness", "schema", "valid_next", "DoD", "failure-record"):
            if forbidden in default:
                errors.append(f"SKILL.md: default startup exposes backstage/system term: {forbidden}")
        for term in DEFAULT_STARTUP_MAINTENANCE_NUDGE_TERMS:
            if term in default:
                errors.append(f"SKILL.md: default startup must not nudge maintenance or public-account copy: {term}")

    for phrase, hits in default_phrase_hits.items():
        if len(hits) > 1:
            errors.append(
                "default startup phrase appears in multiple files: "
                + repr(phrase)
                + " -> "
                + ", ".join(hits)
            )

    rule_by_name = {rule["name"]: rule for rule in SEMANTIC_DUPLICATE_PATTERNS}
    for name, hits in semantic_hits.items():
        unique_hits = sorted(set(hits))
        rule = rule_by_name[name]
        if len(unique_hits) >= rule["threshold"]:
            warnings.append(
                f"semantic duplicate candidate: {name} appears in {len(unique_hits)} file(s): "
                + ", ".join(unique_hits[:8])
                + (" ..." if len(unique_hits) > 8 else "")
                + f"; {rule['hint']}"
            )

    return {
        "ok": not errors,
        "summary": "Eva prompt lint passed" if not errors else "Eva prompt lint failed",
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Eva prompt source-of-truth boundaries.")
    parser.add_argument("--base", default=".", help="Base folder of the eva skill.")
    args = parser.parse_args()

    base = Path(args.base).resolve()
    result = lint(base)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
