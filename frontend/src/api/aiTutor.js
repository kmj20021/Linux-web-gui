import { getAuthHeaders } from './client'

const BASE = `${import.meta.env.VITE_API_URL || '/api'}/ai`
const REQUEST_TIMEOUT_MS = 30_000

export class AITutorAPIError extends Error {
  constructor(message, status, retryAfter = 0) {
    super(message)
    this.name = 'AITutorAPIError'
    this.status = status
    this.retryAfter = retryAfter
  }
}

async function request(path, options = {}) {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...getAuthHeaders(),
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers,
      },
    })
    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      const retryAfter = Number.parseInt(response.headers.get('Retry-After') || '0', 10)
      throw new AITutorAPIError(body.detail || `요청 실패 (${response.status})`, response.status, retryAfter)
    }
    return response.json()
  } catch (error) {
    if (error.name === 'AbortError') throw new AITutorAPIError('요청 시간이 초과되었습니다. 자동 재시도하지 않습니다.', 0)
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

export const aiTutorAPI = {
  curriculum: () => request('/curriculum'),
  createSession: (problem) => request('/sessions', {
    method: 'POST',
    body: JSON.stringify({
      mode: 'simulation',
      level: problem.difficulty,
      scenario_key: problem.scenario_id,
      task_key: problem.task_id,
    }),
  }),
  getSession: (id) => request(`/sessions/${id}`),
  getHistory: (id) => request(`/sessions/${id}/history`),
  command: (id, commandText, version) => request(`/sessions/${id}/commands`, {
    method: 'POST', body: JSON.stringify({ command_text: commandText, expected_version: version }),
  }),
  chat: (id, message) => request(`/sessions/${id}/chat`, {
    method: 'POST', body: JSON.stringify({ message }),
  }),
  hint: (id, version) => request(`/sessions/${id}/hints`, {
    method: 'POST', body: JSON.stringify({ expected_version: version }),
  }),
  grade: (id, version) => request(`/sessions/${id}/grade`, {
    method: 'POST', body: JSON.stringify({ expected_version: version }),
  }),
  reset: (id, version) => request(`/sessions/${id}/reset`, {
    method: 'POST', body: JSON.stringify({ expected_version: version }),
  }),
}
