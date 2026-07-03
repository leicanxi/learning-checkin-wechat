# 学习打卡追踪器 - 实施计划

> **关联文档**：[spec.md](spec.md) | [PRD.md](PRD.md)  
> **文档版本**：v2.0  
> **最后更新**：2026-07-03

---

## 一、项目初始化

### [ ] Task 1: 后端项目初始化
- **Priority**: high
- **Depends On**: None
- **Description**: 
  - 创建 FastAPI 项目结构
  - 配置 SQLAlchemy ORM，定义所有表模型（users / tasks / checkins / groups / user_groups / badges / user_badges）
  - tasks 表需包含 v2.0 新增字段：`subject`, `suggested_duration`, `task_type`, `repeat_days`, `difficulty`, `is_review_task`, `parent_task_id`
  - checkins 表需包含 `subject` 冗余字段
  - users 表需包含 `learning_goal`, `task_expire_notify`, `role`（默认 'user'）字段
  - groups 表需包含 `invite_code` 字段
  - badges 表需包含 `icon_css` 字段
  - 设置 JWT 认证基础（支持 24 小时过期）
  - 实现 get_current_user 依赖（Header Authorization Bearer，解析 JWT）
  - 检查 user_id 是否存在，不存在或 token 过期返回 401
  - 实现 get_current_bot_user（以 user_id `'bot'` 充当系统用户写入卡片）
  - 实现 require_admin 依赖（预留，暂不挂载；校验 user.role == 'admin'，否则 403）
  - 所有请求通过该中间件注入当前用户上下文
  - 编写数据库迁移脚本（Alembic 或手动 DDL）
- **Acceptance Criteria Addressed**: 技术栈搭建完成，数据库表结构符合 spec.md v2.0
- **Test Requirements**:
  - `programmatic` TR-1.1: 项目启动成功，访问 /docs 返回 API 文档
  - `programmatic` TR-1.2: SQLite 数据库连接成功，所有表结构创建完成
  - `programmatic` TR-1.3: 数据库迁移脚本可正确执行，新增字段无遗漏
- **Notes**: 使用 pipenv 或 venv 管理依赖

### [ ] Task 2: 前端项目初始化
- **Priority**: high
- **Depends On**: None
- **Description**: 
  - 使用 Taro 初始化微信小程序项目
  - 配置 TypeScript
  - 安装 Taro UI 组件库、ECharts 小程序版
  - 设置 Pinia 状态管理
  - 创建 `src/config.ts` 环境配置文件（dev / staging / prod 三套）
  - 配置 API 请求拦截器（自动附加 `Authorization: Bearer <token>`）
  - 测试号 AppID 写入 `project.config.json`
- **Acceptance Criteria Addressed**: 前端框架搭建完成，环境配置可切换
- **Test Requirements**:
  - `programmatic` TR-2.1: 项目构建成功，无 TypeScript 错误
  - `human-judgement` TR-2.2: 微信开发者工具可正常预览
  - `programmatic` TR-2.3: API 请求拦截器正确附加 token
- **Notes**: 确保 Taro 版本与微信小程序基础库兼容

---

## 二、用户认证模块

### [ ] Task 3: 用户注册与登录 API
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 实现邮箱注册接口（POST /auth/register）
  - 实现邮箱登录接口（POST /auth/login）
  - JWT token 生成与验证（24 小时有效期）
  - 密码 bcrypt 哈希存储
- **Acceptance Criteria Addressed**: 开发调试登录
- **Test Requirements**:
  - `programmatic` TR-3.1: POST /auth/register 返回 200 和用户信息
  - `programmatic` TR-3.2: POST /auth/login 返回 JWT token
  - `programmatic` TR-3.3: 密码正确哈希存储，不泄露明文
- **Notes**: 邮箱登录仅用于开发调试，不暴露于小程序前端入口

