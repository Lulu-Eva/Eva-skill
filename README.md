# Eva-skill

Eva-skill 是面向创作者的思考陪练与表达工具箱。

当前版本：`1.7.4`

核心链路：

```text
想法 -> 人群 -> 标题/第一句话 -> 内容创作 -> 表达资产
```

商单链路：

```text
品牌 Brief -> 商单约束卡 -> 标题/第一句话 -> 内容创作
```

Eva Learn 是主动触发的学习方法链路：

```text
建档 -> 旅程判断 -> 学习/带读/主题式阅读 -> 掌握检查 -> 判断版本/思想种子卡 -> Eva 内容链路
```

Eva 不急着帮用户写稿。它先判断用户卡在想法、人群、标题/第一句话、正文路线图、商单 Brief，还是表达资产。标题本身就是选题；商单必须先拆 Brief；完整正文必须先过正文路线图。

如果你想专门学习、阅读或做主题研究，需要主动说：

```text
eva-learn
```

Eva Learn 不会因为用户提到“学习、阅读、研究”就自动启动。主动进入后，它会先建档或恢复学习项目，再判断走探索式学习、资料带学、主题式阅读，或思想种子卡交接。

## 核心能力

- `/eva-think`：思考助理。处理脑子乱、表达欲很多但说不清、拆概念、判断方向。
- `/eva-reframe`：表象问题归位。处理限流、垂直、频率、为什么不涨粉等容易问偏的问题。
- `/eva-audience-finder`：话题人群识别器。判断一个话题到底戳中了谁。
- `/eva-benchmark-copy`：对标文案拆解。拆标题、用户疑问、正文结构和可迁移动作。
- `/eva-brief`：商单 Brief 需求拆解。先拆品牌硬要求、卖点池、表达风险和素材匹配，输出商单约束卡。
- `/eva-ai-check`：表达真实性审查。看文本有没有具体意思、个人立场、身体感和内容推进。
- `/eva-memory`：点子卡沉淀与回溯。保存和回捞可复用素材。
- `/eva-persona-memory`：人设记忆采集。沉淀真实经历、选择代价、生活风格和表达资格。
- `/eva-user-voice`：用户表达文风提取。生成 `voice-card`，后续写稿保护用户自己的声音。
- `/eva-shortvideo`：短视频创作主入口。判断有标题链路还是无标题链路。
- `/eva-title`：标题即选题。输出爆款标题搜索方案，判断候选标题，形成内容任务交接卡。
- `/eva-script`：思维流爆款内容创作。先过正文逻辑链和正文路线图，再进入正文撰写。
- `/eva-learn`：提问式学习与主题式阅读。主动触发后建档，按旅程推进学习、资料带学、主题式阅读和思想种子卡。

## 使用入口

```text
/eva
/eva-think
/eva-reframe
/eva-audience-finder
/eva-benchmark-copy
/eva-brief
/eva-memory
/eva-persona-memory
/eva-user-voice
/eva-ai-check
/eva-shortvideo
/eva-title
/eva-script
/eva-learn
```

## 安装

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```

## v1.7.4 更新

v1.7.4 不改变 Eva Learn 的产品名，仍然是“提问式学习与主题式阅读”。这次升级重点是结构稳定性和提示词瘦身。

- 压缩 `SKILL.md` 的路由描述，删除重复的防御性声明。
- 保留弱模型需要的硬路由：每个判断节点都有输入特征、执行路径和兜底。
- Eva Learn 从功能模块拆分改为用户旅程拆分。
- 新增 `11_eva-learn.md` 作为入口，只做触发、建档、恢复和旅程判断。
- Eva Learn 新增学习目标尺度闸门：大主题遇到应用词时，先区分学科型、应用型、制度型和内容素材型，不直接开讲。
- 新增 `11-A_探索式学习.md`：无资料时从问题、谱系和学习目录进入。
- 新增 `11-B_资料带学.md`：单份或少量资料的完整带学和问题驱动学习。
- 新增 `11-C_主题式阅读.md`：多资料、对比研究和长期主题式阅读。
- 新增 `11-D_思想种子卡与内容链路交接.md`：学习成果沉淀和下游内容链路硬闸门。
- 删除旧的 `11a/11b/11c` 运行文件，避免新旧路由并存。

## v1.7.4 结构

```text
Eva-skill/
├── VERSION
├── README.md
├── .claude-plugin/
│   └── marketplace.json
└── skills/
    └── eva/
        ├── SKILL.md
        └── references/
            ├── 01_eva-think_思考助理.md
            ├── 02_eva-reframe_表象问题归位.md
            ├── 03_eva-audience-finder_话题人群识别器.md
            ├── 04_eva-benchmark-copy_对标文案拆解.md
            ├── 05_eva-memory_点子卡沉淀与回溯.md
            ├── 06_eva-voice_互动语气节奏.md
            ├── 07_eva-persona-memory_人设记忆采集.md
            ├── 08_eva-ai-check_表达真实性审查.md
            ├── 09_eva-user-voice_用户表达文风提取.md
            ├── 10_eva-brief_商单Brief需求拆解.md
            ├── 11_eva-learn.md
            ├── 11-A_探索式学习.md
            ├── 11-B_资料带学.md
            ├── 11-C_主题式阅读.md
            ├── 11-D_思想种子卡与内容链路交接.md
            ├── shared/
            │   ├── 01_handoff-cards_交接卡字段真源.md
            │   ├── 02_asset-state_资产状态归一表.md
            │   ├── 03_low-confidence_低置信度授权协议.md
            │   └── 04_commercial-constraint-card_商单约束卡真源.md
            └── shortvideo/
                ├── 00_eva-shortvideo_短视频创作主入口.md
                ├── 01_eva-title_标题即选题.md
                ├── 01a_eva-title-search-plan_爆款标题搜索方案.md
                ├── 01b_eva-title-candidate-check_爆款标题候选判断.md
                ├── 01c_eva-title-body-heading_正文标题补强.md
                ├── 01d_eva-title-promise-check_标题承诺与原稿检查.md
                ├── 02_eva-script_思维流爆款内容创作.md
                ├── 02a_eva-script-logic_正文逻辑链推理.md
                ├── 02a1_eva-script-long-material_长素材消化.md
                ├── 02a2_eva-script-commercial-constraints_商单约束检查.md
                ├── 02a3_eva-script-route-map_正文路线图.md
                ├── 02b_eva-script-writing_正文撰写.md
                └── 03_eva-opening_开头针对性优化.md
```

## 运行原则

运行原则以 `skills/eva/SKILL.md` 为唯一真源。README 只说明能力、入口、版本和结构。

用户运行时生成的 `eva-memory/` 和 `eva-learn/` 不应提交到 GitHub。

## 更新

重新安装即可获取最新版本：

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```
