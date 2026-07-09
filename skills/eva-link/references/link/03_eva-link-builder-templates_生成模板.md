# Eva Link Builder Templates：生成模板

本文件只在用户已经确认 Link 定义卡、准备生成本地 Link 文件时读取。不要在 Builder 访谈阶段默认加载。

## 输出结构

最小输出：

```text
local-modules/{link-id}/
├── eva.link.json
├── module.md
└── tests/
    ├── input.example.md
    └── expected-asset.example.json
```

可选：

```text
README.md        # 只在用户明确需要给团队看时生成
examples/        # 多案例 Link 才需要
assets/          # 只有模板、图片、表格等真实资产时才需要
```

默认不写入 Skill 仓库本体。输出路径必须在用户运行项目或用户明确指定目录。

启用和默认设置写入用户项目的 `.eva/links.json`。不要把默认意图、用户确认语、启用状态写进 `eva.link.json`。

## eva.link.json 模板

```json
{
  "id": "local.weibo-copy",
  "name": "微博文案",
  "scope": "create",
  "version": "0.1.0",
  "accepts": [
    "thought-seed-card",
    "judgment-version-card",
    "audience-card"
  ],
  "requires": [
    "核心判断",
    "目标读者",
    "发布平台"
  ],
  "produces": [
    "content-asset-card"
  ],
  "handoff_to": [
    "eva-memory"
  ],
  "entry_aliases": [
    "微博文案",
    "weibo-copy"
  ]
}
```

生成后必须运行：

```text
python3 ../eva-shared/scripts/eva_link_check.py --link local-modules/{link-id}/ --strict
```

## .eva/links.json 模板

只有用户确认启用 Link 时才写入或更新 `links`；只有用户二次确认默认时才写入或更新 `defaults`。

```json
{
  "version": "1.0.0",
  "links": [
    {
      "id": "local.weibo-copy",
      "path": "local-modules/local.weibo-copy",
      "enabled": true
    }
  ],
  "defaults": []
}
```

如果用户只确认启用、没有确认默认，`defaults` 保持空数组或不追加新项。

用户二次确认默认后，才追加：

```json
{
  "intent": "写微博短文案",
  "link_id": "local.weibo-copy",
  "confirmed": true,
  "confirmed_at": "2026-07-04T10:00:00+08:00",
  "confirmed_phrase": "以后说写微博短文案时，默认走 local.weibo-copy"
}
```

写入后必须运行：

```text
python3 ../eva-shared/scripts/eva_link_check.py --registry .eva/links.json
python3 ../eva-shared/scripts/eva_link_check.py --link local-modules/{link-id}/ --strict --registry .eva/links.json
```

## module.md 模板

```text
# {模块名称}

## 解决什么

{一句话说明}

## 不解决什么

- {边界 1}
- {边界 2}

## 输入要求

必须有：
- {requires 字段 1}
- {requires 字段 2}

缺少时只问最短补齐问题，不要直接编。

## 工作流程

1. 读取上游资产。
2. 检查缺失字段。
3. 按本模块方法处理。
4. 输出 `{produces}`。
5. 标注低置信度和不可交接部分。

## 模块内部输出格式

以下是 `module.md` 内部要求 Link 输出的资产格式，不是 Builder 与用户对话时每轮都要展示的格式。

```text
asset_type：
source_module：
core_content：
user_question：
evidence：
valid_next：
saved：false
confidence：
missing_fields：
privacy_flags：
```

## 禁止

- 不编造经历、数据、用户反馈或来源。
- 不绕过 Eva Asset。
- 不自动保存隐私资产。
- 不直接调用其他 Link。
```

## expected-asset.example.json

测试样例必须是资产卡，不是“好看的输出”。

```json
{
  "asset_type": "content-asset-card",
  "source_module": "local.weibo-copy",
  "core_content": "示例输出内容",
  "user_question": "这条内容要回答的用户问题",
  "evidence": [
    "上游 thought-seed-card",
    "用户提供的素材"
  ],
  "valid_next": [
    "eva-memory"
  ],
  "saved": false,
  "confidence": "medium",
  "missing_fields": [],
  "privacy_flags": []
}
```

生成后必须运行：

```text
python3 ../eva-shared/scripts/eva_asset_validate.py --asset local-modules/{link-id}/tests/expected-asset.example.json --downstream eva-memory
```
