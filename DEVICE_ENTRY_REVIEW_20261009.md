# 多设备接入修订方案（2026-10-09）

本稿替代上一版任务队列、定向领取与Try/Catch方案。用户最新原则：仅处理设备切换和任务分配；已通过的手机执行段继续复用；去掉后不影响功能的内容不加。

## 当前目的与配置事实

尽快完成通用设备接入，然后继续原定切设备测试。用户已确认当前前五行：
1. 连接手机 → phone_device。
2. 获取手机连接详情 → phone_connection_info；输入是手机对象下拉框。
3. physical_device_id = Python phone_connection_info["udid"]。
4. sender_account_id = Python "设备_" + physical_device_id。
5. module1.read_task；账号已传变量，adopt_legacy=False；physical_device_id尚未传入。

第6行仍为target_author。此前建议的IF尚未添加。用户本地其余手机操作继续保留。本轮没有操作用户手机、修改其任务表或执行记录。

## 后台实际改动

仅修改module1.py：
- 新增prepare_devices(connection_infos)：读取实际连接详情、自动建立身份，调用原有allocate_task，返回需要执行的设备与连接对象下标。
- 扩展已有read_task，增加wait_for_task=False。正式多设备调用设为True：沿用原get_next_task领取；冷却中或未到计划时间时等待；本设备没有未完成分配才返回None。
- 一个内部计算等待时间的函数，等待前释放项目锁。

core_runner.py与已核对基线逐字相同。其他已有桥接函数的AST均保持相同。未增加第二套任务清单、指定Task_ID领取、结果覆写或手机异常包装。

prepare_devices返回字段：device_id、sender_account_id、connection_index。没有task_ids队列字段。设备身份仍为“设备_”加当前udid，新手机由连接详情自动识别。

## 管理入口的确定顺序

| 顺序 | 内容 |
|---|---|
| 1 | 连接影刀本次实际连接的全部手机 → phone_devices |
| 2 | connection_infos初始化为空列表 |
| 3 | 遍历phone_devices → phone_device |
| 4 | 获取当前phone_device连接详情 → phone_connection_info |
| 5 | connection_infos = connection_infos + [phone_connection_info] |
| 6 | 结束连接详情循环 |
| 7 | prepare_devices(connection_infos) → device_bindings |
| 8 | 遍历device_bindings → device_identity |
| 9 | 调用同一个设备执行子流程，传对应手机对象与device_identity |
| 10 | 结束设备分发循环 |

对象传参关系：

```python
{"phone_device": phone_devices[device_identity["connection_index"]], "device_identity": device_identity}
```

测试时顺序调用，保持第一台完整执行后再第二台。正式运行并发调用同一子流程，子流程运行至自身结束。对应指令面板和手机对象输入类型在实际配置阶段核对，未见面板不编造字段。

当前单手机连接及详情逻辑复用到管理入口。执行身份在prepare_devices自动生成，不让用户逐台录入UID或改Python账号文本。

## 设备任务读取的确定规则

设备子流程接收phone_device和device_identity。读取使用已有read_task：

```python
module1.read_task(
    sender_account_id=device_identity["sender_account_id"],
    adopt_legacy=False,
    physical_device_id=device_identity["device_id"],
    wait_for_task=True
)
```

单条任务的搜索、作者核验、手机动作及既有回写沿用当前段。

正式连续运行只需在现有单条任务段外加任务循环：
1. 调用read_task得到task_data。
2. task_data为None时结束当前设备子流程。
3. 有任务时运行现有单条任务段。
4. 本次正常结束后再次读取下一条。

第2步是任务循环的结束条件，省略会重现索引None错误；它不检查手机动作。冷却与计划等待已经在read_task内部区分，不另加等待IF。

切设备的单任务测试阶段保留现有执行段。在连续多任务阶段，“未找到”出口需要与正常出口共用现有首页回退，确保下一次搜索从原流程所需页面开始。这只复用现有回退段，不增加首次页面检查或新检测。相应移动位置在实际施工台账中登记，本文不把计算出的整段行号当成已确认位置。

实际运行异常仍按原流程报错并停止，不新增Try/Catch、自动改FAILED或动作重试。本轮不重新审查手机执行逻辑。

## 表格、旧数据与设置

所有设备共享同一项目根目录、task_cases.xlsx和runtime_state.json，使用原有锁与回写机制。

正式分配任务填写Target_Device_Count、Status=PENDING。任务只有一行；后台为同一Task_ID保存各设备的独立执行记录。执行设备数量是已有分配接口的必需输入，缺失时明确报错，不静默跳过。

config/settings.json的sender_accounts需要为空列表[]，使自动身份不受旧手填账号名单限制。这是一次性模式设置，不是逐台登记。已有冷却值和其他设置保持原值；不随测试清空状态。

旧“手机01”测试结果保留，新测试使用新Task_ID。候选评论满足所选设备数量，沿用原预留机制。已分配任务保持原名单；后续新增设备在下一次启动时自动参与新任务分配。

## 三组并发图片路径

并发需要修改三个截图保存文件夹与三个对应OCR图片路径；原文件名保留。截图文件夹为Python task_data["workspace_path"]。

| 用途 | 当前台账截图/OCR行号 | OCR路径（Python） |
|---|---|---|
| 筛选 | 46 / 47 | __import__("os").path.join(task_data["workspace_path"], "dy_filter_screen.png") |
| 搜索结果 | 89 / 90 | __import__("os").path.join(task_data["workspace_path"], "dy_result_screen.png") |
| 分享 | 175 / 176 | __import__("os").path.join(task_data["workspace_path"], "dy_share_screen.png") |

当前行号由已确认190行基线及本轮净增加3行推算；后续搬为子流程后按实际台账重排。单设备顺序测试不因这些文件产生同时覆盖；正式并发前需要完成路径接入。

## 自行检查结果

38项离线检查通过：原有29项回归加9项设备入口测试。新增测试覆盖：
- 第一台完成后，第二台仍领取同一Task_ID，结果和图片目录独立。
- 新设备和连接顺序变化无需登记账号，手机对象下标仍正确。
- 五台只选择指定三台，未选中设备不参与。
- 缺执行数量明确报告，空任务表不启动工作。
- 计划与冷却等待不结束设备线程，等待不占用项目锁。
- 重新启动保持原名单，仅处理未结束设备。
- 领取写入后发生异常，重启仍暴露RUNNING活动任务，不再当成无任务。
- 未找到记录只属于当前设备。

领取异常保留原引擎的停止与活动记录机制，未实现自动续跑；这是对既有行为的保持。本轮没有添加新的异常判定。检查证明后台接入行为，不代表已经替换用户模块或完成新一轮手机运行。

AST核对：原函数仅read_task有变化；其他原桥接函数不变。core_runner.py字节一致，Python语法检查通过。

## 后续配置顺序

1. 替换影刀应用内module1.py为随包版本；核对一次性自动身份设置。
2. 按上述结构整理设备管理入口，复用现有设备执行段；一次指导一张卡，字段以实际界面为准。
3. 接入read_task的physical_device_id与wait_for_task，并处理正常任务结束。
4. 按原计划完成两台视频的顺序测试，再处理图文切设备测试。
5. 接入连续任务循环和必要的共用返回段、独立图片路径后，进行正式并发。

目前用户本地仍停在已确认前五行，未开始新一轮配置。新的实际设备调用参数、子流程类型及编辑器行号不能写成已配置完成。
