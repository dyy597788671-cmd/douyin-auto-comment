# 抖音多手机项目基础框架

代码版本：**0.1.0**。文档修订：**1.4**。

本地工作台已实现设备与登录账号登记、目标账号管理、人工核验任务、内容记录、日志和 SQLite 数据保存。影刀适配层尚未接入，自动搜索、身份识别与互动执行尚未实现。

完整需求流程：选择目标与关键词 → 选择执行账号 → 搜索并筛选内容 → 核对作者 → 身份相符后返回内容页 → 随机点赞、评论、转发。随机规则见架构说明。养号不在项目范围内。

## 文档与交付

- [运行说明](PhoneWorkbench/README.md)
- [需求流程与架构](PhoneWorkbench/docs/架构说明.md)
- [本地 AI 安装与接入任务](PhoneWorkbench/docs/交给本地AI.md)
- [Word 需求与开发交接文档](docs/影刀多手机项目_需求与会话交接文档.docx)
- [基础框架包](dist/PhoneWorkbench_v0.1.0_基础框架.zip)
- [验证记录](PhoneWorkbench/docs/验证记录.md)
- [开发规则](PROJECT_RULES.md)
- [版本记录](CHANGELOG.md)

## 启动

需要 Python 3.10 或更新版本，无第三方 Python 依赖。将框架包中的 `PhoneWorkbench` 放入 `D:\备份文件\项目库\抖音自动发布工具`，双击 `启动工作台.bat`，访问 `http://127.0.0.1:8765`。

账号资料与数据库保存在本机 `PhoneWorkbench/data`。当前任务的“完成”表示人工核验完成。

## 开发入口

继续开发前读取 `PROJECT_RULES.md`、`PhoneWorkbench/docs/架构说明.md`、`CHANGELOG.md` 和 `BASELINE_MANIFEST.json`。代码、文档与交付包更新均需提交本仓库并核对远端结果。

在 `PhoneWorkbench` 内运行 `python -m unittest discover -s tests -v`；前端逻辑检查使用 `node tests/test_ui.cjs`。
