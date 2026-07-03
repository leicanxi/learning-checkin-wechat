<template>
  <view class="page-container">
    <!-- 个人资料卡片 -->
    <view class="profile-card card">
      <view class="profile-header flex-row gap-14">
        <view class="avatar-wrap">
          <text class="avatar-text">{{ avatarInitial }}</text>
        </view>
        <view class="flex-1">
          <text class="profile-name">{{ userStore.nickname }}</text>
          <text class="profile-goal text-muted" style="font-size:13px">
            {{ userStore.learningGoal || '尚未设置学习目标' }}
          </text>
        </view>
        <text class="edit-link" @tap="editProfile">编辑</text>
      </view>
    </view>

    <!-- 提醒设置 -->
    <view class="card">
      <text class="h4" style="margin-bottom:14px;display:block">提醒设置</text>

      <view class="setting-item flex-between">
        <view>
          <text class="setting-label">每日打卡提醒</text>
          <text class="setting-desc text-muted" style="font-size:12px">每天晚上8点提醒打卡</text>
        </view>
        <switch
          :checked="reminderSettings.daily_checkin"
          color="#c96442"
          @change="toggleDailyReminder"
        />
      </view>

      <view class="divider" />

      <view class="setting-item flex-between">
        <view>
          <text class="setting-label">任务到期通知</text>
          <text class="setting-desc text-muted" style="font-size:12px">任务即将到期时提醒</text>
        </view>
        <switch
          :checked="reminderSettings.task_deadline"
          color="#c96442"
          @change="toggleDeadlineReminder"
        />
      </view>
    </view>

    <!-- 小组信息 -->
    <view class="card">
      <text class="h4" style="margin-bottom:12px;display:block">我的小组</text>
      <view v-if="groupInfo" class="group-info">
        <view class="flex-between">
          <text class="text-secondary">小组名称</text>
          <text class="group-name-text">{{ groupInfo.name || '--' }}</text>
        </view>
        <view class="flex-between mt-10">
          <text class="text-secondary">成员数</text>
          <text>{{ groupInfo.member_count || 0 }}人</text>
        </view>
        <view class="flex-between mt-10">
          <text class="text-secondary">本周完成率</text>
          <text class="text-primary">{{ groupInfo.completion_rate || 0 }}%</text>
        </view>
        <view class="flex-between mt-10">
          <text class="text-secondary">排名区间</text>
          <text class="text-primary">{{ groupInfo.rank_range || '--' }}</text>
        </view>
      </view>
      <view v-else class="empty-state" style="padding:16px 0">
        <text class="desc">尚未加入小组</text>
      </view>
    </view>

    <!-- 功能入口 -->
    <view class="card">
      <view class="menu-item flex-between" @tap="exportPDF">
        <text>导出学习报告 (PDF)</text>
        <text class="menu-arrow">&#x203A;</text>
      </view>
    </view>

    <view class="card">
      <view class="menu-item flex-between" @tap="showAbout">
        <text>关于应用</text>
        <view class="flex-row gap-10">
          <text class="text-muted" style="font-size:13px">v1.0.0</text>
          <text class="menu-arrow">&#x203A;</text>
        </view>
      </view>
    </view>

    <!-- 退出登录 -->
    <button class="btn btn-ghost mt-18" style="width:100%;color:#c94043" @tap="handleLogout">
      <text>退出登录</text>
    </button>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import Taro from '@tarojs/taro'
import { useUserStore } from '@/stores/user'
import { get, put } from '@/utils/request'

const userStore = useUserStore()

// 头像首字母
const avatarInitial = computed(() => {
  const name = userStore.nickname
  return name ? name.charAt(0).toUpperCase() : '?'
})

// 提醒设置
const reminderSettings = reactive({
  daily_checkin: false,
  task_deadline: false
})

// 小组信息
interface GroupInfo {
  name: string
  member_count: number
  completion_rate: number
  rank_range: string
}

const groupInfo = ref<GroupInfo | null>(null)

