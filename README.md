# Eva-skill

Eva-skill 是一个面向创作者的思考陪练与表达工具箱。

当前版本：`1.3`

v1.3 的核心变化是继续瘦身：保留真正高频、边界清楚的主模块，把思想镜片、MBTI 和创作者思想工具库折叠进 `/eva-think` 的轻量思考姿势，不再作为独立入口。

核心链路：

```text
想法 -> 人群 -> 标题 -> 口播文案
```

它不急着帮你写稿，而是先判断：你的想法有没有对应的人群，标题有没有被用户点击和平台数据验证，口播能不能兑现标题制造的疑问。

如果标题没有任何验证，Eva 会明确提醒你先验证标题，不会默认进入创作层。除非你明确说“我知道没验证，先低置信度写一版”，它才会帮你写试结构的草案。

一句话说：

> 标题本身就是选题。

## 核心能力

- `/eva-think`：思考助理。适合脑子乱、表达欲很多但说不清、想拆概念、想判断一个点子值不值得继续。
- `/eva-reframe`：表象问题归位。适合限流、垂直、频率、为什么不涨粉、是不是方向错了这类容易问偏的问题。
- `/eva-audience-finder`：话题人群识别器。适合看到一个话题、热词、标题或现象，但不知道它到底戳中了谁。
- `/eva-benchmark-copy`：对标文案拆解。拆一篇对标内容的标题、用户疑问、正文结构和可迁移动作。
- `/eva-shortvideo`：短视频创作主入口。只做短视频生产调度，下面保留标题和口播文案两个环节。
- `/eva-title`：标题即选题。先拆标题关键词、用户疑问、数据验证和口播任务交接卡，再决定能不能写。
- `/eva-script`：思维流爆款口播短视频文案。标题锚点成立后，把标题制造的好奇心写成能推进点赞、收藏和转粉的口播稿。

如果不知道该从哪里开始，直接输入：

```text
/eva
```

## 安装

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```

## 使用入口

```text
/eva
/eva-think
/eva-reframe
/eva-audience-finder
/eva-benchmark-copy
/eva-shortvideo
/eva-title
/eva-script
```

## v1.3 结构

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
            ├── 06_eva-voice_互动语气节奏.md
            └── shortvideo/
                ├── 00_eva-shortvideo_短视频创作主入口.md
                ├── 01_eva-title_标题即选题.md
                └── 02_eva-script_思维流爆款口播短视频文案.md
```

## 运行原则

- 主入口只做轻量归位，不展示复杂菜单。
- 每次只进入一个主模块，不同时给多条路线。
- 信息不足时只问一个问题。
- 不编造经历、数据、评论区原话或对标来源。
- 好点子不直接成稿，先变成可搜索、可验证的标题方向。
- 标题没有任何验证时，不直接写口播文案；先验证标题，或由用户明确授权低置信度试写。
- 互动语气只作用于 Eva 和用户的对话，不覆盖用户自己的稿件风格。

## 更新

重新安装即可获取最新版本：

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```
