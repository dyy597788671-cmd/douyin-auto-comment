# 多设备任务分配与输出接口：第1版

2026-10-08。设备连接、选择手机、运行手机动作继续由影刀负责。未来前端负责输入和显示。本轮已经实现后台分配、账号进度、恢复和输出接口，尚未完成用户电脑上的影刀多设备入口接入及真机联调，不能把本文件或后台接入包当成已验证的影刀发布包。

## 上传人员的操作

填写现有作品信息，再填写执行设备数量。例如影刀当前连接5台，填写4，后台为该作品随机选4台；第五台不参与，也不影响这条任务结束。上传人员不填写各台设备状态。

新增输入字段只有 `Target_Device_Count`，表示执行设备数量，必须为正整数。它是参与设备数量，不是重复点击次数。旧十列表格仍可读取；这一列缺失或空白时沿用旧模式，不能当成已经启用多设备随机分配。

`Status`、`Executed_Actions`、`Result_Message`由后台回写。创建新任务时入口填写`PENDING`，不能留空。后续前端应自动填写这个初始值，不让上传人员处理内部状态。

## 分配名单和标记

- 当前连接名单必须由影刀管理流程在提交时传入，包含每台物理设备的固定标识和其当前执行账号。配置文件里的账号名单仅用于校验登记账号，不代表在线设备。
- 一个连接快照内，同一物理设备和同一执行账号各只能出现一次。临时投屏窗口名称、列表下标、目标作者ID不能用来替代固定标识。切换发送账号时使用新的发送账号标识。
- 执行数量大于实际连接数量时拒绝创建分配，不减少数量或拿未连接设备补齐。被锁定设备不参与；可执行数量不足也拒绝分配。其他任务中忙碌或冷却的设备可以被选中排队，待其空闲后领取。
- 每作品随机抽取一次，在项目锁内保存完整名单、分配ID、分配时间、当时连接快照及每个账号预留的不同评论。评论数量只需满足选中的设备数量，不需要满足整个设备池数量。
- 同一Task_ID重复提交或重启读取仍返回原名单；不重新抽取，不自动换人。已经分配后不得修改作品信息、执行数量或删除预留评论。新的执行批次使用新的Task_ID，保留此前结果。
- 每个账号在本分配中只有一份执行记录。只有名单内账号能领取，且必须传入其线程实际连接的物理设备标识，防止选错手机。一个物理设备不能同时由两个账号领取活动任务。

## 状态含义

| 记录范围 | 状态 | 含义 |
| --- | --- | --- |
| 某个账号 | PENDING | 已分配，尚未领取 |
| 某个账号 | RUNNING | 已领取，尚未结束 |
| 某个账号 | SUCCESS | 本账号本次执行成功 |
| 某个账号 | NOT_FOUND | 本账号未找到目标，成功计数均为0 |
| 某个账号 | FAILED | 本账号执行失败，已确认成功的部分动作仍保留 |
| 整个作品 | PENDING | 名单内全部账号尚未领取 |
| 整个作品 | RUNNING | 已经开始，名单内仍有未结束账号；当前无人正在点击也可能是在等待其余设备 |
| 整个作品 | SUCCESS | 名单内全部账号成功 |
| 整个作品 | NOT_FOUND | 名单内全部账号未找到 |
| 整个作品 | FAILED | 名单内全部结束，但存在失败或混合结果 |

是否结束以`completed`及`finished_device_count / target_device_count`为准，不能用“一台已成功”作为全项目结束，也不能把“全都结束”误写成“全都成功”。四台中只有三台结束时显示3/4，仍未结束。

选中的设备断开不会自动结束任务，也不会自动替换。恢复连接后使用原分配；只有尚未领取的分配允许明确由操作人通过`close_pending_assignment`结束为失败，记录操作人和原因，次数为0。已领取或存在不确定动作的任务必须核对执行进度，不能默认重做或自动清零。

## 结果数据

原有`execution_data/执行数据_<账号>.csv`六列保留：执行账号、项目ID、点赞次数、收藏次数、评论次数、分享次数。每个账号每个项目一行，完成结果重试不追加重复行。

新增`execution_data/project_progress.json`，也可通过`get_project_progress(task_id)`读取。第1版字段固定如下：

| 字段 | 内容 |
| --- | --- |
| schema_version | 输出结构版本1 |
| task_id / source_key | 项目ID与作品信息指纹 |
| allocation_mode | 新模式fixed_random；旧记录legacy |
| assignment_id / allocated_at | 固定分配ID与分配时间 |
| target_device_count / assigned_device_count | 要求数量与实际分配数量 |
| pending_device_count / running_device_count | 待领取与执行中的设备数 |
| finished_device_count | 已结束设备数，包含成功、失败、未找到 |
| success_device_count / failed_device_count / not_found_device_count | 各结束结果的设备数 |
| completed / status | 是否全部结束及整体结果 |
| counts | Like、Comment、Favorite、Share的成功总次数 |
| accounts | 本次名单内每个账号的详细记录 |

