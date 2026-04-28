# Eva-skill

Eva-skill 思维流爆款短视频工具箱，用于小红书、抖音、视频号等口播短视频内容生产和创作者思考陪练。

它覆盖 7 个核心环节：

- 思考助理
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
            ├── 01_eva-topic_爆款选题.md
            ├── 02_eva-deconstruct_爆款拆解与网感训练.md
            ├── 03_eva-title-cover_标题封面点击率.md
            ├── 04_eva-script_思维流口播文案.md
            ├── 05_eva-performance_口播情绪节奏.md
            ├── 06_eva-review_发布复盘诊断.md
            └── 07_eva-think_思考助理.md
```

## 更新

重新安装即可获取最新版本：

```bash
npx skills add Lulu-Eva/Eva-skill -g -y
```
