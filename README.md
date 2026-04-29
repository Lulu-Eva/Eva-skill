# Eva-skill

Eva-skill 创作者思考陪练与思维流爆款短视频工具箱，用于整理表达欲、把表象问题归位、拆概念、发散内容方向，并完成小红书、抖音、视频号等口播短视频内容生产。

它覆盖 8 个核心能力：

- 思考助理
- 表象问题归位
- 爆款选题
- 爆款拆解与网感训练
- 标题封面点击率
- 思维流口播文案
- 口播情绪节奏
- 发布复盘诊断

## 安装

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```

## 使用

安装后，在支持 skills 的 Claude Code / Agent 环境里使用：

```text
/eva
/eva-think
/eva-reframe
/eva-shortvideo
/eva-topic
/eva-deconstruct
/eva-title-cover
/eva-script
/eva-performance
/eva-review
```

## 目录结构

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
            ├── 03_eva-shortvideo_主入口.md
            ├── 04_eva-topic_爆款选题.md
            ├── 05_eva-deconstruct_爆款拆解与网感训练.md
            ├── 06_eva-title-cover_标题封面点击率.md
            ├── 07_eva-script_思维流口播文案.md
            ├── 08_eva-performance_口播情绪节奏.md
            └── 09_eva-review_发布复盘诊断.md
```

## 更新

重新安装即可获取最新版本：

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```
