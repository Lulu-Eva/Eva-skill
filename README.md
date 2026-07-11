# Eva Skill v2.1.0

当前版本：`2.1.0`。

Eva Skill 是面向创作者的思考、短视频创作、学习、商单拆解、本地工作流接入、发布后复盘和多元视角补充工具。2.1.0 保留建档、验证、隐私、交接和质量闸门，同时让高频入口保持轻启动。

## 结构

```text
skills/
├── eva/              # 主路由，同轮执行目标入口
├── eva-think/        # 日常解释、陪聊梳理、问题归位
├── eva-create/       # 短视频、标题、开头、正文
├── eva-learn/        # 学习、资料带读、主题式阅读
├── eva-brief/        # 商单 Brief 与合作约束
├── eva-link/         # 本地 Link 创建、检查、调用
├── eva-review/       # 全平台发布后复盘与规律回溯
├── eva-lens/         # 多元视角快速补光与深度审视
└── eva-shared/       # 共享协议、schema、脚本和示例
```

安装时必须同时安装九个目录。`eva-shared` 不是用户入口，但其他入口需要它提供共享协议和校验真源。

## 2.1.0 新增

- **Eva Review**：只有一个 `/eva-review` 入口，内部自动判断单篇复盘、批量规律回溯和结果回填。支持多平台、多账号、截图、Excel、CSV 和逐条口述。单篇只形成待验证假设，不做确定归因；记录库经首次授权后保存到当前项目 `./eva-review/`。
- **Eva Lens**：默认从读者、反对者、现实行业和创作者四个视角快速补光；用户明确要求时进入深度审视。Lens 不模拟人物、不建档、不保存、不自动联网搜索。
- **主路由扩展**：`/eva` 可以同轮进入 Think、Create、Learn、Brief、Link、Review 或 Lens。

## 核心边界

- Think 负责把尚未成形的问题聊清楚；Lens 负责审视已经成形的判断。
- Create 只负责短视频生产；Review 可以复盘全平台已发布内容。
- Review 记录与 shared 交接卡分离，数量不能替代数据可比性。
- Lens 不生成 `lens-card`；需要真实论据时交 Learn 或搜索，需要保存时交 Memory。
- 普通朋友圈、微博、公众号写作仍由基础模型或明确 Link 处理，不套短视频 Create 闸门。

## 开发验证

从仓库根目录运行九个入口的 `quick_validate.py`，再运行：

```text
python3 skills/eva-shared/scripts/eva_doctor.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_prompt_lint.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_selftest.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_link_check.py --link skills/eva-shared/examples/eva.link.example.json
python3 skills/eva-shared/scripts/eva_link_check.py --link skills/eva-shared/examples/local.weibo-copy/ --strict
PYTHONPYCACHEPREFIX=/private/tmp/eva-shared-pycache python3 -m py_compile skills/eva-shared/scripts/*.py
```
