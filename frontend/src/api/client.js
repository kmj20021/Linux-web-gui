/**
 * API 클라이언트 및 WebSocket 유틸리티
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'
const _wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_BASE_URL = import.meta.env.VITE_WS_URL || `${_wsProtocol}//${window.location.host}/ws`

// 디버깅 정보 출력
console.log('API 설정:')
console.log(`   API_BASE_URL: ${API_BASE_URL}`)
console.log(`   WS_BASE_URL: ${WS_BASE_URL}`)

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
// 인증 API
// ============================================================

export const authAPI = {
  login: async (username, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!response.ok) {
      const err = new Error(`로그인 실패: ${response.status}`)
      err.status = response.status
      throw err
    }
    return await response.json()
  },

  logout: async (token) => {
    const headers = token
      ? { Authorization: `Bearer ${token}` }
      : getAuthHeaders()
    const response = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers,
    })
    if (!response.ok) {
      const err = new Error(`로그아웃 실패: ${response.status}`)
      err.status = response.status
      throw err
    }
    return await response.json()
  },

  getMe: async (token) => {
    const headers = token
      ? { Authorization: `Bearer ${token}` }
      : getAuthHeaders()
    const response = await fetch(`${API_BASE_URL}/auth/me`, { headers })
    if (!response.ok) {
      const err = new Error(`사용자 정보 조회 실패: ${response.status}`)
      err.status = response.status
      throw err
    }
    return await response.json()
  },

  register: async (username, password, password_confirm) => {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, password_confirm }),
    })
    if (!response.ok) {
      const err_body = await response.json().catch(() => ({}))
      const error = new Error(err_body.detail || '회원가입 실패')
      error.status = response.status
      throw error
    }
    return response.json()
  },
}

// ============================================================
// 일반 API 클라이언트
// ============================================================

export const monitoringAPI = {
  getCPU: async () => {
    const response = await fetch(`${API_BASE_URL}/monitor/cpu`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },

  getMemory: async () => {
    const response = await fetch(`${API_BASE_URL}/monitor/memory`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },

  getProcesses: async () => {
    const response = await fetch(`${API_BASE_URL}/monitor/processes`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },

  getNetwork: async () => {
    const response = await fetch(`${API_BASE_URL}/monitor/network`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  }
}

// ============================================================
// 네트워크 API
// ============================================================

export const networkAPI = {
  getInterfaces: async () => {
    const response = await fetch(`${API_BASE_URL}/network/interfaces`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },
  getTraffic: async () => {
    const response = await fetch(`${API_BASE_URL}/network/traffic`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },
  getPackets: async () => {
    const response = await fetch(`${API_BASE_URL}/network/packets`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },
  getConnections: async () => {
    const response = await fetch(`${API_BASE_URL}/network/connections`, {
      headers: getAuthHeaders(),
    })
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },
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

  /**
   * 연결 시 localStorage에서 토큰을 동적으로 읽어 WebSocket URL을 생성합니다.
   */
  _buildUrl() {
    const token = getAuthToken()
    return token
      ? `${WS_BASE_URL}/monitor?token=${token}`
      : `${WS_BASE_URL}/monitor`
  }

  connect() {
    // 이미 연결된 경우 중복 연결 방지
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      return Promise.resolve()
    }
    // 연결 중인 경우도 중복 방지
    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      try {
        this._stopReconnect = false
        const url = this._buildUrl()
        console.log(`WebSocket 연결 시도: ${url}`)
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          this.isConnected = true
          this.reconnectAttempts = 0
          console.log('WebSocket 연결 성공')
          this.notifyStatusChange(true)
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            this.notifyListeners(data)
          } catch (e) {
            console.error('메시지 파싱 실패:', e)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket 에러:', error)
          this.isConnected = false
          this.notifyStatusChange(false, `연결 에러`)
          reject(error)
        }

        this.ws.onclose = (event) => {
          console.log(`WebSocket 연결 종료 (Code: ${event.code}, Reason: ${event.reason})`)
          this.isConnected = false
          this.notifyStatusChange(false, `연결 종료 (${event.code})`)
          if (!this._stopReconnect) {
            this.attemptReconnect()
          }
        }
      } catch (error) {
        console.error('WebSocket 생성 실패:', error)
        this.isConnected = false
        this.notifyStatusChange(false, error.message)
        reject(error)
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
      } catch (e) {
        console.error('리스너 실행 중 에러:', e)
      }
    })
  }

  notifyStatusChange(isConnected, message = '') {
    this.statusListeners.forEach(callback => {
      try {
        callback({ isConnected, message })
      } catch (e) {
        console.error('상태 변화 리스너 실행 중 에러:', e)
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
