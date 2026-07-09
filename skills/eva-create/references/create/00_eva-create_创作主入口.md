# Eva Create：创作主入口

Eva 默认按创作模式接住输入，但创作模式不等于直接写稿。它先判断用户卡在创作链路的哪一层。

创作域默认遵守 `../eva-shared/references/shared/04_light-interaction_轻交互协议.md`：不展示完整功能菜单，不外显 Harness、资产卡字段、schema、valid_next 或 DoD；路由和退回时只给当前判断、一个最高优先级阻塞点和下一步动作。进入具体创作模块后，按模块输出真实产物。

## 分流顺序

| 信号 | 读取 |
|---|---|
| 话题、热词、现象、标题，但不知道讲给谁 | `../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md` |
| 对标文案、爆款笔记、口播稿、图文内容拆解 | `references/create/benchmark/00_eva-benchmark-copy_对标文案拆解.md` |
| 品牌 Brief、商单需求、合作口径、产品卖点、商单原稿、同产品样本 | `../eva-shared/references/commerce/00_eva-commerce_商单主入口.md` |
| AI 味、太机械、表达真实性审查 | `references/create/quality/00_eva-ai-check_表达真实性审查.md` |
| 做一条短视频，但还没判断标题/开头/正文入口 | `references/create/shortvideo/00_eva-shortvideo_主入口.md` |
| 搜标题、判断标题、正文标题、标题兑现 | `references/create/shortvideo/title/00_eva-title_标题即选题.md` |
| 标题交接卡或第一句话交接卡已成立，准备写正文 | `references/create/shortvideo/script/00_eva-script_思维流爆款内容创作.md` |
| 只优化第一句话、前 5 秒、开头 | `references/create/shortvideo/opening/00_eva-opening_开头针对性优化.md` |

## 硬规则

- 没有人群和用户疑问，不直接写完整稿。
- 标题没有验证线索，不进入高置信度正文。
- 商单内容先拆 Brief，再进入标题或第一句话链路。
- 表达真实性审查只诊断表达问题，不顺手改写成完整稿。
- 对标拆解不能变成照搬对标。

## 默认接法

用户没有材料，只说“帮我看看”“我想做一条爆款”时，不展示完整功能菜单，只问当前最上游的问题：

```text
你现在是完全没思路，还是已经有一个话题/标题/素材？
```

有材料时，直接按分流顺序读取唯一优先文件。

如果子模块需要输出交接卡、商单约束卡、正文路线图或资产卡，按对应 shared 真源在后台校验；普通前台只展示摘要和下一步。只有用户要求保存、字段缺失、低置信度确认或进入 Link/Memory 写入，才展开字段。
