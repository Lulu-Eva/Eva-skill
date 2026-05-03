# Eva-skill

Eva-skill 是一个面向创作者的思考陪练与思维流爆款短视频工具箱。

它不只是写稿工具，而是帮助创作者把混乱想法放回正确位置：

```text
私人感受 -> 公共表达 -> 长期资产
```

适用于小红书、抖音、视频号等口播短视频创作，也适合在创作者脑子乱、方向卡住、表达欲很多但说不清时，先做思考整理。

Eva 的互动会更像一个懂内容的创作者陪练：先接住你的混乱，再帮你归位，最后推进一个现实动作。它会保护创作者自己的表达，不会把学员稿件改成统一口吻。

## 核心能力

Eva-skill 覆盖 9 个创作能力，并内置 1 个互动语气层：

- 思考助理：整理表达欲、拆概念、发散内容方向、校准长期路径。
- 思想镜片：用维特根斯坦、杜威、温尼科特、戈夫曼、麦克卢汉、阿德勒、哈耶克、纳瓦尔等思想镜片辅助判断。
- 表象问题归位：把限流、垂直、频率、为什么不涨粉等碎问题放回本质层。
- 爆款选题：从已验证需求、人群处境和爆款结构里生成可拍选题。
- 爆款拆解与网感训练：拆标题、封面、正文结构、爆点来源和可迁移动作。
- 标题封面点击率：生成和诊断封面标题、正文标题、封面画面和双标题配合。
- 思维流口播文案：根据选题和标题写出 800-1200 字口播稿。
- 口播情绪节奏：把稿子转成停顿、重音、表情和拍摄节奏。
- 发布复盘诊断：根据内容和数据定位最大瓶颈，并给下一版修改动作。
- 互动语气节奏：让 Eva 的回复更像陪练，而不是报告；同时保护用户自己的稿件风格。

## 核心判断模型

Eva-skill 的共同底层是“表达公理 + 归位漏斗”。

每次处理前，先判断问题属于哪一层：

- 概念层：词说不清、抽象词太多。
- 表达层：有感受、有经历、有观点，但不知道为什么想说。
- 用户层：不知道用户为什么会听，标题疑问不清。
- 素材层：缺真实经历、案例、数据、评论或对标。
- 链路层：选题、标题、开头、正文、表现、复盘之间错位。
- 证据层：方向、平台、数据判断缺证据。
- 行动层：一直想但不发，反复求判断替代行动。

核心规则：

- 私人感受不能直接成为内容，必须翻译成公共处境。
- 用户不是为表达欲停留，而是为“我被说中了”停留。
- 标题是承诺，正文是兑现。
- 真实素材是表达边界，不能编造经历、数据、评论区原话或对标来源。
- 单条内容是输出，母题才是资产。
- 平台反馈不是审判，而是假设验证。
- 上游错位不能靠下游补救。

## 安装

推荐使用跨 Agent 安装脚本。它会先用 `skills` CLI 安装 Eva-skill，再补齐 WorkBuddy、Cursor、Augment Code 等暂未被 `skills add --all` 覆盖的客户端链接。

```bash
curl -fsSL https://raw.githubusercontent.com/Lulu-Eva/Eva-skill/main/install.sh | bash
```

如果 WorkBuddy 已经打开，安装后请重启或刷新 WorkBuddy，再使用 `/eva`。

如果只需要安装到 `skills` CLI 已支持的客户端，也可以使用：

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```

## 使用

安装后，在支持 skills 的 Claude Code / Agent 环境里使用：

```text
/eva
/eva-think
/eva-lenses
/eva-reframe
/eva-shortvideo
/eva-topic
/eva-deconstruct
/eva-title-cover
/eva-script
/eva-performance
/eva-review
```

如果不知道该用哪个入口，直接使用：

```text
/eva
```

## 公开版边界

这个仓库只包含公开版的思维流爆款短视频方法论和创作者思考陪练。

公开版不包含：

- 私有账号定位策略
- 商单与商业化流程
- 朋友圈与私域转化模块
- 未公开课程逐字稿
- 本地文件路径或内部业务资料

## 目录结构

```text
Eva-skill/
├── VERSION
├── README.md
├── install.sh
├── .claude-plugin/
│   └── marketplace.json
└── skills/
    └── eva/
        ├── SKILL.md
        └── references/
            ├── 00_工具箱总览.md
            ├── 01_eva-think_思考助理.md
            ├── 02_eva-reframe_表象问题归位.md
            ├── 03_eva-shortvideo_主入口.md
            ├── 04_eva-topic_爆款选题.md
            ├── 05_eva-deconstruct_爆款拆解与网感训练.md
            ├── 06_eva-title-cover_标题封面点击率.md
            ├── 07_eva-script_思维流口播文案.md
            ├── 08_eva-performance_口播情绪节奏.md
            ├── 09_eva-review_发布复盘诊断.md
            ├── 10_eva-lenses_思想镜片.md
            └── 11_eva-voice_互动语气节奏.md
```

## 更新

重新执行跨 Agent 安装脚本即可获取最新版本，并同步刷新 WorkBuddy 等客户端链接：

```bash
curl -fsSL https://raw.githubusercontent.com/Lulu-Eva/Eva-skill/main/install.sh | bash
```

如果 WorkBuddy 已经打开，更新后请重启或刷新 WorkBuddy。

如果只更新 `skills` CLI 已支持的客户端，可以使用：

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```
