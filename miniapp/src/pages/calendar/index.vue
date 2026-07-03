<template>
  <view class="page-container">
    <!-- 月份切换头 -->
    <view class="calendar-header">
      <view class="month-nav flex-between">
        <view class="nav-arrow" @tap="prevMonth">
          <text class="arrow-text">&#x2039;</text>
        </view>
        <text class="h2 month-title">{{ currentYear }}年{{ currentMonth }}月</text>
        <view class="nav-arrow" @tap="nextMonth">
          <text class="arrow-text">&#x203A;</text>
        </view>
      </view>

      <!-- 星期头 -->
      <view class="weekday-row">
        <text v-for="wd in weekDays" :key="wd" class="weekday-item">{{ wd }}</text>
      </view>
    </view>

    <!-- 日历网格 7x6 -->
    <view class="calendar-grid">
      <view
        v-for="(cell, idx) in calendarCells"
        :key="idx"
        class="calendar-cell"
        :class="getCellClass(cell)"
        @tap="cell.date ? onDateClick(cell) : null"
      >
        <text v-if="cell.date" class="cell-date">{{ cell.day }}</text>
        <!-- 状态点 -->
        <view v-if="cell.date && cell.status !== 'empty'" class="cell-dot" :class="`dot-${cell.status}`" />
      </view>
    </view>

    <!-- 图例说明 -->
    <view class="legend-row">
      <view class="legend-item">
        <view class="legend-dot dot-full" />
        <text class="legend-text">全勤</text>
      </view>
      <view class="legend-item">
        <view class="legend-dot dot-partial" />
        <text class="legend-text">部分</text>
      </view>
      <view class="legend-item">
        <view class="legend-dot dot-missed" />
        <text class="legend-text">未打卡</text>
      </view>
      <view class="legend-item">
        <view class="legend-dot dot-weekend" />
        <text class="legend-text">休息日</text>
      </view>
      <view class="legend-item">
        <view class="legend-dot dot-today" />
        <text class="legend-text">今天</text>
      </view>
    </view>

    <!-- 底部 Today 和 Tomorrow 卡片 -->
    <view class="bottom-cards">
      <view class="today-card card">
        <view class="card-label">
          <text class="tag tag-main">今天</text>
        </view>
        <view v-if="todayData">
          <text class="card-date-text">{{ todayData.date_str }}</text>
          <view class="card-tasks">
            <view v-for="(t, i) in todayData.tasks" :key="i" class="card-task-item">
              <text class="task-check-icon">{{ t.checked ? '&#x2713;' : '&#x25CB;' }}</text>
              <text :class="t.checked ? 'task-done' : 'task-pending'">{{ t.name }}</text>
            </view>
          </view>
        </view>
        <view v-else class="card-empty">
          <text class="text-muted">暂无任务</text>
        </view>
      </view>

      <view class="tomorrow-card card">
        <view class="card-label">
          <text class="tag tag-light">明天</text>
        </view>
        <view v-if="tomorrowData">
          <text class="card-date-text">{{ tomorrowData.date_str }}</text>
          <view class="card-tasks">
            <view v-for="(t, i) in tomorrowData.tasks" :key="i" class="card-task-item">
              <text class="task-pending-icon">&#x25CB;</text>
              <text class="task-pending">{{ t.name }}</text>
            </view>
          </view>
        </view>
        <view v-else class="card-empty">
          <text class="text-muted">暂无任务</text>
        </view>
      </view>
    </view>

    <!-- 底部弹出层（日期详情） -->
    <view v-if="selectedDate" class="sheet-overlay" @tap="closeSheet">
      <view class="sheet-panel" @tap.stop>
        <view class="sheet-handle" />
        <text class="h3" style="margin-bottom:16px">{{ selectedDate.date_str }} 详情</text>
        <view v-if="selectedDate.tasks && selectedDate.tasks.length > 0" class="sheet-task-list">
          <view v-for="(t, i) in selectedDate.tasks" :key="i" class="sheet-task-item flex-between">
            <view class="flex-row gap-10">
              <text>{{ t.checked ? '&#x2713;' : '&#x25CB;' }}</text>
              <text :class="t.checked ? 'task-done' : ''">{{ t.name }}</text>
            </view>
            <text class="tag tag-muted">{{ t.subject }}</text>
          </view>
        </view>
        <view v-else class="empty-state" style="padding:24px 0">
          <text class="desc">当天没有任务</text>
        </view>
        <button class="btn btn-primary mt-14" style="width:100%" @tap="closeSheet">关闭</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { get } from '@/utils/request'