### [ ] Task 3b: 微信小程序登录 API
- **Priority**: high
- **Depends On**: Task 1
- **Description**: 
  - 实现 POST /auth/wechat-login（小程序主入口鉴权）
  - 接收 `{ code }`（wx.login() 生成的临时 code）
  - 后端调用微信 `code2Session` API 换取 openid
  - 查找 users 表：openid 存在则返回现有用户，不存在则自动注册新用户（role 默认 'user'）
  - 返回 JWT token（payload: { user_id, openid, role }）+ user 信息
  - 配置 WECHAT_APPID / WECHAT_APPSECRET 环境变量
  - 限流：每 IP 每小时最多 20 次
- **Acceptance Criteria Addressed**: 用户可通过微信一键登录
- **Test Requirements**:
  - `programmatic` TR-3b.1: POST /auth/wechat-login 传入有效 code → 返回 JWT token
  - `programmatic` TR-3b.2: 新用户首次登录 → 自动注册 + 返回 token
  - `programmatic` TR-3b.3: 无效 code → 返回 401
- **Notes**: 测试阶段可用测试号 AppSecret

### [ ] Task 4: 用户信息管理 API
- **Priority**: medium
- **Depends On**: Task 3, Task 3b
- **Description**: 
  - 实现 GET /auth/me（获取当前用户信息）
  - 实现 PUT /auth/me（更新昵称、学习目标、头像）
  - 实现 POST /auth/avatar（上传头像 ≤2MB）
- **Acceptance Criteria Addressed**: 用户可查看和修改个人信息
- **Test Requirements**:
  - `programmatic` TR-4.1: GET /auth/me 返回当前用户完整信息（含 learning_goal）
  - `programmatic` TR-4.2: PUT /auth/me 成功更新昵称和学习目标
  - `programmatic` TR-4.3: POST /auth/avatar 成功上传头像文件
- **Notes**: 头像文件大小限制在 2MB 以内

### [ ] Task 5: 前端登录页面
- **Priority**: high
- **Depends On**: Task 2, Task 3b
- **Description**: 
  - 实现微信一键登录入口（调用 wx.login() → POST /auth/wechat-login）
  - JWT token 存储到本地缓存
  - Pinia user store 管理登录状态
  - 自动登录检测（缓存中有 token 则尝试校验）
  - 登录失败友好提示
- **Acceptance Criteria Addressed**: 用户可通过微信一键登录
- **Test Requirements**:
  - `human-judgement` TR-5.1: 登录流程流畅，UI 简洁
  - `programmatic` TR-5.2: 登录成功后 token 正确存储在本地
  - `programmatic` TR-5.3: 应用重启后自动登录功能正常
- **Notes**: 不使用邮箱登录入口（开发调试仅后端可用）

---

## 三、打卡任务模块

### [ ] Task 6: 任务管理 API
- **Priority**: high
- **Depends On**: Task 3b
- **Description**: 
  - 实现 POST /tasks/（创建单个任务，需支持 v2.0 新字段：subject / suggested_duration / task_type / repeat_days / difficulty）
  - 实现 POST /tasks/batch（AI 规划页确认后批量创建任务）
  - 实现 GET /tasks/?status=active（获取用户任务列表，过滤活跃任务）
  - 实现 GET /tasks/{id}（任务详情）
  - 实现 PUT /tasks/{id}（更新任务）
  - 实现 DELETE /tasks/{id}（软删除：status='deleted'，保留历史打卡记录）
  - repeat_days 为位掩码，需实现前端传值和后端解析逻辑
- **Acceptance Criteria Addressed**: 用户可创建、查看、编辑、删除打卡任务
- **Test Requirements**:
  - `programmatic` TR-6.1: POST /tasks/ 成功创建任务（含新字段）
  - `programmatic` TR-6.2: GET /tasks/ 返回用户任务列表，支持状态过滤
  - `programmatic` TR-6.3: PUT /tasks/{id} 成功更新任务
  - `programmatic` TR-6.4: DELETE /tasks/{id} 软删除（保留历史记录）
  - `programmatic` TR-6.5: POST /tasks/batch 批量创建成功
- **Notes**: tasks 表需包含 migration 以增加 v2.0 新字段

