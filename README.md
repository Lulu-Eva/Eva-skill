# LLEva Skill

LLEva 思维流爆款短视频工具箱，用于小红书、抖音、视频号等口播短视频内容生产。

它覆盖 6 个核心环节：

- 爆款选题
- 爆款拆解与网感训练
- 标题封面点击率
- 思维流口播文案
- 口播情绪节奏
- 发布复盘诊断

## 安装

```bash
npx skills add Lulu-Eva/lleva-skill -g -y
```

## 使用

安装后，在支持 skills 的 Claude Code / Agent 环境里使用：

```text
/lleva
/lleva-topic
/lleva-deconstruct
/lleva-title-cover
/lleva-script
/lleva-performance
/lleva-review
```

## 目录结构

```text
lleva-skill/
├── VERSION
├── README.md
├── .claude-plugin/
│   └── marketplace.json
└── skills/
    └── lleva/
        ├── SKILL.md
        └── references/
            ├── 00_工具箱总览.md
            ├── 01_lleva-topic_爆款选题.md
            ├── 02_lleva-deconstruct_爆款拆解与网感训练.md
            ├── 03_lleva-title-cover_标题封面点击率.md
            ├── 04_lleva-script_思维流口播文案.md
            ├── 05_lleva-performance_口播情绪节奏.md
            └── 06_lleva-review_发布复盘诊断.md
```

## 更新

重新安装即可获取最新版本：

```bash
npx skills add Lulu-Eva/lleva-skill -g -y
```
