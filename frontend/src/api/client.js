/**
 * API 클라이언트 및 WebSocket 유틸리티
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
const AUTH_TOKEN = import.meta.env.VITE_AUTH_TOKEN || 'test_token_123'

// 디버깅 정보 출력
console.log('🔧 API 설정:')
console.log(`   API_BASE_URL: ${API_BASE_URL}`)
console.log(`   WS_BASE_URL: ${WS_BASE_URL}`)
console.log(`   AUTH_TOKEN: ${AUTH_TOKEN ? '설정됨' : '없음'}`)

// ============================================================
// 일반 API 클라이언트
// ============================================================

export const monitoringAPI = {
  getCPU: async () => {
    const response = await fetch(`${API_BASE_URL}/monitor/cpu`)
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },

  getMemory: async () => {
    const response = await fetch(`${API_BASE_URL}/monitor/memory`)
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },

  getProcesses: async () => {
    const response = await fetch(`${API_BASE_URL}/monitor/processes`)
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  },

  getNetwork: async () => {
    const response = await fetch(`${API_BASE_URL}/monitor/network`)
    if (!response.ok) throw new Error(`API 실패: ${response.status}`)
    return await response.json()
  }
}

// ============================================================
// WebSocket 관리자
// ============================================================

export class WebSocketManager {
  constructor() {
    this.ws = null
    this.url = `${WS_BASE_URL}/monitor?token=${AUTH_TOKEN}`
    this.isConnected = false
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 3000
    this.listeners = new Set()
    this.statusListeners = new Set()
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        console.log(`🔗 WebSocket 연결 시도: ${this.url}`)
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          this.isConnected = true
          this.reconnectAttempts = 0
          console.log('✅ WebSocket 연결 성공')
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
          console.error('❌ WebSocket 에러:', error)
          console.error('   WebSocket 상태:', this.ws?.readyState)
          console.error('   상세:', error.message)
          this.isConnected = false
          this.notifyStatusChange(false, `연결 에러: ${error.message}`)
          reject(error)
        }

        this.ws.onclose = (event) => {
          console.log(`🔌 WebSocket 연결 종료 (Code: ${event.code}, Reason: ${event.reason})`)
          this.isConnected = false
          this.notifyStatusChange(false, `연결 종료 (${event.code})`)
          this.attemptReconnect()
        }
      } catch (error) {
        console.error('❌ WebSocket 생성 실패:', error)
        this.isConnected = false
        this.notifyStatusChange(false, error.message)
        reject(error)
      }
    })
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      console.log(`재연결 시도 ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`)
      setTimeout(() => {
        this.connect().catch(() => {
          // 자동 재연결 실패 - attemptReconnect에서 다시 시도
        })
      }, this.reconnectDelay)
    } else {
      console.error('WebSocket 재연결 최대 시도 횟수 초과')
      this.notifyStatusChange(false, '연결 실패')
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
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
      url: this.url,
      reconnectAttempts: this.reconnectAttempts
    }
  }
}

// 전역 WebSocket 인스턴스
export const wsManager = new WebSocketManager()
