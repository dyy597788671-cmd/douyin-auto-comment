# 当前影刀实际流程

## 2026-10-06 18:19 执行检查点

- 用户已自行备份；应用内module1已替换；原51—61互动块已整体禁用。不得重复要求。
- 已完成第1—3批配置。当前行数按修改链推算87，尚无全流程导出复核；1—76启用，77—87禁用。
- 最后截图：元素text为全局变量选择标签；第15行search_sections ForEach → current_section，第16行全局nav_section=current_section。已确认配置绑定，未从头进行手机实测。
- 当前41—44为原筛选四条；45仍为原20的旧While；46昵称、47日志、48原昵称IF；74原结果上滑、75结果循环结束、76栏目循环结束。
- 下一步：在当前45旧While前插入布尔设置变量section_finished=False；插入后旧While成为46，再修改它的条件。每次按实际新增重新计算行号。
- 当前第21行等待元素保持5秒；左右滑动第28/30行800毫秒、执行后延迟1秒。用户不赶时间，不能擅自缩短5秒等待。
- 抖音搜索栏目末端text通过fx列表选择全局nav_section，不再手输current_section；全局字符串nav_section默认图文，每轮由第16行赋值。
- nav_container结构XPath和bounds、等待超时False及屏幕外栏目可见性、动态栏目点击、跨手机定位均尚未手机实测。
- 业务继续按原定稿执行：先类型再综合、同屏同名逐卡片ID核验、ID不同继续并最终提示“抖音号不同”、MATCH退出所有搜索循环且留作品；ID读取失败自然报错；企业/互动本阶段不实现。

## 当前87行（按用户逐次确认推算）