### [ ] Task 7: 打卡记录 API
- **Priority**: high
- **Depends On**: Task 6
- **Description**: 
  - 实现 POST /checkins/（打卡，支持同一任务每日多次打卡）
  - 实现 POST /checkins/backfill（补打卡最近 7 天，超过 7 天返回 400）
  - 实现 GET /checkins/（获取打卡记录列表）
  - 实现 GET /checkins/{id}（打卡详情）
  - 实现 PUT /checkins/{id}（更新打卡记录）
  - 实现 DELETE /checkins/{id}（删除打卡记录）
  - 连续天数计算逻辑（支持休息建议不中断连续性）
- **Acceptance Criteria Addressed**: 用户可完成每日打卡和补打卡
- **Test Requirements**:
  - `programmatic` TR-7.1: POST /checkins/ 成功记录打卡
  - `programmatic` TR-7.2: 同一任务每日可打卡多次
  - `programmatic` TR-7.3: 连续天数正确累加，休息建议日不中断
  - `programmatic` TR-7.4: 补打卡超过 7 天返回 400 错误
  - `programmatic` TR-7.5: 补打卡最近 7 天内成功
- **Notes**: 打卡时同步写入 checkins.subject（冗余 task.subject）

### [ ] Task 8: 首页任务列表组件
- **Priority**: high
- **Depends On**: Task 5, Task 6, Task 7
- **Description**: 
  - 创建首页（pages/home）：Hero 区连续天数展示 + 三指标卡片（本周/本月打卡率、规律性排名）
  - 任务列表组件：每个任务显示复选框 + 任务名称 + 元信息（时长 + 科目）+ 类型标签
  - 三种类型标签颜色：已同步=赤陶(#c96442)、主任务=墨色(#141413)、轻量=鼠尾草(#6f735f)
  - 一键打卡：点击复选框 → POST /checkins/ → 状态即时切换
  - 空状态引导：无任务时引导用户去规划页创建
  - 动态激励文案：根据连续天数变化（如"已坚持 15 天"→"太棒了！继续保持"）
- **Acceptance Criteria Addressed**: 用户可在首页查看任务并快速打卡
- **Test Requirements**:
  - `human-judgement` TR-8.1: 任务列表清晰展示，状态区分明显，类型标签颜色正确
  - `programmatic` TR-8.2: 点击打卡按钮状态立即更新
  - `programmatic` TR-8.3: 三指标卡片数据正确渲染
- **Notes**: 添加加载状态和空数据提示

### [ ] Task 9: 规划页自定义计划组件
- **Priority**: high
- **Depends On**: Task 8
- **Description**: 
  - 自定义计划区域：输入任务名称（必填 1-50 字符）+ 建议时长 + 科目标签
  - 打卡周期选择器："每天"快捷按钮 + 周一~周日 7 个独立按钮（位掩码逻辑）
  - 全选时"每天"自动激活；手动取消某天后"每天"自动取消
  - 表单验证：名称必填、至少选一个周期日
  - 添加到计划列表功能
- **Acceptance Criteria Addressed**: 用户可手动创建打卡任务
- **Test Requirements**:
  - `human-judgement` TR-9.1: 表单验证完善，错误提示友好
  - `programmatic` TR-9.2: 周期选择器位掩码逻辑正确
- **Notes**: 参考 prototype.html 中 `.custom-plan` 区域

---

## 四、进度日历模块

### [ ] Task 10: 日历数据 API
- **Priority**: high
- **Depends On**: Task 7
- **Description**: 
  - 实现 GET /calendar/month?year=&month=（返回该月每日打卡状态）
  - 5 种日期状态计算：checked_in（已打卡）/ missed（未打卡）/ rest_suggested（休息建议）/ today（今日）/ tomorrow_suggested（明日推荐）
  - 当月完成率计算
  - 连续打卡高亮标记
  - 休息建议逻辑：连续打卡 ≥7 天时自动推荐休息日
- **Acceptance Criteria Addressed**: 用户可查看日历视图中的打卡情况
- **Test Requirements**:
  - `programmatic` TR-10.1: GET /calendar/month 返回正确月份数据，含 5 种状态
  - `programmatic` TR-10.2: 已打卡 / 未打卡 / 休息日 / 今日 / 明日推荐状态计算正确
  - `programmatic` TR-10.3: 休息建议在连续打卡≥7 天时正确触发
- **Notes**: 支持月份切换

### [ ] Task 11: 日历页面实现
- **Priority**: high
- **Depends On**: Task 5, Task 10
- **Description**: 
  - 创建日历页（pages/calendar）：7×6 月历网格 + 图例说明
  - 5 种日期状态颜色区分（参考 prototype.html CSS）
  - 底部 Today 卡片（墨色标签）+ Tomorrow 卡片（鼠尾草色标签）
  - 点击日期弹出底部 Sheet：过去日期显示打卡摘要，未来日期显示安排任务
  - 月份切换功能
- **Acceptance Criteria Addressed**: 用户可在日历页查看打卡历史和智能推荐
- **Test Requirements**:
  - `human-judgement` TR-11.1: 日历布局美观，交互流畅，5 种状态颜色正确
  - `programmatic` TR-11.2: 点击日期弹出打卡详情 Sheet
  - `programmatic` TR-11.3: 图例说明展示正确
- **Notes**: 适配移动端屏幕尺寸

---

## 五、统计看板模块

### [ ] Task 12: 统计数据 API
- **Priority**: high
- **Depends On**: Task 7
- **Description**: 
  - 实现 GET /stats/?period=week|month|year&start=&end=
  - 本周/本月打卡率计算
  - 当前连续和历史最长连续天数
  - 知识掌握进度环数据
  - **新增**: `subject_distribution` 科目打卡分布数据（按 subject 聚合 checkins）
  - **新增**: `checkin_trend` 打卡趋势数据（按日期聚合）
  - `total_checkins` 累计打卡次数
- **Acceptance Criteria Addressed**: 用户可查看详细统计数据
- **Test Requirements**:
  - `programmatic` TR-12.1: GET /stats/ 返回完整统计数据
  - `programmatic` TR-12.2: 打卡率计算正确（已打卡天数 / 应打卡天数）
  - `programmatic` TR-12.3: subject_distribution 科目分布数据正确
- **Notes**: 支持时间维度切换

### [ ] Task 13: 统计页面实现
- **Priority**: high
- **Depends On**: Task 5, Task 12
- **Description**: 
  - 创建统计页（pages/stats）：时间维度分段控制器（周/月/年/自定义）
  - 打卡趋势折线图（ECharts）
  - 知识掌握进度环（环形图）
  - 累计打卡次数卡片
  - 科目打卡分布横向柱状图
- **Acceptance Criteria Addressed**: 用户可在统计页查看各项数据
- **Test Requirements**:
  - `human-judgement` TR-13.1: 图表展示清晰，数据直观
  - `programmatic` TR-13.2: 趋势图数据正确渲染
  - `programmatic` TR-13.3: 科目分布柱状图正确渲染
- **Notes**: 使用 ECharts 小程序版本

---

## 六、AI辅助学习模块

### [ ] Task 14: AI服务集成
- **Priority**: high
- **Depends On**: Task 3b
- **Description**: 
  - 集成 DeepSeek API
  - 实现 POST /ai/analyze（分析学习材料并拆解任务）
  - 实现 POST /ai/generate-plan（接收 content + mode? + target_days? → 返回含日期的完整计划）
  - **模式推断逻辑**：mode 为空时从 content 做 NLP 关键词匹配推断（冲刺/长期/技能/错题 → 对应模式，无匹配 → free）
  - **Prompt 组装**：根据确定的模式，拼装不同的 System Prompt 指令（考试冲刺=密集排期 / 日常积累=长期反复 / 技能进修=阶段递进 / 错题复盘=间隔拉长 / 自由=AI 自主）
  - 每个子任务必须返回 `scheduled_date`（YYYY-MM-DD）、`day_number`；review_round 固定为 0（AI 只规划新学任务，复习由 Task 17 遗忘曲线统一触发）
  - AI 返回数据格式校验和转换
  - API 调用频率限制（每用户每日 10 次）
- **Acceptance Criteria Addressed**: 用户可使用 AI 生成含日期的完整学习计划
- **Test Requirements**:
  - `programmatic` TR-14.1: POST /ai/generate-plan 成功调用 DeepSeek API，返回带日期计划
  - `programmatic` TR-14.2: 每个子任务含 scheduled_date / day_number 字段，review_round=0
  - `programmatic` TR-14.3: 超过每日调用次数限制返回 429
  - `programmatic` TR-14.4: mode 为空时正确从 content 推断模式（如"冲刺30天"→exam）
  - `programmatic` TR-14.5: exam 模式子任务数 ≤ target_days（每日至少一个任务）
  - `programmatic` TR-14.6: daily 模式子任务不一定每天排（间隔分布）
- **Notes**: API 密钥存储在环境变量中；Prompts 模板见 spec.md 4.4 节

### [ ] Task 14b: AI规划页增强功能
- **Priority**: medium
- **Depends On**: Task 2, Task 14
- **Description**: 
  - 实现 POST /ai/upload-material（文件上传接口，供 AI 分析学习材料图片/文档）
  - 规划页语音输入：调用 wx.getRecorderManager 录音 → 后端语音转文字 → 填入输入框
  - 规划页文件上传：wx.chooseMessageFile 选择文件 → 上传到后端 → AI 分析
  - 前端模式选择器 UI（5 种学习模式下拉）
- **Acceptance Criteria Addressed**: 用户可通过语音和文件辅助 AI 规划
- **Test Requirements**:
  - `programmatic` TR-14b.1: 语音录制→识别→填入输入框流程正常
  - `programmatic` TR-14b.2: 文件上传→AI 分析流程正常
  - `human-judgement` TR-14b.3: 模式选择器 UI 清晰
- **Notes**: 语音识别使用腾讯云 ASR，通过微信原生录音获取音频 → 后端调用腾讯云 API → 返回文本

### [ ] Task 15: AI任务生成 API
- **Priority**: high
- **Depends On**: Task 6, Task 14
- **Description**: 
  - AI 返回的 plan 数组（每个子任务含 scheduled_date）转化为打卡任务列表
  - 每个子任务的 start_date = scheduled_date，end_date = scheduled_date（单日任务）
  - 携带 subject / suggested_duration / difficulty / task_type 字段
  - 支持用户编辑后确认（允许内联编辑任务名称、调整日期、删除子任务）
  - 确认后调用 POST /tasks/batch 批量创建（每个子任务携带各自的 start_date）
- **Acceptance Criteria Addressed**: 用户可使用 AI 生成带日期的打卡任务
- **Test Requirements**:
  - `programmatic` TR-15.1: AI 生成结果正确转化为含 start_date 的任务列表
  - `programmatic` TR-15.2: 确认后任务按各自日期正确创建
  - `programmatic` TR-15.3: 用户修改日期后，创建的任务 start_date 为用户调整后的值
- **Notes**: 生成任务前需用户确认

### [ ] Task 16: AI规划页面实现
- **Priority**: high
- **Depends On**: Task 5, Task 9, Task 14, Task 14b, Task 15
- **Description**: 
  - 创建规划页（pages/planner）：模式选择器（5 种模式下拉，可留空）+ 材料文本输入框 + 语音按钮 + 文件上传按钮
  - 核心交互：模式选择器留空时，用户可在提示词中描述学习需求（如"仅剩30天，冲刺考试"），后端自动推断模式
  - AI 规划按钮 → 调用 POST /ai/generate-plan → 返回含日期的完整计划 JSON
  - 前端以**日期计划表**形式渲染：按 scheduled_date 分组折叠显示，每日期下展开子任务列表
  - 每个子任务：可内联编辑任务名称、调整日期（日期选择器）、删除
  - 自定义计划区域（Task 9 实现）可与 AI 计划合并
  - "确认创建计划"按钮 → POST /tasks/batch（每个子任务携带各自的 start_date）→ 跳转首页，日历同步显示
- **Acceptance Criteria Addressed**: 用户可在规划页通过 AI 生成含日期的完整学习计划
- **Test Requirements**:
  - `human-judgement` TR-16.1: AI 规划流程清晰，日期计划表按日期分组展示
  - `programmatic` TR-16.2: 确认后任务按各自日期正确创建
  - `human-judgement` TR-16.3: 语音按钮和文件上传按钮交互正确
  - `programmatic` TR-16.4: 用户调整子任务日期后，确认创建时使用调整后的日期
- **Notes**: 添加 loading 状态和错误处理；日期分组折叠交互参考日历 UI

### [ ] Task 17: 遗忘曲线复习功能
- **Priority**: medium
- **Depends On**: Task 7
- **Description**: 
  - 实现遗忘曲线算法（1/2/4/7/15 天）
  - 打卡完成后自动计算复习时间点
  - 创建 `is_review_task=true, parent_task_id=原任务ID, task_type='review'` 的复习子任务
  - 用户收到通知后手动确认加入计划
- **Acceptance Criteria Addressed**: 系统自动生成复习任务
- **Test Requirements**:
  - `programmatic` TR-17.1: 打卡完成后正确计算复习时间点
  - `programmatic` TR-17.2: 复习任务正确创建，parent_task_id 关联正确
  - `programmatic` TR-17.3: 复习任务类型标记为 review
- **Notes**: 需用户手动确认后再纳入计划

---

## 七、智能日历展望模块

### [ ] Task 18: 智能日历 API
- **Priority**: medium
- **Depends On**: Task 7, Task 14
- **Description**: 
  - 实现 GET /calendar/today（返回今日安排的任务列表 + subject / task_type / suggested_duration）
  - 实现 GET /calendar/tomorrow（AI 推荐明日任务 + 难度 + 建议用时 + 休息建议）
  - 休息建议逻辑：连续打卡 ≥7 天时 `rest_suggested=true` 并附原因
- **Acceptance Criteria Addressed**: 用户可查看今日任务和明日推荐
- **Test Requirements**:
  - `programmatic` TR-18.1: GET /calendar/today 返回今日任务（含 task_type）
  - `programmatic` TR-18.2: GET /calendar/tomorrow 返回 AI 推荐任务
  - `programmatic` TR-18.3: 休息建议逻辑正确
- **Notes**: 今日任务全部完成后明日推荐自动更新

### [ ] Task 19: 智能日历页面实现
- **Priority**: medium
- **Depends On**: Task 11, Task 18
- **Description**: 
  - 日历页底部今日任务卡片（墨色标签，显示任务名称和预计时长）
  - 日历页底部明日推荐卡片（鼠尾草色标签，显示任务名称、难度、建议用时）
  - 休息建议标记（日期格子灰色小点）
  - 用户完成今日所有任务 → 明日推荐自动刷新
- **Acceptance Criteria Addressed**: 用户可在日历页查看智能推荐
- **Test Requirements**:
  - `human-judgement` TR-19.1: 智能推荐展示直观，交互方便
  - `programmatic` TR-19.2: 今日/明日卡片数据正确渲染
- **Notes**: 不同类型任务使用不同颜色区分

---

## 八、规律排行模块

### [ ] Task 20: 规律性计算 API
- **Priority**: medium
- **Depends On**: Task 7
- **Description**: 
  - 实现规律性得分计算算法（标准差 + 波动系数，最近 30 天数据）
  - 实现 GET /ranking/me?scope=group|global（返回排名区间 + 称号）
  - 排名区间：top_20（前20%/规律达人）/ top_60（20%-60%/习惯养成者）/ bottom_40（60%+/继续加油）/ insufficient（不足7次）
  - 实现 GET /ranking/?scope=group|global（排行榜）
- **Acceptance Criteria Addressed**: 用户可查看规律性排行榜
- **Test Requirements**:
  - `programmatic` TR-20.1: GET /ranking/me 返回正确排名区间
  - `programmatic` TR-20.2: 规律性得分计算正确
  - `programmatic` TR-20.3: 打卡＜7 次返回 insufficient
- **Notes**: 不暴露具体排名数字

### [ ] Task 21: 徽章系统 API
- **Priority**: low
- **Depends On**: Task 20
- **Description**: 
  - 实现 9 个徽章：规律达人 / 习惯养成者 / 进步之星 / 七日连续 / 英语坚持 / 错题复盘 / 早起学习 / 晚间专注 / 小组贡献 / 新计划创建
  - 徽章数据初始化到 badges 表
  - 实现 GET /badges/（获取全部徽章列表）
  - 实现 GET /badges/me（获取用户已获得徽章）
  - 自动授予逻辑（打卡时检查徽章条件）
- **Acceptance Criteria Addressed**: 用户可获得相应徽章奖励
- **Test Requirements**:
  - `programmatic` TR-21.1: GET /badges/me 返回用户已获得徽章
  - `programmatic` TR-21.2: 达到条件时自动授予徽章
- **Notes**: 徽章数据初始化到数据库

### [ ] Task 22: 排行榜页面实现
- **Priority**: medium
- **Depends On**: Task 5, Task 20, Task 21
- **Description**: 
  - 创建排行页（pages/ranking）：深色 Hero 区（排名区间 + 称号文案）
  - 维度切换（小组 / 全局）
  - 三类排名区间说明卡片
  - 徽章墙：3×3 网格展示全部 9 个徽章，区分已获得（亮色）和未获得（灰色）
- **Acceptance Criteria Addressed**: 用户可查看规律性排行和徽章
- **Test Requirements**:
  - `human-judgement` TR-22.1: 排行榜页面美观，信息清晰
  - `programmatic` TR-22.2: 维度切换功能正常
  - `human-judgement` TR-22.3: 徽章墙 3×3 网格正确渲染
- **Notes**: 不显示具体排名数字

---

## 九、设置与其它功能模块

### [ ] Task 23: 提醒与设置 API
- **Priority**: low
- **Depends On**: Task 4
- **Description**: 
  - 实现 GET /settings/reminder（获取提醒设置）
  - 实现 PUT /settings/reminder（更新 reminder_enabled / reminder_time / task_expire_notify）
  - 实现 GET /report/pdf（生成用户学习报告 PDF）
  - 提醒触发：定时任务（APScheduler）→ 检测时间 → 测试号使用本地弹窗（wx.showModal）→ 正式号启用模板消息
- **Acceptance Criteria Addressed**: 用户可设置打卡提醒
- **Test Requirements**:
  - `programmatic` TR-23.1: 提醒设置正确保存
  - `programmatic` TR-23.2: PDF 导出接口可生成有效 PDF
  - `human-judgement` TR-23.3: 提醒时间到达时触发通知
- **Notes**: 测试号无模板消息权限，使用本地弹窗降级方案

### [ ] Task 23b: 小组管理 API
- **Priority**: medium
- **Depends On**: Task 4
- **Description**: 
  - 实现 GET /groups/my（获取当前用户小组信息 + 成员数 + 完成率 + 我的排名区间）
  - 实现 POST /groups/join（通过邀请码加入小组）
  - 实现 PUT /groups/{id}（更新小组信息，仅创建者）
  - 实现 POST /groups/（创建小组 + 自动生成邀请码）
- **Acceptance Criteria Addressed**: 用户可加入和管理学习小组
- **Test Requirements**:
  - `programmatic` TR-23b.1: GET /groups/my 返回正确小组信息
  - `programmatic` TR-23b.2: POST /groups/join 通过邀请码成功加入
  - `programmatic` TR-23b.3: 非创建者无法更新小组信息
- **Notes**: 基础版小组功能（成员数/完成率/排名区间）

### [ ] Task 24: 设置页面实现
- **Priority**: medium
- **Depends On**: Task 4, Task 23, Task 23b
- **Description**: 
  - 创建设置页（pages/settings）：个人资料卡片（头像 + 昵称 + 学习目标 + 编辑入口）
  - 提醒设置区域：每日打卡提醒开关 + 任务到期通知开关
  - 小组信息卡片（小组名称 + 成员数 + 完成率 + 我的排名区间 + 加入/管理入口）
  - PDF 导出入口
  - 关于应用（版本号 + 产品名称）
  - 退出登录（清除 token → 回到登录页）
- **Acceptance Criteria Addressed**: 用户可在设置页配置各项参数
- **Test Requirements**:
  - `human-judgement` TR-24.1: 设置页面布局合理，操作方便
  - `programmatic` TR-24.2: 设置变更正确保存
  - `programmatic` TR-24.3: 退出登录清除 token 并跳转
- **Notes**: 参考 prototype.html 中 `#screen-settings`

---

## 十、测试与优化

### [ ] Task 25: 单元测试与集成测试
- **Priority**: medium
- **Depends On**: 所有 API 开发完成（Task 3~23b）
- **Description**: 
  - 编写后端 API 单元测试（pytest）
  - 编写前端组件测试
  - 集成测试（端到端流程：登录→创建任务→打卡→查看统计→查看排行→设置）
  - 覆盖所有 API 端点（含 v2.0 新增接口）
  - 覆盖边界条件（补打卡超限、AI 超频、空任务等）
- **Acceptance Criteria Addressed**: 核心功能测试覆盖
- **Test Requirements**:
  - `programmatic` TR-25.1: 单元测试覆盖率 ≥ 80%
  - `programmatic` TR-25.2: 所有测试用例通过（100% pass rate）
- **Notes**: 使用 pytest + httpx.AsyncClient 测试后端 API

### [ ] Task 26: 性能优化
- **Priority**: low
- **Depends On**: Task 25
- **Description**: 
  - 数据库查询优化（索引：user_id / task_id / checkin_time）
  - API 响应时间优化（缓存规律性得分、统计聚合）
  - 前端加载性能优化（分包加载、图片压缩）
- **Acceptance Criteria Addressed**: 满足性能要求
- **Test Requirements**:
  - `programmatic` TR-26.1: 页面加载时间 ≤ 2 秒
  - `programmatic` TR-26.2: 打卡响应时间 ≤ 500 毫秒
  - `programmatic` TR-26.3: 日历渲染时间 ≤ 1 秒
- **Notes**: 使用缓存策略优化

### [ ] Task 27: 安全性审计
- **Priority**: medium
- **Depends On**: Task 25
- **Description**: 
  - 安全漏洞扫描
  - 输入验证检查（前端+后端双重校验）
  - 权限控制验证（用户只能访问自己数据）
  - AI API Key 不暴露于前端
  - JWT 签名密钥强度检查
- **Acceptance Criteria Addressed**: 满足安全性要求
- **Test Requirements**:
  - `programmatic` TR-27.1: 无 SQL 注入和 XSS 漏洞
  - `human-judgement` TR-27.2: 权限控制严格，用户只能访问自己的数据
  - `programmatic` TR-27.3: AI API Key 不在前端代码中出现
- **Notes**: 使用安全扫描工具

---

## 十一、部署上线

### [ ] Task 28: 后端部署
- **Priority**: high
- **Depends On**: Task 25, Task 27
- **Description**: 
  - 配置生产环境变量（WECHAT_APPID / WECHAT_APPSECRET / DEEPSEEK_API_KEY / JWT_SECRET_KEY）
  - 部署 FastAPI 到云服务器
  - 配置 HTTPS
  - 数据库初始化（运行迁移脚本）
- **Acceptance Criteria Addressed**: 后端服务线上可用
- **Test Requirements**:
  - `programmatic` TR-28.1: API 接口可通过 HTTPS 访问
  - `programmatic` TR-28.2: 服务健康检查通过
- **Notes**: 使用腾讯云 Serverless 或轻量服务器

### [ ] Task 29: 前端部署与迁移
- **Priority**: high
- **Depends On**: Task 28
- **Description**: 
  - 构建小程序代码
  - **迁移步骤**（测试号 → 正式号）：
    1. 在 `project.config.json` 中更换为正式号 AppID
    2. 在 `src/config.ts` 中将 apiBaseUrl 更新为正式域名
    3. 在微信管理后台配置服务器域名白名单（request + uploadFile 合法域名）
    4. 启用模板消息（正式号 `wx.requestSubscribeMessage`）
  - 上传代码到微信小程序平台
  - 提交审核
- **Acceptance Criteria Addressed**: 小程序上线发布
- **Test Requirements**:
  - `human-judgement` TR-29.1: 小程序审核通过
  - `human-judgement` TR-29.2: 用户可正常使用所有功能
  - `programmatic` TR-29.3: 正式号域名白名单配置正确
- **Notes**: 确保符合微信小程序审核规范；测试号→正式号迁移共 7 个步骤，详见 spec.md §八
