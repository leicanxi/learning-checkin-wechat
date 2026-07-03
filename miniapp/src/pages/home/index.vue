<template>
  <view class="page-container">
    <!-- Hero 区域：连续打卡天数 -->
    <view class="hero-card card">
      <view class="hero-content">
        <view class="streak-section">
          <text class="streak-number">{{ taskStore.streakDays }}</text>
          <text class="streak-label">连续打卡天数</text>
        </view>
        <view class="motivation-section">
          <text class="motivation-text">{{ motivation }}</text>
        </view>
      </view>
      <!-- 进度环 -->
      <view class="progress-ring">
        <view
          class="ring-bg"
          :style="{
            background: `conic-gradient(#c96442 ${taskStore.todayProgress}%, #e8e6dc ${taskStore.todayProgress}%)`
          }"
        >
          <view class="ring-inner">
            <text class="ring-percent">{{ taskStore.todayProgress }}%</text>
            <text class="ring-label">今日进度</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 三个指标卡片 -->
    <view class="stats-row">
      <view class="stat-card card flex-1" @tap="navigateToStats">
        <text class="stat-value">{{ taskStore.weekRate }}%</text>
        <text class="stat-label">本周打卡率</text>
      </view>
      <view class="stat-card card flex-1" @tap="navigateToStats">
        <text class="stat-value">{{ taskStore.monthRate }}%</text>
        <text class="stat-label">本月打卡率</text>
      </view>
      <view class="stat-card card flex-1" @tap="navigateToRanking">
        <text class="stat-value">#{{ taskStore.stats?.subjective_rank || '-' }}</text>
        <text class="stat-label">排名</text>
      </view>
    </view>

    <!-- 今日任务列表 -->
    <view class="section-header flex-between">
      <text class="h3">今日任务</text>
      <text class="text-secondary" style="font-size:14px">
        {{ taskStore.completedTasks.length }}/{{ taskStore.tasks.length }} 已完成
      </text>
    </view>

    <!-- 加载状态 -->
    <view v-if="taskStore.loading" class="empty-state">
      <text class="desc">加载中...</text>
    </view>

    <!-- 任务列表 -->
    <view v-else-if="taskStore.tasks.length > 0" class="task-list">
      <view
        v-for="task in taskStore.tasks"
        :key="task.id"
        class="task-item card flex-row gap-14"
        :class="{ 'task-checked': taskStore.isCheckedIn(task.id) }"
      >
        <!-- 复选框 -->
        <view
          class="checkbox"
          :class="{ 'checkbox-checked': taskStore.isCheckedIn(task.id) }"
          @tap="handleCheckin(task)"
        >
          <text v-if="taskStore.isCheckedIn(task.id)" class="check-icon">&#x2713;</text>
        </view>

        <!-- 任务信息 -->
        <view class="task-info flex-1">
          <view class="flex-row gap-10">
            <text class="task-name">{{ task.name }}</text>
            <text
              class="tag"
              :class="{
                'tag-main': task.task_type === 'main',
                'tag-light': task.task_type === 'light',
                'tag-review': task.task_type === 'review'
              }"
            >
              {{ typeLabels[task.task_type] || task.task_type }}
            </text>
          </view>
          <view class="task-meta flex-row gap-14">
            <text class="text-muted" style="font-size:13px">{{ task.duration_minutes }}分钟</text>
            <text class="text-muted" style="font-size:13px">{{ task.subject }}</text>
          </view>
        </view>
      </view>
    </view>

    <!-- 空状态 -->
    <view v-else class="empty-state">
      <text class="icon">&#x1F4DD;</text>
      <text class="title">还没有任务</text>
      <text class="desc">前往规划页创建你的第一个学习任务</text>
      <button class="btn btn-primary mt-18" @tap="goToPlanner" style="width:200px">去创建任务</button>
    </view>

    <!-- 已完成列表 -->
    <view v-if="taskStore.completedTasks.length > 0" class="completed-section">
      <text class="h4 mb-10">已完成</text>
      <view
        v-for="record in taskStore.completedTasks"
        :key="record.id"
        class="completed-item flex-between"
      >
        <view class="flex-row gap-10">
          <text class="completed-dot">&#x2713;</text>
          <text class="completed-name">{{ record.task_name }}</text>
        </view>
        <text class="text-muted" style="font-size:12px">{{ formatTime(record.checked_in_at) }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Taro from '@tarojs/taro'
import { useTaskStore, type Task } from '@/stores/task'

const taskStore = useTaskStore()

// 类型标签映射
const typeLabels: Record<string, string> = {
  main: '主线',
  light: '轻量',
  review: '复习'
}

// 激励文案
const motivations = [
  '千里之行，始于足下',
  '坚持是一种力量',
  '今天的努力，明天的底气',
  '积跬步以至千里',
  '自律给我自由',
  '每一次打卡都在超越昨天的自己'
]

const motivation = computed(() => {
  const idx = taskStore.streakDays % motivations.length
  return motivations[idx]
})

onMounted(async () => {
  try {
    await Promise.all([
      taskStore.fetchTasks(),
      taskStore.fetchCheckins(),
      taskStore.fetchStats('week')
    ])
  } catch (error) {
    console.error('Failed to load home data:', error)
  }
})

// 打卡/取消打卡
const handleCheckin = async (task: Task) => {
  const isDone = taskStore.isCheckedIn(task.id)
  if (isDone) {
    // 找到对应的打卡记录并取消
    const record = taskStore.todayCheckins.find(c => c.task_id === task.id)
    if (record) {
      try {
        await taskStore.uncheckin(record.id)
        Taro.showToast({ title: '已取消打卡', icon: 'none', duration: 1000 })
      } catch (error) {
        Taro.showToast({ title: '操作失败', icon: 'none', duration: 1500 })
      }
    }
  } else {
    try {
      await taskStore.checkin(task.id)
      Taro.showToast({ title: '打卡成功！', icon: 'success', duration: 1000 })
      // 刷新统计数据
      taskStore.fetchStats('week')
    } catch (error) {
      Taro.showToast({ title: '打卡失败', icon: 'none', duration: 1500 })
    }
  }
}

// 格式化时间
const formatTime = (dateStr: string): string => {
  try {
    const d = new Date(dateStr)
    const h = String(d.getHours()).padStart(2, '0')
    const m = String(d.getMinutes()).padStart(2, '0')
    return `${h}:${m}`
  } catch {
    return ''
  }
}

// 导航
const goToPlanner = () => {
  Taro.switchTab({ url: '/pages/planner/index' })
}

const navigateToStats = () => {
  Taro.switchTab({ url: '/pages/stats/index' })
}

const navigateToRanking = () => {
  Taro.switchTab({ url: '/pages/ranking/index' })
}
</script>

<style lang="scss">
.hero-card {
  background: linear-gradient(135deg, #fefaf6 0%, #ffffff 100%);
  border: 1px solid #f0ece0;
  padding: var(--spacing-card-lg);
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.hero-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.streak-section {
  display: flex;
  flex-direction: column;
}

.streak-number {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 48px;
  font-weight: 700;
  color: #c96442;
  line-height: 1.1;
}

.streak-label {
  font-size: 14px;
  color: #6f735f;
  font-weight: 500;
  margin-top: 2px;
}

.motivation-section {
  margin-top: 6px;
}

.motivation-text {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 15px;
  color: #141413;
  font-style: italic;
  opacity: 0.7;
}

.progress-ring {
  flex-shrink: 0;
}

.ring-bg {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ring-inner {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.ring-percent {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 16px;
  font-weight: 700;
  color: #c96442;
  line-height: 1;
}

.ring-label {
  font-size: 10px;
  color: #9a9a8a;
  margin-top: 2px;
}

// 三指标卡片
.stats-row {
  display: flex;
  flex-direction: row;
  gap: 10px;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 14px 8px;
  border: 1px solid #f0ece0;
  min-height: 72px;
}

.stat-value {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 22px;
  font-weight: 700;
  color: #141413;
}

.stat-label {
  font-size: 12px;
  color: #6f735f;
  margin-top: 4px;
}

// 分割标题
.section-header {
  margin-top: 6px;
  margin-bottom: 12px;
  padding: 0 2px;
}

// 任务列表
.task-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.task-item {
  background: #ffffff;
  border: 1px solid #f0ece0;
  padding: 14px 16px;
  transition: all 0.2s ease;
}

.task-checked {
  opacity: 0.6;
}

.checkbox {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 2px solid #d4d0c0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.checkbox-checked {
  background: #c96442;
  border-color: #c96442;
}

.check-icon {
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-name {
  font-size: 15px;
  font-weight: 600;
  color: #141413;
}

.task-meta {
  font-size: 13px;
}

// 已完成区域
.completed-section {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid #e8e6dc;
}

.completed-item {
  padding: 10px 4px;
  border-bottom: 1px solid #f5f4ed;
}

.completed-dot {
  color: #6f735f;
  font-size: 14px;
  font-weight: 700;
}

.completed-name {
  font-size: 14px;
  color: #9a9a8a;
  text-decoration: line-through;
}
</style>
