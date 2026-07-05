let cachedNavMetrics = null

function getNavMetrics() {
  if (cachedNavMetrics) {
    return cachedNavMetrics
  }

  const systemInfo = wx.getSystemInfoSync ? wx.getSystemInfoSync() : {}
  const statusBarHeight = systemInfo.statusBarHeight || 24

  let menuButton = null
  try {
    menuButton = wx.getMenuButtonBoundingClientRect && wx.getMenuButtonBoundingClientRect()
  } catch (e) {
    menuButton = null
  }

  let navContentHeight = 46
  if (menuButton && menuButton.height && menuButton.top > statusBarHeight) {
    const menuGap = menuButton.top - statusBarHeight
    navContentHeight = menuGap * 2 + menuButton.height
  }

  const navBarHeight = statusBarHeight + navContentHeight

  cachedNavMetrics = {
    statusBarHeight,
    navContentHeight,
    navBarHeight,
    navBarStyle: `height:${navBarHeight}px;padding-top:${statusBarHeight}px;`,
    navContentStyle: `height:${navContentHeight}px;`
  }

  return cachedNavMetrics
}

module.exports = {
  getNavMetrics
}
