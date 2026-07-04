const auth = require('./utils/auth')
const { CURRENT_ENV, getBaseURL } = require('./utils/config')

App({
  onLaunch() {
    // 检查登录态
    auth.checkLogin()
  },

  globalData: {
    userInfo: null,
    token: '',
    env: CURRENT_ENV,
    baseURL: getBaseURL()
  }
})
