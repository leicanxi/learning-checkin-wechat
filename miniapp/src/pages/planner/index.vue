<template>
  <view class="page-container">
    <!-- 模式选择器 -->
    <view class="card" style="margin-bottom:14px">
      <text class="h4" style="margin-bottom:12px;display:block">选择学习模式</text>
      <view class="mode-selector" @tap="showModePicker = true">
        <text class="mode-value">{{ selectedMode || '请选择学习模式' }}</text>
        <text class="mode-arrow">&#x25BC;</text>
      </view>
    </view>

    <!-- 模式选择弹窗 -->
    <view v-if="showModePicker" class="picker-overlay" @tap="showModePicker = false">
      <view class="picker-panel" @tap.stop>
        <text class="h4" style="margin-bottom:14px;display:block">选择学习模式</text>
        <view
          v-for="mode in learningModes"
          :key="mode"
          class="picker-item"
          :class="{ 'picker-item-active': selectedMode === mode }"
          @tap="selectMode(mode)"
        >
          <text>{{ mode }}</text>
          <text v-if="selectedMode === mode" style="color:#c96442">&#x2713;</text>
        </view>
        <button class="btn btn-primary mt-14" style="width:100%" @tap="showModePicker = false">确定</button>
      </view>
    </view>

    <!-- 材料输入区 -->
    <view class="card" style="margin-bottom:14px">
      <text class="h4" style="margin-bottom:10px;display:block">学习材料描述</text>
      <textarea
        class="material-input"
        v-model="materialText"
        placeholder="描述你要学习的内容（例如：复习高等数学第三章、背诵英语单词Unit5...）"
        maxlength="500"
        auto-height
      />
      <text class="text-muted" style="font-size:12px;margin-top:6px">{{ materialText.length }}/500</text>
    </view>

    <!-- AI 规划按钮 -->
    <button class="btn btn-primary" style="width:100%;margin-bottom:14px" @tap="generatePlan" :disabled="aiLoading">
      <text>{{ aiLoading ? 'AI 规划中...' : 'AI 智能规划' }}</text>
    </button>

    <!-- 自定义计划区 -->
    <view class="card" style="margin-bottom:14px">
      <text class="h4" style="margin-bottom:14px;display:block">自定义计划</text>

      <!-- 任务名称 -->
      <view class="form-group">
        <text class="form-label">任务名称</text>
        <input
          class="form-input"
          v-model="customTask.name"
          placeholder="输入任务名称"
        />
      </view>

      <!-- 时长 -->
      <view class="form-group">
        <text class="form-label">建议时长（分钟）</text>
        <input
          class="form-input"
          v-model="customTask.duration"
          type="number"
          placeholder="例如：30"
        />
      </view>

      <!-- 科目标签 -->
      <view class="form-group">
        <text class="form-label">科目标签</text>
        <input
          class="form-input"
          v-model="customTask.subject"
          placeholder="例如：数学"
        />
      </view>

      <!-- 任务类型 -->
      <view class="form-group">
        <text class="form-label">任务类型</text>
        <view class="type-row">
          <view
            class="type-chip"
            :class="{ 'type-chip-active': customTask.task_type === 'main' }"
            @tap="customTask.task_type = 'main'"
          >
            <text>主线</text>
          </view>
          <view
            class="type-chip"
            :class="{ 'type-chip-active': customTask.task_type === 'light' }"
            @tap="customTask.task_type = 'light'"
          >
            <text>轻量</text>
          </view>
          <view
            class="type-chip"
            :class="{ 'type-chip-active': customTask.task_type === 'review' }"
            @tap="customTask.task_type = 'review'"
          >
            <text>复习</text>
          </view>
        </view>
      </view>

      <!-- 周期选择 -->
      <view class="form-group">
        <text class="form-label">重复周期</text>
        <view class="weekday-row">
          <view
            class="everyday-chip"
            :class="{ 'everyday-active': isEveryDay }"
            @tap="toggleEveryDay"
          >
            <text>每天</text>
          </view>
        </view>
        <view class="weekday-row" style="margin-top:8px">
          <view
            v-for="(day, idx) in weekDayLabels"
            :key="idx"
            class="day-chip"
            :class="{ 'day-chip-active': (dayMask & (1 << idx)) !== 0 }"
            @tap="toggleDay(idx)"
          >
            <text>{{ day }}</text>
          </view>
        </view>
      </view>

      <!-- 添加按钮 -->
      <button class="btn btn-outline mt-14" style="width:100%" @tap="addCustomTask">
        <text>+ 添加到计划列表</text>
      </button>
    </view>

    <!-- 已生成的计划列表 -->
    <view v-if="planList.length > 0" class="card">
      <text class="h4" style="margin-bottom:14px;display:block">
        计划列表（{{ planList.length }}项）
      </text>

      <!-- 按日期分组 -->
      <view v-for="(group, dateKey) in groupedPlans" :key="dateKey" class="plan-group">
        <text class="plan-date-header">{{ dateKey }}</text>
        <view
          v-for="(plan, idx) in group"
          :key="plan._id"
          class="plan-item flex-between"
        >
          <view class="flex-1">
            <view class="flex-row gap-10">
              <text class="plan-name">{{ plan.name }}</text>
              <text class="tag" :class="'tag-' + plan.task_type">
                {{ typeLabels[plan.task_type] }}
              </text>
            </view>
            <view class="flex-row gap-14 mt-10" style="font-size:13px">
              <text class="text-muted">{{ plan.duration_minutes }}分钟</text>
              <text class="text-muted">{{ plan.subject }}</text>
            </view>
          </view>
          <!-- 操作按钮 -->
          <view class="flex-row gap-10">
            <text class="action-icon edit-icon" @tap="editPlan(plan._id)">&#x270E;</text>
            <text class="action-icon delete-icon" @tap="removePlan(plan._id)">&#x2715;</text>
          </view>
        </view>
      </view>

      <!-- 确认创建按钮 -->
      <button class="btn btn-primary mt-14" style="width:100%" @tap="confirmCreatePlans" :disabled="submitLoading">
        <text>{{ submitLoading ? '创建中...' : '确认创建计划' }}</text>
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import Taro from '@tarojs/taro'
import { post } from '@/utils/request'
import { useTaskStore } from '@/stores/task'

