const auth = require('./utils/auth')

App({
  onLaunch() {
    // 检查登录态
    auth.checkLogin()
  },

  globalData: {
    userInfo: null,
    token: '',
    baseURL: 'http://localhost:8000'
  }
})
