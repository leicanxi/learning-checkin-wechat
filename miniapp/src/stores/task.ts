import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { get, post, del } from '@/utils/request'

// 任务类型
export interface Task {
  id: number
  name: string
  subject: string
  duration_minutes: number
  task_type: 'main' | 'light' | 'review'
  learning_mode: string
  material_text: string
  is_custom: boolean
  created_at: string
}

// 打卡记录
export interface CheckinRecord {
  id: number
  task_id: number
  task_name: string
  task_type: 'main' | 'light' | 'review'
  subject: string
  duration_minutes: number
  checked_in_at: string
  date: string
}

// 统计数据
export interface Stats {
  streak_days: number
  current_week_rate: number
  current_month_rate: number
  total_checkins: number
  subjective_rank: number
  subject_distribution: Array<{
    subject: string
    count: number
    percentage: number
  }>
  weekly_trend: Array<{
    date: string
    count: number
  }>
  monthly_trend: Array<{
    date: string
    count: number
  }>
  mastery_progress: Array<{
    subject: string
    progress: number
  }>
}

export const useTaskStore = defineStore('task', () => {
  // State
  const tasks = ref<Task[]>([])
  const todayCheckins = ref<CheckinRecord[]>([])
  const stats = ref<Stats | null>(null)
  const loading = ref(false)
  const checkinLoading = ref(false)

  // Getters
  const activeTasks = computed(() =>
    tasks.value.filter(t => {
      // 今天的打卡记录中不包含此任务
      return !todayCheckins.value.some(c => c.task_id === t.id)
    })
  )

  const completedTasks = computed(() =>
    todayCheckins.value
  )

  const todayProgress = computed(() => {
    const total = tasks.value.length
    const done = todayCheckins.value.length
    return total > 0 ? Math.round((done / total) * 100) : 0
  })

  const streakDays = computed(() => stats.value?.streak_days || 0)
  const weekRate = computed(() => stats.value?.current_week_rate || 0)
  const monthRate = computed(() => stats.value?.current_month_rate || 0)

  // Actions

  /**
   * 获取任务列表
   */
  const fetchTasks = async (): Promise<void> => {
    loading.value = true
    try {
      const data = await get<Task[]>('/tasks')
      tasks.value = data
    } catch (error) {
      console.error('Fetch tasks failed:', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建任务
   */
  const createTask = async (taskData: Omit<Task, 'id' | 'created_at'>): Promise<Task> => {
    const data = await post<Task>('/tasks', taskData)
    tasks.value.push(data)
    return data
  }

  /**
   * 批量创建任务
   */
  const batchCreateTasks = async (taskDataList: Omit<Task, 'id' | 'created_at'>[]): Promise<Task[]> => {
    const data = await post<Task[]>('/tasks/batch', { tasks: taskDataList })
    tasks.value.push(...data)
    return data
  }

  /**
   * 更新任务
   */
  const updateTask = async (id: number, updates: Partial<Task>): Promise<void> => {
    const { put } = await import('@/utils/request')
    await put<Task>(`/tasks/${id}`, updates)
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx >= 0) {
      tasks.value[idx] = { ...tasks.value[idx], ...updates }
    }
  }

  /**
   * 删除任务
   */
  const deleteTask = async (id: number): Promise<void> => {
    await del(`/tasks/${id}`)
    tasks.value = tasks.value.filter(t => t.id !== id)
  }

  /**
   * 打卡
   */
  const checkin = async (taskId: number): Promise<CheckinRecord> => {
    checkinLoading.value = true
    try {
      const data = await post<CheckinRecord>('/checkins', { task_id: taskId })
      todayCheckins.value.push(data)
      return data
    } finally {
      checkinLoading.value = false
    }
  }

  /**
   * 取消打卡
   */
  const uncheckin = async (checkinId: number): Promise<void> => {
    await del(`/checkins/${checkinId}`)
    todayCheckins.value = todayCheckins.value.filter(c => c.id !== checkinId)
  }

  /**
   * 获取今日打卡记录
   */
  const fetchCheckins = async (date?: string): Promise<void> => {
    try {
      const params = date ? { date } : {}
      const data = await get<CheckinRecord[]>('/checkins', params)
      if (!date || date === getTodayStr()) {
        todayCheckins.value = data
      }
    } catch (error) {
      console.error('Fetch checkins failed:', error)
    }
  }

  /**
   * 获取统计数据
   */
  const fetchStats = async (period: 'week' | 'month' | 'year' = 'week'): Promise<void> => {
    try {
      const data = await get<Stats>('/stats', { period })
      stats.value = data
    } catch (error) {
      console.error('Fetch stats failed:', error)
    }
  }

  /**
   * 判断某任务今日是否已打卡
   */
  const isCheckedIn = (taskId: number): boolean => {
    return todayCheckins.value.some(c => c.task_id === taskId)
  }

  // 辅助函数
  const getTodayStr = (): string => {
    const d = new Date()
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }

  return {
    // state
    tasks,
    todayCheckins,
    stats,
    loading,
    checkinLoading,
    // getters
    activeTasks,
    completedTasks,
    todayProgress,
    streakDays,
    weekRate,
    monthRate,
    // actions
    fetchTasks,
    createTask,
    batchCreateTasks,
    updateTask,
    deleteTask,
    checkin,
    uncheckin,
    fetchCheckins,
    fetchStats,
    isCheckedIn
  }
})
