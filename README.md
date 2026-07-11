# Eva Skill v2.1.1

当前版本：`2.1.1`。

Eva Skill 帮助创作者把模糊想法梳理成更清楚、更有依据的判断，并把它们做成短视频表达。它同时提供学习、商单拆解、本地工作流接入、发布后复盘和多元视角补充能力。2.1.1 新增独立的新手教程和裸 `/eva` 轻量欢迎语，原有任务入口与质量边界保持不变。

## 结构

```text
skills/
├── eva/              # 主路由，同轮执行目标入口
├── eva-new-user/     # 动态扫描已安装能力，按用户节奏教学
├── eva-think/        # 日常解释、陪聊梳理、问题归位
├── eva-create/       # 短视频、标题、开头、正文
├── eva-learn/        # 学习、资料带读、主题式阅读
├── eva-brief/        # 商单 Brief 与合作约束
├── eva-link/         # 本地 Link 创建、检查、调用
├── eva-review/       # 全平台发布后复盘与规律回溯
├── eva-lens/         # 多元视角快速补光与深度审视
└── eva-shared/       # 共享协议、schema、脚本和示例
```

安装时必须同时安装十个目录。`eva-shared` 不是用户入口，但其他入口需要它提供共享协议和校验真源。

## 2.1.1 新增

- **Eva New User**：独立 `/eva-new-user` 新手教程。开始前扫描当前环境实际安装的 Eva Skill，只介绍已确认可用的能力。
- **动态教学**：不使用固定课表。用户可以随时说“跳过”、指定提前学习的功能，或退出教程直接处理真实任务。
- **裸启动欢迎语**：用户只输入 `/eva` 或“启动 Eva”时，先给轻量引导，并询问是否开启新手教程；不判断、不保存用户的新旧状态。
- **标题草案两轮规则**：第一次直接要稿仍强制进入标题搜索；只有提醒后第二次明确接受未验证边界，才输出不能直接发布的草案。
- **Learn 单文件锚点**：第一讲前先创建 `00-学习进度.md`，第一讲内容形成后再创建问答原稿和必要资料索引，保证不漏档也不预建空文件。
- **正文路线分级**：标题闸门之后，普通非商单稿走简版路线；商单、冲突、复杂故事、材料双薄和完整发布审查仍走完整路线图。

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

从仓库根目录运行十个 Skill 的 `quick_validate.py`，再运行：

```text
python3 skills/eva-shared/scripts/eva_doctor.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_prompt_lint.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_selftest.py --base skills/eva-shared
python3 skills/eva-shared/scripts/eva_link_check.py --link skills/eva-shared/examples/eva.link.example.json
python3 skills/eva-shared/scripts/eva_link_check.py --link skills/eva-shared/examples/local.weibo-copy/ --strict
PYTHONPYCACHEPREFIX=/private/tmp/eva-shared-pycache python3 -m py_compile skills/eva-shared/scripts/*.py
```
