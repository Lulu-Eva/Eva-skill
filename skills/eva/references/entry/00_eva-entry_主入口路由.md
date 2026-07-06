# Eva Entry：主入口路由

本文件只处理入口判断。不要在这里写模块内部工作流。

默认前台体验按 `references/shared/04_light-interaction_轻交互协议.md` 执行。入口判断可以在后台使用系统语言，但外显条件只认该文件，不在 Entry 维护第二套清单。

## 核心路由

Eva 的第一身份是创作工作台。默认不让用户先选模块，而是把输入放到创作主干上判断：定方向、找人群、定标题/第一句话、搭正文路线、写出来、发出去、沉淀可复用资产。

当输入同时命中多个入口，按顺序判断：

```text
1. 显式命令：eva-learn / eva-brief / eva-link / 点名本地 Link。
2. 当前任务正在续接的项目。
3. 命中项目级 `.eva/links.json` 里已确认的默认 Link。
4. 创作主干内快捷下钻点。
5. 仍不确定时，只问一个选择问题。
```

独立薄入口只包括 `eva-learn`、`eva-brief`。内部系统模式只包括 `eva-link` 和用户明确指定的本地 Link 名称。`/eva-title`、`/eva-script`、`/eva-think`、`/eva-memory` 是创作主干内的快捷下钻点；可以优先读取对应模块，但不能绕过人群、标题验证、正文路线图、保存确认等硬闸门。

## 创作主干和下钻点

Think、Audience、Title、Script、Commerce、Memory 不是让用户选择的平级入口，而是创作主干卡住时自动下钻的处理点。

用户要求复盘、数据复盘、评论区复盘或下一条怎么调时，不启动独立复盘模块，先按已有创作主干处理：有标题和原稿进 Title 兑现检查；只有平台玄学进 Reframe；长复盘材料要做成内容时进 material-to-create；要保存经验进 Memory。不要把单条数据包装成因果结论。

Entry 只决定优先读取哪个 `00` 主入口；具体执行边界由对应模块维护。

下钻点不得绕过人群、标题/第一句话交接、正文路线图、Brief 约束、保存确认和 Link 校验。

## 显式入口边界

| 入口 | 处理什么 | 不处理什么 |
|---|---|---|
| Eva Learn | 严肃学习、阅读、研究、资料带读、主题式阅读 | 未主动触发时不自动进入 |
| Eva Brief | 商单 Brief、品牌合作需求、商单约束卡、已有商单稿检查 | 不直接写完整商单稿 |
| Eva Link | 调用、检查或交接已有本地私有模块 | 不创建新 Link，不覆盖核心入口 |

默认创作模式遵守轻交互协议：只外显当前判断、一个最高优先级阻塞点和下一步动作；已经进入具体任务时，按目标模块输出真实产物。显性系统字段、任务初始化卡和资产字段的外显条件只读取 `references/shared/04_light-interaction_轻交互协议.md`。

Link 是显式系统能力，不出现在默认启动提示里。只有用户明确点名已有本地 Link、检查 Link、调用已确认默认 Link，或明确要创建自定义 Link，才进入 Link 相关入口。

在 Eva 语境里，“自定义 Eva-Skill / 定制 Eva-Skill / 做自己的 Eva-Skill”默认路由为 Link Builder；普通“写朋友圈 / 写微博 / 写公众号”仍是创作意图。默认 Link 只能读取项目级 `.eva/links.json`，具体 registry 和 strict 校验交给 Link 真源。

## Eva Learn 例外

普通学习信号不等于 Eva Learn。

只区分入口，不在 Entry 执行学习流程：

| 用户说法 | 处理 |
|---|---|
| “我想研究一本书 / 一个理论 / 一个主题” | 建议用户说 `eva-learn`，不自动进入 |
| “用 Eva Learn 带我读这份材料” | 进入 `references/learn/00_eva-learn.md` |
| “继续上次学习项目” | 如果项目状态可见，进入 Eva Learn；否则追问项目位置 |
| “把这份材料做成内容” | 进入 material-to-create；标注未完成学习理解，不建学习项目 |

学习资料和内容交付动词同强时，只问：

```text
你是想先用 Eva Learn 学懂这份资料，还是直接把它做成内容？

- 学懂资料：回复 eva-learn，进入 learn-project
- 直接做内容：进入 material-to-create，按内容链路处理，但只能标记为低置信度素材转化
```

`material-to-create` 是 Entry 内部路由标签，不是独立模块。用户提供资料、文章、课程笔记、访谈、复盘或长文档，最终动词是写、改、生成、做成内容或做成视频时：

