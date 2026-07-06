# Eva 2.0 Architecture Boundaries

本文件是 Eva 2.0 的结构真源。目录不是分类法，而是边界。

## 核心判断

```text
目录按能力边界分层；
用户入口按任务流表达；
Harness 按协议调度，不碰业务细节；
前台按轻交互表达，后台按严格契约校验；
Schema 管契约；
Script 管确定性校验；
Prompt 管模块内部判断。
```

## 三层结构

### 用户任务层

用户不会说“我要进入某个内部模块”。用户会说：

```text
我有个想法，能不能变成内容？
这篇为什么不好？
我之前沉淀过什么能复用？
帮我读懂这份资料。
帮我把发布经验沉淀成下一条内容。
```

所以对话入口必须按用户任务表达，不按内部能力炫技。

默认前台体验遵守 `references/shared/04_light-interaction_轻交互协议.md`。普通创作、标题、开头、正文、改稿、商单 Brief 初拆、AI 味检测和点子沉淀，调度层只外显当前判断、一个最高优先级阻塞点和下一步动作；进入具体任务后仍输出真实产物。Harness、Asset、schema、valid_next、DoD 和 failure-record 只在后台运行。

Eva 2.0 的第一身份是创作工作台。默认入口必须沿创作主干推进；Think、Learn、Memory 都以“能否喂回创作”为完成定义。已发布内容的数据和评论区输入先按标题兑现、问题归位、素材转内容或经验沉淀处理，不新增独立复盘入口。`eva-learn` 和 `eva-brief` 可以作为独立薄入口；`eva-link` 是显式系统能力，但不拆成独立 Skill。

### 能力边界层

`references/` 按 bounded context 组织：

```text
entry/      主入口、路由、用户任务识别
asset/      资产卡协议和交接语言
harness/    Runner、Initializer、状态、完成前验证、失败处理
learn/      学习、阅读、资料带学、主题式阅读、思想种子卡
think/      想法澄清、问题归位、核心判断
create/     创作生产域：人群、对标、标题、开头、正文、商单内容、表达质量
memory/     点子、人设、文风等可复用资产的保存和回捞
interaction/ Eva 和用户对话时的语气、节奏、追问方式
link/       本地模块连接协议
shared/     跨模块稳定契约
```

`eva-brief` 是独立薄入口，不新增独立 Brief 真源目录；它读取 `create/commerce/` 和 `shared/03_commercial-constraint-card_商单约束卡真源.md`，只处理商单约束资产。

每个边界拥有自己的术语、输入、输出、状态和失败条件。不允许子模块共享内部规则。

### 执行契约层

```text
schemas/    只定义字段、状态、资产、错误；不写业务判断
scripts/    只做解析、转换、校验、扫描；不承载 prompt 语义
examples/   用来验证 schema 和脚本，不代表正式业务模块
```

`schemas/asset-types.json` 是资产类型、每类资产允许下游、最低字段和可见性分层的机器真源。`schemas/handoff-targets.json` 是合法下游目标集合的独立机器真源。文档矩阵、脚本常量和 schema enum 不得另起真源。

## Harness 边界

Harness 是控制面，不是超级业务模块。

允许：

```text
路由
状态读取和更新
任务初始化卡
资产交接校验
完成前验证
失败分类
用户确认
Link 调用前检查
```

禁止：

```text
代替 Learn 做学习判断
代替 Think 生成核心判断
代替 Create 写标题和正文
代替 Memory 决定保存隐私资产
代替 Link 执行本地模块
```

Harness 应该“厚协议、薄业务”。它依赖资产协议，不依赖子模块文件细节。

Harness 不等于前台界面。任务初始化卡、完成定义、失败记录和状态字段只在轻交互协议允许的复杂任务、长期项目、Link、资产保存或校验失败中外显。

## Context 边界

### Entry

输入：用户原话、显式触发词、当前任务状态。  
输出：唯一优先入口，或一个能改变路由的问题。  
失败条件：多个入口同样合理但未确认。

### Asset

输入：模块输出、用户问题、证据、下游请求。  
输出：标准资产卡、低置信度草稿、不可交接说明。  
失败条件：缺必填字段、下游不接受、隐私未确认。

资产卡是后台交接协议，不是普通任务的默认输出格式。只有保存、跨模块字段缺失、低置信度确认、Link/Memory 写入前，或用户要求查看字段时，才外显资产字段。

### Learn

输入：用户明确触发 `eva-learn`、学习材料、研究主题、学习项目状态。  
输出：探究问题卡、阅读谱系、学习进度卡、判断版本卡、思想种子卡。  
失败条件：用户没有主动触发 Eva Learn、材料来源不清、学习目标不明。

### Brief

