# B机迁移完成与局域网工具开发接续（2026-10-10 08:57，北京时间）

## 1. 最新指令与下一步

用户最新明确指令：“能工具解决的先解决；需要影刀程序解决的后续再慢慢改。先同步当前进度，用户将开启新会话开发那个工具。”

新会话直接开始开发原定的一个局域网工具。旧计划“先完成断线异常隔离并真机通过，再迁移、再工具”已被本次顺序调整覆盖。B机已能启动运行，断线异常隔离尚未通过；二者必须分开记录。本轮仅同步，不开发工具、不继续改影刀卡片、不启动新测试。

工具沿用已确认四项功能：录入新任务、提交历史及执行汇总、查看错误、定向清理异常任务与停止后的运行残留。保持B独立执行，其他电脑只访问同一网页；不建立第二个工具、多电脑共享执行、注册账号平台或新调度系统。

## 2. B机已确认环境与文件位置

| 项目 | 已确认值 |
| --- | --- |
| B账号 | 894802265707544578 |
| B应用 | 抖音迁移B |
| B应用UUID | 84fca2ea-8671-4147-8b20-99d5663016e6 |
| 应用编号目录 | C:\Users\Administrator\AppData\Local\ShadowBot\users\894802265707544578\apps\84fca2ea-8671-4147-8b20-99d5663016e6 |
| 实际影刀Shell/Runtime版本目录 | D:\app\ShadowBot\shadowbot-6.3.31 |
| 实际Runtime DLL | D:\app\ShadowBot\shadowbot-6.3.31\ShadowBot.Runtime.dll |
| 自带dotnet | D:\app\ShadowBot\dotnet.win-x64\dotnet.exe |
| 原生模块 | 应用编号目录\xbot_robot\module1.py |
| 外部业务引擎 | 应用编号目录\core_runner.py |
| 唯一业务表格 | 应用编号目录\data\task_cases.xlsx |
| 正式运行状态 | 应用编号目录\data\runtime_state.json |
| 业务配置（可选） | 应用编号目录\config\settings.json |
| 业务日志 | 应用编号目录\logs\execution.log |
| 独立任务错误日志（可能尚未生成） | 应用编号目录\logs\execution_errors.jsonl |
| 既有执行数据 | 应用编号目录\execution_data\project_progress.json 及 执行数据_<账号>.csv |

应用编号目录并列存在copilot、signature-backups、venv、xbot_extensions、xbot_robot及业务目录。外部Python、config、data、execution_data、logs与xbot_robot并列放置。不要把旧data\module1.py当实际应用模块；原业务包里的.core_runner.lock不作为迁移文件。

B注册表曾显示安装版本5.31.34，但运行进程已证明实际Shell及加载Runtime来自6.3.31。不要继续按5.31.34或旧6.2.23选择B签名运行时。用户禁止发版；已通过本地文件方式完成迁移。

## 3. 已完成的迁移与真实验证

1. 修改B的package.json uuid/name后，跨账号签名曾提示应用损坏；已调用B本机ShadowBot原有PackageHelper方法处理，用户输出before=False、after=True、RESULT=REPAIRED。随后三个流程均可正常显示。
2. 缺失 %LOCALAPPDATA%\ShadowBot\mobile_device_connects.json：用户打开手机管理器后解决。不从A复制这个机器连接配置，不手造设备名单。
3. 之前任务1015/1016提示需按实际连接设备分配，错误栈明确进入module1.main() -> read_task()，跳过正常主流程的分配步骤。用户当前主流程第7行已确认“选择模块module1、选择函数prepare_devices”。输入参数及输出变量未在本轮逐项核实，不得补造。
4. 已交付ShadowBot_B_migration_fix.zip，用户在B运行repair_shadowbot_B_migration.ps1成功。实际修改：
   - module1的PROJECT_ROOT自动从其自身位置取得应用编号目录；
   - 下次打开的编辑流程从module1改为main；package.startup原本已为main；
   - 签名检查before=True、RESULT=ALREADY_VALID；
   - RESULT=MIGRATION_CONFIG_REPAIRED。
5. 用户随后亲自运行并报告“可运行了”。这证明B已能够启动并进入实际运行，不等于全部手机动作、断线恢复或长期稳定运行均已通过。
6. B的data和date各有一份task_cases.xlsx；用户脚本输出SHA256完全相同：
   B76FA6C26363A522B3CF57DBA2154BFD9C2669BFECED9EB526C8EAB10A7C14B5。
   当前代码只读取data\task_cases.xlsx。没有自动覆盖或合并表格，也没有删除date；工具须使用data这一真实读取位置。
7. B没有业务config\settings.json，沿用默认sender_accounts=[]自动身份模式；本机手机管理器配置存在；脚本要求的核心文件与模块接口存在。

当前B根目录定义为：
```python
PROJECT_ROOT = str(__import__("pathlib").Path(__file__).resolve().parent.parent)
```
这项修正发生在B实际module1中，不代表A的开发源或GitHub业务代码已同步换成B路径。

## 4. 本轮确认仍未解决的问题

