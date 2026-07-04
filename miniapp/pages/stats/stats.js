const { get } = require('../../utils/api')

Page({
  data: {
    periods: ['周', '月', '年', '自定义'],
    activePeriod: '周',
    trendTitle: '近 7 天趋势',
    trendTag: '完成 -- 次',
    trendData: [],
    masteryData: [],
    completedCount: '--',
    completionCopy: '',
    subjectData: [],
    rankScopeLabel: '小组排名区间',
    rankPercent: '--',
    rankHonor: '',
    rankScopes: ['小组', '全局'],
    activeRankScope: '小组',
    rankInfoShow: false,
    badgesExpanded: false,
    displayBadges: [],
    allBadges: [
      { icon: '稳', name: '规律达人' },
      { icon: '进', name: '进步之星' },
      { icon: '7', name: '七日连续' },
      { icon: '英', name: '英语坚持' },
      { icon: '复', name: '错题复盘' },
      { icon: '早', name: '早起学习' },
      { icon: '夜', name: '晚间专注' },
      { icon: '组', name: '小组贡献' },
      { icon: '新', name: '新计划创建' }
    ],
    tiers: [
      { title: '前 20% · 规律达人', desc: '连续性稳定，完成率高，适合作为小组榜样。' },
      { title: '20–60% · 习惯养成者', desc: '已有基础节奏，建议减少周末或考试前后的中断。' },
      { title: '60%+ · 继续加油', desc: '先完成低压力任务，恢复连续性后排名会明显改善。' }
    ]
  },

  onShow() {
    this.loadAll()
  },

  async loadAll() {
    try {
      const isGlobalScope = this.data.activeRankScope === '全局'
      const [stats, ranking] = await Promise.all([
        get('/stats/', { period: this.getPeriodKey() }).catch(() => null),
        get('/ranking/me', { scope: isGlobalScope ? 'global' : 'group' }).catch(() => null)
      ])

      // 趋势数据 —— 后端字段 checkin_trend
      const trend = (stats && stats.checkin_trend) ? stats.checkin_trend : []
      const trendData = trend.slice(-7).map(item => {
        const parts = item.date.split('-')
        return {
          label: parts.length >= 3 ? `${parts[1]}/${parts[2]}` : item.date,
          count: item.count
        }
      })

      // 掌握进度 —— 后端字段 knowledge_progress（可能是 dict 或 array）
      const rawKp = (stats && stats.knowledge_progress) ? stats.knowledge_progress : {}
      let mastery
      if (Array.isArray(rawKp)) {
        mastery = rawKp
      } else {
        mastery = Object.entries(rawKp).map(([subject, progress]) => {
          const pct = typeof progress === 'number' ? (progress > 1 ? progress : Math.round(progress * 100)) : 0
          return { subject, progress: pct, note: '' }
        })
      }
      const colors = ['var(--terracotta)', 'var(--sage)', '#d4a853', '#4d4c48']
      const masteryData = mastery.slice(0, 2).map((m, i) => ({
        subject: m.subject,
        progress: Math.round(m.progress),
        note: m.note || '',
        bgColor: colors[i % colors.length]
      }))

      // 科目分布
      const subjects = (stats && stats.subject_distribution) ? stats.subject_distribution : []

      this.setData({
        trendData,
        trendTag: `完成 ${trend.reduce((s, d) => s + d.count, 0)} 次`,
        masteryData,
        completedCount: stats ? `${stats.total_checkins || 0} 次` : '--',
        completionCopy: this.getCompletionCopy(stats),
        subjectData: subjects.slice(0, 6).map(s => ({
          ...s,
          percentage: Math.round(s.percentage || 0)
        })),
        rankScopeLabel: isGlobalScope ? '全局排名区间' : '小组排名区间',
        rankPercent: ranking ? (ranking.rank_range_label || '--') : '--',
        rankHonor: ranking ? (ranking.rank_title || '加载中...') : '加载中...',
        displayBadges: this.data.allBadges.slice(0, 3)
      })

      // 绘制折线图
      if (trendData.length > 0) {
        this.drawTrendChart(trendData)
      }
    } catch (e) {
      // 模拟数据
      this.setMockData()
    }
  },

  getPeriodKey() {
    const map = { '周': 'week', '月': 'month', '年': 'year', '自定义': 'custom' }
    return map[this.data.activePeriod] || 'week'
  },

  getCompletionCopy(stats) {
    if (!stats) return '暂无数据'
    const total = stats.total_checkins || 0
    if (total > 100) return '今年已完成超过 100 次学习打卡，最长连续记录保持稳定，整体规律性优于多数同组用户。'
    if (total > 50) return '累计完成超过 50 次打卡，学习习惯正在稳固形成，继续保持。'
    return '本周已完成适量学习任务，连续完成率稳定，周末任务仍有提升空间。'
  },

  setMockData() {
    const trendData = [
      { label: '五', count: 3 },
      { label: '六', count: 2 },
      { label: '日', count: 4 },
      { label: '一', count: 5 },
      { label: '二', count: 3 },
      { label: '三', count: 6 },
      { label: '四', count: 4 }
    ]
    this.setData({
      trendData,
      trendTag: '完成 18 次',
      masteryData: [
        { subject: '英语词汇', progress: 82, note: 'Unit 1-4 掌握较稳定', bgColor: 'var(--terracotta)' },
        { subject: '物理电学', progress: 64, note: '概念题仍需复盘', bgColor: 'var(--sage)' }
      ],
      completedCount: '64 次',
      completionCopy: '本周已完成 18 次学习任务，其中英语任务占比最高。连续完成率稳定，周末任务仍有提升空间。',
      subjectData: [
        { subject: '英语', percentage: 78 },
        { subject: '数学', percentage: 62 },
        { subject: '物理', percentage: 46 }
      ],
      rankPercent: '前 20%',
      rankHonor: '你已获得「规律达人」称号，最近 7 天有 5 天按计划完成。'
    })
    if (trendData.length > 0) {
      this.drawTrendChart(trendData)
    }
  },

  getBarHeight(count) {
    const max = Math.max(...this.data.trendData.map(d => d.count), 1)
    return Math.max(8, (count / max) * 80)
  },

  switchPeriod(e) {
    const period = e.currentTarget.dataset.period
    this.setData({ activePeriod: period })
    this.loadAll()
  },

  switchRankScope(e) {
    const scope = e.currentTarget.dataset.scope
    this.setData({
      activeRankScope: scope,
      rankScopeLabel: scope === '全局' ? '全局排名区间' : '小组排名区间'
    })
    this.loadAll()
  },

  showRankInfo() {
    this.setData({ rankInfoShow: true })
  },

  closeRankInfo() {
    this.setData({ rankInfoShow: false })
  },

  toggleBadges() {
    const expanded = !this.data.badgesExpanded
    this.setData({
      badgesExpanded: expanded,
      displayBadges: expanded ? this.data.allBadges : this.data.allBadges.slice(0, 3)
    })
  },

  // 折线图绘制
  drawTrendChart(data) {
    const query = wx.createSelectorQuery()
    query.select('#trendCanvas').fields({ node: true, size: true }).exec((res) => {
      if (!res || !res[0]) return
      const canvas = res[0].node
      const ctx = canvas.getContext('2d')
      const dpr = wx.getSystemInfoSync().pixelRatio
      const width = res[0].width
      const height = 160
      canvas.width = width * dpr
      canvas.height = height * dpr
      ctx.scale(dpr, dpr)

      // 清空
      ctx.clearRect(0, 0, width, height)

      if (data.length < 2) return

      const maxVal = Math.max(...data.map(d => d.count), 1)
      const padding = { top: 20, right: 30, bottom: 30, left: 10 }
      const chartW = width - padding.left - padding.right
      const chartH = height - padding.top - padding.bottom

      // 点坐标
      const points = data.map((d, i) => ({
        x: padding.left + (i / (data.length - 1)) * chartW,
        y: padding.top + chartH - (d.count / maxVal) * chartH
      }))

      // 填充区域
      ctx.beginPath()
      ctx.moveTo(points[0].x, padding.top + chartH)
      points.forEach(p => ctx.lineTo(p.x, p.y))
      ctx.lineTo(points[points.length - 1].x, padding.top + chartH)
      ctx.closePath()
      const gradient = ctx.createLinearGradient(0, 0, 0, height)
      gradient.addColorStop(0, 'rgba(201,100,66,.22)')
      gradient.addColorStop(1, 'rgba(201,100,66,0)')
      ctx.fillStyle = gradient
      ctx.fill()

      // 折线
      ctx.beginPath()
      ctx.moveTo(points[0].x, points[0].y)
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y)
      }
      ctx.strokeStyle = '#c96442'
      ctx.lineWidth = 3
      ctx.lineCap = 'round'
      ctx.stroke()

      // 标签
      ctx.fillStyle = '#87867f'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'
      data.forEach((d, i) => {
        ctx.fillText(d.label, points[i].x, height - 6)
      })
    })
  }
})
