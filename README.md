# 抖音多手机项目基础框架

本项目基于影刀连接手机，由本地工作台管理设备、目标账号、核验任务、内容记录和日志。当前代码版本为 **0.1.0**，文档修订为 **1.2**。

完整需求流程保留“搜索内容 → 核对作者 → 返回内容页 → 随机点赞、评论、转发”的动作节点及原有随机规则。互动动作继续保留为项目功能需求，当前基础框架尚未实现；暂停的只是多账号养号流程。当前框架的任务完成仅表示人工核验完成，不代表完整业务流程已完成。

## 当前交付

- [基础框架源码与启动说明](PhoneWorkbench/README.md)
- [架构说明和完整需求流程](PhoneWorkbench/docs/架构说明.md)
- [交给本地 AI 的安装说明](PhoneWorkbench/docs/交给本地AI.md)
- [Word 需求与会话交接文档](docs/影刀多手机项目_需求与会话交接文档.docx)
- [基础框架下载包](dist/PhoneWorkbench_v0.1.0_基础框架.zip)
- [验证记录](PhoneWorkbench/docs/验证记录.md)
- [项目固定规则](PROJECT_RULES.md)

## 启动

下载并解压 `dist` 中的框架包，将 `PhoneWorkbench` 文件夹放到 `D:\备份文件\项目库\抖音自动发布工具`，双击 `启动工作台.bat`。需要 Python 3.10 或更新版本，不需要安装第三方 Python 包。

启动后访问 `http://127.0.0.1:8765`。实际账号资料与数据库仅保存在本机，运行数据不提交仓库。

影刀与真实手机尚未接入，设备连接状态明确显示待确认。本地 AI 需先检查真实影刀版本、套餐、手机指令与连接情况，再确定接入方式。

## 继续开发

每次新会话先读取 `PROJECT_RULES.md`、本 README、`PhoneWorkbench/docs/架构说明.md` 和 `CHANGELOG.md`。**任何代码、文档与框架包更新都必须同步到本仓库，并核对远端提交结果。**

验证命令：在 `PhoneWorkbench` 中执行 `python -m unittest discover -s tests -v`。可选前端逻辑验证为 `node tests/test_ui.cjs`。
