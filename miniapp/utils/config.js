const API_BASES = {
  local: 'http://127.0.0.1:8001',
  remote: 'http://120.77.254.150:8001'
}

const CURRENT_ENV = 'local'

function getBaseURL() {
  return API_BASES[CURRENT_ENV] || API_BASES.local
}

module.exports = {
  API_BASES,
  CURRENT_ENV,
  getBaseURL
}
