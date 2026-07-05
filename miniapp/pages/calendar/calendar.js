const { get } = require('../../utils/api')
const { getNavMetrics } = require('../../utils/nav')
const weekDays = ['日', '一', '二', '三', '四', '五', '六']

Page({
  data: {
    year: 2026,
    month: 7,
    selectedDate: '',
    calendarMode: 'month',
    calendarModeText: '周',
    monthTitle: '',
    monthlyCompletionRate: 0,
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
      { dotClass: 'today-dot', text: '今日' },
      { dotClass: 'pending-dot', text: '待完成' }
    ]
  },

  onShow() {
    const d = new Date()
    const todayStr = this.formatDate(d)
    this.setData({
      ...getNavMetrics(),
      year: d.getFullYear(),
      month: d.getMonth() + 1,
      selectedDate: todayStr,
      monthTitle: `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
    })
    this.fetchAll()
  },

  formatDate(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  },

  async fetchAll() {
    try {
      const [monthRes, todayRes, tomorrowRes] = await Promise.all([
        get('/calendar/month', { year: this.data.year, month: this.data.month }).catch(() => null),
        get('/calendar/today').catch(() => null),
        get('/calendar/tomorrow').catch(() => null)
      ])
      const datesArr = (monthRes && monthRes.dates) ? monthRes.dates : []
      const monthData = {}
      datesArr.forEach(d => { monthData[d.date] = d })
      this.buildCells(monthData, monthRes && monthRes.monthly_completion_rate)
      this.setData({
        monthData,
        monthlyCompletionRate: monthRes ? monthRes.monthly_completion_rate : 0,
        todayData: todayRes || null,
        tomorrowData: tomorrowRes || null
      })
    } catch (e) {
      this.buildCells({})
    }
  },

  buildCells(monthData, backendRate) {
    const { year, month } = this.data
    const firstDay = new Date(year, month - 1, 1)
    const lastDay = new Date(year, month, 0)
    const daysInMonth = lastDay.getDate()
    const startDow = firstDay.getDay()
    const today = new Date()
    const todayStr = this.formatDate(today)
    const monthCells = []

    // 前置空白
    for (let i = 0; i < startDow; i++) {
      monthCells.push({ day: '', muted: true, cls: 'date-btn muted' })
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const ds = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
      monthCells.push(this.buildDateCell(ds, d, monthData[ds], todayStr))
    }

    const cells = this.data.calendarMode === 'week'
      ? this.buildWeekCells(monthData, todayStr)
      : monthCells
    const rate = this.data.calendarMode === 'week'
      ? this.calcTaskRateForDates(cells.map(c => c.date).filter(Boolean), monthData)
      : (backendRate != null ? Math.round(backendRate) : this.calcRate(cells))
    this.setData({ cells, completionRate: rate })
  },

  buildDateCell(ds, day, dayData, todayStr) {
    let cls = 'date-btn'
    let status = ''

    if (dayData) {
      switch (dayData.status) {
        case 'checked_in':
          cls += ' done'; status = '已打卡'; break
        case 'missed':
          cls += ' missed'; status = '未打卡'; break
        case 'pending':
          cls += ds === todayStr ? ' today' : ' pending'; status = ds === todayStr ? '今日' : '待完成'; break
        case 'empty':
          status = ''; break
      }
    }

    return { day, muted: false, cls, status, date: ds }
  },

  buildWeekCells(monthData, todayStr) {
    const anchor = this.data.selectedDate ? new Date(this.data.selectedDate) : new Date()
    const start = new Date(anchor)
    start.setDate(anchor.getDate() - anchor.getDay())
    const cells = []
    for (let i = 0; i < 7; i++) {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      const ds = this.formatDate(d)
      cells.push(this.buildDateCell(ds, d.getDate(), monthData[ds], todayStr))
    }
    return cells
  },

  calcTaskRateForDates(dates, monthData) {
    let total = 0
    let completed = 0
    dates.forEach(ds => {
      const dayData = monthData[ds]
      if (!dayData) return
      const taskCount = (dayData.suggested_tasks_preview || []).length
      total += taskCount
      completed += Math.min(dayData.checkin_count || 0, taskCount)
    })
    return total > 0 ? Math.round(completed / total * 100) : 0
  },

  calcRate(cells) {
    const valid = cells.filter(c => c.date && c.status)
    if (valid.length === 0) return 0
    const done = valid.filter(c => c.status === '已打卡').length
    return Math.round(done / valid.length * 100)
  },

  toggleCalendarMode() {
    const nextMode = this.data.calendarMode === 'month' ? 'week' : 'month'
    this.setData({
      calendarMode: nextMode,
      calendarModeText: nextMode === 'month' ? '周' : '月'
    })
    this.buildCells(this.data.monthData || {}, this.data.monthlyCompletionRate)
  },

  onDateTap(e) {
    const { date, status } = e.currentTarget.dataset
    if (!date) return

    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    const cellDate = new Date(date)
    const displayDate = `${cellDate.getMonth() + 1} 月 ${cellDate.getDate()} 日`

    // 从后端返回的 monthData 获取该日期的任务详情
    const dayData = (this.data.monthData && this.data.monthData[date]) || {}
    const preview = dayData.suggested_tasks_preview || []
    const checkinCount = dayData.checkin_count || 0

    let text = ''
    if (date === todayStr) {
      const todayData = this.data.todayData
      if (todayData && todayData.tasks && todayData.tasks.length > 0) {
        const items = todayData.tasks.map(t => `- ${t.name}（${t.suggested_duration || '30'} 分钟）`)
        text = '今日任务：\n' + items.join('\n')
      } else if (preview.length > 0) {
        text = '今日安排：\n' + preview.map(t => `- ${typeof t === 'string' ? t : t.name}`).join('\n')
      } else {
        text = '今天安排了学习任务，暂未加载详情。'
      }
    } else if (date > todayStr) {
      if (preview.length > 0) {
        text = '安排任务：\n' + preview.map(t => `- ${typeof t === 'string' ? t : t.name}`).join('\n')
      } else if (checkinCount > 0) {
        text = `已安排 ${checkinCount} 项学习任务。`
      } else {
        text = '暂无安排，可在规划页添加任务。'
      }
    } else if (status === '已打卡') {
      text = preview.length > 0
        ? '已完成：\n' + preview.map(t => `- ${typeof t === 'string' ? t : t.name}`).join('\n')
        : '当天已完成学习打卡，学习记录已计入统计。'
    } else if (status === '待完成') {
      text = '暂无安排，可在规划页添加任务。'
    } else {
      text = '当天没有完整打卡记录。'
    }

    this.setData({
      selectedDate: date,
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
    this.setData({
      year,
      month,
      selectedDate: `${year}-${String(month).padStart(2, '0')}-01`,
      monthTitle: `${year} 年 ${month} 月`
    })
    this.fetchAll()
  },

  nextMonth() {
    let { year, month } = this.data
    month++
    if (month > 12) { month = 1; year++ }
    this.setData({
      year,
      month,
      selectedDate: `${year}-${String(month).padStart(2, '0')}-01`,
      monthTitle: `${year} 年 ${month} 月`
    })
    this.fetchAll()
  }
})
