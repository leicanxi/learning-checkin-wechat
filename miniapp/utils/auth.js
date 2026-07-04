const { getBaseURL } = require('./config')

function getAppGlobal() {
  const app = getApp()
  return app ? app.globalData : null
}

/**
 * 微信登录 & JWT 鉴权
 */
function login() {
  return new Promise((resolve, reject) => {
    wx.login({
      success(res) {
        if (res.code) {
          const ga = getAppGlobal()
          wx.request({
            url: `${ga ? ga.baseURL : getBaseURL()}/auth/wechat-login`,
            method: 'POST',
            data: { code: res.code },
            success(response) {
              if (response.statusCode === 200 && response.data) {
                const { access_token, user } = response.data
                const gl = getAppGlobal()
                if (gl) {
                  gl.token = access_token
                  gl.userInfo = user
                }
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
    const gl = getAppGlobal()
    if (gl) {
      gl.token = token
      gl.userInfo = userInfo
    }
  }
}

function getToken() {
  const gl = getAppGlobal()
  return (gl && gl.token) || wx.getStorageSync('token') || ''
}

function logout() {
  const gl = getAppGlobal()
  if (gl) {
    gl.token = ''
    gl.userInfo = null
  }
  wx.removeStorageSync('token')
  wx.removeStorageSync('userInfo')
}

module.exports = { login, checkLogin, getToken, logout }
