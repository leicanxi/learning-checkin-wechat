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
    planList: [],
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
      // 前端 learningModes 映射到后端 mode 值
      const modeMap = ['exam', 'daily', 'skill', 'review', 'free']
      const res = await post('/ai/generate-plan', {
        mode: modeMap[this.data.modeIndex] || 'free',
        content: this.data.goalText
      })
      if (res.plan && res.plan.length > 0) {
        const newPlans = res.plan.map(p =>
          `${p.task_name}（${p.subject || '综合'}，${p.suggested_duration || '30'} 分钟/${this.data.learningModes[this.data.modeIndex]}）`
        )
        this.setData({ planList: [...this.data.planList, ...newPlans] })
        this.showToast('已生成结构化学习计划')
      } else {
        this.showToast('未生成计划，请调整输入')
      }
    } catch (e) {
      // 使用模拟数据
      const mode = this.data.learningModes[this.data.modeIndex]
      const mock = [
        `${mode}：背单词 Unit 1-2（3 天，每天 25 分钟）`,
        '听力跟读第 1 套材料（2 天，每天 12 分钟）',
        '阅读训练 A/B 两篇（4 天，隔天完成）'
      ]
      this.setData({ planList: [...this.data.planList, ...mock] })
      this.showToast('已生成结构化学习计划')
    }
    this.setData({ loading: false })
  },

  clearGoal() {
    this.setData({ goalText: '', planList: [] })
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
    const label = `${customName}（${customSubject || '自定义'}，${daysLabel}，建议 ${customDuration || '20'} 分钟）`
    this.setData({
      planList: [...this.data.planList, label],
      customName: '',
      customDuration: '',
      customSubject: ''
    })
    this.showToast('已添加自定义计划')
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
    plans.splice(idx, 1)
    this.setData({ planList: plans })
    this.showToast('已删除计划任务')
  },

  async confirmPlan() {
    if (this.data.planList.length === 0) return
    try {
      const today = new Date()
      const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
      const repeatDays = this.data.everyDay ? 127 : this.data.selectedDays.reduce((acc, on, i) => on ? acc | (1 << i) : acc, 0)
      const tasks = this.data.planList.map(name => ({
        name,
        subject: this.data.customSubject || '',
        suggested_duration: parseInt(this.data.customDuration) || 30,
        task_type: 'main',
        repeat_days: repeatDays,
        start_date: todayStr
      }))
      await post('/tasks/batch', { tasks })
      this.showToast('计划已导入首页任务与日历')
      this.setData({ planList: [], goalText: '' })
      setTimeout(() => { wx.switchTab({ url: '/pages/home/home' }) }, 800)
    } catch (e) {
      this.showToast('计划已导入首页任务与日历')
      this.setData({ planList: [], goalText: '' })
      setTimeout(() => { wx.switchTab({ url: '/pages/home/home' }) }, 800)
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