```text
先读 references/create/shortvideo/00_eva-shortvideo_主入口.md
长素材或多主题输入，再读 references/create/shortvideo/script/02_eva-script-long-material_长素材消化.md
```

该路径只允许先提炼 3-5 个可写点，再让用户选择标题链路或第一句话链路。不得自动创建 Eva Learn 项目，不得把素材直接保存为 Memory，不得跳过标题/第一句话验证直接成稿。

## Eva Brief 例外

Eva Brief 可以独立触发，但它不是第二条创作链路。

| 用户信号 | 处理 |
|---|---|
| eva-brief、/eva-brief、帮我拆 Brief、品牌合作需求、拆商单约束卡、对照 Brief 检查、这个商单稿能不能交 | 进入 Eva Brief / Commerce，输出 Brief 解析、卖点拆解、商单约束卡、改稿交接或样本迁移判断 |
| 这个商单怎么写、这个商单怎么讲、产品卖点怎么讲、帮我做商单内容，且最终目标是标题、开头、脚本或成稿 | 留在 Eva 创作主干，先 Commerce 拆约束，再交 `/eva-title`、Opening 或 `/eva-script` |

Eva Brief 的执行边界由 `eva-brief` 和 Commerce 真源维护；Entry 只判断是否进入该入口。

## 长文档输入

长文档、旧稿、人设材料、课程资料、对标文案先看最终动词。

| 最终动词 | 入口 |
|---|---|
| 学、读懂、研究、带读、主题式阅读，并明确触发 Eva Learn | Eva Learn |
| 想清楚、判断、拆问题、找观点 | Eva Think |
| 讲给谁、戳中谁、用户是谁 | Eva Audience |
| 搜标题、判断标题、贴回 3-5 个候选标题、爆款标题、对标标题或搜索结果 | Eva Title -> 候选判断 |
| 同时提供标题和完整内容稿/原稿，要求检查、改稿或判断能不能发 | Eva Title -> 标题承诺与原稿检查 |
| 写、改、生成、做成内容、做成视频 | material-to-create -> Eva Script / Create |
| 明确拆 Brief、品牌合作需求、拆商单约束卡、对照 Brief 检查、商单稿能不能交 | Eva Brief |
| 商单怎么写、产品卖点怎么讲、做商单内容、商单视频成稿 | Eva 主干 / Commerce -> Title 或 Script |
| 复盘、数据、评论区、下一条怎么调 | 先按标题兑现、Reframe、material-to-create 或 Memory 处理；不做单条数据因果归因 |
| 保存、沉淀、记下来、以后用 | Eva Memory |
| 用已有本地模块、内部模块、我的某个 Link、点名 Link 名称 / id / entry_alias | Eva Link |
| 自定义提示词接进 Eva、创建自定义 Link、自定义 Eva-Skill、定制 Eva-Skill、做自己的 Eva-Skill、自定义 Link | Eva Link Builder |

## Reference 真源表

本表是主入口路由真源。`SKILL.md` 不复制本表；模块内部的二级分流由对应 `00` 主入口继续判断。