const taskStore = useTaskStore()

// 学习模式
const learningModes = [
  '备考冲刺',
  '日常巩固',
  '考前复习',
  '兴趣拓展',
  '技能提升'
]

const selectedMode = ref('')
const showModePicker = ref(false)
const materialText = ref('')
const aiLoading = ref(false)
const submitLoading = ref(false)

const weekDayLabels = ['一', '二', '三', '四', '五', '六', '日']

// 类型标签
const typeLabels: Record<string, string> = {
  main: '主线',
  light: '轻量',
  review: '复习'
}

// 自定义任务表单
const customTask = reactive({
  name: '',
  duration: '30',
  subject: '',
  task_type: 'main' as 'main' | 'light' | 'review'
})

// 位掩码：1 << 0 = 周一, 1 << 1 = 周二 ... 1 << 6 = 周日
const dayMask = ref(0)

// 计划列表
interface PlanItem {
  _id: string
  name: string
  duration_minutes: number
  subject: string
  task_type: 'main' | 'light' | 'review'
  learning_mode: string
  material_text: string
  week_days: number
  date: string // 归属日期（用于分组显示）
}

const planList = ref<PlanItem[]>([])
let planIdCounter = 0

// 是否每天
const isEveryDay = computed(() => dayMask.value === 0x7F) // 0x7F = 0111 1111

// 按日期分组
const groupedPlans = computed(() => {
  const groups: Record<string, PlanItem[]> = {}
  planList.value.forEach(plan => {
    const key = plan.date || '未指定日期'
    if (!groups[key]) groups[key] = []
    groups[key].push(plan)
  })
  return groups
})

// 选择模式
const selectMode = (mode: string) => {
  selectedMode.value = mode
}

// 每天切换
const toggleEveryDay = () => {
  if (isEveryDay.value) {
    dayMask.value = 0
  } else {
    dayMask.value = 0x7F
  }
}

// 单天切换
const toggleDay = (idx: number) => {
  dayMask.value ^= (1 << idx)
}

// AI 规划
const generatePlan = async () => {
  if (!selectedMode.value) {
    Taro.showToast({ title: '请先选择学习模式', icon: 'none', duration: 1500 })
    return
  }
  if (!materialText.value.trim()) {
    Taro.showToast({ title: '请描述学习材料', icon: 'none', duration: 1500 })
    return
  }

  aiLoading.value = true
  try {
    const data = await post<{ plans: any[] }>('/ai/generate-plan', {
      learning_mode: selectedMode.value,
      material_text: materialText.value
    })

    if (data.plans && Array.isArray(data.plans)) {
      const today = getTodayStr()
      data.plans.forEach((p: any) => {
        planList.value.push({
          _id: `ai_${++planIdCounter}`,
          name: p.name,
          duration_minutes: p.duration_minutes || 30,
          subject: p.subject || '',
          task_type: p.task_type || 'main',
          learning_mode: selectedMode.value,
          material_text: materialText.value,
          week_days: p.week_days || 0x1F, // 默认周一至周五
          date: today
        })
      })
      Taro.showToast({ title: `AI 规划了 ${data.plans.length} 个任务`, icon: 'success', duration: 1500 })
    }
  } catch (error) {
    Taro.showToast({ title: 'AI 规划失败，请重试', icon: 'none', duration: 1500 })
  } finally {
    aiLoading.value = false
  }
}

// 添加自定义任务
const addCustomTask = () => {
  if (!customTask.name.trim()) {
    Taro.showToast({ title: '请输入任务名称', icon: 'none', duration: 1500 })
    return
  }
  if (dayMask.value === 0) {
    Taro.showToast({ title: '请选择至少一天', icon: 'none', duration: 1500 })
    return
  }

  planList.value.push({
    _id: `custom_${++planIdCounter}`,
    name: customTask.name,
    duration_minutes: parseInt(customTask.duration) || 30,
    subject: customTask.subject || '未分类',
    task_type: customTask.task_type,
    learning_mode: selectedMode.value || '日常巩固',
    material_text: materialText.value,
    week_days: dayMask.value,
    date: getTodayStr()
  })

  // 重置表单
  customTask.name = ''
  customTask.duration = '30'
  customTask.subject = ''

  Taro.showToast({ title: '已添加到计划列表', icon: 'success', duration: 1000 })
}

