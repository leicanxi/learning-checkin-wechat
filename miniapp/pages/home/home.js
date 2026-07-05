const { get, post, del } = require('../../utils/api')
const { getNavMetrics } = require('../../utils/nav')

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
    heroCopy: '先完成今天的任务，保持稳定节奏。',
    tasks: [],
    toastShow: false,
    toastText: ''
  },

  onShow() {
    this.setData({ ...getNavMetrics(), todayLabel: this.getTodayLabel() })
    this.loadAll()
  },

  getTodayLabel() {
    const d = new Date()
    return `周${weekDayLabels[d.getDay()]}`
  },

  async loadAll() {
    const ts = todayStr()
    try {
      const [tasksRes, statsRes] = await Promise.all([
        get('/tasks/', { date: ts }).catch(() => []),
        get('/stats/').catch(() => null)
      ])

      const tasks = Array.isArray(tasksRes) ? tasksRes : []
      const formattedTasks = tasks.map(t => ({
        ...t,
        timeTip: t.suggested_duration ? `建议 ${t.suggested_duration} 分钟` : '',
        subject: t.subject || '未分类',
        tagClass: t.source === 'ai' ? 'sage' : 'ink',
        tagLabel: t.source === 'ai' ? 'AI' : '手动'
      }))

      const total = formattedTasks.length
      const doneCount = formattedTasks.filter(t => t.completed).length
      const stats = statsRes || {}

      this.setData({
        tasks: formattedTasks,
        streakDays: stats.current_streak || 0,
        weekRate: stats.weekly_rate != null ? Math.round(stats.weekly_rate) : 0,
        monthRate: stats.monthly_rate != null ? Math.round(stats.monthly_rate) : 0,
        rankLabel: '--',
        heroCopy: doneCount === total && total > 0
          ? '今日任务已完成，日历和统计会自动同步。'
          : '先完成今天的任务，保持稳定节奏。'
      })
    } catch (e) {
      console.error('加载首页数据失败:', e)
    }
  },

  async toggleTask(e) {
    const { id, completed, checkinId } = e.currentTarget.dataset
    const isCompleted = completed === true || completed === 'true'
    if (isCompleted) {
      try {
        if (checkinId) {
          await del(`/checkins/${checkinId}`)
          this.showToast('已取消打卡')
        }
      } catch (e) {
        this.showToast('操作失败')
      }
    } else {
      try {
        await post('/checkins/', { task_id: id })
        this.showToast('打卡成功')
      } catch (e) {
        this.showToast('打卡失败')
      }
    }
    await this.loadAll()
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
