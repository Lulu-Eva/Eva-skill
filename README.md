# Eva Skill v2.0

Eva 2.0 是从 Eva 1.7.4 升级而来的创作者工作台。

当前开发版本：`2.0.3`。

1.7.4 的核心是内容创作调度：帮用户把想法推进到标题、开头、正文和商单。  
2.0 的核心是工作台化：在原有创作能力上，新增 Assist Harness、Eva Link，以及独立的 Brief / Learn 入口，让 Eva 能处理更长链路、更复杂的创作任务和跨模块交接。

一句话：

```text
Eva 1.7.4 主要解决“怎么写出来”。
Eva 2.0 进一步解决“怎么判断任务、承接上下文、拆分专门入口、接入自己的工作流，再稳定写出来”。
```

## 2.0 的三件大更新

### 1. Assist Harness：从写作调度器升级为创作工作台底座

Assist Harness 是 2.0 最大的结构变化。

它不是一个给用户直接调用的新功能，而是 Eva 背后的任务协作层。它负责：

- 判断用户当前卡在哪一层：想法、问题、人群、标题、开头、正文、商单、资产保存。
- 在模块之间做交接：Think / Create / Memory / Link 不再各自散跑。
- 把跨模块结果收回 Eva Asset：输出能继续被下游读取，而不是停在一段自由文本。
- 在完成前做校验：缺人群、缺标题验证、缺 Brief、缺真实素材、缺交接字段时，先退回补齐。
- 控制前台体验：普通创作任务不暴露 Harness、schema、valid_next、DoD 等后台词。

对 1.7.4 用户来说，最直接的变化是：

```text
Eva 不再只是“帮我写一条内容”的工具，
而是能判断“这条内容现在该先想清楚、先找人群、先拆 Brief、先搜标题、先补素材，还是可以开始写”的工作台。
```

### 2. Eva Link：从单次对话升级为可接入自己的工作流

Eva 2.0 新增 Eva Link：

| 能力 | 解决什么问题 | 什么时候使用 |
|---|---|---|
| Eva Link | 把本地私有模块、个人提示词、SOP、方法论接入 Eva 资产流 | 用户明确说“把这个提示词接进 Eva”“做一个自己的 Link”“检查本地 Link” |

Link 不是默认创作流程的一部分。  
它只有在用户明确触发或确认后才进入，不抢占普通写作、商单和学习任务。

这次升级的意义不是“多了一个按钮”，而是：

```text
Eva 可以稳定连接你的私有流程和本地模块，
同时仍然用 Eva Asset 和 Harness 保证结果能被主创作链继续承接。
```

### 3. Brief / Learn 独立入口：主 Eva 更干净，专门任务更清楚

1.7.4 里，商单 Brief 和学习项目容易挤在 Eva 主流程里。  
2.0 把它们拆成 sibling Skill：

| 入口 | 定位 | 处理什么 | 不处理什么 |
|---|---|---|---|
| `eva` | 主创作工作台 | 想法归位、人群判断、标题/开头/正文、资料转内容、资产保存 | 不把严肃学习项目和独立 Brief 拆解塞进主流程 |
| `eva-brief` | 独立商单 Brief 入口 | 品牌 Brief、合作需求、商单约束卡、已有商单稿检查、对标样本迁移 | 不直接写完整商单稿、标题、开头或正文 |
| `eva-learn` | 独立学习项目入口 | 带读、主题式阅读、跨轮学习项目、思想种子卡 | 不直接替代创作链路，不直接写标题或正文 |

这个拆分的核心价值：

- 主 Eva 继续以创作为主干，不被长期学习项目拖重。
- 商单 Brief 有专门入口，不再和普通商单成稿混在一起。
- Learn 可以跨轮推进学习项目，但只有用户明确触发时才进入。

## 从 1.7.4 升级到 2.0：用户会感知到什么

| 变化 | 1.7.4 | 2.0 |
|---|---|---|
| 主定位 | 内容生产调度器 | 创作者工作台 |
| 默认入口 | 围绕创作模块分流 | 仍默认创作，但先判断任务层级 |
| 商单 Brief | 在主流程中处理 | `eva-brief` 独立入口，生成约束资产后交回主链路 |
| 学习项目 | 容易和资料转内容混在一起 | `eva-learn` 独立入口，明确区分“学懂资料”和“直接做内容” |
| 模块交接 | 依赖上下文理解 | 通过 Eva Asset 和 handoff 规则承接 |
| 本地私有模块 | 不作为正式系统能力 | 用 Eva Link 接入 |
| 前台体验 | 更像一个写作助手 | 普通任务保持轻交互，复杂任务才展示系统状态 |

## 旧用法还在吗

还在。