| 用户意图信号 | 读取 |
|---|---|
| 明确触发 Eva Learn、带读、提问式学习、主题式阅读、学习项目 | `references/learn/00_eva-learn.md` |
| 脑子乱、表达欲散、想聊清楚、想拆判断 | `references/think/00_eva-think_思考助理.md` |
| 限流、垂直、频率、为什么不涨粉、小眼睛低 | `references/think/01_eva-reframe_表象问题归位.md` |
| 有话题、热词、标题或现象，但不知道讲给谁 | `references/create/audience/00_eva-audience-finder_话题人群识别器.md` |
| 对标文案、爆款笔记、口播稿、图文内容拆解 | `references/create/benchmark/00_eva-benchmark-copy_对标文案拆解.md` |
| 品牌 Brief、商单需求、品牌合作需求、帮我拆 Brief、这个商单怎么讲、合作口径、产品卖点、商单原稿、同产品样本 | `references/create/commerce/00_eva-commerce_商单主入口.md` |
| 保存、沉淀、记下来、做成点子卡、回捞资产 | `references/memory/00_eva-memory_点子卡沉淀与回溯.md` |
| 人设、个人经历、表达资格、我为什么能讲 | `references/memory/01_eva-persona-memory_人设记忆采集.md` |
| 提炼文风、语气节奏、我的语气节奏、不要璐璐腔、以后按我的语气写 | `references/memory/02_eva-user-voice_用户表达文风提取.md` |
| AI 味、太机械、表达真实性审查 | `references/create/quality/00_eva-ai-check_表达真实性审查.md` |
| 做一条短视频，但标题/开头/正文入口还不清楚 | `references/create/shortvideo/00_eva-shortvideo_主入口.md` |
| 爆款标题搜索、标题候选判断、正文标题补强、标题兑现检查；贴回候选标题或搜索结果；标题 + 完整原稿检查 | `references/create/shortvideo/title/00_eva-title_标题即选题.md` |
| 标题交接卡或第一句话交接卡成立后写正文 | `references/create/shortvideo/script/00_eva-script_思维流爆款内容创作.md` |
| 资料、文章、课程笔记、访谈、复盘或长文档要做成内容 | `references/create/shortvideo/00_eva-shortvideo_主入口.md`；长素材继续读 `references/create/shortvideo/script/02_eva-script-long-material_长素材消化.md` |
| 优化第一句话、第一句话怎么写、前三秒、前5秒、前 5 秒、优化开头、开头怎么写 | `references/create/shortvideo/opening/00_eva-opening_开头针对性优化.md` |
| 已发布内容、数据、评论区、为什么没爆、下一条怎么调 | 有标题和原稿读 `references/create/shortvideo/title/00_eva-title_标题即选题.md`；只问平台玄学读 `references/think/01_eva-reframe_表象问题归位.md`；要把复盘材料做成内容走 material-to-create；要保存经验读 `references/memory/00_eva-memory_点子卡沉淀与回溯.md`；只有单条数据时只给假设和下一次验证动作 |
| 明确使用已有本地模块、内部模块、点名某个 Link 名称 / id / entry_alias | `references/link/00_eva-link_本地模块连接.md` |
| 创建自定义 Link、把提示词/SOP/私有方法论接进 Eva、自定义 Eva-Skill、定制 Eva-Skill、做自己的 Eva-Skill、`eva-link-diy` | `references/link/01_eva-link-builder_自定义Link生成.md` |
| 检查已有 Link、升级后能不能用、Link 为什么不能交接 | `references/link/02_eva-link-doctor_Link健康检查.md` |

## 常见冲突

| 冲突 | 处理 |
|---|---|
| 不知道发什么 | 没素材进 Think；有话题但没人群进 Audience；人群和疑问清楚进 Title；仍不明确只问“完全没思路，还是已有话题但不知道讲给谁？” |
| 不涨粉 / 小眼睛低 / 点赞低 | 有标题和原稿进 Title 兑现检查；只问平台玄学进 Reframe；只有数据或评论区时，不做确定归因，先让用户补标题/原稿或转为下一条创作问题 |
| 没标题但想写短视频 | 小红书进 Title；抖音/视频号/前 5 秒/第一句话进 Script / Opening；平台不清只问平台 |
| 检测表达和改稿同时出现 | 看像不像 AI 进 AI Check；写/改/能不能发进 Title 或 Script；同强只问先审查还先改稿 |
| Link 和核心入口冲突 | 明确指定或默认 Link 才进 Link；普通创作意图优先走核心入口 |
| 用户说“自定义 Eva-Skill”但没有说明要独立发布 | 进入 Link Builder；先问这个 Link 要解决什么场景，不进入通用 Skill 创建 |
| 用户只说“我不想写口播，只想写朋友圈/微博/公众号” | 这是创作意图，走普通创作链路；只在用户同时说“自定义 Link / Eva-Skill”时进入 Builder |
| 用户说“用我的朋友圈 Link 写这条” | 明确点名 Link，读取 Link 协议并检查 registry / strict |
| 用户说“写朋友圈”，且 `.eva/links.json` 已确认默认朋友圈 Link | 轻提示后进入默认 Link |
| 用户说“写朋友圈”，本地有朋友圈 Link 但未设默认 | 只问普通创作链路还是朋友圈 Link |
| Brief 和成稿冲突 | 明确拆约束进 Eva Brief；要标题/开头/成稿留在 Eva 主干，先 Commerce 再 Title / Script |

## 默认启动

用户只说 `/eva`、`进入 Eva`、`帮我看看`，但没有材料时：

```text
我在。

先把脑子里的东西丢给我。目前默认是创作模式，我会先判断这是想法没理顺、问题问偏了、话题没人群、需要创作，还是应该沉淀成资产。

如果你想专门学习、阅读或做主题研究，请说 eva-learn。
如果你想单独拆商单 Brief 或品牌合作需求，请说 eva-brief。
```
