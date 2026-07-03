// 环境配置
// 通过 TARO_APP_ENV 环境变量区分 dev / staging / prod

interface EnvConfig {
  apiBaseUrl: string
  debug: boolean
}

const envConfigs: Record<string, EnvConfig> = {
  dev: {
    apiBaseUrl: 'http://localhost:8000',
    debug: true
  },
  staging: {
    apiBaseUrl: 'https://staging-api.example.com',
    debug: true
  },
  prod: {
    apiBaseUrl: 'https://api.example.com',
    debug: false
  }
}

// Taro 中通过 process.env.TARO_APP_ENV 获取编译环境
// 默认为 dev 环境
const env = (typeof process !== 'undefined' && process.env?.TARO_APP_ENV) || 'dev'

export const config: EnvConfig = envConfigs[env] || envConfigs.dev

export default config
