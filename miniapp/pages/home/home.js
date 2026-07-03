const { get, post } = require('../../utils/api')

const weekDayLabels = ['日', '一', '二', '三', '四', '五', '六']

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
    try {
      const [tasksRes, statsRes, checkinsRes] = await Promise.all([
        get('/tasks/today').catch(() => null),
        get('/stats/summary').catch(() => null),
        get('/checkins/today').catch(() => null)
      ])

      // 处理任务
      const tasks = (tasksRes && tasksRes.tasks) ? tasksRes.tasks : []
      const checkinIds = new Set(
        checkinsRes && checkinsRes.checkins
          ? checkinsRes.checkins.map(c => c.task_id)
          : []
      )
      const formattedTasks = tasks.map(t => {
        const done = checkinIds.has(t.id)
        return {
          ...t,
          done,
          timeTip: t.duration_minutes ? `建议 ${t.duration_minutes} 分钟` : '',
          subject: t.subject || '未分类',
          tagClass: t.task_type === 'main' ? 'ink' : (t.task_type === 'light' ? 'sage' : 'clay'),
          tagLabel: t.task_type === 'main' ? '主任务' : (t.task_type === 'light' ? '轻量' : '已同步')
        }
      })

      // 统计数据
      const total = formattedTasks.length
      const doneCount = formattedTasks.filter(t => t.done).length

      const stats = statsRes || {}
      this.setData({
        tasks: formattedTasks,
        streakDays: stats.streak_days || 0,
        weekRate: stats.week_rate != null ? Math.round(stats.week_rate) : (total > 0 ? Math.round(doneCount / total * 100) : 0),
        monthRate: stats.month_rate != null ? Math.round(stats.month_rate) : 0,
        rankLabel: stats.rank_range || '前20%',
        heroCopy: doneCount === total && total > 0
          ? '今日任务已完成。系统已同步到日历与统计，明天会推荐低压力复习任务。'
          : '你已经进入稳定期。今天保持 3 个学习动作即可，不需要额外加量。'
      })
    } catch (e) {
      console.error('加载首页数据失败:', e)
      // 静默使用默认值
    }
  },

  async toggleTask(e) {
    const { id, done } = e.currentTarget.dataset
    if (done) {
      // 取消打卡：需要知道 checkin ID
      // 简化处理，重新加载
      try {
        const res = await get('/checkins/today')
        const record = res.checkins.find(c => c.task_id === id)
        if (record) {
          await post(`/checkins/${record.id}/undo`)
          this.showToast('已取消打卡')
        }
      } catch (e) {
        this.showToast('操作失败')
      }
    } else {
      try {
        await post('/checkins', { task_id: id })
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