原来 1.7.4 的核心创作能力仍然保留：

- 想法归位：`/eva-think`
- 话题人群判断：`/eva-audience-finder`
- 标题搜索和标题判断：`/eva-title`
- 开头、第一句话、前三秒：`/eva-script` 或开头分支
- 正文路线图和正文撰写：`/eva-script`
- 商单内容创作：仍回到 Eva 主创作链，但必须先有 Brief / 商单约束
- 表达真实性审查：`/eva-ai-check`
- 点子、人设、文风沉淀：`/eva-memory`

2.0 不是替换旧创作链，而是给旧创作链加上更清楚的任务边界、资产承接和 Link 接入能力。

## 什么时候用哪个入口

| 用户想做什么 | 应该用 |
|---|---|
| “帮我想想这个选题 / 这个问题怎么讲” | `eva` |
| “这个话题讲给谁 / 戳中谁” | `eva` -> Audience |
| “帮我搜标题 / 判断标题 / 正文标题补强” | `eva` -> Title |
| “帮我写开头 / 第一句 / 前三秒 / 完整视频稿” | `eva` -> Script |
| “帮我拆品牌 Brief / 生成商单约束卡 / 检查商单稿能不能交” | `eva-brief` |
| “用 Eva Learn 带我读 / 做主题式阅读 / 继续学习项目” | `eva-learn` |
| “把这个提示词接进 Eva / 做一个自己的 Link” | `eva-link-builder` |
| “检查本地 Link / 升级后还能不能用” | `eva-link-doctor` |

## 2.0 的工程边界

Eva 2.0 的工程结构围绕“主 Skill + 两个薄入口 + 协议和校验脚本”组织。

```text
skills/
├── eva/              # 主创作工作台
├── eva-brief/        # 独立商单 Brief 薄入口
└── eva-learn/        # 独立学习项目薄入口
```

`skills/eva/` 内部的关键目录：

```text
references/
├── entry/            # 主入口路由真源
├── harness/          # Assist Harness：状态、交接、失败分类、完成前验证
├── asset/            # Eva Asset：资产卡协议
├── shared/           # 交接卡、低置信度、商单约束、轻交互等共享真源
├── create/           # 创作主链路
├── think/            # 想法归位和问题重构
├── memory/           # 点子、人设、文风资产保存和回捞
└── link/             # Eva Link 本地模块连接
```

工程目录只是维护索引，不是用户理解 2.0 的主线。

## 2.0 的约束

- Link 是显式系统能力，不会自动进入普通创作任务。
- `eva-brief` 和 `eva-learn` 是独立薄入口，但不维护第二套规则；它们读取 sibling `eva` 的真源。
- 商单内容不能跳过 Brief / 商单约束卡。
- 完整正文不能跳过标题或第一句话验证，也不能跳过正文路线图。
- 用户资产、学习项目、Link registry 不写进 Skill 仓库本体；保存必须由用户明确触发。
- 普通前台不展示 Harness、schema、valid_next、DoD、failure-record 等后台字段。

## 验证

从本目录运行：

```text
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-learn
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-brief
python3 skills/eva/scripts/eva_doctor.py --base skills/eva
python3 skills/eva/scripts/eva_prompt_lint.py --base skills/eva
python3 skills/eva/scripts/eva_selftest.py --base skills/eva
python3 skills/eva/scripts/eva_asset_validate.py --asset skills/eva/examples/asset-card.example.json --downstream eva-create
python3 skills/eva/scripts/eva_link_check.py --link skills/eva/examples/eva.link.example.json
python3 skills/eva/scripts/eva_link_check.py --link skills/eva/examples/local.weibo-copy/ --strict
python3 skills/eva/scripts/eva_asset_validate.py --asset skills/eva/examples/local.weibo-copy/tests/expected-asset.example.json --downstream eva-memory
PYTHONPYCACHEPREFIX=/private/tmp/eva-harness-pycache python3 -m py_compile skills/eva/scripts/*.py
```

`eva_link_check.py` 不带 `--strict` 只校验 Link config。正式挂载用户 Link 时，应对完整 Link 目录运行：

```text
python3 skills/eva/scripts/eva_link_check.py --link local-modules/{link-id}/ --strict
```

## 发布前检查

- README 首屏是否讲清楚 1.7.4 -> 2.0 的升级价值。
- `eva`、`eva-brief`、`eva-learn` 是否都能通过 quick validate。
- Assist Harness、Eva Asset、Link 的 schema 和脚本是否通过校验。
- `eva_prompt_lint.py` 是否通过，确认字段表没有重新散落到模块文件。
- 未经用户明确触发，不应把用户资产、学习项目或 Link registry 写进 Skill 仓库。
