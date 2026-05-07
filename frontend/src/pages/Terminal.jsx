import { useState, useRef, useCallback } from 'react'
import TerminalComponent from '../components/Terminal'
import FileExplorer from '../components/FileExplorer'
import { useAuth } from '../context/AuthContext'
import '../styles/Terminal.css'

function TerminalPage() {
  const { user: authUser } = useAuth()
  const [sessionId, setSessionId] = useState(null)
  const [cwd, setCwd] = useState('/')
  const [currentUser, setCurrentUser] = useState('')
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [connected, setConnected] = useState(false)
  // true가 되면 "한 번이라도 연결됐었음"을 기억 → 재연결 버튼 표시 조건으로 사용
  const [wasEverConnected, setWasEverConnected] = useState(false)
  const [termKey, setTermKey] = useState(0)
  const terminalRef = useRef(null)

  const handleSessionId = useCallback((id) => setSessionId(id), [])

  const handleCwdChange = useCallback((newCwd) => {
    setCwd(newCwd)
    setRefreshTrigger(prev => prev + 1)
  }, [])

  const handleUserChange = useCallback((username) => setCurrentUser(username), [])

  // 파일탐색기 폴더 클릭 → cd 명령어를 터미널에 에코하며 전송
  const handleNavigate = useCallback((path) => {
    if (terminalRef.current) {
      terminalRef.current.sendCommand(`cd "${path}"`)
    }
  }, [])

  // 파일탐색기 파일 클릭 → cat 명령어 전송
  const handleFileClick = useCallback((path) => {
    if (terminalRef.current) {
      terminalRef.current.sendCommand(`cat "${path}"`)
    }
  }, [])

  const handleRefresh = useCallback(() => setRefreshTrigger(prev => prev + 1), [])

  const handleConnected = useCallback((isConnected) => {
    setConnected(isConnected)
    if (isConnected) {
      setWasEverConnected(true)
    } else {
      setSessionId(null)
    }
  }, [])

  // 재연결: key 변경으로 Terminal 컴포넌트 완전 재마운트
  const handleReconnect = useCallback(() => {
    setSessionId(null)
    setConnected(false)
    setCwd('/')
    setCurrentUser('')
    setTermKey(prev => prev + 1)
  }, [])

  const dotClass = connected
    ? 'terminal-status-dot'
    : wasEverConnected
      ? 'terminal-status-dot disconnected'
      : 'terminal-status-dot connecting'

  const statusText = connected ? '연결됨' : wasEverConnected ? '연결 끊김' : '연결 중...'
  const showReconnect = !connected && wasEverConnected

  return (
    <div className="terminal-page">
      <div className="terminal-statusbar">
        <div className="terminal-statusbar-left">
          <span className="terminal-user-info">
            {(currentUser || authUser?.username)
              ? `${currentUser || authUser?.username}@linux`
              : 'linux'}
          </span>
          <span className="terminal-cwd">{cwd || '/'}</span>
        </div>
        <div className="terminal-statusbar-right">
          {sessionId && (
            <span className="terminal-session-id">{sessionId}</span>
          )}
          <div className="terminal-status-indicator">
            <span className={dotClass} />
            <span>{statusText}</span>
          </div>
          {showReconnect && (
            <button
              className="terminal-reconnect-btn"
              onClick={handleReconnect}
              title="터미널 재연결"
            >
              재연결
            </button>
          )}
        </div>
      </div>

      <div className="terminal-split">
        <div className="file-explorer-panel">
          <div className="file-explorer-header">
            <span className="file-explorer-header-title">파일 탐색기</span>
            <button
              className="file-explorer-refresh-btn"
              onClick={handleRefresh}
              title="새로고침"
              aria-label="파일탐색기 새로고침"
            >
              <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                <path
                  d="M12 7A5 5 0 1 1 7 2a5 5 0 0 1 3.54 1.46"
                  stroke="currentColor"
                  strokeWidth="1.3"
                  strokeLinecap="round"
                  fill="none"
                />
                <path
                  d="M12 2v3.5H8.5"
                  stroke="currentColor"
                  strokeWidth="1.3"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              </svg>
            </button>
          </div>
          <FileExplorer
            sessionId={sessionId}
            currentCwd={cwd}
            onNavigate={handleNavigate}
            onFileClick={handleFileClick}
            refreshTrigger={refreshTrigger}
          />
        </div>

        <div className="terminal-panel">
          <div className="terminal-xterm-wrapper">
            <TerminalComponent
              key={termKey}
              ref={terminalRef}
              onSessionId={handleSessionId}
              onCwdChange={handleCwdChange}
              onUserChange={handleUserChange}
              onConnected={handleConnected}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default TerminalPage
