/**
 * API 클라이언트 및 WebSocket 유틸리티
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'
const _wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_BASE_URL = import.meta.env.VITE_WS_URL || `${_wsProtocol}//${window.location.host}/ws`

// ============================================================
// 인증 토큰 헬퍼
// ============================================================

/**
 * localStorage에서 인증 토큰을 읽어 Authorization 헤더를 반환합니다.
 */
export function getAuthHeaders() {
  const token = localStorage.getItem('auth_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

/**
 * 현재 저장된 인증 토큰을 반환합니다.
 */
export function getAuthToken() {
  return localStorage.getItem('auth_token')
}

// ============================================================
// 공통 요청 계층
// ============================================================

export const DEFAULT_TIMEOUT_MS = 10000

/** 모든 REST 실패가 갖는 오류 타입. status 와 code 로 원인을 구분한다. */
export class ApiError extends Error {
  constructor(message, { status = 0, code = 'http_error' } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }

  /** 인증이 만료됐거나 없는 경우. 페이지마다 같은 방식으로 처리한다. */
  get isAuthExpired() {
    return this.status === 401
  }
}

// 401 을 받았을 때 알림을 받을 구독자들(AuthContext 가 로그아웃 처리에 사용).
const authExpiredListeners = new Set()

/** 인증 만료 알림을 구독한다. 반환된 함수를 호출하면 구독이 해제된다. */
export function onAuthExpired(listener) {
  authExpiredListeners.add(listener)
  return () => authExpiredListeners.delete(listener)
}

function notifyAuthExpired() {
  authExpiredListeners.forEach(listener => {
    try {
      listener()
    } catch {
      console.error('인증 만료 리스너 실행 오류')
    }
  })
}

// 응답 본문을 안전하게 읽는다. 본문이 없거나 JSON 이 아니면 null 을 돌려준다.
async function readJson(response) {
  if (response.status === 204) return null
  const contentType = response.headers?.get?.('content-type') || ''
  if (!contentType.includes('json')) return null
  return response.json().catch(() => null)
}

// FastAPI 의 detail(문자열/검증 오류 배열)을 한 줄 메시지로 만든다.
function extractDetail(body, status) {
  const detail = body?.detail
  if (Array.isArray(detail)) return detail.map(e => e.msg).join(', ')
  if (typeof detail === 'string' && detail) return detail
  return `요청 실패 (${status})`
}

/**
 * 공통 REST 요청.
 *
 * - JSON 직렬화/파싱과 Authorization 헤더를 한 곳에서 처리한다.
 * - 실패는 항상 ApiError 로 통일한다.
 * - 401 은 인증 만료로 보고 구독자에게 알린다(로그인 요청 등 auth:false 는 제외).
 * - timeoutMs 를 넘기면 요청을 중단하고 code 'timeout' 으로 알린다.
 */
export async function apiFetch(path, options = {}) {
  const {
    method = 'GET',
    body,
    headers = {},
    auth = true,
    token,
    timeoutMs = DEFAULT_TIMEOUT_MS,
  } = options

  const requestHeaders = { ...headers }
  if (auth) {
    const authHeaders = token ? { Authorization: `Bearer ${token}` } : getAuthHeaders()
    Object.assign(requestHeaders, authHeaders)
  }
  if (body !== undefined) {
    requestHeaders['Content-Type'] = 'application/json'
  }

  const controller = new AbortController()
  const timer = timeoutMs > 0 ? setTimeout(() => controller.abort(), timeoutMs) : null

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: requestHeaders,
      signal: controller.signal,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    })
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new ApiError('요청 시간이 초과되었습니다.', { code: 'timeout' })
    }
    throw new ApiError('서버에 연결할 수 없습니다.', { code: 'network_error' })
  } finally {
    if (timer) clearTimeout(timer)
  }

  if (!response.ok) {
    const errorBody = await readJson(response)
    if (response.status === 401 && auth) notifyAuthExpired()
    throw new ApiError(extractDetail(errorBody, response.status), {
      status: response.status,
      code: response.status === 401 ? 'unauthorized' : 'http_error',
    })
  }

  return readJson(response)
}

// ============================================================
// 인증 API
// ============================================================

export const authAPI = {
  login: (username, password) =>
    apiFetch('/auth/login', { method: 'POST', body: { username, password }, auth: false }),

  logout: (token) => apiFetch('/auth/logout', { method: 'POST', token }),

  getMe: (token) => apiFetch('/auth/me', { token }),

  register: (username, password, password_confirm) =>
    apiFetch('/auth/register', {
      method: 'POST',
      body: { username, password, password_confirm },
      auth: false,
    }),

  getWebSocketTicket: (purpose) =>
    apiFetch(`/auth/ws-tickets/${purpose}`, { method: 'POST' }),
}