账号详细记录包含：sender_account_id、physical_device_id、status、run_token、claimed_at、finished_at、last_progress_at、resume_requires_review、comment_sent、planned_actions、executed_actions、counts、error_code、log_message。时间带时区，前端可转换北京时间显示。

同一账号同一任务每项动作成功最多计1。只把影刀上报的`PASSED`计为成功；失败、不确定、未执行均不计成功。单项目总成功次数不会超过分配设备数量。保留动作原始状态，不能把0解释为设备一定失败。

手机动作是否实际成功由影刀执行及确认后上报，后台不操作抖音或独立验证界面。现有动作记录卡把“动作卡正常结束”作为PASSED，尚无整段真机成功回读证明；不得把离线计数测试写成平台动作已成功。发生“点击已发生、成功确认尚未保存”时，不猜成功、不自动重放。

## 给后续开发的接口

```python
# 管理入口：必须使用影刀本次实际读取的连接信息。
connected_devices = [
    {"device_id": "实际设备标识1", "sender_account_id": "执行账号1"},
    {"device_id": "实际设备标识2", "sender_account_id": "执行账号2"},
]
module1.allocate_task(task_id, connected_devices)

# 每台影刀执行线程：连接到名单对应手机，再读取本线程任务。
task_data = module1.read_task(
    sender_account_id=sender_account_id,
    physical_device_id=physical_device_id,
)

# 每项动作确认后：覆盖返回列表，并持久化已确认进度。
executed_actions = module1.record_action_result(
    executed_actions, current_action, confirmed_status, "", task_data=task_data
)

# 整个账号结束时：沿用现有接口，传实际结束状态。
module1.finish_task(task_data, executed_actions, status="SUCCESS")

# 前端读取完整名单和计数。
module1.project_progress(task_id, sender_account_id=sender_account_id)
```

底层接口还提供`save_action_results(task_id, run_token, executed_actions)`与人工结束未领取分配的`close_pending_assignment(task_id, sender_account_id, operator, reason)`。CLI也支持这些操作；错误通过既有EngineError.code或CLI JSON错误结构返回。

`module1.read_task`对已领取的新分配默认拒绝重复启动。只有明确核对后可传`resume_active=True`恢复尚未生成互动策略的任务；已生成策略仍保持原来的核对保护，不自动再次执行手机动作。Gateway的`get_active_task`用于取回上下文，不表示允许重放。

## 影刀接入必须完成的项目

1. 多设备管理入口真实读取当前连接手机，建立固定物理设备标识与当前发送账号对应关系，调用allocate_task；不能用配置账号数代替连接数。
2. 每个执行线程连接指定手机并传递自己的账号及实际设备标识。不能所有线程保留手机01，也不能在新分配模式下先读取任务、随后随意选择另一台手机。影刀入口的实际参数/多实例方式尚未取得用户界面证据，不猜指令名称。
3. 所有手机截图卡的保存文件夹改为Python `task_data["workspace_path"]`。三个OCR读取路径分别使用以下单行Python表达式，沿用现有文件名：

```python
__import__("os").path.join(task_data["workspace_path"], "dy_filter_screen.png")
__import__("os").path.join(task_data["workspace_path"], "dy_result_screen.png")
__import__("os").path.join(task_data["workspace_path"], "dy_share_screen.png")
```

4. 现有动作记录调用增加Python参数`task_data=task_data`，使每项确认结果立即保存；旧四参数调用仍兼容，但只有RAM中的列表，不能标记为已接入中断进度保护。
5. 成功、未找到、异常三个出口都接回结果。未找到使用NOT_FOUND及空动作列表；异常使用FAILED并保留已确认动作。中断后只修复输出或核对活动上下文，不自动重新点击或发送。

同一电脑、同一项目根目录及同一运行状态文件由所有线程共享，使用同一版本代码。不要为每台设备复制独立runtime_state，否则不能保证分配和评论唯一性。系统使用OS锁、原子保存和写前事务；Excel运行中保持关闭，后续前端修改输入也必须通过统一入口协调写入，不能同时直接改文件。

旧项目进度和策略不转换为新分配、不删除、不清空。新Task_ID配新字段使用新模式。包不包含真实任务表或runtime_state，不覆盖用户数据。本轮没有修改现成手机元素、检索、作者核验、点击流程、互动顺序或冷却设置。

## 已验证范围

29项离线回归通过，其中原输出7项、新分配22项；包含5进程同时分配/领取且只有4台执行、固定名单重启保持、评论按4台检查、设备身份与同机互斥、部分失败/未找到计数、逐动作进度、旧结果迟到重试、Excel事务恢复、输出恢复、人工关闭未领取项、状态损坏拒绝清零、OCR文件目录隔离及重复线程保护。Python语法检查通过；AST核对作者核验、封面XPath、导航、互动策略、冷却和OS锁保持。

这些是临时测试数据，不是用户手机运行结果。用户电脑上的代码替换、设备入口接入、截图路径和动作记录卡修改尚未确认。完成这些接入并实测之后，才可称为影刀多设备发布流程已完成。
