#!/usr/bin/env python3
"""Prompt-level lint checks for Eva 2.4.2 source-of-truth boundaries."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote


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

NAVIGATION_PRIORITY_MARKERS = (
    "用户明确目标",
    "原始请求中尚未完成的目标",
    "当前硬闸门或返回原调用者",
    "最新任务结论",
    "Eva Think 默认兜底",
)

NAVIGATION_WORKFLOW_STAGE_MARKERS = (
    "当前判断",
    "必要前置",
    "内容生产",
    "发布前审核",
    "用户现实动作",
    "发布后复盘",
)

OPENING_CONTROLLER_PATH = "../eva-create/references/create/shortvideo/opening/00_eva-opening_开头针对性优化.md"
OPENING_DIAGNOSIS_PATH = "../eva-create/references/create/shortvideo/opening/01_eva-opening-diagnosis_开头承接与兑现诊断.md"
OPENING_GENERATION_PATH = "../eva-create/references/create/shortvideo/opening/02_eva-opening-generation_开头方案生成与推荐.md"

TITLE_RECOMBINATION_NAME = "05_eva-title-recombination_原标题优先与兜底重组.md"
TITLE_RECOMBINATION_PATH = (
    "../eva-create/references/create/shortvideo/title/"
    + TITLE_RECOMBINATION_NAME
)
TITLE_RECOMBINATION_ALLOWED_CALLERS = (
    "../eva-create/references/create/shortvideo/title/00_eva-title_标题即选题.md",
    "../eva-create/references/create/shortvideo/title/02_eva-title-candidate-check_爆款标题候选判断.md",
    "../eva-create/references/create/shortvideo/title/03_eva-title-body-heading_正文标题补强.md",
    "../eva-create/references/create/shortvideo/title/04_eva-title-promise-check_标题承诺与原稿检查.md",
    TITLE_RECOMBINATION_PATH,
)
TITLE_NON_GENERATING_CALLER_MARKERS = {
    "../eva-create/references/create/shortvideo/title/02_eva-title-candidate-check_爆款标题候选判断.md": (
        "本模块不负责：生成任何新标题",
        "满足重组条件时只接力到 05",
    ),
    "../eva-create/references/create/shortvideo/title/03_eva-title-body-heading_正文标题补强.md": (
        "不在本模块生成新标题",
        "任何改字后的完整标题都属于新标题",
    ),
    "../eva-create/references/create/shortvideo/title/04_eva-title-promise-check_标题承诺与原稿检查.md": (
        "本模块不生成新标题",
        "任何新标题只由",
    ),
}
TITLE_RECOMBINATION_POLICY_MARKERS = (
    "3-5 个有真实验证线索的标题候选",
    "原标题都不能一字不改使用",
    "就采用原标题并停止该位置",
    "用户明确只要判断",
    "主谜面的张力",
    "最多输出 3 个方案",
    "完整新标题仍是“未单独验证”",
    "不直接输出高置信度标题交接卡",
    "不自动进入 `/eva-script`",
    "两次知情确认",
    "无标题口播场景回第一句话链路",
    "Article 标题",
)

OPENING_GENERATION_POLICY_MARKERS = (
    "内部候选池",
    "默认展示",
    "推荐 1 个",
    "展示 9 个",
    "指定数量优先",
    "再来 N 个",
    "保留 / 从已有候选选择",
    "不重复",
)

SHORTVIDEO_OPTIONAL_SCRIPT_SIGNAL_MARKERS = (
    "内容目标",
    "读者阶段",
    "首要内容支点",
)

ACQUISITION_CONTEXT_MARKERS = (
    "真实产品或服务",
    "交付前后能够被用户观察到的真实差异",
    "真实用户问题",
    "信任判断",
    "可信依据",
    "适用边界",
    "现实中真实可执行的下一步动作",
)

PRODUCT_SERVICE_REFERENCE_NAME = (
    "04_eva-product-service_产品与服务采集.md"
)

AUDIENCE_REFERENCE_NAME = "00_eva-audience-finder_话题人群识别器.md"
AUDIENCE_ALIGNMENT_REFERENCE_NAME = "01_eva-audience-alignment_写后人群对位.md"
BEAT_REFERENCE_NAME = "01_eva-beats_短视频节拍与心智推进.md"
BEAT_TRUTH_PATH = (
    "../eva-create/references/create/shortvideo/"
    + BEAT_REFERENCE_NAME
)

BEAT_REFERENCE_ALLOWED = (
    BEAT_TRUTH_PATH,
    "../eva-create/SKILL.md",
    "../eva-create/references/create/shortvideo/00_eva-shortvideo_主入口.md",
    "../eva-create/references/create/shortvideo/opening/00_eva-opening_开头针对性优化.md",
    "../eva-create/references/create/shortvideo/opening/01_eva-opening-diagnosis_开头承接与兑现诊断.md",
    "../eva-create/references/create/shortvideo/opening/02_eva-opening-generation_开头方案生成与推荐.md",
    "../eva-create/references/create/shortvideo/script/00_eva-script_思维流爆款内容创作.md",
    "../eva-create/references/create/shortvideo/script/01_eva-script-logic_正文逻辑链推理.md",
    "../eva-create/references/create/shortvideo/script/03_eva-script-runtime_普通正文简版路线.md",
    "../eva-create/references/create/shortvideo/script/04_eva-script-route-map_正文路线图.md",
    "../eva-create/references/create/shortvideo/script/05_eva-script-writing_正文撰写.md",
    "../eva-create/references/create/shortvideo/script/06_eva-script-beat-diagnosis_短视频节拍诊断.md",
    "../eva-shared/references/quality/00_eva-ai-check_表达真实性审查.md",
    "../eva-preflight/SKILL.md",
    "../eva-preflight/references/preflight/00_eva-preflight_发布前审核主控.md",
    "../eva-preflight/references/preflight/01_eva-preflight-shortvideo_短视频审核.md",
    "../eva-preflight/references/preflight/05_eva-preflight-truth-source-call_真源只读调用.md",
)

BEAT_TRUTH_DEFINITION_MARKERS = (
    "节拍：围绕当前主问题完成的一次最小有效心智推进",
    "支撑：帮助当前节拍成立的场景、证据、解释、动作、边界、停顿或转场",
    "节拍链：从用户原有理解走到标题或第一句话承诺终点的必要推进顺序",
    "起点理解",
    "推进材料或动作",
    "新理解位置",
    "停拍",
    "复拍",
    "跳拍",
    "挤拍",
)

LEGACY_FIXED_PROGRESSION_RULES = (
    "2-4 个连续推进点",
    "2—4 个连续推进点",
    "每 1-3 句形成一个小推进",
    "每 1—3 句形成一个小推进",
    "每一句都要有信息推进",
)

AUDIENCE_ALIGNMENT_REFERENCE_ALLOWED = (
    "references/audience/00_eva-audience-finder_话题人群识别器.md",
    "../eva-shared/references/audience/01_eva-audience-alignment_写后人群对位.md",
    "../eva-audience-finder/SKILL.md",
    "../eva-preflight/SKILL.md",
    "../eva-preflight/references/preflight/00_eva-preflight_发布前审核主控.md",
    "../eva-preflight/references/preflight/01_eva-preflight-shortvideo_短视频审核.md",
    "../eva-preflight/references/preflight/02_eva-preflight-article_文章审核.md",
    "../eva-preflight/references/preflight/03_eva-preflight-social_图文与一般社媒内容审核.md",
    "../eva-preflight/references/preflight/05_eva-preflight-truth-source-call_真源只读调用.md",
)

AUDIENCE_ALIGNMENT_REQUIRED_MARKERS = (
    "写前判断这个话题准备替谁说话；写后检查这篇内容最后真正让谁接住了。",
    "对位成立",
    "轻微漂移",
    "关键失焦",
    "无法判断",
    "普通静默轻扫不得加载本文件",
    "真诚、温和、清楚的分享本身可以成立",
    "不推测第一批传播者、转发动机、爆款概率、流量、完播或转化",
)

POSITIONING_BRIDGE_REQUIRED_MARKERS = {
    "../eva-positioning/SKILL.md": (
        "只有用户明确把候选题放进“当前账号定位或账号阶段先做什么”的经营问题",
        AUDIENCE_REFERENCE_NAME,
        "只取具体人群、认知缺口、用户问题并返回 Positioning",
        "不经过一级门牌",
        "可调整优先队列",
        "只有队首是当前定位实验",
        "不自动进入 Create",
    ),
    "../eva-positioning/references/positioning/00_entry_账号阶段性定位主控.md": (
        "## 账号选题经营桥梁",
        "不建立全局选题前置",
        AUDIENCE_REFERENCE_NAME,
        "一个主要角色",
        "功能角色映射以可用 L2 工作定位为前提",
        "只选择一个最高信息增益候选题",
        "先区分两种交付",
        "执行排期",
        "不逐题打分、不设固定比例、不预测效果",
        "不返回 Positioning",
    ),
    "../eva-positioning/references/positioning/01_evidence-ledger_证据与候选账本.md": (
        "## 候选题经营桥梁记录",
        "L0/L1 只记录已有的话题外部价值依据、当前缺口与仍待核实项，不记录功能角色",
        "一个候选题当前只能有一个主要功能角色",
        "不逐题打分",
        "不按固定内容比例",
        "可调整优先队列",
        "顺序不等于分数、定位置信度或效果预测",
    ),
    "../eva-positioning/references/positioning/03_stage-output_阶段结论与主页三件套.md": (
        "## 账号选题经营桥梁输出",
        "预期吸引谁",
        "本题不能证明",
        "本轮唯一现实动作",
        "只有 L0/L1 时不分配功能角色",
        "每轮只选一个最高信息增益候选题和一个发布实验",
        "不输出选题打分表、固定内容比例或多个并列主要角色",
        "## 当前周期可调整优先队列",
        "只有“现在执行”拥有本轮定位实验",
        "前台不展示完整桥梁模板",
        "上游已经说明适配理由时，不再附加导航说明句",
        "Create 继续自己的闸门，不返回 Positioning",
    ),
    "references/shared/07_next-step-navigation_动态选路与下一步推荐.md": (
        "上游专项输出已经说明结果和接力理由时，不再另加导航说明句",
        "没有 Positioning 阻塞且当前决定允许生产时才进入 Create",
    ),
    "references/audience/00_eva-audience-finder_话题人群识别器.md": (
        "## Positioning 窄桥梁只读调用",
        "只返回：**具体人群、认知缺口、用户问题**",
        "不返回待验证标题搜索方向、开头第一句、素材槽位、创作下一步或 audience-card",
        "控制权返回 `eva-positioning`",
        "本模块不得预设",
        "不得再次调用本模块形成循环",
    ),
    "../eva-positioning/references/positioning/05_ai-creator_AI博主专项.md": (
        "主线验证、人设证据、流量入口、商业桥梁或辅助",
        "获客是经营目标，定位实验是验证方式，均不新增为功能角色",
    ),
}

POSITIONING_242_REQUIRED_MARKERS = {
    "../eva-positioning/SKILL.md": (
        "裸定位请求只问一次快速／深度二选一",
        "这一问不计入后续澄清轮次",
        "快速定位最多连续两轮只澄清不交付",
        "最多两个“个人材料方向”",
        "快速定位可以合法停在可执行的工作定位",
        "主页三件套是用户明确要求时才生成的表达层",
    ),
    "../eva-positioning/references/positioning/00_entry_账号阶段性定位主控.md": (
        "分诊真实问题\n→ 提取个人材料方向\n→ 用户提供平台现实证据",
        "这次模式选择不计入后续澄清轮次",
        "不把切换前尚未交付的纯澄清轮次清零",
        "最多连续两轮只澄清而没有交付",
        "不得拆成并列任务",
        "第三次响应必须交付一个合法结果",
        "每连续两轮至少交付一次当前判断、候选或候选变化",
        "没有平台证据时，交付的只能是个人材料方向，不是定位候选",
    ),
    "../eva-positioning/references/positioning/01_evidence-ledger_证据与候选账本.md": (
        "个人材料方向不是定位候选",
        "只有内部事实与最低限度的合格平台证据同时存在，才进入定位候选账本",
        "平台搜索材料",
        "自有账号发布材料",
    ),
    "../eva-positioning/references/positioning/02_platform-search_平台现实取证.md": (
        "用户自己账号已发布的内容、可见数据和真实反馈",
        "不得建立 L1 定位候选",
        "不为了形式完整要求用户重复搜索",
    ),
    "../eva-positioning/references/positioning/03_stage-output_阶段结论与主页三件套.md": (
        "L0 未形成定位",
        "L1 候选定位",
        "L2 工作定位",
        "它是快速定位的合法完成结果",
        "L3 深度阶段定位",
        "不以主页三件套为必选产物",
        "当前可用主页方案 v0",
        "L3 可交付成熟主页方案",
    ),
    "../eva-positioning/references/positioning/04_persistence_暂停恢复与隐私.md": (
        "stage: material-direction",
        "恢复 `eva_version: 2.4.1` 的 L1 时",
        "没有时，保留原始事实、反证和公开边界，但把运行权限降回 L0",
        "不覆盖或回写旧档案",
    ),
    "../eva-positioning/references/positioning/05_ai-creator_AI博主专项.md": (
        "最高只能成为“值得调查的个人材料方向”",
        "不能直接进入定位候选",
        "已有材料足够时不重复取证",
    ),
}

POSITIONING_242_STALE_MARKERS = (
    "用户未回传必要平台证据时，最高只能交付候选定位",
    "最高只能交付 L1 候选定位",
    "账号定位完成必须落到同一套可执行的头像",
)

POSITIONING_AUDIENCE_DIRECT_CALLERS = (
    "../eva-positioning/SKILL.md",
    "../eva-positioning/references/positioning/00_entry_账号阶段性定位主控.md",
)

PRODUCT_SERVICE_REFERENCE_ALLOWED = (
    "../eva-shared/references/memory/04_eva-product-service_产品与服务采集.md",
    "../eva-shared/references/memory/00_eva-memory_点子卡沉淀与回溯.md",
    "../eva-shared/references/asset/00_eva-asset_资产卡协议.md",
    "../eva-shared/references/shared/08_acquisition-objective-overlay_获客目标覆盖层.md",
    "../eva-think/SKILL.md",
    "../eva-create/SKILL.md",
    "../eva-preflight/SKILL.md",
)

PRODUCT_SERVICE_ROUTER_REQUIRED_MARKERS = (
    "/eva-product-service",
    "产品与服务采集",
    "帮我采集产品和服务",
    "整理我能提供什么服务",
    "记住我以后主要做这种咨询",
    "先帮我整理并记住这项业务",
    "先建立可复用底稿，还是现在写或规划获客内容",
    "“产品”“服务”“咨询”裸词",
    "普通产品分析",
    "第三方资料整理",
    "客服",
    "CRM",
)

PRODUCT_SERVICE_SCOPED_ENTRY_PATHS = {
    "../eva-think/SKILL.md": ("普通 Think", "普通任务", "普通创作"),
    "../eva-create/SKILL.md": ("普通 Create", "普通创作"),
    "../eva-preflight/SKILL.md": ("普通 Preflight", "普通审核"),
}

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
            "../eva-shared/references/memory/04_eva-product-service_产品与服务采集.md",
            "references/link/03_eva-link-builder-templates_生成模板.md",
        ),
        "fields": ASSET_FIELD_MARKERS,
        "min_hits": 5,
    },
    {
        "name": "dynamic-navigation priority",
        "allowed": ("../eva-shared/references/shared/07_next-step-navigation_动态选路与下一步推荐.md",),
        "fields": NAVIGATION_PRIORITY_MARKERS,
        "min_hits": 4,
    },
    {
        "name": "dynamic workflow stage taxonomy",
        "allowed": ("../eva-shared/references/shared/07_next-step-navigation_动态选路与下一步推荐.md",),
        "fields": NAVIGATION_WORKFLOW_STAGE_MARKERS,
        "min_hits": 4,
    },
    {
        "name": "opening candidate-count and recommendation policy",
        "allowed": (OPENING_GENERATION_PATH,),
        "fields": OPENING_GENERATION_POLICY_MARKERS,
        "min_hits": 4,
    },
    {
        "name": "shortvideo optional script-ranking signals",
        "allowed": (
            "../eva-create/references/create/shortvideo/script/"
            "00_eva-script_思维流爆款内容创作.md",
        ),
        "fields": SHORTVIDEO_OPTIONAL_SCRIPT_SIGNAL_MARKERS,
        "min_hits": 2,
    },
    {
        "name": "acquisition objective temporary context",
        "allowed": (
            "../eva-shared/references/shared/08_acquisition-objective-overlay_获客目标覆盖层.md",
        ),
        "fields": ACQUISITION_CONTEXT_MARKERS,
        "min_hits": 5,
    },
    {
        "name": "title recombination internal main-riddle tension",
        "allowed": (TITLE_RECOMBINATION_PATH,),
        "fields": ("主谜面的张力",),
        "min_hits": 1,
    },
    {
        "name": "short-video beat definitions and failure taxonomy",
        "allowed": (BEAT_TRUTH_PATH,),
        "fields": BEAT_TRUTH_DEFINITION_MARKERS,
        "min_hits": 7,
    },
)


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return "../" + str(path.relative_to(base.parent))


def md_files(base: Path) -> list[Path]:
    # Scan every installed/source Eva sibling dynamically.  A hard-coded peer
    # list silently skipped new top-level entries (for example Preflight), which
    # made source-of-truth duplication checks weaker each time Eva grew.
    skills_root = base.parent
    candidates: list[Path] = []
    if skills_root.exists():
        for skill_root in skills_root.iterdir():
            if skill_root.is_dir():
                candidates.extend(skill_root.rglob("*.md"))
    return sorted({path.resolve() for path in candidates})


def numbered_eva_references(text: str) -> list[tuple[int, str]]:
    """Extract concrete numbered Eva file references, excluding example blocks.

    Eva instructions use both Markdown links and inline code paths.  Bare
    filenames are intentional references too; directory trees, shell examples,
    template variables and remote URLs are not local file references.
    """
    references: list[tuple[int, str]] = []
    fence: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        fence_match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        candidates = re.findall(r"(?<!`)`([^`\n]+)`(?!`)", line)
        for match in re.finditer(r"\]\(\s*(?:<([^>]+)>|([^\s)]+))", line):
            candidates.append(match.group(1) or match.group(2))
        for candidate in candidates:
            candidate = unquote(candidate.strip())
            if any(marker in candidate for marker in ("://", "<", ">", "{", "}", "*", "$", "...", "…")):
                continue
            candidate = candidate.split("#", 1)[0]
            if re.fullmatch(r"(?:[^\s`/]+/)*\d{2}_eva-[^\s`/]+\.md", candidate):
                references.append((line_number, candidate))
    return sorted(set(references))


def lint_numbered_eva_references(base: Path) -> list[str]:
    """Resolve Eva references using document-relative and skill-root conventions."""
    base = base.resolve()
    skills_root = base.parent
    paths = sorted({
        path.resolve()
        for skill_root in skills_root.glob("eva*")
        if skill_root.is_dir()
        for path in skill_root.rglob("*.md")
    })
    basenames = {path.name for path in paths}
    errors: list[str] = []
    for path in paths:
        relative_parts = path.relative_to(skills_root).parts
        skill_root = skills_root / relative_parts[0]
        for line_number, reference in numbered_eva_references(path.read_text(encoding="utf-8")):
            if "/" not in reference:
                exists = reference in basenames
            else:
                # References inside deep prompt files are often relative to the
                # owning SKILL.md, rather than to the prompt's own directory.
                roots = (path.parent, skill_root, skills_root, skills_root.parent)
                exists = any((root / reference).resolve().is_file() for root in roots)
            if not exists:
                errors.append(f"{rel(path, base)}:{line_number}: missing numbered Eva reference: {reference}")
    return errors


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


def has_positive_reference(text: str, marker: str) -> bool:
    """Return true when a reference is used, not merely named in a prohibition."""
    negative_markers = ("禁止读取", "不得读取", "不读取", "禁止读", "不得读", "不读")
    return any(
        marker in line and not any(negative in line for negative in negative_markers)
        for line in text.splitlines()
    )


def lint(base: Path) -> dict:
    errors: list[str] = lint_numbered_eva_references(base)
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

        normalized_path = path.as_posix()
        if "/eva-positioning/" in normalized_path:
            for stale_marker in POSITIONING_242_STALE_MARKERS:
                if stale_marker in text:
                    errors.append(
                        f"{path_rel}: keeps pre-2.4.2 Positioning rule: {stale_marker}"
                    )
        if "/eva-create/references/create/article/" in normalized_path:
            for coupling in ARTICLE_FORBIDDEN_SHORTVIDEO_COUPLINGS:
                if coupling in text:
                    errors.append(f"{path_rel}: Article protocol couples to short-video gate: {coupling}")
        if "/eva-create/references/create/shortvideo/" in normalized_path:
            for coupling in SHORTVIDEO_FORBIDDEN_ARTICLE_COUPLINGS:
                if coupling in text:
                    errors.append(f"{path_rel}: short-video protocol couples to Article branch: {coupling}")
        if "/eva-create/references/create/shortvideo/script/" in normalized_path:
            for forbidden in ("800 字左右", "800字左右"):
                if forbidden in text:
                    errors.append(
                        f"{path_rel}: short-video script protocol contains fixed-length wording {forbidden!r}"
                    )
        if "/eva-preflight/" in normalized_path and has_positive_reference(
            text, "02_eva-opening-generation_开头方案生成与推荐.md"
        ):
            errors.append(f"{path_rel}: Preflight must not read Opening generation truth 02")

        if has_positive_reference(text, PRODUCT_SERVICE_REFERENCE_NAME) and not in_allowed(
            path, PRODUCT_SERVICE_REFERENCE_ALLOWED
        ):
            errors.append(
                f"{path_rel}: product-service truth may only be loaded by its truth "
                "source, acquisition overlay, Think, Create or Preflight"
            )

        if has_positive_reference(text, AUDIENCE_ALIGNMENT_REFERENCE_NAME) and not in_allowed(
            path, AUDIENCE_ALIGNMENT_REFERENCE_ALLOWED
        ):
            errors.append(
                f"{path_rel}: write-after audience-alignment truth may only be "
                "loaded by its truth source, Audience entry or explicit Preflight paths"
            )

        if has_positive_reference(text, BEAT_REFERENCE_NAME) and not in_allowed(
            path, BEAT_REFERENCE_ALLOWED
        ):
            errors.append(
                f"{path_rel}: short-video beat truth may only be loaded by "
                "short-video Opening/Script or read-only short-video Preflight"
            )

        for legacy_rule in LEGACY_FIXED_PROGRESSION_RULES:
            if legacy_rule in text:
                errors.append(
                    f"{path_rel}: keeps legacy fixed progression rule "
                    f"{legacy_rule!r}; use the minimum necessary beat chain instead"
                )

        if has_positive_reference(text, TITLE_RECOMBINATION_NAME) and not in_allowed(
            path, TITLE_RECOMBINATION_ALLOWED_CALLERS
        ):
            errors.append(
                f"{path_rel}: Title recombination is a conditional short-video "
                "Title fallback and must not be loaded by Article, no-title, "
                "Positioning, Preflight or unrelated modules"
            )

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
        if len(text.splitlines()) > 140:
            errors.append(f"eva router must stay at or below 140 lines, got {len(text.splitlines())}")
        if len(text) > 8500:
            errors.append(f"eva router must stay at or below 8500 characters, got {len(text)}")
        for marker in (
            "../eva-shared/references/shared/07_next-step-navigation_动态选路与下一步推荐.md",
            "下一步怎么走",
            "先用哪个功能",
            "入口排序",
            "工作流",
            "仅在当前 Eva 任务上下文中",
            "用户只说“研究 / 看看 / 处理这份资料”",
            "按发散对象而不是“发散”一词路由",
            "指定数量的开头方案",
            "内容候选数量不是入口排序",
            "围绕当前阶段判断选题",
            "为本人自媒体账号做定位/赛道定位/定位复盘",
            "自然语言包括想法梳理、话题人群识别、学科发散",
            "Positioning 仅在账号选题经营桥梁已命中且人群三项不清时调用",
        ):
            if marker not in text:
                errors.append(f"eva router missing dynamic-navigation trigger/reference: {marker}")
        for marker in PRODUCT_SERVICE_ROUTER_REQUIRED_MARKERS:
            if marker not in text:
                errors.append(
                    f"eva router missing precise product-service route marker: {marker}"
                )
        router_frontmatter = (
            text.split("---", 2)[1]
            if text.startswith("---") and len(text.split("---", 2)) == 3
            else ""
        )
        if "或业务任务" in router_frontmatter:
            errors.append(
                "eva router frontmatter must not claim all generic business tasks"
            )
        for pattern in (
            r"(?:自然语言触发|触发：)[^\n]*(?:^|[、，])(?:产品|服务|咨询)(?:[、，。]|$)",
            r"\|\s*(?:产品|服务|咨询)\s*\|",
        ):
            if re.search(pattern, router_frontmatter):
                errors.append(
                    "eva router frontmatter must not expose bare 产品/服务/咨询 "
                    "as product-service collection triggers"
                )
        if has_positive_reference(text, PRODUCT_SERVICE_REFERENCE_NAME):
            errors.append(
                "eva router must route product-service collection to eva-think "
                "instead of loading the shared truth directly"
            )
        if "或 Positioning 在内部发现人群不清" in text:
            errors.append(
                "eva router must not generalize Positioning Audience use beyond the account-topic bridge"
            )
        default = extract_section(text, "## 默认启动")
        for forbidden in ("Link", "Synchro", "Asset", "Harness", "schema", "valid_next", "DoD", "failure-record"):
            if forbidden in default:
                errors.append(f"SKILL.md: default startup exposes backstage/system term: {forbidden}")

    for relative, markers in POSITIONING_BRIDGE_REQUIRED_MARKERS.items():
        bridge_path = (base / relative).resolve()
        if not bridge_path.exists():
            errors.append(f"missing Positioning account-topic bridge owner: {relative}")
            continue
        bridge_text = bridge_path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in bridge_text:
                errors.append(
                    f"{relative}: missing narrow Positioning account-topic bridge marker: {marker}"
                )

    for relative, markers in POSITIONING_242_REQUIRED_MARKERS.items():
        positioning_path = (base / relative).resolve()
        if not positioning_path.exists():
            errors.append(f"missing Eva 2.4.2 Positioning owner: {relative}")
            continue
        positioning_text = positioning_path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in positioning_text:
                errors.append(
                    f"{relative}: missing Eva 2.4.2 Positioning marker: {marker}"
                )

    audience_alignment_path = (
        base / "references/audience/01_eva-audience-alignment_写后人群对位.md"
    ).resolve()
    if not audience_alignment_path.exists():
        errors.append("missing write-after audience-alignment truth")
    else:
        audience_alignment_text = audience_alignment_path.read_text(encoding="utf-8")
        for marker in AUDIENCE_ALIGNMENT_REQUIRED_MARKERS:
            if marker not in audience_alignment_text:
                errors.append(
                    "write-after audience-alignment truth missing marker: " + marker
                )

    beat_truth_path = (base / BEAT_TRUTH_PATH).resolve()
    if not beat_truth_path.exists():
        errors.append("missing short-video beat truth")
    else:
        beat_truth_text = beat_truth_path.read_text(encoding="utf-8")
        for marker in (
            *BEAT_TRUTH_DEFINITION_MARKERS,
            "内部表示：起点理解 → 推进材料或动作 → 新理解位置",
            "不规定固定拍数、每段一拍、每句一拍或每分钟拍数",
            "30 秒与 90 秒可以共享必要理解步骤",
            "不建立节拍评分、密度或 KPI",
            "一句话可以完成一拍，多句话也可以共同完成一拍",
            "就不是水分",
            "事实与安全、Brief、平台规则、标题或第一句话承诺、原意与事实颗粒度、正文兑现、voice-card 与口播自然 > 节拍清晰度",
            "不适用于 Article、Think、Lens、Audience 或 Positioning",
            "用户原有理解\n→ 最少必要节拍链\n→ 本稿允许抵达的新理解",
            "不得超过标题或第一句话承诺",
            "一项用户期待可以由一拍回答，也可以由多拍共同回答",
            "一拍可以回应相邻的多项期待",
            "不机械等于最后一拍，也不自动等于 CTA",
            "节拍只组织已经成立的内容",
            "节拍不能覆盖 Audience、方法动作颗粒度、动态时长、低置信度或用户明确要求",
        ):
            if marker not in beat_truth_text:
                errors.append(f"short-video beat truth missing marker: {marker}")

    beat_diagnosis_path = (
        base
        / "../eva-create/references/create/shortvideo/script/"
        "06_eva-script-beat-diagnosis_短视频节拍诊断.md"
    ).resolve()
    if not beat_diagnosis_path.exists():
        errors.append("missing on-demand short-video beat diagnosis adapter")
    else:
        beat_diagnosis_text = beat_diagnosis_path.read_text(encoding="utf-8")
        for marker in (
            "只在用户已经提供短视频稿，并明确要求检查节拍、水分或推进时读取",
            "用白话说明一个最高优先级问题",
            "最多附一个轻量标签",
            "不默认展示完整节拍链",
            "只诊断、不要改",
            "不给调整方向、下一步或续轮邀请",
            "明确问“怎么调、给建议”时，才在结果后增加一个调整原则",
            "明确要求修改时，才返回现有 Writing 链路",
            "列出节拍链、逐拍拆解、按四类分类",
        ):
            if marker not in beat_diagnosis_text:
                errors.append(f"beat diagnosis adapter missing marker: {marker}")

    for relative in POSITIONING_AUDIENCE_DIRECT_CALLERS:
        caller_path = (base / relative).resolve()
        if not caller_path.exists():
            continue
        caller_text = caller_path.read_text(encoding="utf-8")
        if not has_positive_reference(caller_text, AUDIENCE_REFERENCE_NAME):
            errors.append(
                f"{relative}: Positioning must directly read the shared Audience truth when the narrow bridge lacks external-value fields"
            )
        if "/eva-audience-finder" in caller_text:
            errors.append(
                f"{relative}: Positioning internal Audience use must not route through the user-facing signboard"
            )

    ai_positioning_path = (
        base / "../eva-positioning/references/positioning/05_ai-creator_AI博主专项.md"
    ).resolve()
    if ai_positioning_path.exists():
        ai_positioning_text = ai_positioning_path.read_text(encoding="utf-8")
        for stale_role in ("主体证据", "主线内容", "业务获客或定位实验"):
            if stale_role in ai_positioning_text:
                errors.append(
                    f"AI creator positioning must not keep a second account-topic role taxonomy: {stale_role}"
                )

    for relative, ordinary_markers in PRODUCT_SERVICE_SCOPED_ENTRY_PATHS.items():
        entry_path = (base / relative).resolve()
        if not entry_path.exists():
            continue
        entry_text = entry_path.read_text(encoding="utf-8")
        if not has_positive_reference(entry_text, PRODUCT_SERVICE_REFERENCE_NAME):
            errors.append(
                f"{relative}: must reference product-service truth on explicit demand"
            )
            continue
        scoped_boundary = any(
            any(
                product_marker in line
                for product_marker in (
                    "product-service",
                    "Product Service",
                    "产品与服务底稿",
                )
            )
            and (
                (
                    any(marker in line for marker in ordinary_markers)
                    and any(
                        negative in line
                        for negative in (
                            "不读取",
                            "不扫描",
                            "不加载",
                            "不询问",
                            "不得",
                        )
                    )
                )
                or ("只有" in line and "才" in line)
            )
            for line in entry_text.splitlines()
        )
        if not scoped_boundary:
            errors.append(
                f"{relative}: product-service loading must have an explicit "
                "ordinary-task no-load boundary"
            )

    navigation_path = base / "references/shared/07_next-step-navigation_动态选路与下一步推荐.md"
    if not navigation_path.exists():
        errors.append("missing shared dynamic-navigation truth source")
    else:
        navigation_text = navigation_path.read_text(encoding="utf-8")
        for marker in (
            *NAVIGATION_PRIORITY_MARKERS,
            "只问一个能改变交付的问题",
            "推荐不是隐性授权",
            "只有用户明确要求“给我一个工作流",
            "谁调用，控制权返回给谁",
            "不新增导航资产、状态字段、schema 或 handoff target",
            "内容产物数量不是入口数量",
            "局部内容创作或发散留在对应 Create 分支",
        ):
            if marker not in navigation_text:
                errors.append(f"dynamic-navigation truth missing marker: {marker}")

    opening_paths = {
        "controller": (base / OPENING_CONTROLLER_PATH).resolve(),
        "diagnosis": (base / OPENING_DIAGNOSIS_PATH).resolve(),
        "generation": (base / OPENING_GENERATION_PATH).resolve(),
    }
    for role, opening_path in opening_paths.items():
        if not opening_path.exists():
            errors.append(f"missing Opening {role} truth: {opening_path}")
    if all(path.exists() for path in opening_paths.values()):
        controller_text = opening_paths["controller"].read_text(encoding="utf-8")
        diagnosis_text = opening_paths["diagnosis"].read_text(encoding="utf-8")
        generation_text = opening_paths["generation"].read_text(encoding="utf-8")
        for required_reference in (
            "01_eva-opening-diagnosis_开头承接与兑现诊断.md",
            "02_eva-opening-generation_开头方案生成与推荐.md",
        ):
            if required_reference not in controller_text:
                errors.append(f"Opening controller must reference {required_reference}")
        if "唯一诊断真源" not in diagnosis_text or "不生成新开头" not in diagnosis_text:
            errors.append("Opening diagnosis truth must state that it diagnoses without generating options")
        for marker in (
            "### 可感知落点软检查",
            "第一拍缺少可感知支撑",
            "不增加追问",
            "不强制讲故事",
            "**入口与停留**",
            "**解释与澄清**",
            "**回报与兑现线索**",
            "不要求正好三句",
            "### 现有关注入口软检查",
            "真实的情绪张力或公共关注入口",
            "不自动联网",
            "不追问、不阻塞",
        ):
            if marker not in diagnosis_text:
                errors.append(
                    f"Opening diagnosis truth missing soft perceptible-anchor marker: {marker}"
                )
        generation_policy_hits = count_fields(generation_text, OPENING_GENERATION_POLICY_MARKERS)
        if generation_policy_hits < 6:
            errors.append(
                "Opening generation truth must own the candidate-count policy "
                f"(found {generation_policy_hits} of {len(OPENING_GENERATION_POLICY_MARKERS)} markers)"
            )
        if count_fields(diagnosis_text, OPENING_GENERATION_POLICY_MARKERS) >= 2:
            errors.append("Opening diagnosis truth duplicates candidate-count or recommendation policy")
        if has_positive_reference(diagnosis_text, "02_eva-opening-generation_开头方案生成与推荐.md"):
            errors.append("Opening diagnosis truth must not call the generation truth")
        if "## Preflight 只读调用" in generation_text:
            errors.append("Opening generation truth must not expose a Preflight read-only entry")
        for marker in (
            "才按顺序使用两个平局信号",
            "先比较候选能否",
            "仍相当且 Diagnosis 已确认",
            "一句成立则停",
            "不强制它独立完成全部三项功能",
            "不新增第七种机制",
            "不得放大情绪",
            "预测传播效果",
        ):
            if marker not in generation_text:
                errors.append(
                    f"Opening generation truth missing grounded recommendation marker: {marker}"
                )
        tie_break_order = ("才按顺序使用两个平局信号", "先比较候选能否", "仍相当且 Diagnosis 已确认")
        if not all(generation_text.find(marker) < generation_text.find(next_marker) for marker, next_marker in zip(tie_break_order, tie_break_order[1:])):
            errors.append("Opening generation tie-break signals must keep their declared order")
        if "不把它扩展成新的开头机制" in diagnosis_text:
            errors.append("Opening diagnosis must not own generation-mechanism policy")
        for forbidden in ("第一句不能独立交代话题、停留理由和兑现线索", "第一句 + 必要的前三句承接"):
            if forbidden in generation_text:
                errors.append(f"Opening generation keeps one-sentence/three-sentence conflict: {forbidden}")

    opening_downstream_contracts = (
        (
            (base / "references/shared/00_handoff-cards_交接卡字段真源.md").resolve(),
            ("第一句至少要让人确认话题入口", "一至三句整体完成"),
            "first-line handoff",
        ),
        (
            (base / "../eva-create/references/create/shortvideo/script/00_eva-script_思维流爆款内容创作.md").resolve(),
            ("第一句话至少确认话题入口", "一至三句整体完成"),
            "Script controller",
        ),
        (
            (base / "../eva-create/references/create/shortvideo/script/04_eva-script-route-map_正文路线图.md").resolve(),
            ("至少确认话题入口", "一至三句整体完成", "一句成立即停"),
            "Script route map",
        ),
        (
            (base / "../eva-preflight/references/preflight/01_eva-preflight-shortvideo_短视频审核.md").resolve(),
            ("第一句是否至少让人确认话题入口", "必要的一至三句整体", "不因数量少而判为问题"),
            "short-video Preflight",
        ),
    )
    legacy_first_line_contracts = (
        "第一句话不能独立建立话题、停留理由和兑现线索",
        "第一句话要能独立建立话题、停留理由和兑现线索",
        "必须独立建立话题、停留理由和兑现线索",
        "第一句是否能独立交代在讲什么、为什么继续看、后面能兑现什么",
    )
    for downstream_path, required_markers, label in opening_downstream_contracts:
        if not downstream_path.exists():
            errors.append(f"missing {label}: {downstream_path}")
            continue
        downstream_text = downstream_path.read_text(encoding="utf-8")
        for marker in required_markers:
            if marker not in downstream_text:
                errors.append(f"{label} missing adaptive first-line marker: {marker}")
        for forbidden in legacy_first_line_contracts:
            if forbidden in downstream_text:
                errors.append(f"{label} keeps legacy first-line hard contract: {forbidden}")

    script_writing_path = (
        base
        / "../eva-create/references/create/shortvideo/script/"
        "05_eva-script-writing_正文撰写.md"
    ).resolve()
    if not script_writing_path.exists():
        errors.append(f"missing short-video Script writing truth: {script_writing_path}")
    else:
        script_writing_text = script_writing_path.read_text(encoding="utf-8")
        for marker in (
            "正文中的句子要么完成当前节拍，要么提供必要支撑",
            "节拍优化低于事实、Brief、标题承诺、正文兑现和用户文风",
            "抽象悬浮在节拍分类中不是第五类失效",
            "中段抽象悬浮",
            "推进断层",
            "节奏同质",
            "默认内部检查并先修稿",
            "不得覆盖 voice-card",
            "正文必须回到原定人群和同一个主问题",
            "不得扩大情绪、借热点换题",
            "不得承诺流量或传播效果",
        ):
            if marker not in script_writing_text:
                errors.append(
                    f"Script writing truth missing silent viewing-experience marker: {marker}"
                )

    script_logic_path = (
        base
        / "../eva-create/references/create/shortvideo/script/"
        "01_eva-script-logic_正文逻辑链推理.md"
    ).resolve()
    if not script_logic_path.exists():
        errors.append(f"missing short-video Script logic truth: {script_logic_path}")
    else:
        script_logic_text = script_logic_path.read_text(encoding="utf-8")
        for marker in (
            "## Preflight 只读调用",
            "停拍、复拍、跳拍和挤拍只读",
            "中段连续抽象是否缺少可辨认落点",
            "上下段是否推进断层",
            "非节拍观看体验独立判断",
            "节拍标签本身不能触发“暂不建议发布”",
            "不改写正文",
        ):
            if marker not in script_logic_text:
                errors.append(
                    f"Script logic Preflight branch missing viewing-experience boundary: {marker}"
                )

    preflight_controller_path = (
        base / "../eva-preflight/references/preflight/00_eva-preflight_发布前审核主控.md"
    ).resolve()
    preflight_truth_map_path = (
        base / "../eva-preflight/references/preflight/05_eva-preflight-truth-source-call_真源只读调用.md"
    ).resolve()
    for preflight_rule_path, markers in (
        (
            preflight_controller_path,
            (
                "轻微节拍问题、可感知支撑不足或节奏平稳",
                "节拍标签、抽象支撑不足或节奏同质本身不能单独触发“暂不建议发布”",
                "继续归事实与兑现问题",
                "主任务没有统一",
                "确认保留开头承诺还是现有正文任务",
                "Preflight 不代选",
            ),
        ),
        (
            preflight_truth_map_path,
            (
                "第一拍可感知支撑",
                "中段可感知支撑、推进断层、节奏同质及其他非节拍观看体验问题",
                "问题类型、原文证据和实际影响",
                "全部按 00 主控处理",
                "不继承生产流程",
                "改写、生成标题、生成开头、补写正文或完整成稿",
                "不读取节拍诊断的前台适配器",
                "不继承调整原则、生成或改稿动作",
            ),
        ),
    ):
        if not preflight_rule_path.exists():
            errors.append(f"missing Preflight viewing-experience boundary: {preflight_rule_path}")
            continue
        preflight_rule_text = preflight_rule_path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in preflight_rule_text:
                errors.append(
                    f"{preflight_rule_path}: missing Preflight viewing-experience marker: {marker}"
                )

    route_map_path = (
        base
        / "../eva-create/references/create/shortvideo/script/"
        "04_eva-script-route-map_正文路线图.md"
    ).resolve()
    handoff_truth_path = (
        base / "references/shared/00_handoff-cards_交接卡字段真源.md"
    ).resolve()
    for path, markers, label in (
        (
            route_map_path,
            (
                "用户原有理解",
                "本稿允许抵达的新理解",
                "由一拍回答",
                "由多拍共同回答",
                "与相邻期待由同一拍回应",
                "不机械等于最后一拍",
            ),
            "Script route map",
        ),
        (
            handoff_truth_path,
            (
                "用户期待清单：1..N 条必要期待",
                "保留兼容字段名",
                "不得机械一一对应正文层级",
            ),
            "handoff truth",
        ),
    ):
        if not path.exists():
            errors.append(f"missing {label}: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{label} missing conservative-beat marker: {marker}")
        for forbidden in (
            "期待 1 -> 第一层",
            "期待 2 -> 第二层",
            "期待 3 -> 第三层",
            "期待 4 -> 结尾/动作",
            "用户期待清单：至少 2 条具体期待",
        ):
            if forbidden in text:
                errors.append(f"{label} keeps fixed expectation-layer mapping: {forbidden}")

    ai_check_path = (
        base / "references/quality/00_eva-ai-check_表达真实性审查.md"
    ).resolve()
    if ai_check_path.exists():
        ai_check_text = ai_check_path.read_text(encoding="utf-8")
        for marker in (
            "Article 和一般社媒继续使用本模块自己的内容推进漏斗",
            "每一部分是否推进当前意思或提供必要支撑",
            "推进与必要支撑都有效",
            "短视频同时要查 AI 味与水分 / 没推进",
            "只交付一个最高优先级问题",
        ):
            if marker not in ai_check_text:
                errors.append(f"AI Check missing cross-format progression marker: {marker}")
        for forbidden in ("每句话是否把读者往前推", "每句推进"):
            if forbidden in ai_check_text:
                errors.append(f"AI Check keeps fixed per-sentence progression rule: {forbidden}")

    if script_logic_path.exists():
        script_logic_text = script_logic_path.read_text(encoding="utf-8")
        for marker in (
            "## 核心判断来源窄检查",
            "从材料提炼—待确认",
            "必须已执行 Script 主控",
            "不重复定义",
        ):
            if marker not in script_logic_text:
                errors.append(f"Script logic missing narrow derived-stance boundary: {marker}")

    script_router_path = (
        base
        / "../eva-create/references/create/shortvideo/script/"
        "00_eva-script_思维流爆款内容创作.md"
    ).resolve()
    if script_router_path.exists():
        script_router_text = script_router_path.read_text(encoding="utf-8")
        for marker in (
            "## 全路线共用的核心判断来源窄检查",
            "在简版路线和完整路线分流之前执行",
            "不是普通创作的固定确认环节",
            "不得把本检查扩张成价值观访谈",
        ):
            if marker not in script_router_text:
                errors.append(f"Script router missing common derived-stance boundary: {marker}")

    compact_route_path = (
        base
        / "../eva-create/references/create/shortvideo/script/"
        "03_eva-script-runtime_普通正文简版路线.md"
    ).resolve()
    if compact_route_path.exists():
        compact_route_text = compact_route_path.read_text(encoding="utf-8")
        for marker in (
            "简版路线不得绕过 Script 主控",
            "从材料提炼—待确认",
            "用户已明确的判断和普通保守改写不追问",
        ):
            if marker not in compact_route_text:
                errors.append(f"Compact route missing common derived-stance gate: {marker}")

    for mixed_route_path in (
        (base / "../eva-create/SKILL.md").resolve(),
        (base / "../eva-create/references/create/00_eva-create_创作主入口.md").resolve(),
    ):
        if not mixed_route_path.exists():
            errors.append(f"missing Create mixed AI/beat router: {mixed_route_path}")
            continue
        mixed_route_text = mixed_route_path.read_text(encoding="utf-8")
        for marker in ("AI 味", "只看节拍", "不叠加两份报告"):
            if marker not in mixed_route_text:
                errors.append(f"Create mixed AI/beat router missing marker {marker}: {mixed_route_path}")

    title_recombination_path = (base / TITLE_RECOMBINATION_PATH).resolve()
    if not title_recombination_path.exists():
        errors.append("missing conditional Title original-first recombination truth")
    else:
        title_recombination_text = title_recombination_path.read_text(encoding="utf-8")
        policy_hits = count_fields(
            title_recombination_text, TITLE_RECOMBINATION_POLICY_MARKERS
        )
        if policy_hits < len(TITLE_RECOMBINATION_POLICY_MARKERS):
            errors.append(
                "Title recombination truth must keep original-first, validation, "
                "fulfillment and platform boundaries "
                f"(found {policy_hits} of {len(TITLE_RECOMBINATION_POLICY_MARKERS)} markers)"
            )

    for relative in TITLE_RECOMBINATION_ALLOWED_CALLERS[:-1]:
        caller_path = (base / relative).resolve()
        if not caller_path.exists():
            errors.append(f"missing Title recombination caller: {relative}")
            continue
        if not has_positive_reference(
            caller_path.read_text(encoding="utf-8"), TITLE_RECOMBINATION_NAME
        ):
            errors.append(
                f"{relative}: must conditionally reference the Title "
                "recombination truth"
            )

    for relative, markers in TITLE_NON_GENERATING_CALLER_MARKERS.items():
        caller_path = (base / relative).resolve()
        if not caller_path.exists():
            continue
        caller_text = caller_path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in caller_text:
                errors.append(
                    f"{relative}: Title judgment caller missing no-generation "
                    f"ownership marker: {marker}"
                )
    body_title_path = (
        base
        / "../eva-create/references/create/shortvideo/title/"
        "03_eva-title-body-heading_正文标题补强.md"
    ).resolve()
    if body_title_path.exists() and "轻微替换" in body_title_path.read_text(encoding="utf-8"):
        errors.append(
            "Title body-heading must not lightly edit a title outside the "
            "conditional recombination truth"
        )

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
