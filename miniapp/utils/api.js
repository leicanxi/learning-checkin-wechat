const auth = require('./auth')
const { getBaseURL } = require('./config')

const BASE = () => {
  const app = getApp()
  return app ? app.globalData.baseURL : getBaseURL()
}

function request(method, path, data) {
  return new Promise((resolve, reject) => {
    const token = auth.getToken()
    const header = { 'Content-Type': 'application/json' }
    if (token) header['Authorization'] = `Bearer ${token}`

    wx.request({
      url: `${BASE()}${path}`,
      method,
      data,
      header,
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          const msg = (res.data && res.data.detail) || '请求失败'
          wx.showToast({ title: msg, icon: 'none', duration: 1500 })
          reject(new Error(msg))
        }
      },
      fail(err) {
        wx.showToast({ title: '网络错误', icon: 'none', duration: 1500 })
        reject(err)
      }
    })
  })
}

const get = (path, params = {}) => {
  const qs = Object.keys(params)
    .filter(k => params[k] !== undefined && params[k] !== null)
    .map(k => `${k}=${encodeURIComponent(params[k])}`)
    .join('&')
  return request('GET', qs ? `${path}?${qs}` : path)
}

const post = (path, data = {}) => request('POST', path, data)
const put = (path, data = {}) => request('PUT', path, data)
const del = (path, data = {}) => request('DELETE', path, data)

module.exports = { get, post, put, del }
