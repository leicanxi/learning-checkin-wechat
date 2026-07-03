const app = getApp()

/**
 * 微信登录 & JWT 鉴权
 */
function login() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(res) {
        if (res.code) {
          wx.request({
            url: `${app.globalData.baseURL}/auth/wechat-login`,
            method: 'POST',
            data: { code: res.code },
            success(response) {
              if (response.statusCode === 200 && response.data) {
                const { access_token, user } = response.data
                app.globalData.token = access_token
                app.globalData.userInfo = user
                wx.setStorageSync('token', access_token)
                wx.setStorageSync('userInfo', user)
                resolve(user)
              } else {
                reject(new Error('登录失败'))
              }
            },
            fail: reject
          })
        } else {
          reject(new Error('wx.login 失败'))
        }
      },
      fail: reject
    })
  })
}

function checkLogin() {
  const token = wx.getStorageSync('token')
  const userInfo = wx.getStorageSync('userInfo')
  if (token) {
    app.globalData.token = token
    app.globalData.userInfo = userInfo
  }
}

function getToken() {
  return app.globalData.token || wx.getStorageSync('token') || ''
}

function logout() {
  app.globalData.token = ''
  app.globalData.userInfo = null
  wx.removeStorageSync('token')
  wx.removeStorageSync('userInfo')
}

module.exports = { login, checkLogin, getToken, logout }
