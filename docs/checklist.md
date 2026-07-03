# 学习打卡追踪器 - 验证清单

> **文档版本**：v2.0  
> **最后更新**：2026-07-03

## 一、项目初始化验证

- [ ] 后端项目可正常启动，访问 /docs 返回 API 文档
- [ ] SQLite 数据库连接成功，所有 7 张表创建完成（users / tasks / checkins / groups / user_groups / badges / user_badges）
- [ ] tasks 表包含 v2.0 新增字段：subject / suggested_duration / task_type / repeat_days / difficulty / is_review_task / parent_task_id
- [ ] checkins 表包含 subject 冗余字段
- [ ] users 表包含 learning_goal / task_expire_notify 字段
- [ ] groups 表包含 invite_code 字段
- [ ] badges 表包含 icon_css 字段
- [ ] 前端项目构建成功，无 TypeScript 错误
- [ ] `src/config.ts` 三套环境配置（dev / staging / prod）可正常切换
- [ ] API 请求拦截器正确附加 Authorization Header
- [ ] 微信开发者工具可正常预览前端页面

## 二、用户认证模块验证

### 微信登录（主流程）
- [ ] POST /auth/wechat-login 接收有效 code → 返回 JWT token + user 信息
- [ ] 新用户首次登录 → 自动注册 + 返回 token
- [ ] 无效 code → 返回 401 错误
- [ ] 限流：每 IP 每小时最多 20 次
- [ ] 前端 wx.login() → 获取 code → 调用登录接口 → 存储 token（流程完整）

### 邮箱登录（开发备用）
- [ ] POST /auth/register 返回 200 和用户信息
- [ ] POST /auth/login 返回 JWT token
- [ ] 密码正确 bcrypt 哈希存储，不泄露明文
- [ ] GET /auth/me 返回当前用户完整信息（含 learning_goal）
- [ ] PUT /auth/me 成功更新昵称和学习目标
- [ ] POST /auth/avatar 成功上传头像（≤2MB）

### 前端
- [ ] 微信一键登录流程流畅，UI 简洁
- [ ] 登录成功后 token 正确存储在本地
- [ ] 应用重启后自动登录功能正常（token 未过期）
- [ ] JWT token 过期 → 静默重授权 → 恢复操作（用户无感知）
- [ ] 登录失败友好提示

## 三、打卡任务模块验证

### 任务管理 API
- [ ] POST /tasks/ 成功创建任务（含 v2.0 新字段：subject / suggested_duration / task_type / repeat_days / difficulty）
- [ ] POST /tasks/batch 批量创建任务成功
- [ ] GET /tasks/?status=active 返回用户任务列表，支持状态过滤
- [ ] GET /tasks/{id} 返回完整任务详情
- [ ] PUT /tasks/{id} 成功更新任务
- [ ] DELETE /tasks/{id} 软删除（status='deleted'），保留历史打卡记录
- [ ] repeat_days 位掩码逻辑正确：127=每天、0=不重复

### 打卡记录 API
- [ ] POST /checkins/ 成功记录打卡
- [ ] 同一任务每日可打卡多次
- [ ] 同一天同一任务重复打卡 → 幂等返回已有记录（不产生重复 checkin）
- [ ] 打卡时 checkins.subject 正确冗余 task.subject
- [ ] 连续天数正确累加，休息建议日不中断
- [ ] POST /checkins/backfill 补打卡最近 7 天成功
- [ ] 补打卡超过 7 天返回 400 错误
- [ ] GET /checkins/ 返回打卡记录列表
- [ ] PUT /checkins/{id} / DELETE /checkins/{id} 正常

