# Eva Link Builder：自定义 Link 生成

Eva Link Builder，也可以被用户口头叫作 `eva-link-diy`。正式名称用 `eva-link-builder`，因为它的任务不是“自己写提示词”，而是把用户的 prompt、SOP、方法论或私有工作流包装成合规 Eva Link。

Builder 是显性系统任务，允许展示结构、字段和校验结果；但它只在用户明确创建自定义 Link 时启动，不参与普通创作、标题、开头、复盘或点子沉淀。

用户说“自定义一个 Eva-skill”“自定义 Link”“定制 Eva-skill”“做自己的 Eva-skill”时，按产品语义解释为“创建自定义 Eva Link”。不要把这类请求路由到通用 Skill Creator，也不要建议新建 `eva-*` sibling Skill，除非用户明确说要开发一个不接入 Eva Link 的独立 Skill。

普通创作意图不能触发 Builder。用户只说“我想写朋友圈 / 微博 / 公众号”“我不想写口播，只想写朋友圈”时，仍走 Eva 创作链路。只有用户明确补充“把这套流程自定义成 Eva-skill / Link / 以后复用”时，才进入 Builder。

## 定位

```text
输入：用户的私有流程、提示词、SOP、方法论、样例或口述需求
输出：local-modules/{link-id}/eva.link.json + module.md + tests/
目标：可校验、可交接、可升级
```

Builder 不做正式内容生产，不替 Link 承接用户创作任务。它先引导用户把模糊习惯定义成清楚的 Link，再把这个工作流做成合规模块；生成后只允许做校验性试跑。

核心原则：

```text
先定义用户真正想要的创作工作流
-> 再确认 Link 定义卡
-> 最后生成本地 Link 文件
```

用户刚说“我想自定义一个 Eva-skill”时，不要立刻生成文件，不要进入通用 Skill 创建教程。先问：

```text
你想自定义一个什么样的 Link？

比如：朋友圈、微博短文字、公众号长文、商单复盘、直播脚本、播客大纲。
先说你主要用它做什么，我会一步步把它定义成本地 Eva Link。
```

如果用户只是要调用已有 Link，回到 `references/link/00_eva-link_本地模块连接.md`。本文件不维护完整触发词清单；入口路由以 `../eva/SKILL.md` 为准。

## 交互式定义流程

Builder 的前台体验是“访谈式定义”，不是“表单一次性填完”。一次只问会影响下一步判断的问题。

### 第 1 步：确认 Link 场景

先问用户要自定义什么工作流：

```text
你想自定义一个什么样的 Link？
```

如果用户已经说清场景，比如“朋友圈”“微博”“公众号”“行业案例”，不要重复问场景，直接进入第 2 步。

### 第 2 步：收集真实样本

如果用户说的是表达类 Link，比如朋友圈、微博、公众号、短文案，必须优先收样本。

前台问法：

```text
把你以前写得比较像自己的 3-5 条样本发我。

我会从里面提取：
- 长度范围；
- 句子节奏；
- 开头方式；
- 常用结构；
- 不能丢的表达习惯；
- 明确不要出现的口吻。
```

如果用户已经给了样本，直接进入样本拆解，不要再要求“先填完整字段”。

### 第 3 步：提炼 Link 定义卡

拿到场景和样本后，先输出 Link 定义卡，让用户确认，不直接生成文件。

```text
Link 定义卡：
模块名称：
用户会怎么叫它：
主要平台 / 场景：
目标长度：
输入材料：
输出形态：
必须保留的表达习惯：
不要做什么：
接收哪些 Eva 上游资产：
输出交给 Eva 的哪个下游：
还缺什么：
权限说明：要读哪些材料、写到哪里、是否联网、是否保存用户数据
```

定义卡必须用用户语言写，不要把用户一上来就推到 `accepts / produces / handoff_to` 这些字段里。机器字段只在生成文件时转换。

### 第 4 步：确认后再生成

只有用户确认定义卡，或者用户明确说“按这个生成 / 直接做成本地 Link”，才进入文件生成。

如果定义卡还有关键缺口，只问一个最影响质量的问题。不要因为缺少进阶字段就停住；可以先用低置信度草案，但必须标注缺口。

### 第 5 步：试跑或检查

文件生成后，不要马上设为默认。先做两件事：

```text
1. 运行 strict Link 校验，包括模块夹带指令检查和权限检查。
2. 让用户选择试跑一次，或直接查看 Link 定义卡。
```

前台问法：

```text
这个 Link 已经生成并通过基础检查。
权限：{read_scope / write_scope / network / save_user_data 的人话摘要}

下一步你要先试跑一次，还是直接启用？
```

如果用户选择试跑，用用户给的样本或一条最小输入跑出 `content-asset-card` 草案，并明确标注“仅用于校验 Link，不是正式创作结果”。如果用户选择直接启用，只写入 `.eva/links.json` 的 `links`，不写默认项。

### 第 6 步：启用 Link

启用只表示这个项目以后可以调用该 Link，不等于默认调用。

写入项目级 `.eva/links.json`：

```json
{
  "links": [
    {
      "id": "local.private-moments",
      "path": "local-modules/local.private-moments",
      "enabled": true,
      "approved_sha256": "<strict 校验输出的 data.link_sha256>",
      "approved_at": "<用户确认时间>",
      "approved_phrase": "我确认启用 local.private-moments 的当前版本和权限"
    }
  ]
}
```

如果 `.eva/links.json` 已存在，只追加或更新对应 `links` 记录，不覆盖其他 Link 和 defaults。