// 日期单元格数据接口
interface CalendarCell {
  date: string | null
  day: number | null
  status: 'full' | 'partial' | 'missed' | 'weekend' | 'today' | 'empty'
}

interface DayTask {
  name: string
  subject: string
  checked: boolean
}

interface DayData {
  date_str: string
  tasks: DayTask[]
}

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth() + 1)
const calendarCells = ref<CalendarCell[]>([])
const todayData = ref<DayData | null>(null)
const tomorrowData = ref<DayData | null>(null)
const selectedDate = ref<DayData | null>(null)

// 生成日历网格
const generateCalendar = (monthData: Record<string, DayData>) => {
  const year = currentYear.value
  const month = currentMonth.value
  const firstDay = new Date(year, month - 1, 1)
  const lastDay = new Date(year, month, 0)
  const daysInMonth = lastDay.getDate()
  const startDayOfWeek = firstDay.getDay() // 0=周日

  const cells: CalendarCell[] = []
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  // 填充前置空格
  for (let i = 0; i < startDayOfWeek; i++) {
    cells.push({ date: null, day: null, status: 'empty' })
  }

  // 填充日期
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const dayOfWeek = new Date(year, month - 1, d).getDay()
    const dayData = monthData[dateStr]

    let status: CalendarCell['status'] = 'missed'
    if (dateStr === todayStr) {
      status = 'today'
    } else if (dayOfWeek === 0 || dayOfWeek === 6) {
      status = 'weekend'
    } else if (dayData) {
      const total = dayData.tasks.length
      const done = dayData.tasks.filter(t => t.checked).length
      if (total > 0 && done === total) {
        status = 'full'
      } else if (done > 0) {
        status = 'partial'
      } else {
        status = 'missed'
      }
    }

    cells.push({ date: dateStr, day: d, status })
  }

  // 补齐到42格（7x6）
  while (cells.length < 42) {
    cells.push({ date: null, day: null, status: 'empty' })
  }

  calendarCells.value = cells
}

// 获取单元格样式类
const getCellClass = (cell: CalendarCell) => {
  if (!cell.date) return 'cell-empty'
  return {
    'cell-full': cell.status === 'full',
    'cell-partial': cell.status === 'partial',
    'cell-missed': cell.status === 'missed',
    'cell-weekend': cell.status === 'weekend',
    'cell-today': cell.status === 'today'
  }
}

// 月份切换
const prevMonth = () => {
  if (currentMonth.value === 1) {
    currentYear.value--
    currentMonth.value = 12
  } else {
    currentMonth.value--
  }
  fetchMonthData()
}

const nextMonth = () => {
  if (currentMonth.value === 12) {
    currentYear.value++
    currentMonth.value = 1
  } else {
    currentMonth.value++
  }
  fetchMonthData()
}

// 点击日期
const onDateClick = (cell: CalendarCell) => {
  if (!cell.date) return
  // 从已缓存的月度数据中查找
  fetchDateDetail(cell.date)
}

// 关闭底部弹层
const closeSheet = () => {
  selectedDate.value = null
}

// 获取月度数据
const fetchMonthData = async () => {
  try {
    const data = await get<{ days: Record<string, DayData> }>('/calendar/month', {
      year: currentYear.value,
      month: currentMonth.value
    })
    generateCalendar(data.days || {})
  } catch (error) {
    // 如果接口不可用，生成空日历
    generateCalendar({})
  }
}

// 获取 Today/Tomorrow 数据
const fetchDayCards = async () => {
  try {
    const [today, tomorrow] = await Promise.all([
      get<DayData>('/calendar/today'),
      get<DayData>('/calendar/tomorrow')
    ])
    todayData.value = today
    tomorrowData.value = tomorrow
  } catch (error) {
    // 静默失败
  }
}