| 当前行 | 影刀指令 | 配置与输出 | 来源 | 状态 |
|---|---|---|---|---|
| 1 | 调用模块 | module1.read_task() → task_data | 原1 | 启用 |
| 2 | 设置变量 | target_author = task_data["expected_author"]（字符串） | 原2 | 启用 |
| 3 | 连接手机 | 保留Appium、运行时手动选择 → phone_device；沿用现有参数 | 原3 | 启用 |
| 4 | 打开手机APP | phone_device；com.ss.android.ugc.aweme；激活到屏幕 | 原4 | 启用 |
| 5 | 等待 | 保留现有3—10秒 | 原5 | 启用 |
| 6 | 点击元素(手机) | 抖音搜索入口；单击中心；保留现有参数 | 原6 | 启用 |
| 7 | 输入文本(手机) | 抖音搜索输入框；task_data["keyword"]；phone_device | 原7 | 启用 |
| 8 | 点击元素(手机) | 搜索按钮；单击中心；保留现有参数 | 原8 | 启用 |
| 9 | 获取元素对象(手机) | phone_device；XPath "//android.widget.HorizontalScrollView[.//androidx.appcompat.app.ActionBar.Tab]" → nav_container | 新增 | 启用 |
| 10 | 获取手机元素信息 | phone_device；操作目标nav_container；获取属性bounds → nav_bounds_raw | 新增 | 启用 |
| 11 | 调用模块 | module1.make_nav_swipe_points(nav_bounds_raw) → nav_swipe_points | 新增 | 启用 |
| 12 | 设置变量 | search_sections = [task_data["content_type"], "综合"]（列表） | 新增 | 启用 |
| 13 | 设置变量 | saw_id_mismatch = False（布尔）；当前任务范围，仅初始化一次 | 新增 | 启用 |
| 14 | 设置变量 | author_check_result = "NOT_FOUND"（字符串） | 原19 | 启用 |
| 15 | ForEach列表循环 | 遍历search_sections → current_section；外层栏目循环 | 新增 | 启用 |
| 16 | 设置变量 | 字符串；变量值Python current_section；输出通过fx选择全局变量nav_section（glv["nav_section"]）；每轮栏目开始赋值 | 复制原2 | 启用 |
| 17 | 设置变量 | nav_found = False（布尔）；每轮栏目初始化 | 新增 | 启用 |
| 18 | 设置变量 | nav_directions = (["right", "left"] if current_section == "综合" else ["left", "right"])（列表） | 新增 | 启用 |
| 19 | ForEach列表循环 | 遍历nav_directions → nav_direction；仅处理顶部导航 | 新增 | 启用 |
| 20 | For次数循环 | 起始数1；结束数12；递增值1；当前循环项loop_index；仅为导航上限，不限制结果分页 | 新增 | 启用 |
| 21 | 等待元素(手机) | phone_device；已有抖音搜索栏目；等待元素出现；超时5秒 → nav_exists；错误处理默认（超时行为待手机实测） | 新增 | 启用 |
| 22 | IF 条件 | 对象1 Python nav_exists；关系等于；对象2 Python True | 原9复用 | 启用 |
| 23 | 点击元素(手机) | phone_device；已有抖音搜索栏目（text通过fx绑定全局nav_section）；单击中心点一次；点击后延迟1秒；等待元素存在5秒 | 原10复用 | 启用 |
| 24 | 设置变量 | nav_found = True（布尔） | 新增 | 启用 |
| 25 | 退出循环 | 退出20行次数循环 | 新增 | 启用 |
| 26 | Else | 对应22行 | 新增 | 启用 |
| 27 | IF 条件 | 对象1 Python nav_direction；关系等于；对象2 Python "left" | 新增 | 启用 |
| 28 | 滑动手机屏幕 | phone_device；在整个屏幕中；坐标；四项Python nav_swipe_points["left"]["start_x"/"start_y"/"end_x"/"end_y"]；滑动时间800毫秒；执行后延迟1秒；错误处理默认 | 复制原49，原49保留 | 启用 |
| 29 | Else | 对应27行 | 新增 | 启用 |
| 30 | 滑动手机屏幕 | phone_device；在整个屏幕中；坐标；四项Python nav_swipe_points["right"]["start_x"/"start_y"/"end_x"/"end_y"]；滑动时间800毫秒；执行后延迟1秒；错误处理默认 | 复制左滑 | 启用 |
| 31 | End IF | 结束27行 | 新增 | 启用 |
| 32 | End IF | 结束22行 | 新增 | 启用 |
| 33 | 循环结束标记 | 结束20行次数循环 | 新增 | 启用 |
| 34 | IF 条件 | nav_found 等于True | 原12复用 | 启用 |
| 35 | 退出循环 | 退出19行方向循环 | 复制导航退出循环，替换原13点击 | 启用 |
| 36 | End IF | 结束34行 | 新增 | 启用 |
| 37 | 循环结束标记 | 结束19行方向循环 | 新增 | 启用 |
| 38 | IF 条件 | nav_found 等于False | 新增 | 启用 |
| 39 | Raise | "未找到搜索栏目：" + current_section；定位异常终止，不冒充结果到底 | 新增 | 启用 |
| 40 | End IF | 结束38行 | 新增 | 启用 |
| 41 | 点击元素(手机) | 抖音筛选入口；保留原参数 | 原15 | 启用 |
| 42 | 点击屏幕(手机) | 原“最新发布”匹配图与原参数，不改为固定坐标 | 原16 | 启用 |
| 43 | 点击屏幕(手机) | 原“一天内”匹配图与原参数 | 原17 | 启用 |
| 44 | 点击屏幕(手机) | 原红底“查看结果”匹配图与原参数 | 原18 | 启用 |
| 45 | While条件循环 | True 等于 True | 原20 | 启用 |
| 46 | 获取相似元素列表(手机) | phone_device；搜索结果作者昵称；获取文本；返回 author_name_list；在45内 | 原21 | 启用 |
| 47 | 打印日志 | 信息；目标昵称和本屏读取昵称；长表达式在截图中被截断；在45内 | 原22 | 启用 |
| 48 | IF | 表达式以 task_data["expected_author"] in… 开头，比较 True；完整表达式未展示；在45内 | 原23 | 启用 |
| 49 | 获取元素对象(手机) | phone_device；XPath以 //*[@resource-id='com.ss.andr… 开头；返回 mobile_element_result；完整XPath未展示；在48内 | 原24 | 启用 |
| 50 | 点击元素(手机) | mobile_element_result；单击中心；在48内 | 原25 | 启用 |
| 51 | 设置变量 | is_tuwen，布尔；表达式 task_data["content_type"] == "图… 被截断；在48内 | 原26 | 启用 |
| 52 | IF | is_tuwen 等于 True；在48内 | 原27 | 启用 |
| 53 | 点击元素(手机) | 图文作者头像；在52真分支 | 原28 | 启用 |
| 54 | Else | 对应52 | 原29 | 启用 |
| 55 | 点击元素(手机) | 视频作者头像；在52假分支 | 原30 | 启用 |
| 56 | End IF | 结束52 | 原31 | 启用 |
| 57 | 获取手机元素信息 | 文本；抖音主页_账号；返回 profile_douyin_id_raw；在48内 | 原32 | 启用 |
| 58 | 获取手机元素信息 | 文本；主页_作者昵称；返回 profile_author_name_raw；在48内 | 原33 | 启用 |
| 59 | 调用模块 | module1.verify_author；传 task_data、profile_douyin_id_raw、profile_author_name_raw；返回设置未展示；在48内 | 原34 | 启用 |
| 60 | 点击按键 | phone_device；后退；在48内 | 原35 | 启用 |
| 61 | IF | author_check_result 等于 MATCH；在48内 | 原36 | 启用 |
| 62 | 退出循环 | 退出当前循环；在61内 | 原37 | 启用 |
| 63 | End IF | 结束61 | 原38 | 启用 |
| 64 | IF | author_check_result 等于 MISMATCH；在48内 | 原39 | 启用 |
| 65 | 点击按键 | phone_device；后退；在64内 | 原40 | 启用 |
| 66 | End IF | 结束64 | 原41 | 启用 |
| 67 | IF | author_check_result 等于 UNCERTAIN；在48内 | 原42 | 启用 |
| 68 | Raise | 作者抖音号核验不确定，请检查任务表中的抖音号及主页读取结果；在67内 | 原43 | 启用 |
| 69 | End IF | 结束67 | 原44 | 启用 |
| 70 | End IF | 结束48 | 原45 | 启用 |
| 71 | IF 图像存在(手机) | phone_device；目标图像显示名为“图像”；实际图像未展示；在45内 | 原46 | 启用 |
| 72 | 退出循环 | 退出当前循环；在71内 | 原47 | 启用 |
| 73 | End IF | 结束71 | 原48 | 启用 |
| 74 | 滑动手机屏幕 | phone_device；向上滑动；在45内 | 原49 | 启用 |
| 75 | 循环结束标记 | 结束45 | 原50 | 启用 |
| 76 | 循环结束标记 | 结束第15行栏目ForEach | 新增 | 启用 |
| 77 | IF | author_check_result 等于 MATCH | 原51 | 禁用 |
| 78 | 调用模块 | module1.prepare_interactions；task_data；返回 interaction_plan；在51内 | 原52 | 禁用 |
| 79 | 设置变量 | executed_actions = []，列表；在51内 | 原53 | 禁用 |
| 80 | ForEach列表循环 | interaction_plan["execution_orde… 被截断；循环项 current_action；在51内 | 原54 | 禁用 |
| 81 | IF | current_action 等于 Like；在54内 | 原55 | 禁用 |
| 82 | IF | interaction_plan["content_type"] 等于 视频；在55内 | 原56 | 禁用 |
| 83 | 获取手机元素信息 | 获取属性；视频——点赞按钮（图中显示）；返回 like_state_raw；具体属性未展示；在56内 | 原57 | 禁用 |
| 84 | End IF | 结束56 | 原58 | 禁用 |
| 85 | End IF | 结束55 | 原59 | 禁用 |
| 86 | 循环结束标记 | 结束54 | 原60 | 禁用 |
| 87 | End IF | 结束51 | 原61 | 禁用 |

## 原61行基线（历史，禁止当成当前行号）

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
