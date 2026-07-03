<template>
  <view class="page-container">
    <!-- 时间维度切换 -->
    <view class="period-tabs flex-row">
      <view
        v-for="p in periods"
        :key="p.value"
        class="period-tab"
        :class="{ 'period-tab-active': activePeriod === p.value }"
        @tap="switchPeriod(p.value)"
      >
        <text>{{ p.label }}</text>
      </view>
    </view>

    <!-- 累计打卡次数卡片 -->
    <view class="total-card card">
      <text class="total-number">{{ statsData?.total_checkins || 0 }}</text>
      <text class="total-label">累计打卡次数</text>
    </view>

    <!-- 打卡趋势柱状图（简易） -->
    <view class="card">
      <text class="h4" style="margin-bottom:14px;display:block">打卡趋势</text>
      <view class="chart-bars">
        <view
          v-for="(item, idx) in trendData"
          :key="idx"
          class="chart-bar-col"
        >
          <view class="bar-value-text">{{ item.count }}</view>
          <view
            class="chart-bar"
            :style="{ height: getBarHeight(item.count) + 'px' }"
          />
          <text class="bar-label">{{ item.label }}</text>
        </view>
        <!-- 空状态 -->
        <view v-if="trendData.length === 0" class="empty-state" style="padding:24px 0">
          <text class="desc">暂无打卡数据</text>
        </view>
      </view>
    </view>

    <!-- 知识掌握进度环形图 -->
    <view class="card">
      <text class="h4" style="margin-bottom:14px;display:block">知识掌握进度</text>
      <view class="mastery-grid">
        <view
          v-for="item in masteryData"
          :key="item.subject"
          class="mastery-item"
        >
          <view
            class="mastery-ring"
            :style="{
              background: `conic-gradient(#c96442 ${item.progress}%, #e8e6dc ${item.progress}%)`
            }"
          >
            <view class="mastery-ring-inner">
              <text class="mastery-percent">{{ item.progress }}%</text>
            </view>
          </view>
          <text class="mastery-label">{{ item.subject }}</text>
        </view>
        <!-- 空状态 -->
        <view v-if="masteryData.length === 0" class="empty-state" style="padding:24px 0;width:100%">
          <text class="desc">暂无掌握数据</text>
        </view>
      </view>
    </view>

    <!-- 科目打卡分布 -->
    <view class="card">
      <text class="h4" style="margin-bottom:14px;display:block">科目打卡分布</text>
      <view v-if="subjectData.length > 0" class="subject-list">
        <view
          v-for="item in subjectData"
          :key="item.subject"
          class="subject-item"
        >
          <view class="flex-between" style="margin-bottom:6px">
            <text class="subject-name">{{ item.subject }}</text>
            <text class="subject-count">{{ item.count }}次（{{ item.percentage }}%）</text>
          </view>
          <view class="subject-bar-bg">
            <view
              class="subject-bar-fill"
              :style="{ width: item.percentage + '%' }"
            />
          </view>
        </view>
      </view>
      <view v-else class="empty-state" style="padding:24px 0">
        <text class="desc">暂无科目数据</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useTaskStore } from '@/stores/task'

const taskStore = useTaskStore()

const periods = [
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '年', value: 'year' }
]

const activePeriod = ref<'week' | 'month' | 'year'>('week')

// 统计数据
const statsData = computed(() => taskStore.stats)

// 趋势数据（柱状图）
const trendData = computed(() => {
  const data = statsData.value
  if (!data) return []

  const source = activePeriod.value === 'week'
    ? data.weekly_trend
    : data.monthly_trend || data.weekly_trend

  if (!source || source.length === 0) return []

  return source.slice(-7).map(item => {
    const parts = item.date.split('-')
    const label = parts.length >= 3
      ? `${parts[1]}/${parts[2]}`
      : item.date
    return {
      label,
      count: item.count
    }
  })
})

// 掌握数据
const masteryData = computed(() => {
  return statsData.value?.mastery_progress || []
})

// 科目分布
const subjectData = computed(() => {
  const data = statsData.value?.subject_distribution
  if (!data || data.length === 0) return []
  return data.slice(0, 6).map(item => ({
    ...item,
    percentage: Math.round(item.percentage)
  }))
})

// 柱状图高度计算
const getBarHeight = (count: number): number => {
  const max = Math.max(...trendData.value.map(d => d.count), 1)
  return Math.max(8, (count / max) * 80)
}

// 切换时间维度
const switchPeriod = (period: 'week' | 'month' | 'year') => {
  activePeriod.value = period
  taskStore.fetchStats(period)
}

onMounted(() => {
  taskStore.fetchStats('week')
})
</script>

<style lang="scss">
// 时间维度切换
.period-tabs {
  background: #ffffff;
  border-radius: var(--radius-card);
  padding: 4px;
  margin-bottom: 14px;
  box-shadow: var(--shadow-card);
}

.period-tab {
  flex: 1;
  padding: 8px;
  border-radius: var(--radius-btn);
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #6f735f;
  transition: all 0.25s ease;
}

.period-tab-active {
  background: #c96442;
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(201, 100, 66, 0.3);
}

// 累计打卡卡片
.total-card {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #fefaf6, #ffffff);
  border: 1px solid #f0ece0;
}

.total-number {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 40px;
  font-weight: 700;
  color: #c96442;
  display: block;
  margin-bottom: 4px;
}

.total-label {
  font-size: 13px;
  color: #6f735f;
}

// 柱状图
.chart-bars {
  display: flex;
  flex-direction: row;
  align-items: flex-end;
  justify-content: space-around;
  height: 130px;
  padding-top: 18px;
}

.chart-bar-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.bar-value-text {
  font-size: 10px;
  font-weight: 600;
  color: #c96442;
  margin-bottom: 4px;
}

.chart-bar {
  width: 24px;
  border-radius: 6px 6px 0 0;
  background: linear-gradient(180deg, #c96442, #d48364);
  min-height: 4px;
  transition: height 0.3s ease;
}

.bar-label {
  font-size: 10px;
  color: #9a9a8a;
  margin-top: 6px;
}

// 掌握进度环
.mastery-grid {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
}

.mastery-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.mastery-ring {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mastery-ring-inner {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mastery-percent {
  font-size: 12px;
  font-weight: 700;
  color: #c96442;
}

.mastery-label {
  font-size: 11px;
  color: #6f735f;
  font-weight: 500;
  max-width: 64px;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

// 科目分布
.subject-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.subject-item {
  display: flex;
  flex-direction: column;
}

.subject-name {
  font-size: 14px;
  font-weight: 600;
  color: #141413;
}

.subject-count {
  font-size: 12px;
  color: #6f735f;
}

.subject-bar-bg {
  height: 6px;
  border-radius: 3px;
  background: #f0ece0;
  overflow: hidden;
}

.subject-bar-fill {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #c96442, #d48364);
  transition: width 0.5s ease;
}
</style>
