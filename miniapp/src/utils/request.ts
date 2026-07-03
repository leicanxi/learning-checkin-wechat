import Taro from '@tarojs/taro'
import config from '@/config'

// 请求配置
const BASE_URL = config.apiBaseUrl
const TIMEOUT = 15000

// 响应数据类型
export interface ApiResponse<T = any> {
  code: number
  data: T
  message: string
}

// 请求选项
export interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  data?: any
  header?: Record<string, string>
  showLoading?: boolean
  loadingText?: string
}

/**
 * 统一请求封装
 */
export const request = async <T = any>(options: RequestOptions): Promise<T> => {
  const {
    url,
    method = 'GET',
    data = {},
    header = {},
    showLoading = false,
    loadingText = '加载中...'
  } = options

  if (showLoading) {
    Taro.showLoading({ title: loadingText, mask: true })
  }

  // 读取 token
  let token = ''
  try {
    token = Taro.getStorageSync('token') || ''
  } catch (e) {
    // ignore
  }

  // 构建完整的请求头
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...header
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  try {
    const res = await Taro.request({
      url: `${BASE_URL}${url}`,
      method,
      data,
      header: headers,
      timeout: TIMEOUT
    })

    if (showLoading) {
      Taro.hideLoading()
    }

    // HTTP 状态码检查
    const statusCode = res.statusCode
    const responseData = res.data as ApiResponse<T>

    if (statusCode === 401) {
      // Token 过期或无效，清除登录状态
      try {
        Taro.removeStorageSync('token')
        Taro.removeStorageSync('user')
      } catch (e) {
        // ignore
      }
      Taro.showToast({
        title: '登录已过期，请重新登录',
        icon: 'none',
        duration: 2000
      })
      // 跳转到登录页
      setTimeout(() => {
        Taro.reLaunch({ url: '/pages/login/index' })
      }, 500)
      throw new Error('Unauthorized')
    }

    if (statusCode >= 500) {
      Taro.showToast({
        title: '服务器繁忙，请稍后重试',
        icon: 'none',
        duration: 2000
      })
      throw new Error(`Server Error: ${statusCode}`)
    }

    if (statusCode !== 200) {
      Taro.showToast({
        title: responseData?.message || '请求失败',
        icon: 'none',
        duration: 2000
      })
      throw new Error(responseData?.message || `HTTP ${statusCode}`)
    }

    // 业务逻辑错误码
    if (responseData.code && responseData.code !== 0 && responseData.code !== 200) {
      Taro.showToast({
        title: responseData.message || '操作失败',
        icon: 'none',
        duration: 2000
      })
      throw new Error(responseData.message || `Business Error: ${responseData.code}`)
    }

    // 返回 data 字段，如果没有则返回整个响应
    return (responseData.data !== undefined ? responseData.data : responseData) as T
  } catch (error: any) {
    if (showLoading) {
      Taro.hideLoading()
    }

    // 网络错误
    if (error?.errMsg?.includes('timeout')) {
      Taro.showToast({
        title: '请求超时，请检查网络',
        icon: 'none',
        duration: 2000
      })
    } else if (error?.errMsg?.includes('fail')) {
      Taro.showToast({
        title: '网络异常，请检查连接',
        icon: 'none',
        duration: 2000
      })
    }

    // 如果上面的处理中没有抛出，这里统一抛出
    if (error.message && !error.message.startsWith('HTTP') && !error.message.startsWith('Business') && error.message !== 'Unauthorized') {
      // 是网络层面的错误，已经显示了 toast
    }

    throw error
  }
}

// 便捷方法
export const get = <T = any>(url: string, data?: any, options?: Partial<RequestOptions>) =>
  request<T>({ url, method: 'GET', data, ...options })

export const post = <T = any>(url: string, data?: any, options?: Partial<RequestOptions>) =>
  request<T>({ url, method: 'POST', data, ...options })

export const put = <T = any>(url: string, data?: any, options?: Partial<RequestOptions>) =>
  request<T>({ url, method: 'PUT', data, ...options })

export const del = <T = any>(url: string, data?: any, options?: Partial<RequestOptions>) =>
  request<T>({ url, method: 'DELETE', data, ...options })

export const patch = <T = any>(url: string, data?: any, options?: Partial<RequestOptions>) =>
  request<T>({ url, method: 'PATCH', data, ...options })

export default request
