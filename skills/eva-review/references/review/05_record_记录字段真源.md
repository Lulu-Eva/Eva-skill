# Eva Review 记录字段真源

`review-record` 是 Eva Review 内部持久化记录，不是 shared Asset。

## 最小字段

```text
record_id
account_name_or_id
platform
content_type
published_at_or_elapsed
cover_title
body_title
content_text_or_summary
available_metrics
source
```

## 判断字段

```text
content_goal
core_topic
content_angle
main_promise
promise_fulfillment_check
candidate_hypothesis
supporting_observation
alternative_explanations
test_variable
control_items
primary_metric
observation_window
falsification_condition
unable_to_judge
privacy_flags
```

推断字段必须写成判断，不能冒充用户事实。平台没有的指标允许缺失，不用空数值占位。

## Markdown 记录模板

```markdown
# Review Record：{标题或日期}

## 基础信息
- 记录 ID：
- 账号：
- 平台：
- 内容形式：
- 发布时间 / 已发布时长：
- 内容目标：
- 来源：

## 内容与数据
- 封面标题：
- 正文标题：
- 正文 / 逐字稿或摘要：
- 已提供指标：

## 本次判断
- 待验证假设：
- 观察依据：
- 竞争解释：
- 当前不能判断：

## 下一篇测试
- 只改：
- 保持不变：
- 主指标：
- 观察窗口：
- 否证条件：

## 状态
- 回填状态：pending / backfilled
- 隐私标记：
```