### 第 7 步：二次确认默认 Link

只有在 Link 已启用后，才能追问默认设置。不能在 Link 定义卡阶段提前问。

前台问法：

```text
以后你说“{intent}”时，默认走「{Link name}」吗？

如果你不设默认，以后仍然可以说“用我的 {Link name} Link 写这条”来调用它。
```

用户明确回答“是 / 以后默认 / 设成默认”后，才写入 `.eva/links.json` 的 `defaults`：

```json
{
  "intent": "写朋友圈",
  "link_id": "local.private-moments",
  "confirmed": true,
  "confirmed_at": "2026-07-04T10:00:00+08:00",
  "confirmed_phrase": "以后说写朋友圈时，默认走 local.private-moments"
}
```

用户没有明确确认时，只启用 Link，不设置默认。

### 朋友圈 Link 示例

当用户明确说“自定义 Eva-skill / 自定义 Link”，并且场景是：

```text
我大部分时间是用来写朋友圈的。
我不想写口播，我就想写朋友圈。
我的朋友圈大概 200 字左右，希望 200 字能写清楚。
这是我以前写的朋友圈，你帮我定义成一个 Eva-skill。
```

Builder 应该理解为：

```text
目标：创建朋友圈本地 Link
不是：创建新的 eva-* sibling Skill
不是：写一条朋友圈成品
```

前台应该这样接：

```text
这是在做朋友圈 Link。

你先发 3-5 条你以前写过、自己觉得最像你的朋友圈。
我会先把它们拆成一张 Link 定义卡：长度、结构、语气、开头方式、结尾方式、不要出现的口吻。
定义卡确认后，我再把它做成本地 Eva Link。
```

如果用户已经发了样本，就输出朋友圈 Link 定义卡：

```text
Link 定义卡：
模块名称：朋友圈短文案
用户会怎么叫它：朋友圈 / 朋友圈 Link / 我的朋友圈
主要平台 / 场景：微信朋友圈
目标长度：约 200 字
输入材料：Eva 的思想卡、点子卡、文风卡，或用户临时给的想法
输出形态：一条可直接发朋友圈的短文案
必须保留的表达习惯：从样本中提炼
不要做什么：不写口播腔、不拉长成文章、不编造经历
接收哪些 Eva 上游资产：thought-seed-card、idea-card、voice-card、persona-card
输出交给 Eva 的哪个下游：eva-memory 或 eva-create
还缺什么：样本不足时标注
```

## 问题清单

一次只问会阻塞结构判断的问题。不要把下面清单一次性甩给用户。

必须最终拿到，但不要求第一轮全部问完：

```text
模块名称：
用户会怎么叫它：
解决什么问题：
不解决什么问题：
输入材料是什么：
输出应该是什么：
输出交给 Eva 的哪个下游：
成功样例：
失败样例或不要做什么：
是否涉及隐私、商业秘密、内部资料：
需要读取什么范围：
需要写入哪里：
是否需要联网：
是否需要保存用户数据：
```

进阶字段：

```text
接收哪些上游资产 accepts：
缺少哪些信息 requires：
输出哪种资产 produces：
可以交给哪些下游 handoff_to：
适配 Eva 版本范围：
```

## link-id 规则

生成 `id` 时：

```text
local.{short-name}
```

规则：

- 只用小写字母、数字、点、横线。
- 不使用 `eva`、`eva-learn`、`eva-think`、`eva-create`、`eva-memory`、`eva-link`。
- 不用过宽泛名称，比如 `local.writer`、`local.content`。
- 名称要表达具体工作流，例如 `local.weibo-copy`、`local.private-moments`、`local.b2b-case-study`。

## 生成模板

只有用户确认定义卡并要求生成本地文件时，才读取 `references/link/03_eva-link-builder-templates_生成模板.md`。访谈阶段不要默认加载模板文件。

## 构建流程

```text
1. 判断用户是要调用 Link，还是创建 Link。
2. 用访谈方式确认 Link 场景。
3. 表达类 Link 优先收集 3-5 条真实样本。
4. 提炼并输出 Link 定义卡。
5. 等用户确认定义卡；未确认前不生成文件。
6. 生成 link-id。
7. 生成带最小 `permissions` 的 eva.link.json。
8. 生成 module.md。
9. 生成 input.example.md 和 expected-asset.example.json。
10. 运行 link check。
11. 运行 asset validate。
12. 引导用户试跑或查看定义。
13. 向用户展示一次 Link 定义和权限摘要；用户确认后，把 strict 输出的 `data.link_sha256`、确认时间和用户确认语与 enabled Link 一起写入 `.eva/links.json`。
14. 二次确认是否设置默认；确认后才写入 `.eva/links.json` 的 defaults。
15. 输出安装位置、显式调用方式、默认状态、可交接下游、低置信度限制。
```

## 完成定义

Builder 完成必须满足：

```text
eva.link.json 能通过 strict Link 校验。
module.md 明确解决/不解决什么。
tests/input.example.md 存在。
tests/expected-asset.example.json 能通过资产校验。
Link 没有覆盖核心入口。
Link 已声明最小权限，模块内容无夹带指令或隐藏动作。
当前 `link_sha256` 已在用户确认后写入 registry；未确认前不标记 enabled。
输出资产能交给至少一个下游。
隐私或商业秘密已标注。
启用状态写入项目级 `.eva/links.json`，而不是写入 `eva.link.json`。
默认 Link 已有用户二次确认；没有确认就不能出现 defaults。
```

不满足时不能说“Link 已完成”，只能说“Link 草案已生成”。