### 首页（pages/home）
- [ ] Hero 区连续天数展示正确
- [ ] 动态激励文案根据连续天数变化
- [ ] 三指标卡片数据正确（本周打卡率 / 本月打卡率 / 规律性排名）
- [ ] 任务列表清晰展示：复选框 + 名称 + 元信息（时长/科目）+ 类型标签
- [ ] 三种类型标签颜色正确：已同步=赤陶(#c96442) / 主任务=墨色(#141413) / 轻量=鼠尾草(#6f735f)
- [ ] 点击复选框 → 打卡接口调用 → 状态即时更新
- [ ] 首次使用无任务时 → 空状态引导去规划页

### 规划页自定义计划（pages/planner）
- [ ] 表单验证：名称必填（1-50 字符）、至少选一个周期日
- [ ] 科目标签、建议时长字段正常
- [ ] "每天"快捷按钮 + 周一~周日 7 个独立按钮
- [ ] 周期选择器位掩码逻辑：全选→"每天"激活；取消某天→"每天"取消
- [ ] 错误提示友好

## 四、进度日历模块验证

### 日历 API
- [ ] GET /calendar/month?year=&month= 返回正确月份数据
- [ ] 5 种日期状态计算正确：checked_in / missed / rest_suggested / today / tomorrow_suggested
- [ ] 当月完成率计算正确
- [ ] 休息建议在连续打卡 ≥7 天时正确触发
- [ ] GET /calendar/today 返回今日任务（含 task_type / suggested_duration）
- [ ] GET /calendar/tomorrow 返回 AI 推荐任务 + 休息建议

### 日历页面（pages/calendar）
- [ ] 7×6 月历网格布局美观，5 种状态颜色区分正确
- [ ] 图例说明展示正确
- [ ] 底部 Today 卡片（墨色标签）+ Tomorrow 卡片（鼠尾草色标签）
- [ ] 点击日期弹出底部 Sheet：过去日期显示打卡摘要，未来日期显示安排任务
- [ ] 月份切换功能正常
- [ ] 适配移动端屏幕尺寸

## 五、统计看板模块验证

### 统计 API
- [ ] GET /stats/?period=week|month|year&start=&end= 返回完整统计数据
- [ ] 本周/本月打卡率计算正确（已打卡天数 / 应打卡天数 × 100%）
- [ ] 当前连续和历史最长连续天数正确
- [ ] subject_distribution 科目打卡分布数据正确（按 subject 聚合）
- [ ] checkin_trend 打卡趋势数据正确（按日期聚合）
- [ ] total_checkins 累计打卡次数正确
- [ ] knowledge_progress 知识掌握进度环数据正确

### 统计页面（pages/stats）
- [ ] 时间维度分段控制器（周/月/年/自定义）正常切换
- [ ] 打卡趋势折线图数据正确渲染
- [ ] 知识掌握进度环正确展示
- [ ] 累计打卡次数卡片展示
- [ ] 科目打卡分布横向柱状图正确渲染

## 六、AI辅助学习模块验证

### AI 服务
- [ ] POST /ai/generate-plan 成功调用 DeepSeek API
- [ ] 5 种模式正确映射：exam / daily / skill / review / free
- [ ] 返回数据格式符合规范（task_name / scheduled_date / day_number / review_round / subject / suggested_duration / difficulty / knowledge_tags）
- [ ] 超过每用户每日 10 次调用限制返回 429
- [ ] AI 调用失败 → 友好错误提示 + 重试按钮
- [ ] AI JSON 解析失败 → 后端自动重试（最多 3 次）→ 3 次均失败返回 500
- [ ] AI 返回 scheduled_date 异常值（超出范围/过去日期）→ 过滤 + 提示
- [ ] POST /ai/upload-material 文件上传接口正常

### 语音与文件输入
- [ ] 语音录制（wx.getRecorderManager）→ 后端语音识别 → 填入输入框流程正常
- [ ] 文件上传（wx.chooseMessageFile）→ 上传到后端 → 用于 AI 分析流程正常

### AI 任务生成
- [ ] AI 解析结果正确转化为包含 subject / suggested_duration / difficulty / scheduled_date 的任务列表
- [ ] AI 生成任务支持内联编辑和删除
- [ ] 批量创建子任务部分失败 → 全量回滚 + 错误提示（事务保证）
- [ ] 确认后调用 POST /tasks/batch 批量创建成功
- [ ] 用户拒绝 AI 生成的任务 → 任务不创建

### 规划页面
- [ ] AI 规划页 UI 完整：模式选择器 + 文本输入 + 语音按钮 + 文件上传按钮
- [ ] AI 规划流程清晰，操作友好，loading 状态正确
- [ ] 生成任务列表：顺序编号 + 可内联编辑 + 删除按钮
- [ ] "确认创建计划"→ POST /tasks/batch → 跳转首页

### 遗忘曲线复习
- [ ] 打卡完成后正确计算 1/2/4/7/15 天复习时间点
- [ ] 创建复习子任务：is_review_task=true / parent_task_id=原任务ID / task_type='review'
- [ ] 复习任务需用户手动确认后纳入计划

## 七、智能日历展望模块验证

- [ ] GET /calendar/today 返回今日任务正确
- [ ] GET /calendar/tomorrow 返回 AI 推荐明日任务正确
- [ ] 休息建议：连续打卡 ≥7 天时 rest_suggested=true
- [ ] 今日任务卡片（墨色标签）正确显示任务名称和预计时长
- [ ] 明日推荐卡片（鼠尾草色标签）正确显示任务名称、难度、建议用时
- [ ] 休息建议标记（日期格子灰色小点）正确
- [ ] 用户完成今日所有任务后明日推荐自动更新

## 八、规律排行模块验证

### 规律性计算
- [ ] 规律性得分计算正确（标准差 + 波动系数，最近 30 天数据）
- [ ] GET /ranking/me?scope=group|global 返回正确排名区间
- [ ] 排名区间枚举正确：top_20 / top_60 / bottom_40 / insufficient
- [ ] 打卡次数 < 7 次 → 返回 insufficient + "数据不足，继续打卡"
- [ ] 不显示具体排名数字
- [ ] 维度切换功能正常（小组/全局）

### 徽章系统
- [ ] 全部 9 个徽章初始化到 badges 表
- [ ] GET /badges/ 返回全部徽章列表
- [ ] GET /badges/me 返回用户已获得徽章
- [ ] 规律达人徽章（top_20）正常授予
- [ ] 习惯养成者徽章（top_60）正常授予
- [ ] 进步之星徽章（持续进步）正常授予
- [ ] 七日连续 / 英语坚持 / 错题复盘 / 早起学习 / 晚间专注 / 小组贡献 / 新计划创建徽章按条件授予

### 排行页面（pages/ranking）
- [ ] 深色 Hero 区（排名区间 + 称号文案）展示正确
- [ ] 三类排名区间说明卡片展示
- [ ] 徽章墙 3×3 网格，已获得（亮色）和未获得（灰色）区分正确
- [ ] 维度切换按钮交互正常

## 九、设置与小组模块验证

### 提醒与设置
- [ ] GET /settings/reminder 返回提醒配置
- [ ] PUT /settings/reminder 更新 reminder_enabled / reminder_time / task_expire_notify
- [ ] GET /report/pdf 生成并返回有效 PDF 报告
- [ ] 提醒时间到达 → 测试号 wx.showModal 弹窗 → 正式号模板消息（已预留）

### 小组管理
- [ ] GET /groups/my 返回当前用户小组信息（名称/成员数/完成率/排名区间）
- [ ] POST /groups/ 创建小组 + 自动生成邀请码
- [ ] POST /groups/join 通过邀请码成功加入
- [ ] PUT /groups/{id} 仅创建者可更新
- [ ] 非创建者更新 → 返回 403

### 设置页面（pages/settings）
- [ ] 个人资料卡片（头像 + 昵称 + 学习目标 + 编辑入口）正常
- [ ] 提醒设置区域：两个开关正常
- [ ] 小组信息卡片（名称/成员数/完成率/排名区间/加入/管理入口）正常
- [ ] PDF 导出入口正常
- [ ] 关于应用（版本号 + 产品名称）正常
- [ ] 退出登录 → 清除 token + 回到登录页

## 十、非功能性需求验证

### 性能
- [ ] 页面加载时间 ≤ 2 秒
- [ ] 打卡响应时间 ≤ 500 毫秒
- [ ] 日历渲染时间 ≤ 1 秒
- [ ] AI 解析响应时间 ≤ 5 秒
- [ ] 规律性排行计算 ≤ 1 秒

### 安全
- [ ] 无 SQL 注入和 XSS 漏洞
- [ ] 权限控制严格，用户只能访问自己数据
- [ ] 用户输入转义处理
- [ ] AI API Key 不在前端代码中暴露
- [ ] JWT token 有效期 24 小时

### 兼容性
- [ ] 微信版本 ≥ 7.0 兼容性正常
- [ ] iOS ≥ 12、Android ≥ 8.0 兼容性正常
- [ ] 屏幕适配 320px-1080px 宽度

### 用户体验
- [ ] 界面语言为中文（简体）
- [ ] 关键操作有明确提示和反馈
- [ ] 友好的错误提示和引导

## 十一、边界条件验证

### 打卡相关
- [ ] 当天未打卡 → 日历显示 missed（虚线边框），统计计入未打卡天数
- [ ] 补打卡最近 7 天正常，超过 7 天不可补
- [ ] 连续打卡中断（非休息日）→ 连续天数重置为 0
- [ ] 休息建议日不打卡 → 不中断连续天数
- [ ] 同一任务多次打卡正常
- [ ] 任务结束日期过期 → status 自动标记为 expired
- [ ] 任务软删除 → 历史打卡记录保留

### AI 相关
- [ ] AI 解析失败 → 错误提示 + 引导重试
- [ ] AI 返回数据格式异常 → 前端数据校验 + 提示重试
- [ ] AI 调用超时 → 加载超时提示 + 重试按钮
- [ ] 超过每日调用次数 → 429 + "今日 AI 规划次数已用完"
- [ ] 用户拒绝 AI 生成任务 → 任务不创建

### 日历相关
- [ ] 用户无今日任务 → 今日任务卡片显示"暂无任务" + 引导去规划页
- [ ] 用户拒绝休息建议 → 可继续打卡，休息标记保留但不强制

### 排行相关
- [ ] 打卡次数 < 7 次 → 排行页显示"数据不足，继续打卡"

### 通用异常
- [ ] 用户首次使用 → 首页空状态引导
- [ ] 无打卡记录 → 统计页"暂无数据"提示
- [ ] 前端防抖处理，防止重复提交
- [ ] 跨时区打卡 → 按用户设置时区（默认 Asia/Shanghai）计算

## 十二、个人测试号专项验证

- [ ] 测试号 AppID 配置正确
- [ ] 前端 config.ts 中 apiBaseUrl 指向本地后端
- [ ] 不依赖 wx.requestSubscribeMessage（模板消息）
- [ ] 不依赖手机号授权
- [ ] 提醒降级方案：本地 wx.showModal 弹窗正常
- [ ] 所有功能在开发者工具「不校验合法域名」模式下正常运行
- [ ] 代码中无硬编码正式号专属 API 调用

## 十三、迁移验证：测试号 → 正式号

- [ ] 更换 `project.config.json` 中的 AppID 为正式号 AppID
- [ ] 更新 `src/config.ts` 中 `prod.apiBaseUrl` 为正式域名
- [ ] 微信管理后台配置 request 和 uploadFile 合法域名
- [ ] 更新后端 WECHAT_APPID / WECHAT_APPSECRET 环境变量为正式号
- [ ] 正式号启用模板消息（wx.requestSubscribeMessage）
- [ ] 生产环境 HTTPS 可访问
- [ ] 迁移后全部核心功能回归通过

## 十四、部署验证

- [ ] API 接口可通过 HTTPS 访问
- [ ] 服务健康检查通过
- [ ] 小程序代码上传成功
- [ ] 小程序审核通过
- [ ] 用户可正常使用所有功能
- [ ] 数据库定期备份机制正常（如果实现）
