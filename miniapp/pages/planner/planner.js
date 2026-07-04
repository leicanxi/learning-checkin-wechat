const { post } = require('../../utils/api')

Page({
  data: {
    learningModes: ['考试冲刺', '日常积累', '技能进修', '错题复盘', '自由模式'],
    modeIndex: 0,
    goalText: '',
    voiceActive: false,
    loading: false,
    customName: '',
    customDuration: '',
    customSubject: '',
    weekDays: ['一', '二', '三', '四', '五', '六', '日'],
    selectedDays: [true, true, true, true, true, false, false],
    everyDay: false,
    planList: [],        // 展示用字符串数组，保持 WXML 兼容
    planItems: [],       // 结构化数据 [{ type, name, task_date, subject, suggested_duration, difficulty, knowledge_tags, source, display }]
    aiSummary: '',       // AI 计划概述
    toastShow: false,
    toastText: ''
  },

  // 学习模式
  onModeChange(e) {
    this.setData({ modeIndex: parseInt(e.detail.value) })
  },

  onGoalInput(e) {
    this.setData({ goalText: e.detail.value })
  },

  // 语音
  toggleVoice() {
    const active = !this.data.voiceActive
    this.setData({ voiceActive: active })
    this.showToast(active ? '正在模拟语音输入' : '语音输入已结束')
  },

  // 上传材料
  uploadMaterial() {
    wx.chooseMessageFile({
      count: 5,
      type: 'all',
      success: (res) => {
        const count = res.tempFiles.length
        this.showToast(count ? `已上传 ${count} 份学习材料` : '未选择材料')
      }
    })
  },

  // AI 规划
  async generatePlan() {
    if (!this.data.goalText.trim()) {
      wx.showToast({ title: '请先输入学习材料或目标', icon: 'none', duration: 1500 })
      return
    }
    this.setData({ loading: true })
    try {
      const modeMap = ['exam', 'daily', 'skill', 'review', 'free']
      const res = await post('/ai/generate-plan', {
        mode: modeMap[this.data.modeIndex] || 'free',
        content: this.data.goalText
      })
      const generatedTasks = res.tasks || []
      if (generatedTasks.length > 0) {
        // 结构化存储每个任务，保留全部字段
        const aiItems = generatedTasks.map(p => ({
          type: 'ai',
          name: p.name,
          task_date: p.task_date,
          subject: p.subject || '',
          suggested_duration: p.suggested_duration || 30,
          difficulty: p.difficulty || 'medium',
          knowledge_tags: p.knowledge_tags || [],
          source: 'ai',
          display: `${p.name}（${p.task_date || '待排期'}｜${p.subject || '综合'}｜${p.suggested_duration || 30}min）`
        }))

        this.setData({
          aiSummary: res.summary || '',
          planItems: [...this.data.planItems, ...aiItems],
          planList: [...this.data.planList, ...aiItems.map(i => i.display)]
        })
        this.showToast(`已生成 ${generatedTasks.length} 项学习任务`)
      } else {
        this.showToast('未生成计划，请调整输入')
      }
    } catch (e) {
      wx.showToast({ title: e.message || 'AI 服务暂不可用', icon: 'none', duration: 2000 })
    }
    this.setData({ loading: false })
  },

  clearGoal() {
    this.setData({ goalText: '', planList: [], planItems: [], aiSummary: '' })
  },

  // 自定义任务
  onCustomName(e) { this.setData({ customName: e.detail.value }) },
  onCustomDuration(e) { this.setData({ customDuration: e.detail.value }) },
  onCustomSubject(e) { this.setData({ customSubject: e.detail.value }) },

  toggleEveryDay() {
    const active = !this.data.everyDay
    this.setData({
      everyDay: active,
      selectedDays: active
        ? [true, true, true, true, true, true, true]
        : [false, false, false, false, false, false, false]
    })
  },

  toggleDay(e) {
    const idx = parseInt(e.currentTarget.dataset.idx)
    const days = [...this.data.selectedDays]
    days[idx] = !days[idx]
    const allOn = days.every(d => d)
    this.setData({
      selectedDays: days,
      everyDay: allOn
    })
  },

  addCustomTask() {
    const { customName, customDuration, customSubject, weekDays, selectedDays } = this.data
    if (!customName.trim()) {
      wx.showToast({ title: '请填写自定义任务名称', icon: 'none', duration: 1500 })
      return
    }
    const hasSelection = selectedDays.some(d => d)
    if (!hasSelection) {
      wx.showToast({ title: '请至少选择一个打卡日', icon: 'none', duration: 1500 })
      return
    }
    const daysLabel = this.data.everyDay
      ? '每天'
      : weekDays.filter((_, i) => selectedDays[i]).join('、')
    const display = `${customName}（${customSubject || '自定义'}，${daysLabel}，建议 ${customDuration || '20'} 分钟）`

    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
    const items = []
    for (let offset = 0; offset < 7; offset++) {
      const d = new Date(today)
      d.setDate(today.getDate() + offset)
      const weekdayIndex = (d.getDay() + 6) % 7
      if (!selectedDays[weekdayIndex]) continue
      const taskDate = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      items.push({
        type: 'custom',
        name: customName,
        task_date: taskDate,
        subject: customSubject || '',
        suggested_duration: parseInt(customDuration) || 20,
        difficulty: 'medium',
        knowledge_tags: [],
        source: 'manual',
        display: `${customName}（${taskDate}｜${customSubject || '自定义'}｜${customDuration || '20'}min）`
      })
    }
    this.setData({
      planItems: [...this.data.planItems, ...items],
      planList: [...this.data.planList, ...items.map(i => i.display)],
      customName: '',
      customDuration: '',
      customSubject: ''
    })
    this.showToast(`已添加 ${items.length} 项自定义任务`)
  },

  // 编辑计划（弹窗）
  editPlan(e) {
    const idx = parseInt(e.currentTarget.dataset.idx)
    const plans = [...this.data.planList]
    wx.showModal({
      title: '编辑任务',
      content: plans[idx],
      editable: true,
      placeholderText: plans[idx],
      success: (res) => {
        if (res.confirm && res.content) {
          plans[idx] = res.content
          this.setData({ planList: plans })
        }
      }
    })
  },

  removePlan(e) {
    const idx = parseInt(e.currentTarget.dataset.idx)
    const plans = [...this.data.planList]
    const items = [...this.data.planItems]
    plans.splice(idx, 1)
    items.splice(idx, 1)
    this.setData({ planList: plans, planItems: items })
    this.showToast('已删除计划任务')
  },

  async confirmPlan() {
    if (this.data.planItems.length === 0) return
    try {
      // 从结构化 planItems 构建 TaskCreate 数组
      const tasks = this.data.planItems.map(item => ({
        name: item.name,
        task_date: item.task_date,
        subject: item.subject || '',
        suggested_duration: item.suggested_duration || 30,
        difficulty: item.difficulty || 'medium',
        knowledge_tags: item.knowledge_tags || [],
        source: item.source || 'manual'
      }))

      await post('/tasks/batch', { tasks })
      this.showToast('计划已导入首页任务与日历')
      this.setData({ planList: [], planItems: [], goalText: '', aiSummary: '' })
      setTimeout(() => { wx.switchTab({ url: '/pages/home/home' }) }, 800)
    } catch (e) {
      this.showToast(e.message || '计划导入失败')
    }
  },

  showToast(text) {
    this.setData({ toastText: text, toastShow: true })
    clearTimeout(this._toastTimer)
    this._toastTimer = setTimeout(() => {
      this.setData({ toastShow: false })
    }, 1500)
  }
})
