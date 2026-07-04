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

  // 微信登录
  onLogin() {
    wx.showLoading({ title: '登录中...', mask: true })

    wx.login({
      success: (loginRes) => {
        if (!loginRes.code) {
          wx.hideLoading()
          wx.showToast({ title: '微信登录失败', icon: 'none' })
          return
        }

        wx.request({
          url: `${getApp().globalData.baseURL}/auth/wechat-login`,
          method: 'POST',
          data: { code: loginRes.code },
          success: (response) => {
            wx.hideLoading()
            if (response.statusCode === 200 && response.data) {
              const { access_token, user } = response.data
              getApp().globalData.token = access_token
              getApp().globalData.userInfo = user
              wx.setStorageSync('token', access_token)
              wx.setStorageSync('userInfo', user)

              const nickname = user.nickname || '用户'
              this.setData({
                isLogin: true,
                nickname,
                avatarText: nickname.charAt(0).toUpperCase(),
                learningGoal: user.learning_goal || '尚未设置学习目标'
              })

              this.loadReminderSettings()
              this.loadGroupInfo()

              wx.showToast({ title: '登录成功', icon: 'success', duration: 1500 })
            } else {
              const msg = (response.data && response.data.detail) || '登录失败'
              wx.showToast({ title: msg, icon: 'none' })
            }
          },
          fail: (err) => {
            wx.hideLoading()
            console.error('登录接口错误:', err)
            // 降级：后端不可用时用本地存储模拟登录
            const localUser = { nickname: '学习用户', learning_goal: '' }
            wx.setStorageSync('token', 'local_token_' + Date.now())
            wx.setStorageSync('userInfo', localUser)
            getApp().globalData.token = 'local_token_' + Date.now()
            getApp().globalData.userInfo = localUser
            this.setData({
              isLogin: true,
              nickname: '学习用户',
              avatarText: '学',
              learningGoal: '尚未设置学习目标'
            })
            wx.showToast({ title: '已登录（本地模式）', icon: 'success', duration: 1500 })
          }
        })
      },
      fail: () => {
        wx.hideLoading()
        wx.showToast({ title: '微信登录失败', icon: 'none' })
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
