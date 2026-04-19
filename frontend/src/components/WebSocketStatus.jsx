import { useEffect, useState, useRef } from 'react'
import { wsManager } from '../api/client'
import '../styles/WebSocketStatus.css'

/**
 * WebSocket 연결 상태 표시 위젯
 * - 초록색 (연결됨)
 * - 주황색 (연결 중)
 * - 빨간색 (연결 끊김)
 * @param {boolean} compact - true일 때 topbar 스타일로 표시
 */
function WebSocketStatus({ compact = false }) {
  const [status, setStatus] = useState({
    isConnected: false,
    message: ''
  })
  const [stats, setStats] = useState({
    messagesReceived: 0,
    bytesReceived: 0
  })
  const lastMessageTimeRef = useRef(null)

  useEffect(() => {
    // WebSocket 상태 변화 감지
    const unsubscribe = wsManager.onStatusChange((newStatus) => {
      setStatus(newStatus)
      if (newStatus.isConnected) {
        lastMessageTimeRef.current = Date.now()
      }
    })

    // WebSocket 데이터 수신 감지
    const unsubscribeData = wsManager.onData(() => {
      lastMessageTimeRef.current = Date.now()
      setStats(prev => ({
        ...prev,
        messagesReceived: prev.messagesReceived + 1
      }))
    })

    // 현재 상태 반영
    setStatus({
      isConnected: wsManager.isConnected,
      message: ''
    })
    if (wsManager.isConnected) {
      lastMessageTimeRef.current = Date.now()
    }

    // 10초 이상 메시지를 받지 못하면 연결 끊김으로 표시
    const healthCheck = setInterval(() => {
      if (wsManager.isConnected && lastMessageTimeRef.current) {
        const timeSinceLastMessage = Date.now() - lastMessageTimeRef.current
        if (timeSinceLastMessage > 10000) {
          setStatus({
            isConnected: false,
            message: '응답 없음 (10초 타임아웃)'
          })
        }
      }
    }, 5000)

    return () => {
      unsubscribe()
      unsubscribeData()
      clearInterval(healthCheck)
    }
  }, [])

  const statusClass = status.isConnected ? 'connected' : 'disconnected'
  const statusText = status.isConnected ? '연결됨' : '연결 안 됨'
  const statusIcon = status.isConnected ? '🟢' : '🔴'

  // Compact 모드 (topbar용)
  if (compact) {
    return (
      <div className={`websocket-status ${statusClass} compact`}>
        <span className="status-dot"></span>
        <span className="status-text">{statusIcon} {statusText}</span>
      </div>
    )
  }

  // 일반 모드 (Dashboard 카드용)
  return (
    <div className={`websocket-status ${statusClass}`}>
      <div className="status-header">
        <div className="status-indicator">
          <span className="status-dot"></span>
          <span className="status-label">
            {statusIcon} {statusText}
          </span>
        </div>
        <div className="status-reconnect-info">
          {wsManager.reconnectAttempts > 0 && (
            <span className="reconnect-badge">
              재시도: {wsManager.reconnectAttempts}/{wsManager.maxReconnectAttempts}
            </span>
          )}
        </div>
      </div>

      {status.message && (
        <div className="status-message">
          {status.message}
        </div>
      )}

      <div className="status-stats">
        <div className="stat-item">
          <span className="stat-label">수신 메시지</span>
          <span className="stat-value">{stats.messagesReceived}</span>
        </div>
      </div>

      <div className="status-url">
        <small>Endpoint: {wsManager.url}</small>
      </div>
    </div>
  )
}

export default WebSocketStatus