- 某台手机连接一段时间后直接断开，出现失去连接类错误（用户口述；完整报错文字、行号、具体异常类型未提供）。
- 该异常导致整个影刀流程停止，未实现预期“单台失败、其余继续”。
- 用户再次启动曾提示“ID已经被占用”。具体ID类别和完整错误未提供，不能确定是Task_ID、执行账号、物理设备还是影刀内部连接会话占用。
- 未读取B当前runtime_state.json，不能把“活动任务一定未释放”写成已经验证的结论；未正常结束的RUNNING/active_task残留是需要检查的候选。
- 用户此前已清空runtime状态及表格发布记录，理解这些文件可以重新生成；无需为此次工具开发强制恢复A旧记录。已有归档仅是备份时快照，不代表B最新执行数据。
- Try/Catch、FAILED结束和独立错误记录曾按指导添加；最新实际断线路径仍停止，不能把配置已添加写成断线隔离已运行通过。
- 可能需要后续影刀修复的边界：连接/任务领取异常、一次任务异常结束、收尾失败、主流程调用子流程传播。离线手机无法执行回推荐页，其他设备继续不能依赖它完成回退。本轮不直接定位根因或修改卡片。
- 主/子可视化.pybx和.dev流程数据受编码保护，当前环境不能直接取得全部卡片参数；缓存中的单步运行残留不能当作当前完整主流程。不要让用户逐卡重核全项目，也不要重复要求上传已有应用归档或右侧属性图。

## 5. 工具开发的固定范围

### 5.1 一个入口与权限

B机提供同一个后台和网页，B本机通过127.0.0.1访问，其他电脑通过B局域网IP访问。其他电脑只查自己的提交、汇总、错误，只清理自己已经结束的异常任务。B本机查看及处理全部；强制中断后的占用残留仅B停止影刀后处理。

浏览器持久标识与Task_ID关联，后台核对归属，IP只记来源。保持既定最小设计，不加注册、用户权限管理平台、多项目管理或网页远程停止影刀。

### 5.2 录入与执行接入

复用当前任务表必填字段、现有设备分配器及锁。工具自动生成新Task_ID及合法默认值，新提交先暂存。在现有条目边界接入表格并完成设备分配，不把“网页写入Excel”冒充“影刀已经能领取新任务”。需要影刀侧最小接入的位置留作明确对接项，不为此重排手机动作或当前设备/条目循环。

### 5.3 汇总与错误查看

复用project_progress和单账号CSV的实际成功计数，每设备每动作成功最多计1。提交记录保存关键词、昵称、归属和历史。错误同页提供明确入口，清理后仍可查看已记录的原错误。

当前断线异常可能没有进入module1.finish_task和独立JSONL。开发时先核对实际现有日志，不假定execution_errors.jsonl一定存在或包含全部影刀错误。可关联Task_ID的错误按归属展示；无法关联任务的程序错误仅B本机展示。不承诺工具能从不存在的记录还原全部历史错误；不新增诊断平台或日志成功才能清理的门槛。

### 5.4 定向清理与占用

复用现有项目锁，针对选定Task_ID一致处理表格条目、该任务分配/活动残留/待回写及必要派生数据；保留其他任务、原提交、独立错误日志与已留存历史。

正常执行中的任务不删除。异常中断后先在B停止影刀，再处理确认属于项目文件的残留。只删Excel行不能当作释放活动任务；整份runtime_state删除不作为工具的默认清理动作。

工具可以处理本项目数据层残留。若占用实际来自影刀内部手机会话或连接驱动，工具不能仅删业务记录就声称已经修复；这类问题保留为后续影刀问题。界面不混淆“清理记录”与“手机恢复连接/流程自动继续”。

## 6. 禁止扩大范围与接续依据

- 用户明确拒绝回推荐页循环次数上限；不设置，卡住由用户手动处理。旧计划的次数上限已被用户覆盖。
- 保留已通过的搜索、筛选、作者核验、互动动作、计数、设备身份及当前顺序。
- 不添加自动重试整个任务、复杂恢复树、逐动作异常包装、多设备并行、新等待体系、提醒/已查看/已清理标记或独立刷新流程。
- 新会话先完整读PROJECT_RULES.md本次最新规则、本文、STABILITY_AND_TOOL_PLAN_20261010.md，再读取实际要使用的core_runner.py和模块接口，直接开发工具。
- 先实现工具可解决的功能；断线后自动释放、跳过离线手机并继续其他执行的影刀修复后续处理。本轮未开始工具开发，也未实际清理B数据。

已存在资料，不重复索取：
- 当前A应用归档：85829411-64c6-4d5b-b15e-f0789566bb75.rar，Library libfile_f69fffce56588191b3a1f369776bea92。
- 业务备份：抖音自动发布工具3.rar，Library libfile_5db37ac2ed9881918f5c07c756b76820；其中data/module1.py为旧副本，不用来替换当前模块。
- 签名修复脚本：repair_shadowbot_B_signature.ps1，Library libfile_eff5154d5a688191810f329efd397cbc，B曾存放Y:\01_文件中转。
- 迁移配置包：ShadowBot_B_migration_fix.zip，Library libfile_39009c5a16648191ada7b9e45cfab42c。
- 主流程名称清单：主流程.txt，Library libfile_975df2ec02688191ba82238ce435694c。
- B迁移包只修必要配置、路径及签名，不包含网页工具或断线异常隔离修复。
