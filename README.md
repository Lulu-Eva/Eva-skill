# Eva Skill v2.0.5

当前版本：`2.0.5`。

Eva Skill 是面向创作者的思考、短视频创作、学习、商单拆解和本地工作流接入工具。2.0.5 保留 Eva 的建档、验证、隐私、交接和质量闸门，同时减少高频入口的默认读取与前台等待。

## 从 1.7.4 到 2.0.5

1.7.4 使用一个主 `SKILL.md` 承担路由和全局规则，Think、Learn、Brief、Create、Memory 等能力位于 `references/` 内部。

2.0.5 拆成一个路由入口、五个能力入口和一个共享真源层：

```text
skills/
├── eva/              # 路由后同轮执行目标入口
├── eva-think/        # 日常解释、聊天、想法归位、问题重构
├── eva-create/       # 短视频、标题、开头、正文、对标、AI 味检测
├── eva-learn/        # 学习、资料带读、主题式阅读
├── eva-brief/        # 商单 Brief、合作需求、商单约束
├── eva-link/         # 本地 Link 创建、检查、调用
└── eva-shared/       # 共享协议、schema、脚本和示例
```

安装时必须同时安装七个目录。`eva-shared` 不是用户入口，但其他入口需要它提供共享协议、schema、脚本和正式校验规则。

## 主要升级

- **同轮路由**：`/eva` 判断入口后立即执行目标模块，不停在模块介绍或功能菜单。
- **Think 轻启动但不轻思考**：普通解释直接回答；陪聊梳理会持续承接主线、区分事实与判断、找到核心冲突并形成阶段性结论。只有涉及文风、人设、保存或创作交接时，才加载对应外部协议。
- **Learn 分级建档**：所有 Learn 任务仍然先建档。单概念或单资料先建立最小可追溯档案，系统学习、多资料对读、长期研究和项目恢复使用完整档案；建档成功后同轮开始教学。
- **Create 聚焦短视频**：继续执行人群、用户疑问、标题或第一句话、正文路线图等质量闸门，不承接普通朋友圈、微博或公众号写作。
- **Brief 保留商单闸门**：商单先拆正式约束，再交回短视频创作；约束不足时不进入高置信度成稿。
- **Link 显式调用**：只有用户点名、创建、检查或确认项目默认 Link 时才进入，完整 Link 校验不减。
- **资产按阶段校验**：普通入口启动不读取完整 schema；生成资产、保存或跨模块交接前仍必须读取 schema 并校验字段。
- **表达资产按需读取**：只有内容需要个性化、人设资格、用户文风或真实经历时，才轻量读取当前项目的 persona/voice 资产；隐私和授权边界不变。
- **兼容 1.7.4 入口**：Reframe、Audience Finder、Benchmark、Memory、Persona Memory、User Voice 和 AI Check 的旧触发词由根 Eva 重定向到现有 Think/Create/shared 真源，不复制第二套模块。
- **通用诊断不丢失**：AI Check 和 Benchmark 仍可处理一般自然语言、公众号长文和图文样本；Create 本身继续只负责短视频生产。

## 入口边界

| 入口 | 负责 | 硬边界 |
|---|---|---|
| `eva` | 判断入口并同轮执行 | 不替代目标入口的内部闸门 |
| `eva-think` | 日常解释、现象讨论、问题归位、人设资格诊断 | 不直接写完整短视频稿 |
| `eva-create` | 短视频、视频标题、开头、正文、对标、视频稿检查 | 不处理普通朋友圈、微博、公众号写作 |
| `eva-learn` | 单概念学习、资料带读、系统学习、主题式阅读 | 必须先建档；建档失败停止 |
| `eva-brief` | 品牌 Brief、合作需求、商单约束、商单稿检查 | 不直接写完整商单稿 |
| `eva-link` | 创建、检查、调用已确认的本地 Link | 普通写作意图不自动触发 Link |

用户通过 `/eva` 提出普通朋友圈、微博、公众号或其他非短视频写作时，由基础模型直接完成，不加载 Eva Create、Brief 或 Link，也不把结果标记为经过 Eva 短视频闸门验证的资产。

## 开发验证

从仓库根目录运行：

```text
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-shared
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-think
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-create
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-learn
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-brief
python3 "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-creator/scripts/quick_validate.py" skills/eva-link
python3 skills/eva-shared/scripts/eva_doctor.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_prompt_lint.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_selftest.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_link_check.py --link skills/eva-shared/examples/eva.link.example.json
python3 skills/eva-shared/scripts/eva_link_check.py --link skills/eva-shared/examples/local.weibo-copy/ --strict
PYTHONPYCACHEPREFIX=/private/tmp/eva-shared-pycache python3 -m py_compile skills/eva-shared/scripts/*.py
```
