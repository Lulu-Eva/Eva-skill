# Eva Create：内容形式主入口

Eva Create 只做一层内容形式分流：短视频进入 shortvideo，非虚构自媒体文章进入 Article。本入口不复制两个分支的成稿规则，也不把其他普通写作包装成 Eva 任务。

创作域默认遵守 `../eva-shared/references/shared/04_light-interaction_轻交互协议.md`：不展示完整功能菜单，不外显 Harness、资产卡字段、schema、valid_next 或 DoD；路由和退回时只给当前判断、一个最高优先级阻塞点和下一步动作。进入具体创作模块后，按模块输出真实产物。

## 第一层：最终内容形式

最终输出形式优先于输入材料形式。一篇长文可以被做成短视频，一条视频稿也可以被重写成文章；用户最后要什么，才决定读哪个分支。

| 用户最终要的产物 | 读取 |
|---|---|
| 短视频、口播稿、视频标题、前几秒开头或资料转视频 | `references/create/shortvideo/00_eva-shortvideo_主入口.md` |
| 公众号文章、非虚构自媒体文章、观点长文、文章续写或修改 | `references/create/article/00_eva-article_文章主入口.md` |

用户只说“把这个做成内容”，而内容形式会改变整条流程时，只问：

```text
你这次最后想要一条短视频，还是一篇文章？
```

## 短视频分支内的分流

| 信号 | 读取 |
|---|---|
| 话题、热词、现象、标题，但不知道讲给谁 | `../eva-shared/references/audience/00_eva-audience-finder_话题人群识别器.md` |
| 短视频对标文案、爆款笔记、口播稿拆解 | `../eva-shared/references/benchmark/00_eva-benchmark-copy_对标文案拆解.md` |
| 品牌 Brief、商单需求、合作口径、产品卖点、商单原稿、同产品样本 | `../eva-shared/references/commerce/00_eva-commerce_商单主入口.md` |
| 视频稿 AI 味、太机械、表达真实性审查 | `../eva-shared/references/quality/00_eva-ai-check_表达真实性审查.md` |
| 做一条短视频，但还没判断标题/开头/正文入口 | `references/create/shortvideo/00_eva-shortvideo_主入口.md` |
| 搜标题、判断标题、正文标题、标题兑现 | `references/create/shortvideo/title/00_eva-title_标题即选题.md` |
| 标题交接卡或第一句话交接卡已成立，准备写正文 | `references/create/shortvideo/script/00_eva-script_思维流爆款内容创作.md` |
| 只优化第一句话、前 5 秒、开头 | `references/create/shortvideo/opening/00_eva-opening_开头针对性优化.md` |

不属于两个 Create 分支的处理：

```text
明确点名已有 Link / 创建 Link / 检查 Link -> eva-link
没有点名 Link 的朋友圈、微博、小红书短图文或其他短文案 -> 退出 Eva Create，由基础模型直接完成
虚构文学、学术论文、技术文档、法律文书、医疗报告等专业写作 -> 退出 Article，交给对应专业能力或基础模型
正式品牌赞助文章 -> eva-brief 先形成商业约束；首版不在 Article 内直接成稿
```

## 硬规则

- 短视频没有人群和用户疑问，不直接写完整稿；Article 按自己的读者任务与材料充分度判断。
- 标题验证是短视频标题链路的硬闸门，不是 Article 成稿前的硬闸门。
- 依赖封面或标题点击的短视频平台，第一次要求完整稿且标题无验证线索时先交付定制标题搜索方案。明确做抖音、视频号等没有封面点击的完整口播时，不强制平台标题搜索；先形成能被正文兑现的第一句话，再进入路线和成稿。
- 短视频商单先拆 Brief，再进入标题或第一句话链路。
- 表达真实性审查只诊断表达问题，不顺手改写成完整稿。
- 对标拆解不能变成照搬对标。
- Article 不得声称通过短视频人群、标题或路线图闸门；未明确保存时，两个分支都不自动生成资产。

## 默认接法

用户已经说清内容形式时，立即读取对应分支。只有短视频用户没有材料，只说“帮我看看”“我想做一条爆款”时，才保留原有最上游问题：

```text
你现在是完全没思路，还是已经有一个话题/标题/素材？
```

有材料时，先按最终输出形式读取唯一分支，再由该分支继续。

如果子模块需要输出交接卡、商单约束卡、正文路线图或资产卡，按对应 shared 真源在后台校验；普通前台只展示摘要和下一步。只有用户要求保存、字段缺失、低置信度确认或进入 Link/Memory 写入，才展开字段。
