# Eva Link Doctor：Link 健康检查

Eva Link Doctor 负责检查已有 Link 是否仍能被 Eva 2.x 安全调用和交接。

## 触发

进入本文件的信号：

```text
eva-link-doctor
检查这个 Link
升级后这个 Link 还能不能用
帮我体检本地 Link
为什么这个 Link 不能交给下游
```

如果用户要创建新 Link，读取 `01_eva-link-builder_自定义Link生成.md`。

## 检查对象

支持：

```text
local-modules/{link-id}/
local-modules/{link-id}/eva.link.json
.eva/links.json
```

默认只检查用户指定 Link。不要扫描整个用户项目，除非用户明确要求。

运行命令前，必须先按 `00_eva-link_本地模块连接.md` 的“运行路径解析”得到绝对 `EVA_SHARED_ROOT` 和 `PROJECT_ROOT`。下列命令中的占位符必须替换为绝对路径；不得假设 Skill 安装目录就是用户项目目录。

## 检查项

### 1. 配置结构

运行：

```text
python3 "<EVA_SHARED_ROOT>/scripts/eva_link_check.py" --link "<PROJECT_ROOT>/local-modules/{link-id}/" --strict
```

必须检查：

```text
id 是否合法
entry_aliases 是否覆盖核心入口
accepts 是否声明
requires 是否声明
produces 是否声明
handoff_to 是否声明
```

### 2. 模块文件

检查 `module.md` 是否存在，并包含：

```text
解决什么
不解决什么
输入要求
工作流程
输出格式
禁止事项
```

没有 `module.md` 时，Link 不能运行。

### 3. 资产交接

检查 `produces` 是否是 Eva Asset 已知资产类型。  
如果 Link 输出 `content-asset-card`，至少要能交给：

```text
eva-memory
```

如果 `handoff_to` 不接受该资产，标记为资产交接失败。

### 4. 测试样例

建议检查：

```text
tests/input.example.md
tests/expected-asset.example.json
```

如果 expected asset 存在，运行：

```text
python3 "<EVA_SHARED_ROOT>/scripts/eva_asset_validate.py" --asset "<PROJECT_ROOT>/local-modules/{link-id}/tests/expected-asset.example.json"
```

缺测试样例不一定阻塞运行，但必须标记为风险。

### 5. 版本兼容

检查：

```text
Link version
Eva 版本范围
使用的 asset_type 是否仍存在
requires 字段是否仍能由上游资产提供
```

缺版本范围时，标记为 warning，不直接失败。

### 6. Registry 和默认 Link

如果用户提供 `.eva/links.json`，运行：

```text
python3 "<EVA_SHARED_ROOT>/scripts/eva_link_check.py" --registry "<PROJECT_ROOT>/.eva/links.json"
python3 "<EVA_SHARED_ROOT>/scripts/eva_link_check.py" --link "<PROJECT_ROOT>/local-modules/{link-id}/" --strict --registry "<PROJECT_ROOT>/.eva/links.json"
```

必须检查：

```text
defaults[].link_id 是否指向已存在 Link
defaults[].link_id 是否已 enabled
defaults[].confirmed 是否为 true
defaults[].confirmed_phrase 是否存在
同一个 intent 是否只绑定一个默认 Link
intent 是否过宽
```

过宽 intent 包括：

```text
写
写内容
创作
帮我写
写一条
生成内容
做内容
内容创作
```

过宽 intent 不一定阻塞，但必须标记为高风险：它会抢占 Eva 普通创作主干。除非用户再次明确坚持，不建议保留。

Registry 检查只处理启用和默认关系，不替用户创建 Link。

## 输出格式

```text
Link Doctor Report：
Link：
状态：通过 / 有风险 / 阻塞

阻塞问题：
- ...

风险警告：
- ...

默认 Link：
- registry：
- enabled links：
- defaults：
- 冲突：

资产交接：
- accepts：
- produces：
- handoff_to：
- 可交接 / 不可交接：

最短修复路径：
1. ...
2. ...
```

## 失败分级

| 等级 | 条件 | 处理 |
|---|---|---|
| 阻塞 | 配置非法、覆盖核心入口、缺 module.md、缺 produces | 禁止运行 |
| 阻塞 | 默认 Link 未确认、default 指向不存在或 disabled 的 Link、同一 intent 多个默认 | 禁止默认调用 |
| 有风险 | 缺测试样例、版本范围不明、requires 不完整、默认 intent 过宽 | 可以低置信度运行或要求用户确认 |
| 通过 | 配置、模块、资产、测试都成立 | 可以调用 |

## 禁止

- 不自动修改用户 Link，除非用户明确要求修。
- 不扫描无关私有模块。
- 不绕过 `eva_link_check.py`。
- 不把自由文本输出当作合格资产。
