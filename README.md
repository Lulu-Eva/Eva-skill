# Eva-skill

Eva-skill 是一个面向创作者的思考陪练与表达工具箱。

当前版本：`1.2.0`

v1.2 的核心变化是把工具箱瘦身成一条更清楚的创作链路：

```text
想法 -> 人群 -> 标题 -> 正文
```

它不急着帮你写稿，而是先判断：你的想法有没有对应的人群，标题有没有被用户点击和平台数据验证，正文能不能兑现标题制造的疑问。

如果标题没有任何验证，Eva 会明确提醒你先验证标题，不会默认进入创作层。除非你明确说“我知道没验证，先低置信度写一版”，它才会帮你写试结构的草案。

一句话说：

> 标题本身就是选题。

## 核心能力

- `/eva-think`：思考助理。适合脑子乱、表达欲很多但说不清、想拆概念、想判断一个点子值不值得继续。
- `/eva-reframe`：表象问题归位。适合限流、垂直、频率、为什么不涨粉、是不是方向错了这类容易问偏的问题。
- `/eva-audience-finder`：话题人群识别器。适合看到一个话题、热词、标题或现象，但不知道它到底戳中了谁。
- `/eva-shortvideo`：短视频创作主入口。只做短视频生产调度，下面只保留标题和正文两个环节。
- `/eva-title`：标题即选题。先拆标题关键词、用户疑问、数据验证和正文承诺，再决定能不能写。
- `/eva-script`：正文文案。标题锚点成立后，生成或修改口播正文，保护用户自己的表达风格。
- `/eva-benchmark-copy`：对标文案拆解。拆一篇对标内容的标题、用户疑问、正文结构和可迁移动作。
- `/eva-lenses`：思想镜片。用学者视角辅助思考，但不抢主模块。
- `/eva-mbti`：MBTI 镜片。只校准表达能量、信息密度和收束方式，不做人格测评。
- `/eva-sediment`：沉淀机制。用户明确要求保存时，把点子、判断或内容状态整理成可回捞卡片。

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
/eva-shortvideo
/eva-title
/eva-script
/eva-benchmark-copy
/eva-lenses
/eva-mbti
/eva-sediment
```

## v1.2 结构

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
            ├── 00_工具箱总览.md
            ├── 01_eva-think_思考助理.md
            ├── 02_eva-reframe_表象问题归位.md
            ├── 03_eva-audience-finder_话题人群识别器.md
            ├── 04_eva-benchmark-copy_对标文案拆解.md
            ├── 05_eva-lenses_思想镜片.md
            ├── 06_eva-voice_互动语气节奏.md
            ├── 07_eva-core-tools_创作者思想工具库.md
            ├── 08_eva-mbti-lens_MBTI镜片.md
            ├── 09_eva-fallback_兜底机制.md
            ├── 10_eva-sediment_沉淀机制.md
            └── shortvideo/
                ├── 00_eva-shortvideo_短视频创作主入口.md
                ├── 01_eva-title_标题即选题.md
                └── 02_eva-script_正文文案.md
```

## 运行原则

- 主入口只做轻量归位，不展示复杂菜单。
- 每次只进入一个主模块，不同时给多条路线。
- 辅助层只做校准，不覆盖主模块格式。
- 信息不足时只问一个问题。
- 不编造经历、数据、评论区原话或对标来源。
- 好点子不直接成稿，先变成可搜索、可验证的标题方向。
- 标题没有任何验证时，不直接写正文；先验证标题，或由用户明确授权低置信度试写。

## 更新

重新安装即可获取最新版本：

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```
