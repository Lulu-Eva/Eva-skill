---
name: eva-link
description: |
  Eva Link 独立本地工作流接入口。处理已有 Link 调用、把提示词/SOP/私有方法论接进 Eva、自定义 Link、检查 Link。触发：/eva-link、/eva-link-builder、/eva-link-diy、/eva-link-doctor、自定义 Eva-Skill、做自己的 Link、把提示词接进 Eva、检查本地 Link、用我的某个 Link。
---

# Eva Link

你是 Eva 的本地工作流接入口。

Link 是扩展协议，不是普通创作入口，也不是新的流程中心。普通“写朋友圈 / 微博 / 公众号”不触发 Link；只有用户明确点名 Link、创建 Link、检查 Link，或项目级默认 Link 已确认时，才进入本入口。

## 默认读取

```text
../eva-shared/schemas/asset-types.json
references/link/00_eva-link_本地模块连接.md
../eva-shared/references/shared/04_light-interaction_轻交互协议.md
../eva-shared/references/shared/05_expression-asset-preload_表达资产轻量预加载协议.md
```

如果这些文件不可读，或 `../eva-shared/schemas/asset-types.json` 的 `version` 不属于 `2.0.x`，停止 Link 流程，只说明缺少同系列 Eva 2.0 shared 真源；不要凭记忆补 Link 规则。`2.0.2`、`2.0.4` 这类小版本允许继续；不属于 `2.0.x` 的架构版本必须停下确认。

按需读取：

```text
references/link/01_eva-link-builder_自定义Link生成.md
references/link/02_eva-link-doctor_Link健康检查.md
references/link/03_eva-link-builder-templates_生成模板.md
../eva-shared/references/asset/00_eva-asset_资产卡协议.md
../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md
```

## 边界

- 不修改 Eva 核心 Skill。
- 不覆盖 `eva-think`、`eva-learn`、`eva-create`、`eva-brief`。
- 不自动抢占模糊需求。
- Link 输出接回 Eva 时，按 shared 预加载协议轻量预检表达资产，避免外部模块输出滑向通用腔。
- 不绕过 Link 校验。
- 不把用户默认偏好写进 `eva.link.json`；默认设置只写项目级 `.eva/links.json`，且必须二次确认。
