const { get, post, del } = require('../../utils/api')

const weekDayLabels = ['日', '一', '二', '三', '四', '五', '六']

function todayStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

Page({
  data: {
    todayLabel: '',
    streakDays: 0,
    weekRate: 0,
    monthRate: 0,
    rankLabel: '--',
    heroCopy: '你已经进入稳定期。今天保持 3 个学习动作即可，不需要额外加量。',
    tasks: [],
    toastShow: false,
    toastText: ''
  },

  onShow() {
    this.setData({ todayLabel: this.getTodayLabel() })
    this.loadAll()
  },

  getTodayLabel() {
    const d = new Date()
    return `周${weekDayLabels[d.getDay()]}`
  },

  async loadAll() {
    const ts = todayStr()
    try {
      const [tasksRes, statsRes, checkinsRes] = await Promise.all([
        get('/tasks/', { status: 'active' }).catch(() => null),
        get('/stats/').catch(() => null),
        get('/checkins/', { start_date: ts, end_date: ts }).catch(() => null)
      ])

      // 处理任务 —— 后端返回 TaskOut 数组，用 status=active 过滤后前端按 start_date 筛选今天
      const allTasks = (tasksRes && Array.isArray(tasksRes)) ? tasksRes : []
      const tasks = allTasks.filter(t => {
        if (!t.start_date) return true
        const start = t.start_date.split('T')[0]
        if (start > ts) return false
        // 有 end_date 且已过期则排除
        if (t.end_date) {
          const end = t.end_date.split('T')[0]
          if (end < ts) return false
        }
        return true
      })

      const checkinIds = new Set(
        checkinsRes && Array.isArray(checkinsRes)
          ? checkinsRes.map(c => c.task_id)
          : []
      )
      const formattedTasks = tasks.map(t => {
        const done = checkinIds.has(t.id)
        return {
          ...t,
          done,
          timeTip: t.suggested_duration ? `建议 ${t.suggested_duration} 分钟` : '',
          subject: t.subject || '未分类',
          tagClass: t.task_type === 'main' ? 'ink' : (t.task_type === 'light' ? 'sage' : 'clay'),
          tagLabel: t.task_type === 'main' ? '主任务' : (t.task_type === 'light' ? '轻量' : '复习')
        }
      })

      // 统计数据
      const total = formattedTasks.length
      const doneCount = formattedTasks.filter(t => t.done).length

      const stats = statsRes || {}
      this.setData({
        tasks: formattedTasks,
        streakDays: stats.current_streak || 0,
        weekRate: stats.weekly_rate != null ? Math.round(stats.weekly_rate) : (total > 0 ? Math.round(doneCount / total * 100) : 0),
        monthRate: stats.monthly_rate != null ? Math.round(stats.monthly_rate) : 0,
        rankLabel: '--',
        heroCopy: doneCount === total && total > 0
          ? '今日任务已完成。系统已同步到日历与统计，明天会推荐低压力复习任务。'
          : '你已经进入稳定期。今天保持 3 个学习动作即可，不需要额外加量。'
      })
    } catch (e) {
      console.error('加载首页数据失败:', e)
    }
  },

  async toggleTask(e) {
    const { id, done } = e.currentTarget.dataset
    const ts = todayStr()
    if (done) {
      try {
        const res = await get('/checkins/', { start_date: ts, end_date: ts })
        const record = res.find(c => c.task_id === id)
        if (record) {
          await del(`/checkins/${record.id}`)
          this.showToast('已取消打卡')
        }
      } catch (e) {
        this.showToast('操作失败')
      }
    } else {
      try {
        await post('/checkins/', { task_id: id })
        this.showToast('打卡成功！')
      } catch (e) {
        this.showToast('打卡失败')
      }
    }
    this.loadAll()
  },

  showToast(text) {
    this.setData({ toastText: text, toastShow: true })
    clearTimeout(this._toastTimer)
    this._toastTimer = setTimeout(() => {
      this.setData({ toastShow: false })
    }, 1500)
  },

  goPlanner() {
    wx.switchTab({ url: '/pages/planner/planner' })
  }
})