// 获取提醒设置
const fetchReminderSettings = async () => {
  try {
    const data = await get<{ daily_checkin: boolean; task_deadline: boolean }>('/settings/reminder')
    reminderSettings.daily_checkin = data.daily_checkin
    reminderSettings.task_deadline = data.task_deadline
  } catch (error) {
    // 使用默认值
  }
}

// 切换每日提醒
const toggleDailyReminder = async (e: any) => {
  const checked = e.detail.value
  reminderSettings.daily_checkin = checked
  try {
    await put('/settings/reminder', { daily_checkin: checked })
  } catch (error) {
    // 恢复
    reminderSettings.daily_checkin = !checked
    Taro.showToast({ title: '设置失败', icon: 'none', duration: 1500 })
  }
}

// 切换任务到期通知
const toggleDeadlineReminder = async (e: any) => {
  const checked = e.detail.value
  reminderSettings.task_deadline = checked
  try {
    await put('/settings/reminder', { task_deadline: checked })
  } catch (error) {
    reminderSettings.task_deadline = !checked
    Taro.showToast({ title: '设置失败', icon: 'none', duration: 1500 })
  }
}

// 获取小组信息
const fetchGroupInfo = async () => {
  try {
    const data = await get<GroupInfo>('/groups/my')
    groupInfo.value = data
  } catch (error) {
    groupInfo.value = null
  }
}

// 编辑个人资料
const editProfile = () => {
  Taro.showModal({
    title: '修改学习目标',
    editable: true,
    placeholderText: userStore.learningGoal || '输入你的学习目标',
    success: async (res) => {
      if (res.confirm && res.content) {
        try {
          await userStore.updateUser({ learning_goal: res.content } as any)
          Taro.showToast({ title: '更新成功', icon: 'success', duration: 1500 })
        } catch (error) {
          Taro.showToast({ title: '更新失败', icon: 'none', duration: 1500 })
        }
      }
    }
  })
}

// 导出 PDF
const exportPDF = () => {
  Taro.showToast({ title: 'PDF 导出功能开发中', icon: 'none', duration: 1500 })
}

// 关于应用
const showAbout = () => {
  Taro.showModal({
    title: '学习打卡追踪器',
    content: '版本：v1.0.0\n\n帮助你养成每日学习的习惯，追踪学习进度，与朋友一起进步。',
    showCancel: false,
    confirmText: '知道了'
  })
}

// 退出登录
const handleLogout = () => {
  Taro.showModal({
    title: '确认退出',
    content: '退出后需要重新登录，确定退出吗？',
    success: async (res) => {
      if (res.confirm) {
        await userStore.logout()
        Taro.reLaunch({ url: '/pages/login/index' })
      }
    }
  })
}

onMounted(async () => {
  await Promise.all([
    fetchReminderSettings(),
    fetchGroupInfo()
  ])
})
</script>

<style lang="scss">
// 个人资料卡片
.profile-card {
  background: linear-gradient(135deg, #fefaf6, #ffffff);
  border: 1px solid #f0ece0;
}

.profile-header {
  padding: 4px 0;
}

.avatar-wrap {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #c96442, #d48364);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-text {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 22px;
  font-weight: 700;
  color: #ffffff;
}

.profile-name {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 18px;
  font-weight: 600;
  color: #141413;
  display: block;
}

.profile-goal {
  margin-top: 4px;
  display: block;
}

.edit-link {
  font-size: 14px;
  color: #c96442;
  font-weight: 500;
}

// 设置项
.setting-item {
  padding: 6px 0;
}

.setting-label {
  font-size: 15px;
  font-weight: 500;
  color: #141413;
  display: block;
}

.setting-desc {
  margin-top: 2px;
  display: block;
}

// 小组信息
.group-info {
  padding: 4px 0;
}

.group-name-text {
  color: #c96442;
  font-weight: 600;
}

// 菜单项
.menu-item {
  padding: 6px 0;
  font-size: 15px;
  color: #141413;
}

.menu-arrow {
  font-size: 20px;
  color: #d0cdc0;
}
</style>
