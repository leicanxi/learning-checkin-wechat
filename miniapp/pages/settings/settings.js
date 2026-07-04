const { get, put, post, del } = require('../../utils/api')
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
    groupInfo: '',
    groupId: null,
    groupRole: 'none',
    groupInviteCode: '',
    groupMembers: [],
    groupSheetShow: false,
    groupSheetTitle: '',
    groupSheetMode: 'detail'
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
      const group = res.group
      if (!group) {
        this.setData({
          groupName: '',
          groupInfo: '',
          groupId: null,
          groupRole: 'none',
          groupInviteCode: '',
          groupMembers: []
        })
        return
      }
      const rankLabel = res.my_rank_range_label || '数据不足'
      this.setData({
        groupId: group.id,
        groupName: group.name || '',
        groupRole: res.my_group_role || 'member',
        groupInviteCode: group.invite_code || '',
        groupInfo: `${group.member_count || 0} 名成员 · 本周小组完成率 ${group.completion_rate || 0}% · 我的区间${rankLabel}`
      })
    } catch (e) {
      this.setData({ groupName: '', groupInfo: '', groupId: null, groupRole: 'none', groupMembers: [] })
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
    wx.showModal({
      title: '加入小组',
      editable: true,
      placeholderText: '输入邀请码',
      success: async (res) => {
        if (!res.confirm || !res.content) return
        try {
          await post('/groups/join', { invite_code: res.content.trim().toUpperCase() })
          await this.loadGroupInfo()
          wx.showToast({ title: '加入成功', icon: 'success' })
        } catch (e) {
          wx.showToast({ title: e.message || '加入失败', icon: 'none' })
        }
      }
    })
  },

  createGroup() {
    wx.showModal({
      title: '创建小组',
      editable: true,
      placeholderText: '输入小组名称',
      success: async (res) => {
        if (!res.confirm || !res.content) return
        try {
          await post('/groups/', { name: res.content.trim(), description: '' })
          await this.loadGroupInfo()
          wx.showToast({ title: '创建成功', icon: 'success' })
        } catch (e) {
          wx.showToast({ title: e.message || '创建失败', icon: 'none' })
        }
      }
    })
  },

  async loadGroupMembers() {
    if (!this.data.groupId) return
    try {
      const members = await get(`/groups/${this.data.groupId}/members`)
      this.setData({ groupMembers: members || [] })
    } catch (e) {
      wx.showToast({ title: e.message || '成员加载失败', icon: 'none' })
    }
  },

  async openMyGroup() {
    await this.loadGroupMembers()
    this.setData({
      groupSheetShow: true,
      groupSheetMode: 'detail',
      groupSheetTitle: '我的小组'
    })
  },

  async manageGroup() {
    await this.loadGroupMembers()
    this.setData({
      groupSheetShow: true,
      groupSheetMode: 'manage',
      groupSheetTitle: '管理小组'
    })
  },

  closeGroupSheet() {
    this.setData({ groupSheetShow: false })
  },

  leaveGroup() {
    wx.showModal({
      title: '退出小组',
      content: '退出后将不再参与该小组排名，确定退出吗？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await del('/groups/leave')
          await this.loadGroupInfo()
          wx.showToast({ title: '已退出', icon: 'success' })
        } catch (e) {
          wx.showToast({ title: e.message || '退出失败', icon: 'none' })
        }
      }
    })
  },

  removeMember(e) {
    const memberId = e.currentTarget.dataset.id
    wx.showModal({
      title: '移除成员',
      content: '确定将该成员移出小组吗？',
      success: async (res) => {
        if (!res.confirm) return
        try {
          await del(`/groups/${this.data.groupId}/members/${memberId}`)
          await this.loadGroupMembers()
          await this.loadGroupInfo()
          wx.showToast({ title: '已移除', icon: 'success' })
        } catch (e) {
          wx.showToast({ title: e.message || '移除失败', icon: 'none' })
        }
      }
    })
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
