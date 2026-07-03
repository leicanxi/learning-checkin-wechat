export default defineAppConfig({
  pages: [
    'pages/login/index',
    'pages/home/index',
    'pages/calendar/index',
    'pages/planner/index',
    'pages/stats/index',
    'pages/ranking/index',
    'pages/settings/index'
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#c96442',
    navigationBarTitleText: '学习打卡追踪器',
    navigationBarTextStyle: 'white',
    backgroundColor: '#f5f4ed'
  },
  tabBar: {
    color: '#6f735f',
    selectedColor: '#c96442',
    backgroundColor: '#ffffff',
    borderStyle: 'white',
    list: [
      {
        pagePath: 'pages/home/index',
        text: '首页',
        iconPath: 'assets/tab/home.png',
        selectedIconPath: 'assets/tab/home-active.png'
      },
      {
        pagePath: 'pages/calendar/index',
        text: '日历',
        iconPath: 'assets/tab/calendar.png',
        selectedIconPath: 'assets/tab/calendar-active.png'
      },
      {
        pagePath: 'pages/planner/index',
        text: '规划',
        iconPath: 'assets/tab/planner.png',
        selectedIconPath: 'assets/tab/planner-active.png'
      },
      {
        pagePath: 'pages/stats/index',
        text: '统计',
        iconPath: 'assets/tab/stats.png',
        selectedIconPath: 'assets/tab/stats-active.png'
      },
      {
        pagePath: 'pages/ranking/index',
        text: '排行',
        iconPath: 'assets/tab/ranking.png',
        selectedIconPath: 'assets/tab/ranking-active.png'
      },
      {
        pagePath: 'pages/settings/index',
        text: '设置',
        iconPath: 'assets/tab/settings.png',
        selectedIconPath: 'assets/tab/settings-active.png'
      }
    ]
  }
})
