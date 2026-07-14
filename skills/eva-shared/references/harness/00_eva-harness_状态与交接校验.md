# Eva Harness：状态与交接校验

Harness 是 Eva 2.1.5 的异常恢复与正式状态校验协议，不是用户功能入口，也不是所有入口默认加载的全局调度器。

只有 Learn 恢复/写入/状态失败、Link/脚本/schema/Asset 校验失败、正式 Asset 交接失败，或用户明确要求查看状态时，入口才读取 Harness。前台是否展示状态，按 `../eva-shared/references/shared/04_light-interaction_轻交互协议.md` 判断。

被入口明确读取时，它负责：

```text
失败状态
必要初始化信息
交接校验
完成前验证
失败处理
用户确认
```

## Runner 原则

模块不决定下一步。

```text
Module 输出：我完成了什么、我需要什么、我建议交给谁。
Harness 判断：是否允许交接、是否补字段、是否需要用户确认、是否启动 Link。
```

禁止：

```text
Eva Learn 直接调用 Eva Create
Eva Brief 直接调用 Eva Script 成稿
Eva Link 直接调用另一个 Link
Persona / Agent 自行调用另一个 Persona / Agent
```

允许：

```text
Module / Link 返回交接请求
-> Harness 校验
-> 用户确认或低风险自动交接
```

## Initializer

2.1.5 不因任务复杂就默认生成任务初始化卡。只有用户要求查看结构化任务状态，或异常恢复确实需要重建任务上下文时才生成。

触发条件只读取 `../eva-shared/references/shared/04_light-interaction_轻交互协议.md` 的 Harness 读取与外显条件。本文件只说明命中条件后如何生成和校验初始化卡，不维护第二套条件清单。

不用于简单聊天、一次性改写、低风险标题发散、用户明确要求快速草稿。

未命中轻交互协议条件时，不读取 Harness、不生成任务初始化卡。

任务初始化卡：

```text
用户目标：
任务类型：
完成定义 DoD：
需要生成的资产：
必填字段：
可用资料：
缺失资料：
验证方式：
是否需要用户确认：
下一步建议：
```

Schema 真源：`schemas/initializer-card.schema.json`。

## 前台外显规则

Harness 输出分两层：

```text
后台层：路由、状态、资产判断、交接校验、完成前验证。
前台层：当前判断、一个最高优先级阻塞点、下一步动作。
```

前台是否可以外显 Harness 字段，只读取 `../eva-shared/references/shared/04_light-interaction_轻交互协议.md`。未命中时，不输出后台状态字段、任务初始化卡或失败记录。

## 状态三层

| 状态层级 | 生命周期 | 典型字段 | 保存规则 |
|---|---|---|---|
| Ephemeral | 当前一步 | confidence、pending_user_confirmation、last_tool_result | 默认不保存 |
| Task | 当前任务 | current_phase、current_module、current_asset、missing_fields、DoD | 任务内维护 |
| Long-term | 跨会话 | 学习项目、Memory 资产、Link registry | 用户启用或确认后写入 |

持久化边界：

```text
1. Ephemeral 可以自动维护，但默认不保存。
2. Task State 要跨会话续接，必须进入学习项目、任务文件或 Memory。
3. Memory 资产必须由用户明确要求保存。
4. Link registry 只有用户启用后才写入。
5. 隐私、内部资料和私有 Link 状态不静默保存。
```

## 自动交接边界

Eva 可以低风险自动交接，但必须同时满足：

```text
1. 只在 Eva 核心模块之间交接。
2. 当前资产字段完整。
3. 下游明确接受该 asset_type。
4. 不涉及私有 Link、文件写入或隐私保存。
5. 用户当前意图明显指向下一步。
```

`eva-brief` 是 Commerce 的独立薄入口包装。它可以把完整 `commercial-constraint-card` 交给 Title、Opening 或 Script 的上游分支，但不能直接交正文成稿。字段缺失、低置信度未授权或稿件身份不明时，只能回 `eva-brief` 补齐。

以下情况必须询问：

```text
需要调用私有 Link 或用户自定义 Link
需要保存资产到本地
当前资产字段不完整
下游路径有多个合理选择
```

Harness 不做第一入口路由；第一入口以 `../eva/SKILL.md` 为准。当前入口和 handoff/Asset 真源先做常规交接判断，只有正式交接失败或需要结构化状态恢复时才追加读取 Harness。

资产交接判断顺序：

```text
1. 当前资产的 asset_type 是否在下游 accepts / valid_next 里。
2. 当前资产必填字段是否完整。
3. 是否涉及私有 Link、文件写入、隐私保存或用户确认。
4. 用户当前动词是否仍然指向这个下游。
5. 多个下游同样合理时，只问一个选择问题。
```

如果用户动词改变了任务方向，停止自动交接，按新动词重新判断入口。例如用户先说“保存这个点子”，随后说“直接写正文”，不能继续按 Memory 处理。

## 完成前验证

Eva 不能在缺少校验时声称完成。

| 场景 | 完成前检查 |
|---|---|
| Learn | 是否形成探究问题卡、判断版本卡或思想种子卡 |
| Think | 是否形成明确核心判断 |
| Create | 是否具备目标读者、核心判断、平台和内容草稿 |
| Brief | 是否形成 Brief 解析、低置信度边界、商单约束卡或改稿交接 |
| Review 跨模块交接卡 | 按 shared Asset 校验；账号 `review-record` 不进入 Harness |
| Memory | 是否用户明确要求保存，且资产不含未确认隐私 |
| Link | 输出是否符合 Eva Asset 协议 |

不通过时输出缺失项和最短补齐路径。

## Failure Taxonomy

| 失败类型 | 触发场景 | 处理 |
|---|---|---|
| 输入不足 | 缺少必填字段、材料、目标或对象 | 追问用户，给最短补齐路径 |
| 路由冲突 | 多个模块或 Link 都合理 | 询问用户选择，或给推荐路径 |
| 资产校验失败 | 字段不完整或下游不接受 | 暂存、降级草稿或补字段 |
| 低置信度判断 | 判断未被证成 | 标注低置信度并输出草案；用户要求认知反向审查时交 Lens Deep |
| 脚本 / 工具失败 | 本地脚本、扫描、校验不可用 | 说明失败原因；结构性任务暂停 |
| 权限 / 安全边界 | 隐私保存、私有 Link | 停止并请求确认 |

记录格式真源：`schemas/failure-record.schema.json`。

## 认知反向审查交接

Harness 不维护第二套认知审查卡。用户明确要求“反向审查、系统压力测试、不要轻易下结论”时：

1. 当前判断已经成形：交给 `eva-lens` 的深度审视模式。
2. 当前判断尚未成形：先交 `eva-think` 梳理，不让 Lens 猜测审查对象。
3. 交给 Lens 时只传当前对话中已有的原始判断、成立条件、已知风险、未证成前提和证据缺口；不得补造事实。
4. Lens 返回后，仍回到当前入口执行 Asset、保存、隐私和正式交接校验；Lens 结果不能绕过 Harness 闸门。

用户要快速草稿时仍可输出低置信度草案。保存、发团队或用于重要决策前继续执行原有质量闸门；只有用户要求认知反向审查时才交 Lens，不自动增加一轮深度分析。

## Script Harness 失败兜底

```text
1. 说明哪个脚本不可用或哪项校验失败。
2. 不假装已经完成确定性检查。
3. 低风险任务可降级为 Prompt Harness，并标注低置信度。
4. Link / Asset 保存等结构性任务暂停并要求确认或修复配置。
```
