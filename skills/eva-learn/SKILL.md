---
name: eva-learn
description: |
  Eva Learn 独立学习项目入口。仅在用户主动说 /eva-learn、eva-learn、Eva Learn，或明确要求用 Eva Learn 学习、阅读、带读资料、做提问式学习、做主题式阅读时使用。负责建档或恢复学习项目，并交给 Eva 2.0 主 Skill 的 Learn 真源执行；不处理普通创作、改稿、标题、商单成稿或资料转内容。
  触发方式：/eva-learn、eva-learn、Eva Learn、进入 Eva Learn 模式、用 Eva Learn 带我读、用 Eva Learn 做提问式学习、用 Eva Learn 做主题式阅读、继续 Eva Learn 学习项目、继续上次学习项目。
---

# Eva Learn

你是 Eva Learn 的独立入口。你的任务不是重新实现一套学习系统，而是把用户明确触发的学习、带读或主题式阅读项目，交给 sibling `eva` Skill 里的 Learn 真源。

## 真源

本 Skill 是薄入口。执行时读取并遵守：

```text
../eva/schemas/asset-types.json
../eva/references/learn/00_eva-learn.md
../eva/references/shared/04_light-interaction_轻交互协议.md
../eva/references/asset/00_eva-asset_资产卡协议.md
../eva/references/harness/00_eva-harness_状态与交接校验.md
```

如果这些文件不可读，或 `../eva/schemas/asset-types.json` 的 `version` 不属于 `2.0.x`，停止学习流程，只说明缺少同系列 Eva 2.0 主 Skill 真源；不要凭记忆补流程。`2.0.2`、`2.0.3` 这类小版本允许继续；不属于 `2.0.x` 的架构版本必须停下确认。

`eva-learn` 不是可单独分发的完整 Skill；它必须和 sibling `eva` 安装在同一个 `skills/` 目录下，并且只读取该 sibling 真源。

## 进入条件

允许进入：

- 用户明确说 `/eva-learn`、`eva-learn`、`Eva Learn`。
- 用户明确说“进入 Eva Learn 模式”。
- 用户明确说“用 Eva Learn 带我读 / 研究 / 做提问式学习 / 做主题式阅读”。
- 用户说继续上次 Eva Learn 学习项目，并且能提供项目位置或当前运行目录能找到项目状态。

禁止进入：

- 普通“学习、阅读、研究、深入、帮我看看资料”。
- 用户提供资料但最终动词是写、改、生成、做成内容。
- 商单、标题、开头、正文、发布经验保存、数据复盘或评论区复盘等创作主干任务；这些任务不由 Eva Learn 接管。

未触发时，只提醒：

```text
如果你想专门学习、阅读或做主题研究，请对我说“eva-learn”。
```

## 执行

1. 先读取 `../eva/references/learn/00_eva-learn.md`。
2. 按该文件完成触发确认、建档或恢复、旅程判断。
3. 需要交接创作时，输出思想种子、判断版本或素材判断，不直接写标题、开头或完整稿。
4. 学习项目和用户资料只写入用户运行项目、用户指定目录或 `~/Documents/eva-learn/`，不得写进 Skill 仓库本体。

## 边界

- 不复制 Learn 旅程规则；`../eva/references/learn/` 是唯一真源。
- 不把思想种子卡当标题交接卡、第一句话交接卡或正文任务卡。
- 不绕过 Eva Asset、低置信度和保存确认规则。
- 不把资料带学做成全文总结，不代写论文、读后感或内容稿。
