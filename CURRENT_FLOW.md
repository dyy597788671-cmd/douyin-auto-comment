# 当前影刀流程基线

时间：2026-10-06。用户当前主流程为61行；尚未在用户电脑修改。以下为截图逐行转录，涉及长表达式以本文件后半部分的用户补充为准。

| 原行号 | 操作 | 截图中可确认内容 |
|---|---|---|
| 1 | 调用模块 | module1.read_task，返回 task_data |
| 2 | 设置变量 | target_author = task_data["expected_author"]，字符串 |
| 3 | 连接手机 | Appium模式，运行时手动选择，返回 phone_device |
| 4 | 打开手机APP | phone_device；com.ss.android.ugc.aweme；激活到屏幕 |
| 5 | 等待 | 3—10秒 |
| 6 | 点击元素(手机) | 抖音搜索入口；单击中心 |
| 7 | 输入文本(手机) | phone_device；抖音搜索输入框；task_data["keyword"] |
| 8 | 点击元素(手机) | 搜索按钮；单击中心 |
| 9 | IF | task_data["search_section"] 等于 图文 |
| 10 | 点击元素(手机) | 搜索分区_图文；在9内 |
| 11 | End IF | 结束9 |
| 12 | IF | task_data["search_section"] 等于 视频 |
| 13 | 点击元素(手机) | 搜索分区_视频；在12内 |
| 14 | End IF | 结束12 |
| 15 | 点击元素(手机) | 抖音筛选入口 |
| 16 | 点击屏幕(手机) | phone_device；通过图像匹配取得坐标；具体图像及设置未展示 |
| 17 | 点击屏幕(手机) | 同上，具体目标未展示 |
| 18 | 点击屏幕(手机) | 同上，具体目标未展示 |
| 19 | 设置变量 | author_check_result = NOT_FOUND，字符串 |
| 20 | While条件循环 | True 等于 True |
| 21 | 获取相似元素列表(手机) | phone_device；搜索结果作者昵称；获取文本；返回 author_name_list；在20内 |
| 22 | 打印日志 | 信息；目标昵称和本屏读取昵称；长表达式在截图中被截断；在20内 |
| 23 | IF | 表达式以 task_data["expected_author"] in… 开头，比较 True；完整表达式未展示；在20内 |
| 24 | 获取元素对象(手机) | phone_device；XPath以 //*[@resource-id='com.ss.andr… 开头；返回 mobile_element_result；完整XPath未展示；在23内 |
| 25 | 点击元素(手机) | mobile_element_result；单击中心；在23内 |
| 26 | 设置变量 | is_tuwen，布尔；表达式 task_data["content_type"] == "图… 被截断；在23内 |
| 27 | IF | is_tuwen 等于 True；在23内 |
| 28 | 点击元素(手机) | 图文作者头像；在27真分支 |
| 29 | Else | 对应27 |
| 30 | 点击元素(手机) | 视频作者头像；在27假分支 |
| 31 | End IF | 结束27 |
| 32 | 获取手机元素信息 | 文本；抖音主页_账号；返回 profile_douyin_id_raw；在23内 |
| 33 | 获取手机元素信息 | 文本；主页_作者昵称；返回 profile_author_name_raw；在23内 |
| 34 | 调用模块 | module1.verify_author；传 task_data、profile_douyin_id_raw、profile_author_name_raw；返回设置未展示；在23内 |
| 35 | 点击按键 | phone_device；后退；在23内 |
| 36 | IF | author_check_result 等于 MATCH；在23内 |
| 37 | 退出循环 | 退出当前循环；在36内 |
| 38 | End IF | 结束36 |
| 39 | IF | author_check_result 等于 MISMATCH；在23内 |
| 40 | 点击按键 | phone_device；后退；在39内 |
| 41 | End IF | 结束39 |
| 42 | IF | author_check_result 等于 UNCERTAIN；在23内 |
| 43 | Raise | 作者抖音号核验不确定，请检查任务表中的抖音号及主页读取结果；在42内 |
| 44 | End IF | 结束42 |
| 45 | End IF | 结束23 |
| 46 | IF 图像存在(手机) | phone_device；目标图像显示名为“图像”；实际图像未展示；在20内 |
| 47 | 退出循环 | 退出当前循环；在46内 |
| 48 | End IF | 结束46 |
| 49 | 滑动手机屏幕 | phone_device；向上滑动；在20内 |
| 50 | 循环结束标记 | 结束20 |
| 51 | IF | author_check_result 等于 MATCH |
| 52 | 调用模块 | module1.prepare_interactions；task_data；返回 interaction_plan；在51内 |
| 53 | 设置变量 | executed_actions = []，列表；在51内 |
| 54 | ForEach列表循环 | interaction_plan["execution_orde… 被截断；循环项 current_action；在51内 |
| 55 | IF | current_action 等于 Like；在54内 |
| 56 | IF | interaction_plan["content_type"] 等于 视频；在55内 |
| 57 | 获取手机元素信息 | 获取属性；视频——点赞按钮（图中显示）；返回 like_state_raw；具体属性未展示；在56内 |
| 58 | End IF | 结束56 |
| 59 | End IF | 结束55 |
| 60 | 循环结束标记 | 结束54 |
| 61 | End IF | 结束51 |

## 用户补充的完整配置

- 原16：最新发布，图像识别。
- 原17：一天内，图像识别。
- 原18：红色底框“查看结果”，图像识别。
- 原46：“暂无更多，查看所有内容”，图像识别；作为展示结束标记，不点击它。
- 原23：Python `task_data["expected_author"] in author_name_list`，比较True。
- 原26：本次定稿以 `task_data["content_type"] == "图文"` 写入is_tuwen。
- 原34：module1.verify_author；输入task_data、profile_douyin_id_raw、profile_author_name_raw；返回任意类型；输出author_check_result。已核对正确。
- 原54的执行列表键在截图中被截断，定稿互动块暂禁用，未来恢复时核实；本阶段无需改其业务。
- 当前module1完整代码由用户上传文本提供，对应module1.baseline.py；原逻辑留存，新的两个纯计算函数位于module1.py末尾。

原24行完整表达式：

```python
"//*[@resource-id='com.ss.android.ugc.aweme:id/dp7'][count(.//*[@resource-id='com.ss.android.ugc.aweme:id/rej'])=1 and .//*[@resource-id='com.ss.android.ugc.aweme:id/-+' and @text=concat(''," + ", \"'\", ".join("'" + part + "'" for part in task_data["expected_author"].split("'")) + ")]]//*[@resource-id='com.ss.android.ugc.aweme:id/rej']"
```

导航实据：初始截图可见综合、团购、视频、直播、用户；图文隐藏在右侧。横向滚动后可见用户、图文、商品、音乐、话题、小程序。用户已确认不同设备栏目顺序不同，不能按固定序号或某机型坐标定位。

![原1—61行拼接图](CURRENT_FLOW.png)