// 编辑计划
const editPlan = (_id: string) => {
  const plan = planList.value.find(p => p._id === _id)
  if (!plan) return
  // 简单编辑：弹出一个提示
  Taro.showModal({
    title: '编辑任务',
    content: `任务名：${plan.name}`,
    editable: true,
    placeholderText: '修改任务名称',
    success: (res) => {
      if (res.confirm && res.content) {
        plan.name = res.content
      }
    }
  })
}

// 删除计划
const removePlan = (_id: string) => {
  planList.value = planList.value.filter(p => p._id !== _id)
}

// 确认创建计划
const confirmCreatePlans = async () => {
  if (planList.value.length === 0) {
    Taro.showToast({ title: '请先添加计划', icon: 'none', duration: 1500 })
    return
  }

  submitLoading.value = true
  try {
    const tasks = planList.value.map(p => ({
      name: p.name,
      subject: p.subject,
      duration_minutes: p.duration_minutes,
      task_type: p.task_type,
      learning_mode: p.learning_mode,
      material_text: p.material_text,
      week_days: p.week_days
    }))

    await taskStore.batchCreateTasks(tasks)
    Taro.showToast({ title: `成功创建 ${tasks.length} 个任务`, icon: 'success', duration: 1500 })

    // 清空计划列表
    planList.value = []

    // 延迟跳转到首页
    setTimeout(() => {
      Taro.switchTab({ url: '/pages/home/index' })
    }, 800)
  } catch (error) {
    Taro.showToast({ title: '创建失败，请重试', icon: 'none', duration: 1500 })
  } finally {
    submitLoading.value = false
  }
}

// 获取今天日期字符串
const getTodayStr = (): string => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
</script>

<style lang="scss">
.mode-selector {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: #f5f4ed;
  border-radius: var(--radius-btn);
  border: 1px solid #e8e6dc;
}

.mode-value {
  font-size: 15px;
  color: #141413;
}

.mode-arrow {
  font-size: 12px;
  color: #9a9a8a;
}

// 模式选择器弹窗
.picker-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(20, 20, 19, 0.4);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.picker-panel {
  background: #ffffff;
  border-radius: 18px 18px 0 0;
  padding: 20px 18px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom));
  width: 100%;
}

.picker-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 14px 8px;
  border-bottom: 1px solid #f5f4ed;
  font-size: 15px;
  color: #141413;
}

.picker-item-active {
  color: #c96442;
  font-weight: 600;
  background: #fefaf6;
}

// 材料输入
.material-input {
  width: 100%;
  min-height: 80px;
  padding: 12px;
  background: #f5f4ed;
  border-radius: var(--radius-btn);
  font-size: 14px;
  color: #141413;
  line-height: 1.6;
}

// 表单
.form-group {
  margin-bottom: 14px;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: #6f735f;
  margin-bottom: 6px;
  display: block;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  background: #f5f4ed;
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: #141413;
}

// 类型选择
.type-row {
  display: flex;
  flex-direction: row;
  gap: 10px;
}

.type-chip {
  flex: 1;
  padding: 10px;
  border-radius: var(--radius-btn);
  background: #f5f4ed;
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #6f735f;
  border: 1.5px solid transparent;
  transition: all 0.2s ease;
}

.type-chip-active {
  background: #ffffff;
  color: #c96442;
  border-color: #c96442;
  font-weight: 600;
}

// 周期选择
.weekday-row {
  display: flex;
  flex-direction: row;
  gap: 8px;
  flex-wrap: wrap;
}

.everyday-chip {
  padding: 8px 16px;
  border-radius: var(--radius-tag);
  background: #f5f4ed;
  font-size: 13px;
  font-weight: 500;
  color: #6f735f;
  border: 1.5px solid transparent;
}

.everyday-active {
  background: #141413;
  color: #ffffff;
  border-color: #141413;
}

.day-chip {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #f5f4ed;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 500;
  color: #6f735f;
  border: 1.5px solid transparent;
  transition: all 0.2s ease;
}

.day-chip-active {
  background: #ffffff;
  color: #c96442;
  border-color: #c96442;
  font-weight: 600;
}

// 计划列表
.plan-group {
  margin-bottom: 14px;
}

.plan-date-header {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 14px;
  font-weight: 600;
  color: #c96442;
  display: block;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0ece0;
}

.plan-item {
  padding: 12px 0;
  border-bottom: 1px solid #f5f4ed;
}

.plan-name {
  font-size: 14px;
  font-weight: 600;
  color: #141413;
}

.action-icon {
  font-size: 16px;
  padding: 4px;
}

.edit-icon {
  color: #6f735f;
}

.delete-icon {
  color: #c94043;
}
</style>
