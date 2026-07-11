# Eva Review 记录库与保存协议

聊天里的“记下来”不等于已经写入。没有授权或写入失败时，不得声称保存成功。

## 默认位置

```text
./eva-review/
├── 00_review-settings.md
└── accounts/
    └── {platform}__{account}/
        ├── account-profile.md
        ├── records/
        ├── backfills/
        └── pattern-reports/
```

目录名必须净化路径字符；账号原名保存在 `account-profile.md`，不依赖目录名还原。

## 首次授权

第一次持续复盘时先完成本次判断，再问：

```text
要不要在当前项目开启 Eva Review 记录库？确认后，这个账号后续复盘会默认保存。位置：{绝对路径}
```

用户确认后才创建目录和设置。用户说“临时看看 / 不保存”时，不创建文件，也不在结尾继续推动保存。

## 多账号

- 当前项目只有一个已配置账号时可以继承。
- 多账号且本轮无法确定时，只问平台和账号。
- 每条记录只属于一个平台账号。
- 跨平台报告分别读取各账号记录，不能混合指标。

## 命名

```text
records/YYYY-MM-DD_{short-title}.md
backfills/YYYY-MM-DD_{record-id}_backfill.md
pattern-reports/YYYY-MM-DD_{range-or-topic}.md
```

重名时追加 `-02`、`-03`，不得覆盖原文件。回填只追加链接或摘要。

## 失败处理

目录不可写、创建失败或记录写入失败时：

1. 保留本轮前台复盘结果。
2. 明确说明哪一步失败和目标路径。
3. 不把记录计入批量样本。
4. 不说“已保存、已记下来、以后可以回看”。
