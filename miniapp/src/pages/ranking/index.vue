<template>
  <view class="page-container">
    <!-- 深色 Hero 区 -->
    <view class="ranking-hero">
      <view class="hero-rank">
        <text class="rank-range">{{ rankingData?.rank_range || '--' }}</text>
        <text class="rank-title">{{ rankingData?.title || '加载中...' }}</text>
      </view>
      <text class="hero-desc">{{ rankingData?.description || '' }}</text>
    </view>

    <!-- 维度切换 -->
    <view class="dimension-tabs flex-row">
      <view
        class="dimension-tab"
        :class="{ 'dimension-tab-active': activeDimension === 'group' }"
        @tap="switchDimension('group')"
      >
        <text>小组</text>
      </view>
      <view
        class="dimension-tab"
        :class="{ 'dimension-tab-active': activeDimension === 'global' }"
        @tap="switchDimension('global')"
      >
        <text>全局</text>
      </view>
    </view>

    <!-- 排名区间说明卡片 -->
    <view class="rank-tiers">
      <view class="tier-card tier-gold">
        <view class="tier-icon">&#x1F947;</view>
        <text class="tier-title" style="color:#c96442">前 10%</text>
        <text class="tier-desc">学霸区</text>
      </view>
      <view class="tier-card tier-silver">
        <view class="tier-icon">&#x1F948;</view>
        <text class="tier-title" style="color:#6f735f">前 30%</text>
        <text class="tier-desc">进阶区</text>
      </view>
      <view class="tier-card tier-bronze">
        <view class="tier-icon">&#x1F949;</view>
        <text class="tier-title" style="color:#d4a853">其他</text>
        <text class="tier-desc">追赶区</text>
      </view>
    </view>

    <!-- 徽章墙 -->
    <view class="card">
      <text class="h4" style="margin-bottom:14px;display:block">我的徽章</text>
      <view class="badge-grid">
        <view
          v-for="badge in badgeList"
          :key="badge.id"
          class="badge-item"
          :class="{ 'badge-earned': badge.earned }"
        >
          <view class="badge-icon-wrap">
            <text class="badge-icon">{{ badge.icon }}</text>
          </view>
          <text class="badge-name">{{ badge.name }}</text>
        </view>
        <!-- 空状态 -->
        <view v-if="badgeList.length === 0" class="empty-state" style="width:100%;padding:20px 0">
          <text class="desc">暂无徽章</text>
        </view>
      </view>
    </view>

    <!-- 个人排名详情（可选） -->
    <view v-if="rankingData" class="card mt-14">
      <text class="h4" style="margin-bottom:12px;display:block">我的数据</text>
      <view class="flex-between">
        <text class="text-secondary">连续打卡</text>
        <text>{{ rankingData.streak_days || 0 }}天</text>
      </view>
      <view class="flex-between mt-10">
        <text class="text-secondary">本周打卡率</text>
        <text class="text-primary">{{ rankingData.week_rate || 0 }}%</text>
      </view>
      <view class="flex-between mt-10">
        <text class="text-secondary">排名区间</text>
        <text class="text-primary">{{ rankingData.rank_range || '--' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { get } from '@/utils/request'

interface RankingData {
  rank_range: string
  title: string
  description: string
  streak_days: number
  week_rate: number
}

interface Badge {
  id: number
  name: string
  icon: string
  description: string
  earned: boolean
}

const activeDimension = ref<'group' | 'global'>('group')
const rankingData = ref<RankingData | null>(null)

// 模拟徽章数据（可从 API 获取）
const badgeList = ref<Badge[]>([
  { id: 1, name: '首次打卡', icon: '\u{1F31F}', description: '完成第一次打卡', earned: true },
  { id: 2, name: '连续7天', icon: '\u{1F525}', description: '连续打卡7天', earned: true },
  { id: 3, name: '连续30天', icon: '\u{1F4AA}', description: '连续打卡30天', earned: false },
  { id: 4, name: '满分周', icon: '\u{1F3AF}', description: '一周全勤打卡', earned: true },
  { id: 5, name: '学霸认证', icon: '\u{1F393}', description: '排名前10%', earned: false },
  { id: 6, name: '任务达人', icon: '\u{1F4CB}', description: '创建10个任务', earned: false },
  { id: 7, name: '早起鸟', icon: '\u{1F426}', description: '早上8点前打卡', earned: false },
  { id: 8, name: '夜猫子', icon: '\u{1F319}', description: '晚上10点后打卡', earned: false },
  { id: 9, name: '百次打卡', icon: '\u{1F389}', description: '累计打卡100次', earned: false }
])

// 获取排名数据
const fetchRanking = async () => {
  try {
    const data = await get<RankingData>('/ranking/me', {
      dimension: activeDimension.value
    })
    rankingData.value = data
  } catch (error) {
    // 使用模拟数据
    rankingData.value = {
      rank_range: '前 30%',
      title: '进阶学友',
      description: '坚持得不错，继续加油！',
      streak_days: 3,
      week_rate: 75
    }
  }
}

// 获取徽章
const fetchBadges = async () => {
  try {
    const [allBadges, myBadges] = await Promise.all([
      get<any[]>('/badges'),
      get<any[]>('/badges/me')
    ])
    if (allBadges && myBadges) {
      const earnedIds = new Set(myBadges.map((b: any) => b.id))
      badgeList.value = allBadges.map((b: any) => ({
        ...b,
        earned: earnedIds.has(b.id)
      }))
    }
  } catch (error) {
    // 使用默认徽章数据
  }
}

// 切换维度
const switchDimension = (dim: 'group' | 'global') => {
  activeDimension.value = dim
  fetchRanking()
}

onMounted(() => {
  fetchRanking()
  fetchBadges()
})
</script>

<style lang="scss">
// 深色 Hero 区
.ranking-hero {
  background: linear-gradient(135deg, #141413, #2a2928);
  border-radius: var(--radius-card);
  padding: 24px 20px;
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.hero-rank {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.rank-range {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 36px;
  font-weight: 700;
  color: #c96442;
}

.rank-title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
}

.hero-desc {
  font-size: 13px;
  color: #9a9a8a;
}

// 维度切换
.dimension-tabs {
  background: #ffffff;
  border-radius: var(--radius-card);
  padding: 4px;
  margin-bottom: 14px;
  box-shadow: var(--shadow-card);
}

.dimension-tab {
  flex: 1;
  padding: 8px;
  border-radius: var(--radius-btn);
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #6f735f;
  transition: all 0.25s ease;
}

.dimension-tab-active {
  background: #141413;
  color: #ffffff;
  font-weight: 600;
}

// 排名区间说明
.rank-tiers {
  display: flex;
  flex-direction: row;
  gap: 10px;
  margin-bottom: 14px;
}

.tier-card {
  flex: 1;
  background: #ffffff;
  border-radius: var(--radius-card);
  padding: 14px 10px;
  text-align: center;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.tier-icon {
  font-size: 24px;
  margin-bottom: 2px;
}

.tier-title {
  font-size: 15px;
  font-weight: 700;
}

.tier-desc {
  font-size: 11px;
  color: #9a9a8a;
}

// 徽章墙
.badge-grid {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 12px;
}

.badge-item {
  width: calc((100% - 24px) / 3);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 6px;
  border-radius: var(--radius-md);
  background: #f5f4ed;
  opacity: 0.35;
  transition: all 0.2s ease;
}

.badge-earned {
  opacity: 1;
  background: #ffffff;
  box-shadow: var(--shadow-card);
}

.badge-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #f5f4ed;
  display: flex;
  align-items: center;
  justify-content: center;
}

.badge-earned .badge-icon-wrap {
  background: #fefaf6;
}

.badge-icon {
  font-size: 22px;
}

.badge-name {
  font-size: 11px;
  color: #6f735f;
  font-weight: 500;
  text-align: center;
}

.badge-earned .badge-name {
  color: #141413;
  font-weight: 600;
}
</style>
