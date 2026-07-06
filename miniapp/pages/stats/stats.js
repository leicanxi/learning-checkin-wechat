const { get } = require('../../utils/api')
const { getNavMetrics } = require('../../utils/nav')

Page({
  data: {
    periods: ['周', '月', '年', '自定义'],
    activePeriod: '周',
    trendTitle: '近 7 天趋势',
    trendTag: '完成 -- 次',
    trendChartMode: 'line',
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
    allBadges: [],
    tiers: [
      { title: '前 20% · 规律达人', desc: '连续性稳定，完成率高，适合作为小组榜样。' },
      { title: '20–60% · 习惯养成者', desc: '已有基础节奏，建议减少周末或考试前后的中断。' },
      { title: '60%+ · 继续加油', desc: '先完成低压力任务，恢复连续性后排名会明显改善。' }
    ]
  },

  onShow() {
    this.setData(getNavMetrics())
    this.loadAll()
  },

  async loadAll() {
    try {
      const isGlobalScope = this.data.activeRankScope === '全局'
      const [stats, ranking, badges] = await Promise.all([
        get('/stats/', { period: this.getPeriodKey() }).catch(() => null),
        get('/ranking/me', { scope: isGlobalScope ? 'global' : 'group' }).catch(() => null),
        get('/badges/me').catch(() => [])
      ])

      // 趋势数据 —— 后端字段 checkin_trend
      const trend = (stats && stats.checkin_trend) ? stats.checkin_trend : []
      const trendData = this.withBarHeights(this.buildRecentTrendData(trend))

      // MVP 已砍掉复习/掌握系统，不展示 knowledge_progress 的占位数据。
      // 这里复用环形样式展示真实完成率。
      const masteryData = stats ? [
        {
          subject: '本周完成率',
          progress: Math.round(stats.weekly_rate || 0),
          note: '近 7 天任务完成占比',
          bgColor: 'var(--terracotta)'
        },
        {
          subject: '近30天完成率',
          progress: Math.round(stats.monthly_rate || 0),
          note: '近 30 天任务完成占比',
          bgColor: 'var(--sage)'
        }
      ] : []

      // 科目分布
      const subjects = (stats && stats.subject_distribution) ? stats.subject_distribution : []
      const earnedBadges = (badges || [])
        .filter(b => b.earned)
        .map(b => ({
          id: b.id,
          icon: b.icon_css || (b.name || '?').slice(0, 1),
          name: b.name,
          earned_at: b.earned_at || ''
        }))

      this.setData({
        trendData,
        trendTag: `完成 ${trendData.reduce((s, d) => s + d.count, 0)} 次`,
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
        allBadges: earnedBadges,
        displayBadges: earnedBadges.slice(0, 3)
      }, () => {
        if (this.data.trendChartMode === 'line' && trendData.length > 0) {
          this.drawTrendChart(trendData)
        }
      })
    } catch (e) {
      // 模拟数据
      this.setMockData()
    }
  },

  getPeriodKey() {
    const map = { '周': 'week', '月': 'month', '年': 'year', '自定义': 'custom' }
    return map[this.data.activePeriod] || 'week'
  },

  buildRecentTrendData(trend) {
    const countByDate = {}
    ;(trend || []).forEach(item => {
      countByDate[item.date] = item.count || 0
    })

    const result = []
    const today = new Date()
    for (let offset = 6; offset >= 0; offset--) {
      const d = new Date(today)
      d.setDate(today.getDate() - offset)
      const date = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      result.push({
        date,
        label: `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`,
        count: countByDate[date] || 0
      })
    }
    return result
  },

  getCompletionCopy(stats) {
    if (!stats) return '暂无数据'
    const total = stats.total_checkins || 0
    if (total > 100) return '今年已完成超过 100 次学习打卡，最长连续记录保持稳定，整体规律性优于多数同组用户。'
    if (total > 50) return '累计完成超过 50 次打卡，学习习惯正在稳固形成，继续保持。'
    return '本周已完成适量学习任务，连续完成率稳定，周末任务仍有提升空间。'
  },

  setMockData() {
    const trendData = this.withBarHeights([
      { label: '五', count: 3 },
      { label: '六', count: 2 },
      { label: '日', count: 4 },
      { label: '一', count: 5 },
      { label: '二', count: 3 },
      { label: '三', count: 6 },
      { label: '四', count: 4 }
    ])
    this.setData({
      trendData,
      trendTag: '完成 18 次',
      masteryData: [
        { subject: '本周完成率', progress: 82, note: '近 7 天任务完成占比', bgColor: 'var(--terracotta)' },
        { subject: '近30天完成率', progress: 64, note: '近 30 天任务完成占比', bgColor: 'var(--sage)' }
      ],
      completedCount: '64 次',
      completionCopy: '本周已完成 18 次学习任务，其中英语任务占比最高。连续完成率稳定，周末任务仍有提升空间。',
      subjectData: [
        { subject: '英语', percentage: 78 },
        { subject: '数学', percentage: 62 },
        { subject: '物理', percentage: 46 }
      ],
      rankPercent: '前 20%',
      rankHonor: '你已获得「规律达人」称号，最近 7 天有 5 天按计划完成。',
      allBadges: [],
      displayBadges: []
    }, () => {
      if (this.data.trendChartMode === 'line') {
        this.drawTrendChart(trendData)
      }
    })
  },

  withBarHeights(data) {
    const max = Math.max(...data.map(d => d.count), 1)
    return data.map(item => ({
      ...item,
      barHeight: Math.max(8, Math.round((item.count / max) * 104))
    }))
  },

  toggleTrendChart() {
    const nextMode = this.data.trendChartMode === 'line' ? 'bar' : 'line'
    this.setData({ trendChartMode: nextMode }, () => {
      if (nextMode === 'line' && this.data.trendData.length > 0) {
        this.drawTrendChart(this.data.trendData)
      }
    })
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
