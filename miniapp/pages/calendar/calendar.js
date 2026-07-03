const { get } = require('../../utils/api')
const weekDays = ['日', '一', '二', '三', '四', '五', '六']

Page({
  data: {
    year: 2026,
    month: 7,
    monthTitle: '',
    cells: [],
    completionRate: 0,
    todayData: null,
    tomorrowData: null,
    sheetShow: false,
    sheetTitle: '',
    sheetText: '',
    // 图例
    legends: [
      { dotClass: 'done-dot', text: '已打卡' },
      { dotClass: 'missed-dot', text: '未打卡' },
      { dotClass: 'rest-dot', text: '休息日' },
      { dotClass: 'today-dot', text: '今日' },
      { dotClass: 'tomorrow-dot', text: '明日推荐' }
    ]
  },

  onShow() {
    const d = new Date()
    this.setData({
      year: d.getFullYear(),
      month: d.getMonth() + 1,
      monthTitle: `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
    })
    this.fetchAll()
  },

  async fetchAll() {
    try {
      const [monthRes, todayRes, tomorrowRes] = await Promise.all([
        get('/calendar/month', { year: this.data.year, month: this.data.month }).catch(() => null),
        get('/calendar/today').catch(() => null),
        get('/calendar/tomorrow').catch(() => null)
      ])
      const monthData = (monthRes && monthRes.days) ? monthRes.days : {}
      this.buildCells(monthData)
      this.setData({
        todayData: todayRes || null,
        tomorrowData: tomorrowRes || null
      })
    } catch (e) {
      this.buildCells({})
    }
  },

  buildCells(monthData) {
    const { year, month } = this.data
    const firstDay = new Date(year, month - 1, 1)
    const lastDay = new Date(year, month, 0)
    const daysInMonth = lastDay.getDate()
    const startDow = firstDay.getDay()
    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)
    const tomorrowStr = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, '0')}-${String(tomorrow.getDate()).padStart(2, '0')}`

    const cells = []

    // 前置空白
    for (let i = 0; i < startDow; i++) {
      cells.push({ day: '', muted: true, cls: 'date-btn muted' })
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const ds = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      const dayData = monthData[ds]
      const dow = new Date(year, month - 1, d).getDay()

      let cls = 'date-btn'
      let status = ''

      if (ds === todayStr) {
        cls += ' today'
        status = '今日'
      } else if (ds === tomorrowStr) {
        cls += ' tomorrow'
        status = '明日推荐'
      } else if (dow === 0 || dow === 6) {
        cls += ' rest'
        status = '休息日'
      } else if (dayData) {
        const allDone = dayData.tasks && dayData.tasks.every(t => t.checked)
        cls += allDone ? ' done' : ' missed'
        status = allDone ? '已打卡' : '未打卡'
      } else if (ds < todayStr) {
        cls += ' missed'
        status = '未打卡'
      }

      cells.push({ day: d, muted: false, cls, status, date: ds })
    }

    this.setData({ cells, completionRate: this.calcRate(cells) })
  },

  calcRate(cells) {
    const valid = cells.filter(c => c.date && c.status !== '休息日')
    if (valid.length === 0) return 0
    const done = valid.filter(c => c.status === '已打卡').length
    return Math.round(done / valid.length * 100)
  },

  onDateTap(e) {
    const { date, status } = e.currentTarget.dataset
    if (!date) return

    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    const cellDate = new Date(date)
    const displayDate = `${cellDate.getMonth() + 1} 月 ${cellDate.getDate()} 日`

    let text = ''
    if (date === todayStr) {
      text = '今天安排了学习任务。完成后会更新连续天数和统计页数据。'
    } else if (date > todayStr) {
      text = '已安排学习任务，建议保持连续学习节奏。'
    } else if (status === '已打卡') {
      text = '当天已完成学习打卡，包含复习、练习或阅读任务，学习记录已计入统计。'
    } else if (status === '休息日') {
      text = '系统建议休息日，可做 5 分钟轻量复盘，不影响长期节奏。'
    } else {
      text = '当天没有完整打卡记录。可以补写学习备注，但不会计入连续天数。'
    }

    this.setData({
      sheetShow: true,
      sheetTitle: displayDate,
      sheetText: text
    })
  },

  closeSheet() {
    this.setData({ sheetShow: false })
  },

  prevMonth() {
    let { year, month } = this.data
    month--
    if (month < 1) { month = 12; year-- }
    this.setData({ year, month, monthTitle: `${year} 年 ${month} 月` })
    this.fetchAll()
  },

  nextMonth() {
    let { year, month } = this.data
    month++
    if (month > 12) { month = 1; year++ }
    this.setData({ year, month, monthTitle: `${year} 年 ${month} 月` })
    this.fetchAll()
  }
})
