# Eva Link：本地模块连接

Eva Link 不是“多一个功能”，而是本地模块接入 Eva 资产流的协议。

用户口头说“自定义 Eva-Skill / 自定义 Link / 定制 Eva-Skill / 做自己的 Eva-Skill”时，默认指自定义 Eva Link。Link 是用户工作流接入层，不是新建 sibling Skill。普通“写朋友圈 / 微博 / 公众号”不触发 Link；只有显式点名 Link、项目级默认 Link 命中，或用户当场确认，才进入 Link。

它解决的问题：

```text
公开 Eva 核心保持稳定；
内部模块、创作者私有模块、用户自定义模块通过协议接入；
所有输出仍可被 Memory / Create 继续承接。
```

Link 属于 `references/shared/04_light-interaction_轻交互协议.md` 允许显性 Harness 的系统任务。可以展示配置检查、缺字段和交接失败原因，但仍只说明必要字段，不把普通创作任务升级成 Link 界面。

本文件只维护运行时协议：识别、校验、调用、交接。创建 Link 读取 Builder，检查 Link 读取 Doctor；不要把 Builder / Doctor 细节复制回本文件。

## Link 不能做什么

- 不修改 Eva-Skill 本体。
- 不覆盖 `/eva-think`、`/eva-learn`、`/eva-create` 等核心入口。
- 不自动抢占模糊需求。
- 不绕过资产卡协议。
- 不绕过用户确认保存隐私资产。
- 不直接调用另一个 Link。

## 最小结构

推荐本地结构：

```text
运行项目/
├── .eva/
│   └── links.json
└── local-modules/
    └── local.weibo-copy/
        ├── eva.link.json
        └── module.md
```

Skill 仓库只放协议和脚本，不保存用户私有模块。

## eva.link.json

`eva.link.json` 只声明模块能力：它接收什么、需要什么、产出什么、能交给谁、用户可以怎样显式点名它。不要在这里保存“以后写朋友圈默认用我”这类用户偏好。

最小字段：

```json
{
  "id": "local.weibo-copy",
  "name": "微博文案",
  "scope": "create",
  "version": "1.0.0",
  "accepts": ["thought-seed-card", "judgment-version-card", "audience-card"],
  "requires": ["核心判断", "目标读者", "发布平台"],
  "produces": ["content-asset-card"],
  "handoff_to": ["eva-memory"],
  "entry_aliases": ["微博文案"]
}
```

Schema 真源：`schemas/eva-link.schema.json`。

## .eva/links.json

`.eva/links.json` 是项目级 Link registry，只保存用户在当前项目里启用了哪些 Link，以及哪些创作意图被用户二次确认设为默认。它不放在 Skill 仓库本体里。

最小结构：

```json
{
  "version": "1.0.0",
  "links": [
    {
      "id": "local.weibo-copy",
      "path": "local-modules/local.weibo-copy",
      "enabled": true
    }
  ],
  "defaults": []
}
```

Schema 真源：`schemas/link-registry.schema.json`。

设置默认 Link 的唯一合法时机：Link 已生成、strict 校验通过、用户试跑或看过定义后，用户明确回答“以后默认 / 设成默认 / 是”。不能在创建 Link 时顺手默认。

用户二次确认默认后，才允许追加：

```json
{
  "intent": "写微博短文案",
  "link_id": "local.weibo-copy",
  "confirmed": true,
  "confirmed_at": "2026-07-04T10:00:00+08:00",
  "confirmed_phrase": "以后说写微博短文案时，默认走 local.weibo-copy"
}
```

检查命令：

```text
python3 scripts/eva_link_check.py --link examples/eva.link.example.json
python3 scripts/eva_link_check.py --link local-modules/local.weibo-copy/
python3 scripts/eva_link_check.py --link local-modules/local.weibo-copy/ --strict
python3 scripts/eva_link_check.py --registry .eva/links.json
python3 scripts/eva_link_check.py --link local-modules/local.weibo-copy/ --strict --registry .eva/links.json
```

不带 `--strict` 只表示 Link config 字段合法，不表示 Link 模块完整可运行。正式挂载或升级前必须使用 `--strict`。

## 调用流程

```text
用户明确指定 Link 名称 / id / entry_alias
-> 读取 Link registry
-> 运行 eva_link_check.py --strict
-> 检查当前资产是否在 accepts
-> 检查 requires 是否完整
-> 若非已确认默认 Link，先确认调用；已确认默认 Link 只轻提示
-> 读取 module.md
-> Link 输出 produces 声明的资产
-> 运行资产交接校验
-> 交给 Memory / Create，或停在 Link 内修正
```

默认 Link 命中时：

```text
用户说出 registry.defaults.intent
-> 检查该 default 已 confirmed
-> 检查 link_id 已 enabled
-> 轻提示“我按你默认的「{Link name}」来写”
-> 继续执行上面的 strict Link 调用流程
```

无默认但存在可能匹配的 Link 时，只问一个选择：

```text
你想走 Eva 普通创作链路，还是用你已经做好的「{Link name}」？
```

用户只说“写朋友圈 / 写微博 / 写公众号”时，不能因为本地存在同名 Link 就自动调用。

## 冲突处理

| 场景 | 处理 |
|---|---|
| Link id 或 entry_aliases 覆盖核心入口 | 禁止挂载 |
| Link 和核心模块都能处理 | 无明确指定时优先核心模块 |
| 用户明确指定 Link | 进入 Link，但仍检查资产和缺字段 |
| 用户命中已确认默认 Link | 轻提示后进入 Link，不再反复追问 |
| 用户未设默认但有相关 Link | 只问普通创作链路还是该 Link |
| Link 缺 accepts / produces / handoff_to | 禁止交接 |
| Link 输出自由文本 | 要求转成标准资产卡 |
| Link 涉及隐私保存 | 必须用户确认 |

## Link 输出要求

Link 输出必须能被 Eva Asset 承接。字段真源读取 `references/asset/00_eva-asset_资产卡协议.md` 和 `schemas/asset-card.schema.json`；本文件不维护第二套资产字段表。

运行时前台只显示：

```text
完成了什么：
缺失字段：
建议交给谁：
```

如果输出不符合 `produces`，不能交给下游。

完整资产字段只在 Link 创建、检查、校验失败、写入 Memory 或用户要求查看时展开。

## Link 子能力

| 用户意图 | 读取 |
|---|---|
| 创建自定义 Link、把提示词/SOP/私有方法论接进 Eva、用户说 `eva-link-diy` 或“自定义 Eva-Skill / 定制 Eva-Skill / 做自己的 Eva-Skill” | `references/link/01_eva-link-builder_自定义Link生成.md` |
| 检查已有 Link、升级后能不能用、Link 为什么不能交接 | `references/link/02_eva-link-doctor_Link健康检查.md` |

Link 不出现在默认创作启动提示里；只有用户明确触发或确认后进入。