输入：用户明确触发 `eva-brief`、品牌 Brief、品牌合作需求、商单约束卡请求、已有商单稿检查、对标样本迁移。  
输出：Brief 需求拆解、低置信度卖点拆解、commercial-constraint-card、商单原稿改稿交接卡、对标样本迁移判断。  
失败条件：用户只是要商单成稿、Brief 缺产品/目标用户/必提/禁区/不可承诺内容、稿件身份不明、试图直接写标题/开头/正文。

Brief 是独立薄入口，不是第二条创作链。它读取 `create/commerce/` 和 `shared/03_commercial-constraint-card_商单约束卡真源.md`；完整商单内容必须回到 Eva 主创作链，经 Title、Opening 或 Script 完成。

### Think

输入：混乱感受、经历、问题、概念、表达欲。  
输出：核心判断卡、用户疑问卡、思想种子卡、点子卡候选。  
失败条件：没有具体情境、无法形成可表达判断。

### Create

输入：核心判断、人群、用户疑问、标题线索、Brief、内容任务。  
输出：人群卡、对标拆解卡、标题交接卡、第一句话交接卡、内容任务卡、内容成品卡、表达质量诊断。  
失败条件：没有人群、没有用户疑问、标题未验证、商单未拆 Brief。

### Inactive Drafts

输入：尚未进入本次发布、已移出 2.0 主目录的能力草案。  
输出：候选设计、回归样例、后续候选模块。  
失败条件：被 Entry 或默认触发词当成正式能力调用。

### Memory

输入：用户明确保存/回捞请求、点子、人设、文风、学习进度、用户明确要保留的发布经验。  
输出：idea-card、persona-card、voice-card、learning-progress-card、review-card。  
失败条件：用户未确认保存、隐私未确认、资产太空泛不可复用。

### Interaction

输入：Eva 自己的回复任务、追问任务、低置信度提醒、拒绝编造场景。  
输出：对话语气、追问密度、表达边界。  
失败条件：把 Eva 的互动语气误当成用户稿件文风，或把用户文风提取放进 interaction。

Interaction 拥有前台语言边界，但不拥有业务判断。业务模块决定做什么，Interaction 只决定如何轻量、清楚地说出来。

### Link

输入：用户明确指定本地模块、项目级 registry 中已确认的默认 Link、符合 accepts 的资产。  
输出：Link 声明的 produces 资产。  
失败条件：覆盖核心入口、缺 requires、输出不符合资产协议、默认 Link 未经用户二次确认。

`eva.link.json` 是模块能力声明；`.eva/links.json` 是用户项目里的启用和默认偏好 registry。不要把用户默认习惯写进 Link 模块本身。

## Shared 契约

`shared/` 只放跨模块稳定契约：

```text
交接卡字段真源
资产类型单一真源
资产状态归一
低置信度授权协议
商单约束卡真源
轻交互协议
```

禁止把某个模块的临时规则放进 shared。shared 一旦膨胀，说明边界在腐烂。

## Create 子域

`create/audience/` 可以独立存在，因为人群卡是标题、正文和学习交接的共同上游。

`create/benchmark/` 可以独立存在，因为对标拆解的输入、证据和风险边界不同于正文创作。

`create/quality/` 可以独立存在，因为表达真实性审查是质量诊断，不是 Memory 保存，也不是正文撰写。

`create/shortvideo/` 可以独立存在，因为短视频已经有独立流程、模板、交接卡和验证标准。

`create/shortvideo/title/` 只处理标题搜索、候选判断、正文标题补强和标题兑现。

`create/shortvideo/script/` 只处理内容入口、正文逻辑链、长素材、商单约束、路线图和正文撰写。

`create/shortvideo/opening/` 只处理第一句话、前三句承接和前 5 秒停留理由。

`create/commerce/` 可以独立存在，因为商单 Brief 和商单约束卡是商业内容的前置契约。

`create/commerce/00_eva-commerce_商单主入口.md` 只做商单输入身份判断和分流。

`create/commerce/01_brief-parse_Brief基础解析.md` 只处理 Brief 原文、品牌硬要求和卖点池，不生成正式商单约束卡。

`create/commerce/02_constraint-card_商单约束卡生成.md` 只处理表达资产匹配、主讲卖点筛选和商单约束卡输出。

`create/commerce/03_draft-check_已有商单稿检查.md` 只检查学员自写商单原稿，不完整改稿。

`create/commerce/04_sample-transfer_对标样本迁移.md` 只拆对标样本/品牌参考样例的切入点和结构，不照搬原文。

新子域必须满足三个条件才允许新增：

```text
1. 有独立输入和产物格式。
2. 有独立验证标准。
3. 至少有一个真实任务反复触发。
```

否则先放在 `create/` 根层，不提前铺功能树。

## 调试要求

Prompt 文件变多后，可调试性比文件夹美观更重要。

每次复杂任务应能追踪：

```text
命中的入口
读取的 reference
使用的 schema 版本
脚本输入输出
当前资产卡
状态变更
失败类型
用户确认点
```

如果无法解释“为什么路由到这里”，Harness 就失职。
