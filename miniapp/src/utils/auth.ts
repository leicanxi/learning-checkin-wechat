import Taro from '@tarojs/taro'
import { post, get } from './request'

// 用户信息
export interface UserInfo {
  id: number
  openid: string
  nickname: string
  avatar_url: string
  learning_goal: string
  group_id: number | null
  group_name: string | null
  created_at: string
}

// 登录响应
export interface LoginResponse {
  token: string
  user: UserInfo
}

/**
 * 微信登录
 * 1. 调用 wx.login 获取 code
 * 2. 将 code 发送到后端换取 token
 */
export const login = async (): Promise<LoginResponse> => {
  try {
    // 1. 获取微信登录凭证
    const loginRes = await Taro.login()
    if (!loginRes.code) {
      throw new Error('获取登录凭证失败')
    }

    // 2. 发送到后端
    const data = await post<LoginResponse>('/auth/wechat-login', {
      code: loginRes.code
    })

    // 3. 存储 token 和用户信息
    Taro.setStorageSync('token', data.token)
    Taro.setStorageSync('user', JSON.stringify(data.user))

    return data
  } catch (error) {
    Taro.showToast({
      title: '登录失败，请重试',
      icon: 'none',
      duration: 2000
    })
    throw error
  }
}

/**
 * 退出登录
 */
export const logout = async (): Promise<void> => {
  try {
    // 调用后端登出接口（可选）
    await post('/auth/logout').catch(() => {
      // 忽略失败，本地清除即可
    })
  } finally {
    // 清除本地存储
    Taro.removeStorageSync('token')
    Taro.removeStorageSync('user')
  }
}

/**
 * 获取存储的 token
 */
export const getToken = (): string => {
  try {
    return Taro.getStorageSync('token') || ''
  } catch (e) {
    return ''
  }
}

/**
 * 获取存储的用户信息
 */
export const getStoredUser = (): UserInfo | null => {
  try {
    const userStr = Taro.getStorageSync('user')
    if (userStr) {
      return JSON.parse(userStr) as UserInfo
    }
    return null
  } catch (e) {
    return null
  }
}

/**
 * 检查是否已登录
 */
export const isLoggedIn = (): boolean => {
  return !!getToken()
}

/**
 * 获取当前用户信息
 */
export const fetchCurrentUser = async (): Promise<UserInfo> => {
  const data = await get<UserInfo>('/auth/me')
  Taro.setStorageSync('user', JSON.stringify(data))
  return data
}

export default {
  login,
  logout,
  getToken,
  getStoredUser,
  isLoggedIn,
  fetchCurrentUser
}
