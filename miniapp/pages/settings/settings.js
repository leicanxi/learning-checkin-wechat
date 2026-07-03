const { get, put, post } = require('../../utils/api')
const auth = require('../../utils/auth')

Page({
  data: {
    isLogin: false,
    avatarText: '?',
    nickname: '用户',
    learningGoal: '尚未设置学习目标',
    dailyCheckin: false,
    taskDeadline: false,
    reminderTime: '21:10',
    groupName: '',
    groupInfo: ''
  },

  onShow() {
    this.checkLoginState()
    if (this.data.isLogin) {
      this.loadReminderSettings()
      this.loadGroupInfo()
    }
  },

  checkLoginState() {
    const token = wx.getStorageSync('token')
    const userInfo = wx.getStorageSync('userInfo')
    if (token && userInfo) {
      this.setData({
        isLogin: true,
        nickname: userInfo.nickname || '用户',
        avatarText: (userInfo.nickname || '?').charAt(0).toUpperCase(),
        learningGoal: userInfo.learning_goal || '尚未设置学习目标'
      })
    } else {
      this.setData({ isLogin: false })
    }
  },

  // 微信授权登录
  onLogin(e) {
    if (!e.detail.userInfo) return
    const { nickName, avatarUrl } = e.detail.userInfo

    wx.login({
      success: (loginRes) => {
        if (!loginRes.code) {
          wx.showToast({ title: '登录失败', icon: 'none' })
          return
        }

        wx.request({
          url: `${getApp().globalData.baseURL}/auth/wechat-login`,
          method: 'POST',
          data: {
            code: loginRes.code,
            nickname: nickName,
            avatar_url: avatarUrl
          },
          success: (response) => {
            if (response.statusCode === 200 && response.data) {
              const { access_token, user } = response.data
              getApp().globalData.token = access_token
              getApp().globalData.userInfo = user
              wx.setStorageSync('token', access_token)
              wx.setStorageSync('userInfo', user)

              this.setData({
                isLogin: true,
                nickname: user.nickname || nickName,
                avatarText: (user.nickname || nickName || '?').charAt(0).toUpperCase(),
                learningGoal: user.learning_goal || '尚未设置学习目标'
              })

              this.loadReminderSettings()
              this.loadGroupInfo()

              wx.showToast({ title: '登录成功', icon: 'success', duration: 1500 })
            } else {
              wx.showToast({ title: '登录失败，请重试', icon: 'none' })
            }
          },
          fail: (err) => {
            console.error('登录接口错误:', err)
            // 降级：后端不可用时用本地存储
            const localUser = { nickname: nickName, avatar_url: avatarUrl }
            wx.setStorageSync('token', 'local_token')
            wx.setStorageSync('userInfo', localUser)
            this.setData({
              isLogin: true,
              nickname: nickName,
              avatarText: nickName.charAt(0).toUpperCase(),
              learningGoal: '尚未设置学习目标'
            })
            wx.showToast({ title: '已登录（本地模式）', icon: 'success', duration: 1500 })
          }
        })
      }
    })
  },

  async loadReminderSettings() {
    try {
      const res = await get('/settings/reminder')
      const enabled = !!res.reminder_enabled
      const timeStr = enabled && res.reminder_time
        ? (typeof res.reminder_time === 'string' ? res.reminder_time.slice(0, 5) : '21:00')
        : '--'
      this.setData({
        dailyCheckin: enabled,
        taskDeadline: !!res.task_expire_notify,
        reminderTime: timeStr
      })
    } catch (e) {
      // 使用默认值
    }
  },

  async loadGroupInfo() {
    try {
      const res = await get('/groups/my')
      const group = res.group || res
      this.setData({
        groupName: group.name || '',
        groupInfo: `${group.member_count || 0} 名成员 · 本周完成率 ${group.completion_rate || 0}%`
      })
    } catch (e) {
      // 未加入小组
    }
  },

  editProfile() {
    wx.showModal({
      title: '修改学习目标',
      editable: true,
      placeholderText: this.data.learningGoal || '输入你的学习目标',
      success: async (res) => {
        if (res.confirm && res.content) {
          try {
            await put('/auth/me', { learning_goal: res.content })
            this.setData({ learningGoal: res.content })
            const userInfo = wx.getStorageSync('userInfo') || {}
            userInfo.learning_goal = res.content
            wx.setStorageSync('userInfo', userInfo)
            wx.showToast({ title: '更新成功', icon: 'success', duration: 1500 })
          } catch (e) {
            // 本地保存
            this.setData({ learningGoal: res.content })
            const userInfo = wx.getStorageSync('userInfo') || {}
            userInfo.learning_goal = res.content
            wx.setStorageSync('userInfo', userInfo)
            wx.showToast({ title: '更新成功', icon: 'success', duration: 1500 })
          }
        }
      }
    })
  },

  toggleDailyCheckin() {
    this.setData({ dailyCheckin: !this.data.dailyCheckin })
  },

  toggleTaskDeadline() {
    this.setData({ taskDeadline: !this.data.taskDeadline })
  },

  joinGroup() {
    wx.showToast({ title: '功能开发中', icon: 'none', duration: 1500 })
  },

  manageGroup() {
    wx.showToast({ title: '功能开发中', icon: 'none', duration: 1500 })
  },

  exportPDF() {
    wx.showToast({ title: 'PDF 导出功能开发中', icon: 'none', duration: 1500 })
  },

  showAbout() {
    wx.showModal({
      title: '学习打卡追踪器',
      content: '版本：v1.0.0\n\n帮助你养成每日学习的习惯，追踪学习进度，与朋友一起进步。',
      showCancel: false,
      confirmText: '知道了'
    })
  },

  handleLogout() {
    wx.showModal({
      title: '确认退出',
      content: '退出后需要重新登录，确定退出吗？',
      success: (res) => {
        if (res.confirm) {
          auth.logout()
          this.setData({ isLogin: false })
        }
      }
    })
  }
})
