// ============================================================
//  GRYPHONE — клиент API
//  ИСПРАВЛЕНО (v27): добавлены updateAudio и updateLocation.
// ============================================================
const API_BASE = '/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`Ошибка запроса: ${response.status}`)
  }
  return response.json()
}

export function getCameras() { return request('/cameras') }
export function saveCameras(cameras) {
  return request('/cameras/save', { method: 'POST', body: JSON.stringify({ cameras }) })
}
export function toggleCamera(camId, enabled) {
  return request('/cameras/toggle', { method: 'POST', body: JSON.stringify({ cam_id: camId, enabled }) })
}
export function updateComment(camId, comment) {
  return request('/cameras/comment', { method: 'POST', body: JSON.stringify({ cam_id: camId, comment }) })
}
// НОВОЕ (v27):
export function updateAudio(camId, audio) {
  return request('/cameras/audio', { method: 'POST', body: JSON.stringify({ cam_id: camId, audio }) })
}
export function updateLocation(camId, location) {
  return request('/cameras/location', { method: 'POST', body: JSON.stringify({ cam_id: camId, location }) })
}

export function getSets() { return request('/sets') }
export function getCurrentSetCameras() { return request('/sets/current') }
export function saveSets(data) {
  return request('/sets/save', { method: 'POST', body: JSON.stringify(data) })
}
export function switchSet(setId) {
  return request('/sets/switch', { method: 'POST', body: JSON.stringify({ set_id: setId }) })
}

export function getConfig() { return request('/config') }
export function saveConfig(data) {
  return request('/config/save', { method: 'POST', body: JSON.stringify(data) })
}
export function getEvents() { return request('/events') }
export function publishEvent(event) {
  return request('/events/publish', { method: 'POST', body: JSON.stringify(event) })
}
export function getDashboard() { return request('/dashboard') }
export function getFfmpegLogs() { return request('/ffmpeg_logs') }