// 获取日期详情
const fetchDateDetail = async (date: string) => {
  try {
    const data = await get<DayData>('/calendar/date', { date })
    selectedDate.value = data
  } catch (error) {
    // 如果 API 不可用，显示空状态
    selectedDate.value = {
      date_str: date,
      tasks: []
    }
  }
}

onMounted(async () => {
  await Promise.all([
    fetchMonthData(),
    fetchDayCards()
  ])
})
</script>

<style lang="scss">
.calendar-header {
  margin-bottom: 14px;
}

.month-nav {
  padding: 0 4px;
  margin-bottom: 14px;
}

.nav-arrow {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(20, 20, 19, 0.05);
}

.arrow-text {
  font-size: 22px;
  color: #c96442;
  font-weight: 300;
}

.month-title {
  font-family: Georgia, 'Times New Roman', serif;
}

.weekday-row {
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  padding: 8px 0;
}

.weekday-item {
  font-size: 12px;
  font-weight: 600;
  color: #9a9a8a;
  width: 36px;
  text-align: center;
  text-transform: uppercase;
}

// 日历网格
.calendar-grid {
  display: flex;
  flex-wrap: wrap;
  background: #ffffff;
  border-radius: var(--radius-card);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.calendar-cell {
  width: calc(100% / 7);
  aspect-ratio: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  border-right: 0.5px solid #f5f4ed;
  border-bottom: 0.5px solid #f5f4ed;

  &:nth-child(7n) {
    border-right: none;
  }
}

.cell-empty {
  background: #fafaf8;
}

.cell-full {
  background: linear-gradient(135deg, #e8f0e4, #f0f6ec);
}

.cell-partial {
  background: linear-gradient(135deg, #fef8f0, #fff5ec);
}

.cell-missed {
  background: #fafaf8;
}

.cell-weekend {
  background: #f5f4ed;
}

.cell-today {
  background: #ffffff;
  border: 2px solid #c96442;
  border-radius: 8px;
}

.cell-date {
  font-size: 14px;
  font-weight: 600;
  color: #141413;
  z-index: 1;
}

.cell-today .cell-date {
  color: #c96442;
  font-weight: 700;
}

.cell-weekend .cell-date {
  color: #9a9a8a;
}

.cell-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  margin-top: 3px;
}

.dot-full {
  background: #6f735f;
}

.dot-partial {
  background: #d4a853;
}

.dot-missed {
  background: #e0ddd0;
}

.dot-weekend {
  background: #d0cdc0;
}

.dot-today {
  background: #c96442;
}

// 图例
.legend-row {
  display: flex;
  flex-direction: row;
  justify-content: center;
  gap: 16px;
  padding: 14px 0;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 4px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-text {
  font-size: 11px;
  color: #9a9a8a;
}

// 底部 Today/Tomorrow 卡片
.bottom-cards {
  display: flex;
  flex-direction: row;
  gap: 12px;
  margin-top: 8px;
}

.today-card,
.tomorrow-card {
  flex: 1;
  background: #ffffff;
  border: 1px solid #f0ece0;
  padding: 14px;
}

.card-label {
  margin-bottom: 8px;
}

.card-date-text {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 15px;
  font-weight: 600;
  color: #141413;
  display: block;
  margin-bottom: 8px;
}

.card-tasks {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-task-item {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.task-check-icon {
  font-size: 13px;
  color: #6f735f;
}

.task-pending-icon {
  font-size: 13px;
  color: #d0cdc0;
}

.task-done {
  font-size: 13px;
  color: #9a9a8a;
  text-decoration: line-through;
}

.task-pending {
  font-size: 13px;
  color: #6f735f;
}

.card-empty {
  padding: 12px 0;
  text-align: center;
}

// 底部弹出层
.sheet-overlay {
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

.sheet-panel {
  background: #ffffff;
  border-radius: 18px 18px 0 0;
  padding: 20px 18px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom));
  width: 100%;
  max-height: 60vh;
  overflow-y: auto;
}

.sheet-handle {
  width: 36px;
  height: 4px;
  border-radius: 2px;
  background: #e0ddd0;
  margin: 0 auto 16px;
}

.sheet-task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sheet-task-item {
  padding: 10px 0;
  border-bottom: 1px solid #f5f4ed;
}
</style>
