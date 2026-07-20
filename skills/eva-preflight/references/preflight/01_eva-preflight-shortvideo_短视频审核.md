# Eva Preflight 01：短视频审核

本文件只决定短视频或口播稿应调用哪些既有真源。具体标题、开头和正文标准不在这里复制。

## 1. 先分平台链路

| 场景 | 主审核路径 |
|---|---|
| 小红书等依赖封面/标题点击的平台 | 标题承诺 -> 有标题开头 -> 正文兑现 -> 无标题韧性复核 |
| 抖音、视频号等非封面点击场景 | 无标题第一句话 -> 前三句承接 -> 正文兑现 |
| 平台不明且两条路径会改变结论 | 只问：`这条主要发小红书，还是抖音/视频号？` |

不要因为稿件里出现了一个标题，就自动把抖音/视频号拉进标题验证；也不要因为要检查第一句话，就让小红书绕过标题承诺和既有标题验证状态。

## 2. 小红书等标题点击场景

按需只读调用：

1. `../eva-create/references/create/shortvideo/title/04_eva-title-promise-check_标题承诺与原稿检查.md`
2. `../eva-create/references/create/shortvideo/opening/01_eva-opening-diagnosis_开头承接与兑现诊断.md` 的“有标题开头”只读诊断分支
3. `../eva-create/references/create/shortvideo/script/01_eva-script-logic_正文逻辑链推理.md`
4. `../eva-shared/references/quality/00_eva-ai-check_表达真实性审查.md`

先检查“标题 -> 开头 -> 正文”的承诺是否连续。已有标题验证状态时原样读取；没有验证线索时只能返回“无法判断”，不得替用户假装完成平台搜索。该缺口固定映射为 `暂不建议发布`，不是“修改一个关键问题后发布”；若在这里早停，必须声明“其余维度尚未完成审核”。需要验证时，下一步指向 `/eva-title`，Preflight 不生成标题或搜索结果。

完成标题承诺主路径后，再用 Opening Diagnosis 的无标题标准检查第一句和前三句能否在脱离标题时仍有基本可理解性。这个第二层是**软韧性检查**：

- 不要求一个自然承接可见标题的开头独立重复标题全部信息。
- 单独不够完整通常只算优化建议。
- 发布级阻塞仍以标题、开头和正文承诺断裂为准。
- 不得用无标题检查替代或绕过标题验证。

## 3. 抖音、视频号等无标题场景

直接只读调用 `../eva-create/references/create/shortvideo/opening/01_eva-opening-diagnosis_开头承接与兑现诊断.md` 的“无标题第一句话”分支作为主路径，不强制标题验证。检查：

- 第一句是否能独立交代在讲什么、为什么继续看、后面能兑现什么。
- 前三句是否完成停留、解释和回报承诺。
- 正文是否真正支撑第一句，而不是换词重复或只留情绪。
- 口播是否能自然念出，是否存在关键逻辑跳跃。

再按需调用 Script Logic 和 AI Check。开头审核只读 `../eva-create/references/create/shortvideo/opening/01_eva-opening-diagnosis_开头承接与兑现诊断.md`，不读取 `../eva-create/references/create/shortvideo/opening/02_eva-opening-generation_开头方案生成与推荐.md`，不改稿。

## 4. 人群与商单条件

- 只有当人群、认知缺口或用户问题明显失焦，并且它已经导致承诺与正文无法判断时，才只读参考 `../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md`；不要把发布前审核变成人群问卷。
- 商单稿追加 `../eva-shared/references/commerce/03_draft-check_已有商单稿检查.md` 和商单约束真源。Brief 或约束不完整时，不得判定“可以交”。
- 自有稿的表达资产检查统一交 `04_eva-preflight-expression-assets_表达资产增强.md`，本文件不复制 persona / voice 规则。

## 5. 返回边界

本分支按 05 的统一字段返回，最终三档结论只归 00 主控。不生成第一句话交接卡或其他生产资产，不跳转生产路径，不保存。