// ============================================================
// 일반 API 클라이언트
// ============================================================

export const monitoringAPI = {
  getCPU: () => apiFetch('/monitor/cpu'),
  getMemory: () => apiFetch('/monitor/memory'),
  getProcesses: () => apiFetch('/monitor/processes'),
  getNetwork: () => apiFetch('/monitor/network'),
}

// ============================================================
// 네트워크 API
// ============================================================

export const networkAPI = {
  getInterfaces: () => apiFetch('/network/interfaces'),
  getTraffic: () => apiFetch('/network/traffic'),
  getPackets: () => apiFetch('/network/packets'),
  getConnections: () => apiFetch('/network/connections'),
}

// ============================================================
// WebSocket 관리자
// ============================================================

export class WebSocketManager {
  constructor() {
    this.ws = null
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.listeners = new Set()
    this.statusListeners = new Set()
    this._stopReconnect = false
  }

  /** WebSocket 인증 정보 없이 monitor 엔드포인트 URL을 생성합니다. */
  _buildUrl() {
    return `${WS_BASE_URL}/monitor`
  }

  async connect() {
    // 이미 연결된 경우 중복 연결 방지
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve()
    }
    // 연결 중인 경우도 중복 방지
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      return Promise.resolve()
    }

    let ticketResponse
    try {
      this._stopReconnect = false
      ticketResponse = await authAPI.getWebSocketTicket('monitor')
    } catch (error) {
      this.isConnected = false
      this.notifyStatusChange(false, '인증 티켓 요청 실패')
      throw error
    }

    return new Promise((resolve, reject) => {
      try {
        const url = this._buildUrl()
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          this.ws.send(JSON.stringify({ type: 'authenticate', ticket: ticketResponse.ticket }))
          this.isConnected = true
          this.reconnectAttempts = 0
          console.info('WebSocket 연결 성공')
          this.notifyStatusChange(true)
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            this.notifyListeners(data)
          } catch {
            console.error('WebSocket 메시지 파싱 실패')
          }
        }

        this.ws.onerror = () => {
          console.error('WebSocket 연결 오류')
          this.isConnected = false
          this.notifyStatusChange(false, `연결 에러`)
          reject(new Error('WebSocket 연결 오류'))
        }

        this.ws.onclose = (event) => {
          console.info(`WebSocket 연결 종료 (Code: ${event.code})`)
          this.isConnected = false
          this.notifyStatusChange(false, `연결 종료 (${event.code})`)
          if (!this._stopReconnect) {
            this.attemptReconnect()
          }
        }
      } catch {
        console.error('WebSocket 생성 실패')
        this.isConnected = false
        this.notifyStatusChange(false, '연결 생성 실패')
        reject(new Error('WebSocket 생성 실패'))
      }
    })
  }

  attemptReconnect() {
    if (this._stopReconnect) return

    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`)
      setTimeout(() => {
        if (!this._stopReconnect) {
          this.connect().catch(() => {
            // 자동 재연결 실패 - attemptReconnect에서 다시 시도
          })
        }
      }, this.reconnectDelay)
    } else {
      console.error('WebSocket 재연결 최대 시도 횟수 초과')
      this.notifyStatusChange(false, '연결 실패')
    }
  }

  disconnect() {
    this._stopReconnect = true
    this.reconnectAttempts = 0
    if (this.ws) {
      this.ws.close()
      this.ws = null
      this.isConnected = false
      this.notifyStatusChange(false)
    }
  }

  onData(callback) {
    this.listeners.add(callback)
    return () => {
      this.listeners.delete(callback)
    }
  }

  onStatusChange(callback) {
    this.statusListeners.add(callback)
    return () => {
      this.statusListeners.delete(callback)
    }
  }

  notifyListeners(data) {
    this.listeners.forEach(callback => {
      try {
        callback(data)
      } catch {
        console.error('WebSocket 리스너 실행 오류')
      }
    })
  }

  notifyStatusChange(isConnected, message = '') {
    this.statusListeners.forEach(callback => {
      try {
        callback({ isConnected, message })
      } catch {
        console.error('WebSocket 상태 리스너 실행 오류')
      }
    })
  }

  getStatus() {
    return {
      isConnected: this.isConnected,
      url: this._buildUrl(),
      reconnectAttempts: this.reconnectAttempts
    }
  }
}

// 전역 WebSocket 인스턴스
export const wsManager = new WebSocketManager()
