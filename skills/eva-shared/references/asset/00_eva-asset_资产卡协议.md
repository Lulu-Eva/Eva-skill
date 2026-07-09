# Eva Asset：资产卡协议

Eva 2.0 的交接中心不是模块，而是资产卡。

资产卡默认是后台协议，不是默认用户界面。前台外显条件按 `../eva-shared/references/shared/04_light-interaction_轻交互协议.md` 执行。

工作问题：

```text
这次使用留下了什么资产？
这个资产下一次能被谁接着用？
```

## 通用最小字段

所有可交接资产至少包含：

```text
asset_type：
source_module：
core_content：
user_question：
evidence：
valid_next：
saved：
confidence：
low_confidence_reason：
missing_fields：
privacy_flags：
```

脚本校验真源是 `schemas/asset-card.schema.json`。字段级检查用：

```text
python3 scripts/eva_asset_validate.py --asset examples/asset-card.example.json --downstream eva-create
```

脚本只能判断字段和交接资格，不能判断内容质量。

## 外显边界

后台每次都要判断是否形成资产卡，但普通任务不默认展示字段表。

只有以下情况外显资产卡字段：

```text
用户要求保存、沉淀、记下来或下次继续
当前结果要跨模块交接但字段不完整
当前结果是没经过验证的草稿，需要提醒用户不要直接发布
Link / Memory 写入前
用户明确要求查看资产卡、交接卡或字段
```

普通任务只提示：

```text
这次可以沉淀成一张资产卡。要保存的话你说“保存”。
```

不得默认输出 `asset_type / valid_next / saved / confidence` 字段表。

## 主要资产类型

资产类型、每类资产的 `valid_next`、`required_fields` 和可见性真源是 `schemas/asset-types.json`。合法下游目标真源是 `schemas/handoff-targets.json`。本表只做人读说明；新增、改名、调整下游或调整可见性时，先改对应 schema，再让 `scripts/eva_doctor.py` 检查漂移。

资产可见性分三档：

```text
surface：用户直接感知的主干成品或主干输入。
bridge：主干上承上启下的半成品，需要交接、缺字段或低置信度时才外显。
internal：辅助模块或系统内部件，默认不向用户展示字段。
```

| asset_type | 典型来源 | 可见性 |
|---|---|---|
| inquiry-question-card | Learn | internal |
| reading-lineage-card | Learn | internal |
| learning-progress-card | Learn / Memory | internal |
| judgment-version-card | Learn / Think | internal |
| thought-seed-card | Learn / Think | bridge |
| core-judgment-card | Think | bridge |
| user-question-card | Think | bridge |
| idea-card | Think / Memory | bridge |
| audience-card | Shared Audience / Think / Create / Learn / Link | bridge |
| title-handoff-card | Create | bridge |
| opening-handoff-card | Create | bridge |
| commercial-constraint-card | Brief / Commerce | bridge |
| content-task-card | Create / Brief / Commerce | bridge |
| content-asset-card | Create / Link | surface |
| review-card | Internal Pending / 历史兼容 | bridge |
| persona-card | Memory | bridge |
| voice-card | Memory | bridge |

上表只做人读说明，不维护 `valid_next`、`required_fields` 或完整 produced_by。下游识别资产类型，不识别模块来源；每类资产的具体下游和最低字段必须读取 `schemas/asset-types.json`，合法下游目标集合必须读取 `schemas/handoff-targets.json`。

## 模块最低字段

### Think 输出

```text
asset_type：core-judgment-card / thought-seed-card / idea-card
core_content：一句明确判断
user_question：用户真正卡住的问题
evidence：具体经历、素材或推理依据
```

### Shared Audience 输出

```text
asset_type：audience-card
core_content：目标人群、真实缺口、用户疑问和内容入口
user_question：这个话题替谁说话，用户点进来想听什么
evidence：话题、热词、标题、评论、素材或用户提供的现象
```

`audience-card` 的能力真源在 `../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md`。它可以由 `eva-think`、`eva-create`、`eva-learn` 或 `eva-link` 读取后产出；不要把它绑死在 Create 内。

### Create 输出

```text
asset_type：audience-card / title-handoff-card / opening-handoff-card / content-asset-card
core_content：人群、标题、第一句话、正文或内容草稿
user_question：内容要回答的用户问题
evidence：验证线索、对标来源、用户原始素材或 Brief
```

没有目标读者、核心判断、平台和内容草稿，不能标记为完成的 content-asset-card。

### Brief 输出

商单资产字段以 `../eva-shared/references/shared/03_commercial-constraint-card_商单约束卡真源.md` 为准。没有正式商单约束卡，不进入高置信度标题或正文。

`commercial-constraint-card` 的 `valid_next` 可以包含 `eva-brief`，但只表示字段缺失、低置信度待确认、稿件身份不明或需要对照 Brief 检查时回补。字段完整且用户目标是标题、开头、脚本或成稿时，不回流 Brief，应交给 Eva 主创作链的 Title、Opening 或 Script 上游分支。

### 历史复盘卡兼容输出

```text
asset_type：review-card / user-question-card / idea-card
core_content：复盘判断、评论区问题池、下一步调整
user_question：这次复盘要回答什么
evidence：数据、评论、原稿、标题承诺或发布反馈
```

本段只用于历史 `review-card` 兼容，不作为 Eva 2.0 主链路主动产物。每类资产允许的 `valid_next` 以 `schemas/asset-types.json` 为准；目标名是否合法以 `schemas/handoff-targets.json` 为准。

### Link 输出

Link 必须输出 `produces` 声明的资产类型。否则只能停在 Link 内修正，不能交给 Memory 或 Create。

## 交接校验

每次交接前检查：

```text
1. 当前 asset_type 是什么？
2. 下游是否接受这种资产？
3. 必填字段是否完整？
4. 是否存在低置信度、隐私、未确认保存、外部来源限制？
5. 如果不能交接，是追问、暂存、降级为草稿，还是建议换入口？
```

校验不通过时，不能硬接。

示例：

```text
thought-seed-card 缺少目标读者
-> 不能直接写完整稿
-> 先进入 audience 判断，或降级为低置信度草稿
```

## 保存边界

- `saved: false` 是默认值。
- 保存 Memory 必须由用户明确触发。
- `privacy_flags` 非空时，保存前必须提醒并确认。
- 用户资产保存到运行项目的 `eva-memory/`、`eva-learn/` 或用户指定目录，不写入 Skill 仓库。
- Link registry 只有用户启用后才写入 `.eva/`。

## 低置信度资产

以下情况必须标记低置信度：

| 原因 | low_confidence_reason |
|---|---|
| 标题未验证 | title-unverified |
| Brief 不完整 | brief-incomplete |
| 缺少人群 | missing-audience |
| 缺少用户疑问 | missing-user-question |
| 缺少原始素材 | missing-source-material |
| 用户要求先写但证据不足 | user-requested-draft-before-evidence |
| Link 输出不满足 schema | link-output-schema-failed |
| 复盘缺标题或正文 | missing-title-or-content |
| 复盘缺数据 | missing-data |
| 评论样本过少 | small-comment-sample |
| 数据窗口不清 | unclear-data-window |
| 用户发布目标不清 | missing-user-goal |
| 归因未证成 | unverified-causality |

低置信度可以输出草稿，但不能伪装成完成资产。

`confidence: low` 时必须写 `low_confidence_reason`。如果原因不在上表，先写入 `missing_fields` 或 failure-record，不自行发明原因枚举。
