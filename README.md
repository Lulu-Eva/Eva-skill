# Eva Skill v2.0.4

当前版本：`2.0.4`。

Eva Skill 是面向创作者的思考、学习、商单拆解和内容生产工具。2.0.4 延续 1.7.4 的主链路，但把入口结构和共享规则拆得更清楚，让高频聊天更轻，创作链路更稳，学习、商单和本地扩展可以显式直达。

## 从 1.7.4 到 2.0.4

1.7.4 是单入口结构：

```text
Eva-skill 1.7.4/
├── SKILL.md                 # 主入口，负责路由和全局规则
└── references/              # Think / Learn / Brief / Create / Memory 等内部模块
```

2.0.4 改为一个路由入口、五个能力入口和一个共享真源层：

```text
skills/
├── eva/              # 极薄路由，只判断进入哪个入口
├── eva-think/        # 日常聊天、想法归位、问题重构
├── eva-learn/        # 学习、带读、主题式阅读
├── eva-create/       # 短视频、标题、开头、正文、对标、AI 味检测
├── eva-brief/        # 商单 Brief、合作需求、商单约束
├── eva-link/         # 本地 Link 创建、检查、调用
└── eva-shared/       # 共享真源包，只为安装和 sibling 读取存在
```

`eva-shared` 是安装用支撑包，不处理用户任务。它只存放多个入口共同依赖的规则、脚本、schema 和示例，避免每个入口维护一套重复规则。安装时必须和其他 Eva 入口一起安装，否则 Think / Create / Learn / Brief / Link 会缺少 shared 真源。

## 主要升级点

- **入口更轻**：`/eva` 只做路由；材料不清时默认交给 `eva-think`，先把问题聊清楚。
- **能力入口平级**：Think、Create、Learn、Brief、Link 都是独立入口，不再全部挤在一个主入口里判断。
- **Learn 明确直达**：用户明确说 Eva Learn，或自然表达“带我学懂 / 带我系统学 / 带我读 / 主题式阅读 / 继续上次学习”时进入学习链路；普通资料不会自动变成学习项目。
- **Brief 显式直达**：品牌 Brief、合作需求和商单约束由 `eva-brief` 先拆清楚，再交回创作链路。
- **Create 保留深链路**：标题、人群、第一句话、正文路线图、商单约束和素材置信度仍然由创作链路控制。
- **Link 独立接入**：用户可以把本地提示词、SOP 或私有方法接入 Eva；普通“写朋友圈 / 写微博 / 写公众号”仍默认走 Create。
- **表达资产轻量预加载**：已保存的 `persona-card` / `voice-card` 可以在需要时只读加载，用来保护表达资格和用户文风；使用具体个人经历时会给出更明确提示，没有命中时不打扰用户。
- **共享校验集中**：资产、Link、回归用例和基础结构检查集中在 `eva-shared`，便于升级后验证。

## 入口说明

| 入口 | 适合处理 | 不负责 |
|---|---|---|
| `eva` | 判断这次该进 Think / Create / Learn / Brief / Link 哪个入口 | 不直接诊断、学习、拆 Brief、写稿或校验 Link |
| `eva-think` | 日常聊天、想法归位、概念澄清、表象问题重构 | 不直接写完整稿 |
| `eva-create` | 短视频、标题、开头、正文、对标、AI 味检测、普通图文/朋友圈/微博/公众号创作 | 不自动调用 Link，不绕过人群和标题验证 |
| `eva-learn` | 学习项目、资料带读、主题式阅读 | 不直接写标题、正文或商单稿 |
| `eva-brief` | 品牌 Brief、合作需求、商单约束卡、已有商单稿检查 | 不直接写完整商单稿 |
| `eva-link` | 自定义 Link、检查 Link、调用已确认 Link | 不抢占普通创作意图 |

## 表达资产

2.0.4 仍然沿用 1.7.4 的 `eva-memory/` 思路，但把表达资产的读取边界写得更明确。

默认只读取当前运行项目里的：

```text
./eva-memory/persona/
./eva-memory/voice/
```

轻量预加载只读，不保存、不生成新卡、不推断、不编造。命中后可以辅助 Think、Create 或 Link 保护用户的人设素材和文风；是否能被标题或正文阶段继续复用，要按资产状态规则重新判断当前任务是否仍相关。

## 开发验证

从仓库根目录运行：

```text
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-shared
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-think
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-create
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-learn
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-brief
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-link
python3 skills/eva-shared/scripts/eva_doctor.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_prompt_lint.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_selftest.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_link_check.py --link skills/eva-shared/examples/eva.link.example.json
python3 skills/eva-shared/scripts/eva_link_check.py --link skills/eva-shared/examples/local.weibo-copy/ --strict
PYTHONPYCACHEPREFIX=/private/tmp/eva-harness-pycache python3 -m py_compile skills/eva-shared/scripts/*.py
```
