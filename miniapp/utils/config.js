const API_BASES = {
  local: 'http://127.0.0.1:8001',
  remote: 'https://inkfield.leicanxi.top'
}

const CURRENT_ENV = 'remote'

function getBaseURL() {
  return API_BASES[CURRENT_ENV] || API_BASES.local
}

module.exports = {
  API_BASES,
  CURRENT_ENV,
  getBaseURL
}
