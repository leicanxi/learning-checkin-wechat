<template>
  <view class="login-page">
    <!-- 顶部品牌区 -->
    <view class="brand-section">
      <view class="brand-icon">
        <text class="icon-text">&#x270E;</text>
      </view>
      <text class="brand-name">学习打卡追踪器</text>
      <text class="brand-slogan">坚持每一天，成就更好的自己</text>
    </view>

    <!-- 功能亮点 -->
    <view class="features">
      <view class="feature-item">
        <view class="feature-icon">&#x1F4C5;</view>
        <text class="feature-text">每日打卡记录</text>
      </view>
      <view class="feature-item">
        <view class="feature-icon">&#x1F4CA;</view>
        <text class="feature-text">学习数据分析</text>
      </view>
      <view class="feature-item">
        <view class="feature-icon">&#x1F3C6;</view>
        <text class="feature-text">好友排行激励</text>
      </view>
    </view>

    <!-- 登录按钮区域 -->
    <view class="login-section">
      <button
        class="wechat-login-btn"
        :disabled="loading"
        @tap="handleLogin"
      >
        <text v-if="!loading" class="btn-text">微信一键登录</text>
        <text v-else class="btn-text">登录中...</text>
      </button>
      <text class="privacy-tip">登录即表示同意《用户协议》和《隐私政策》</text>
    </view>

    <!-- 底部版本号 -->
    <text class="version-text">v1.0.0</text>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Taro from '@tarojs/taro'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const loading = ref(false)

onMounted(async () => {
  // 检查是否已登录
  if (userStore.isLoggedIn) {
    Taro.switchTab({ url: '/pages/home/index' })
  }
})

const handleLogin = async () => {
  if (loading.value) return

  loading.value = true
  try {
    await userStore.login()
    Taro.showToast({
      title: '登录成功',
      icon: 'success',
      duration: 1500
    })
    // 延迟跳转，让 toast 显示完成
    setTimeout(() => {
      Taro.switchTab({ url: '/pages/home/index' })
    }, 500)
  } catch (error: any) {
    console.error('登录失败:', error)
    Taro.showToast({
      title: error.message || '登录失败，请重试',
      icon: 'none',
      duration: 2000
    })
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss">
.login-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 60px 40px;
  background: linear-gradient(180deg, #fefaf6 0%, #f5f4ed 100%);
}

.brand-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 60px;
}

.brand-icon {
  width: 90px;
  height: 90px;
  border-radius: 24px;
  background: linear-gradient(135deg, #c96442, #d48364);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 22px;
  box-shadow: 0 8px 24px rgba(201, 100, 66, 0.3);

  .icon-text {
    font-size: 42px;
    color: #ffffff;
  }
}

.brand-name {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 26px;
  font-weight: 700;
  color: #141413;
  letter-spacing: 0.04em;
  margin-bottom: 10px;
}

.brand-slogan {
  font-size: 15px;
  color: #6f735f;
  letter-spacing: 0.02em;
}

.features {
  display: flex;
  flex-direction: row;
  gap: 30px;
  margin-bottom: 60px;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.feature-icon {
  font-size: 28px;
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(20, 20, 19, 0.06);
}

.feature-text {
  font-size: 12px;
  color: #6f735f;
  font-weight: 500;
}

.login-section {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.wechat-login-btn {
  width: 100%;
  max-width: 320px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #c96442, #d48364);
  color: #ffffff;
  font-size: 17px;
  font-weight: 600;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 20px rgba(201, 100, 66, 0.35);
  transition: all 0.2s ease;

  &::after {
    border: none;
  }

  &[disabled] {
    opacity: 0.7;
  }
}

.btn-text {
  color: #ffffff;
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.privacy-tip {
  font-size: 12px;
  color: #9a9a8a;
  margin-top: 16px;
  text-align: center;
}

.version-text {
  position: absolute;
  bottom: 40px;
  font-size: 12px;
  color: #c0c0b0;
}
</style>
