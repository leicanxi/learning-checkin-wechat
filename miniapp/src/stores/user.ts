import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import Taro from '@tarojs/taro'
import { login as doLogin, logout as doLogout, getStoredUser, fetchCurrentUser, type UserInfo } from '@/utils/auth'
import { getToken } from '@/utils/auth'

export const useUserStore = defineStore('user', () => {
  // State
  const user = ref<UserInfo | null>(getStoredUser())
  const token = ref<string>(getToken())
  const loading = ref(false)

  // Getters
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const nickname = computed(() => user.value?.nickname || '未设置昵称')
  const avatarUrl = computed(() => user.value?.avatar_url || '')
  const learningGoal = computed(() => user.value?.learning_goal || '')
  const groupName = computed(() => user.value?.group_name || '未加入小组')

  // Actions
  /**
   * 微信一键登录
   */
  const login = async (): Promise<void> => {
    if (loading.value) return

    loading.value = true
    try {
      const result = await doLogin()
      token.value = result.token
      user.value = result.user
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 退出登录
   */
  const logout = async (): Promise<void> => {
    loading.value = true
    try {
      await doLogout()
    } finally {
      token.value = ''
      user.value = null
      loading.value = false
    }
  }

  /**
   * 获取当前用户信息
   */
  const fetchUser = async (): Promise<void> => {
    try {
      const userData = await fetchCurrentUser()
      user.value = userData
    } catch (error) {
      console.error('Fetch user failed:', error)
    }
  }

  /**
   * 更新用户信息
   */
  const updateUser = async (updates: Partial<UserInfo>): Promise<void> => {
    const { put } = await import('@/utils/request')
    const data = await put<UserInfo>('/auth/me', updates)
    user.value = { ...user.value!, ...data }
    Taro.setStorageSync('user', JSON.stringify(user.value))
  }

  /**
   * 初始化：从存储恢复登录态
   */
  const init = async (): Promise<void> => {
    if (token.value && !user.value) {
      try {
        await fetchUser()
      } catch {
        // token 可能已过期，清除
        token.value = ''
      }
    }
  }

  return {
    // state
    user,
    token,
    loading,
    // getters
    isLoggedIn,
    nickname,
    avatarUrl,
    learningGoal,
    groupName,
    // actions
    login,
    logout,
    fetchUser,
    updateUser,
    init
  }
})
