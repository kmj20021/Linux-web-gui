import { useState, useRef, useEffect, useCallback } from 'react'
import '../styles/NetworkDiagnostics.css'

// ============================================================
// 상수
// ============================================================
const TOOLS = [
  {
    id: 'ping',
    label: 'Ping',
    cmd: 'ping',
    description: '특정 호스트에 ICMP 패킷을 보내 응답 시간을 측정합니다.',
    usage: 'ping -c <count> <host>',
  },
  {
    id: 'traceroute',
    label: '경로 추적',
    cmd: 'traceroute',
    description: '패킷이 목적지까지 거치는 네트워크 경로를 추적합니다.',
    usage: 'traceroute <host>',
  },
  {
    id: 'ss',
    label: '포트/소켓',
    cmd: 'ss',
    description: '시스템에서 열려 있는 포트와 소켓 연결 상태를 표시합니다.',
    usage: 'ss -tuln',
  },
  {
    id: 'nslookup',
    label: 'DNS 조회',
    cmd: 'nslookup',
    description: '도메인 이름의 IP 주소와 DNS 레코드를 조회합니다.',
    usage: 'nslookup <domain>',
  },
  {
    id: 'curl',
    label: 'HTTP 테스트',
    cmd: 'curl',
    description: 'HTTP 요청을 보내 서버 응답 헤더와 상태 코드를 확인합니다.',
    usage: 'curl -I <url>',
  },
]

// ============================================================
// 유틸리티
// ============================================================
function now() {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

// ============================================================
// 시뮬레이션 함수들
// ============================================================
function simulatePing(host, count) {
  const ip = '142.250.196.142'
  const lines = [`PING ${host} (${ip}): 56 data bytes`]
  for (let i = 0; i < count; i++) {
    const ms = (10 + Math.random() * 15).toFixed(1)
    lines.push(`64 bytes from ${ip}: icmp_seq=${i} ttl=117 time=${ms} ms`)
  }
  lines.push(`--- ${host} ping statistics ---`)
  lines.push(`${count} packets transmitted, ${count} received, 0% packet loss`)
  return lines
}

function simulateTraceroute(host) {
  return [
    `traceroute to ${host} (142.250.196.142), 30 hops max, 60 byte packets`,
    ` 1  _gateway (192.168.1.1)  0.543 ms  0.512 ms  0.489 ms`,
    ` 2  10.0.0.1 (10.0.0.1)  1.234 ms  1.198 ms  1.267 ms`,
    ` 3  * * *`,
    ` 4  72.14.215.165 (72.14.215.165)  8.765 ms  8.712 ms  8.698 ms`,
    ` 5  ${host} (142.250.196.142)  12.345 ms  12.312 ms  12.298 ms`,
  ]
}

function simulateSS(opts) {
  const rows = [
    'Netid  State    Recv-Q  Send-Q  Local Address:Port    Peer Address:Port',
    'tcp    LISTEN   0       128     0.0.0.0:22            0.0.0.0:*',
    'tcp    LISTEN   0       128     0.0.0.0:80            0.0.0.0:*',
    'tcp    LISTEN   0       128     0.0.0.0:8000          0.0.0.0:*',
    'tcp    LISTEN   0       128     0.0.0.0:443           0.0.0.0:*',
    'tcp    ESTAB    0       0       192.168.1.100:22      192.168.1.200:54321',
    'udp    UNCONN   0       0       0.0.0.0:68            0.0.0.0:*',
  ]
  if (opts.l) return rows.filter(r => r.includes('LISTEN') || r.includes('UNCONN') || r.includes('Netid'))
  return rows
}

function simulateNslookup(domain) {
  return [
    `Server:    8.8.8.8`,
    `Address:   8.8.8.8#53`,
    ``,
    `Non-authoritative answer:`,
    `Name:    ${domain}`,
    `Address: 142.250.196.142`,
    `Name:    ${domain}`,
    `Address: 2404:6800:4004:81b::200e`,
  ]
}

function simulateCurl(url, opt) {
  const headers = [
    `HTTP/2 200`,
    `content-type: text/html; charset=utf-8`,
    `date: ${new Date().toUTCString()}`,
    `server: nginx`,
    `x-content-type-options: nosniff`,
    ``,
    `* Connection to ${url} left intact`,
  ]
  if (opt === '-v') {
    return [
      `*   Trying 142.250.196.142:80...`,
      `* Connected to ${url} (142.250.196.142) port 80 (#0)`,
      `> GET / HTTP/1.1`,
      `> Host: ${url}`,
      `> User-Agent: curl/7.81.0`,
      `>`,
      ...headers,
    ]
  }
  return headers
}

// ============================================================
// SVG 아이콘
// ============================================================
function ToolIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
      <circle cx="5.5" cy="5.5" r="3.5" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M8.5 8.5L12 12" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    </svg>
  )
}

function EmptyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7"/>
      <path d="M21 21l-4-4"/>
      <path d="M8 11h6M11 8v6" opacity="0.5"/>
    </svg>
  )
}

// ============================================================
// 메인 컴포넌트
// ============================================================
function NetworkDiagnostics() {
  const [selectedTool, setSelectedTool] = useState(null)
  const [results, setResults] = useState({})
  const [cmdLog, setCmdLog] = useState([
    { id: Date.now(), time: now(), type: 'comment', text: '# 네트워크 진단 도구 시작' },
  ])
  const [modal, setModal] = useState(null)

  const logBodyRef = useRef(null)

  useEffect(() => {
    if (logBodyRef.current) {
      logBodyRef.current.scrollTop = logBodyRef.current.scrollHeight
    }
  }, [cmdLog])

  const addLog = useCallback((text, type = 'cmd') => {
    setCmdLog(prev => {
      const next = [...prev, { id: Date.now() + Math.random(), time: now(), type, text }]
      return next.length > 50 ? next.slice(next.length - 50) : next
    })
  }, [])

  const tool = TOOLS.find(t => t.id === selectedTool)

  function handleRun(toolId, cmdStr, lines) {
    addLog(cmdStr)
    setResults(prev => ({ ...prev, [toolId]: lines }))
    setModal(null)
  }

  function handleClearResult() {
    if (!selectedTool) return
    setResults(prev => {
      const next = { ...prev }
      delete next[selectedTool]
      return next
    })
  }

  // ============================================================
  // 렌더링
  // ============================================================
  return (
    <div className="nd-page">
      {/* 상단 툴바 */}
      <div className="nd-toolbar">
        <span className="nd-toolbar-title">네트워크 진단</span>
        <div className="nd-toolbar-divider" />

        <button
          className="nd-btn primary"
          disabled={!selectedTool}
          onClick={() => selectedTool && setModal(selectedTool)}
        >
          <span className="nd-btn-label">실행</span>
          {tool && <span className="nd-btn-cmd">{tool.cmd}</span>}
        </button>

        <button
          className="nd-btn warning"
          disabled={!selectedTool}
          onClick={handleClearResult}
        >
          <span className="nd-btn-label">결과 지우기</span>
        </button>

        <div className="nd-toolbar-divider" />

        <button
          className="nd-btn"
          onClick={() => setCmdLog([{ id: Date.now(), time: now(), type: 'comment', text: '# 로그 지움' }])}
        >
          <span className="nd-btn-label">로그 지우기</span>
        </button>
      </div>

      {/* 메인 영역 */}
      <div className="nd-main">
        {/* 좌측 목록 패널 */}
        <div className="nd-list-panel">
          <div className="nd-list-panel-header">진단 도구</div>
          <div className="nd-list-body">
            {TOOLS.map(t => (
              <div
                key={t.id}
                className={`nd-list-item${selectedTool === t.id ? ' selected' : ''}`}
                onClick={() => setSelectedTool(t.id)}
              >
                <span className="nd-list-item-icon"><ToolIcon /></span>
                <span className="nd-list-item-name">{t.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 우측 상세 패널 */}
        <div className="nd-detail-panel">
          {!selectedTool && (
            <div className="nd-detail-empty">
              <div className="nd-detail-empty-icon"><EmptyIcon /></div>
              <span>도구를 선택하세요</span>
            </div>
          )}

          {tool && (
            <div className="nd-detail-section">
              <div className="nd-detail-tool-name">{tool.label}</div>
              <div className="nd-detail-cmd-badge">{tool.cmd}</div>
              <div className="nd-detail-description">{tool.description}</div>
              <div className="nd-detail-section-title">사용법</div>
              <div className="nd-tool-usage">{tool.usage}</div>

              {results[selectedTool] && (
                <>
                  <div className="nd-detail-section-title" style={{ marginTop: '16px' }}>실행 결과</div>
                  <div className="nd-result-output">
                    {results[selectedTool].join('\n')}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 하단 커맨드 로그 */}
      <div className="nd-log-panel">
        <div className="nd-log-header">
          <span className="nd-log-header-title">커맨드 로그</span>
          <button
            className="nd-log-clear-btn"
            onClick={() => setCmdLog([{ id: Date.now(), time: now(), type: 'comment', text: '# 로그 지움' }])}
          >
            지우기
          </button>
        </div>
        <div className="nd-log-body" ref={logBodyRef}>
          {cmdLog.map(entry => (
            <div key={entry.id} className="nd-log-entry">
              <span className="nd-log-time">{entry.time}</span>
              {entry.type === 'comment' ? (
                <span className="nd-log-comment">{entry.text}</span>
              ) : (
                <>
                  <span className="nd-log-prompt">$</span>
                  <span className="nd-log-cmd">{entry.text}</span>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 모달들 */}
      {modal === 'ping' && (
        <PingModal onRun={handleRun} onClose={() => setModal(null)} />
      )}
      {modal === 'traceroute' && (
        <TracerouteModal onRun={handleRun} onClose={() => setModal(null)} />
      )}
      {modal === 'ss' && (
        <SSModal onRun={handleRun} onClose={() => setModal(null)} />
      )}
      {modal === 'nslookup' && (
        <NslookupModal onRun={handleRun} onClose={() => setModal(null)} />
      )}
      {modal === 'curl' && (
        <CurlModal onRun={handleRun} onClose={() => setModal(null)} />
      )}
    </div>
  )
}

// ============================================================
// Ping 모달
// ============================================================
function PingModal({ onRun, onClose }) {
  const [host, setHost] = useState('google.com')
  const [count, setCount] = useState(4)

  const cmdStr = `ping -c ${count} ${host || '<host>'}`

  function handleSubmit() {
    if (!host.trim()) return
    onRun('ping', cmdStr, simulatePing(host.trim(), Number(count)))
  }

  return (
    <div className="nd-modal-overlay" onClick={onClose}>
      <div className="nd-modal" onClick={e => e.stopPropagation()}>
        <div className="nd-modal-header">
          <div className="nd-modal-title">
            Ping
            <span className="nd-modal-cmd-badge">ping</span>
          </div>
          <button className="nd-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="nd-modal-body">
          <div className="nd-cmd-preview">실행될 명령어: {cmdStr}</div>

          <div className="nd-modal-field">
            <label className="nd-modal-label">호스트</label>
            <input
              className="nd-modal-input"
              value={host}
              onChange={e => setHost(e.target.value)}
              placeholder="예: google.com"
              autoFocus
            />
          </div>

          <div className="nd-modal-field">
            <label className="nd-modal-label">패킷 수</label>
            <select
              className="nd-modal-select"
              value={count}
              onChange={e => setCount(e.target.value)}
            >
              {[1, 2, 4, 8, 16].map(n => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="nd-modal-footer">
          <button className="nd-action-btn cancel" onClick={onClose}>취소</button>
          <button className="nd-action-btn confirm" onClick={handleSubmit}>실행</button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Traceroute 모달
// ============================================================
function TracerouteModal({ onRun, onClose }) {
  const [host, setHost] = useState('google.com')

  const cmdStr = `traceroute ${host || '<host>'}`

  function handleSubmit() {
    if (!host.trim()) return
    onRun('traceroute', cmdStr, simulateTraceroute(host.trim()))
  }

  return (
    <div className="nd-modal-overlay" onClick={onClose}>
      <div className="nd-modal" onClick={e => e.stopPropagation()}>
        <div className="nd-modal-header">
          <div className="nd-modal-title">
            경로 추적
            <span className="nd-modal-cmd-badge">traceroute</span>
          </div>
          <button className="nd-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="nd-modal-body">
          <div className="nd-cmd-preview">실행될 명령어: {cmdStr}</div>

          <div className="nd-modal-field">
            <label className="nd-modal-label">호스트</label>
            <input
              className="nd-modal-input"
              value={host}
              onChange={e => setHost(e.target.value)}
              placeholder="예: google.com"
              autoFocus
            />
          </div>
        </div>
        <div className="nd-modal-footer">
          <button className="nd-action-btn cancel" onClick={onClose}>취소</button>
          <button className="nd-action-btn confirm" onClick={handleSubmit}>실행</button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// SS 모달
// ============================================================
function SSModal({ onRun, onClose }) {
  const [opts, setOpts] = useState({ t: true, u: true, l: true, n: true })

  const flags = [
    opts.t ? '-t' : '',
    opts.u ? '-u' : '',
    opts.l ? '-l' : '',
    opts.n ? '-n' : '',
  ].filter(Boolean).join('')

  const cmdStr = `ss ${flags || '-tuln'}`

  function toggleOpt(key) {
    setOpts(prev => ({ ...prev, [key]: !prev[key] }))
  }

  function handleSubmit() {
    onRun('ss', cmdStr, simulateSS(opts))
  }

  return (
    <div className="nd-modal-overlay" onClick={onClose}>
      <div className="nd-modal" onClick={e => e.stopPropagation()}>
        <div className="nd-modal-header">
          <div className="nd-modal-title">
            포트/소켓
            <span className="nd-modal-cmd-badge">ss</span>
          </div>
          <button className="nd-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="nd-modal-body">
          <div className="nd-cmd-preview">실행될 명령어: {cmdStr}</div>

          <div className="nd-modal-field">
            <label className="nd-modal-label">옵션</label>
            <div className="nd-checkbox-group">
              {[
                { key: 't', desc: '-t  TCP' },
                { key: 'u', desc: '-u  UDP' },
                { key: 'l', desc: '-l  리슨만' },
                { key: 'n', desc: '-n  숫자 형식' },
              ].map(({ key, desc }) => (
                <label key={key} className="nd-checkbox-item">
                  <input
                    type="checkbox"
                    checked={opts[key]}
                    onChange={() => toggleOpt(key)}
                  />
                  <span>{desc}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className="nd-modal-footer">
          <button className="nd-action-btn cancel" onClick={onClose}>취소</button>
          <button className="nd-action-btn confirm" onClick={handleSubmit}>실행</button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Nslookup 모달
// ============================================================
function NslookupModal({ onRun, onClose }) {
  const [domain, setDomain] = useState('google.com')

  const cmdStr = `nslookup ${domain || '<domain>'}`

  function handleSubmit() {
    if (!domain.trim()) return
    onRun('nslookup', cmdStr, simulateNslookup(domain.trim()))
  }

  return (
    <div className="nd-modal-overlay" onClick={onClose}>
      <div className="nd-modal" onClick={e => e.stopPropagation()}>
        <div className="nd-modal-header">
          <div className="nd-modal-title">
            DNS 조회
            <span className="nd-modal-cmd-badge">nslookup</span>
          </div>
          <button className="nd-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="nd-modal-body">
          <div className="nd-cmd-preview">실행될 명령어: {cmdStr}</div>

          <div className="nd-modal-field">
            <label className="nd-modal-label">도메인</label>
            <input
              className="nd-modal-input"
              value={domain}
              onChange={e => setDomain(e.target.value)}
              placeholder="예: google.com"
              autoFocus
            />
          </div>
        </div>
        <div className="nd-modal-footer">
          <button className="nd-action-btn cancel" onClick={onClose}>취소</button>
          <button className="nd-action-btn confirm" onClick={handleSubmit}>실행</button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Curl 모달
// ============================================================
function CurlModal({ onRun, onClose }) {
  const [url, setUrl] = useState('google.com')
  const [opt, setOpt] = useState('-I')

  const cmdStr = `curl ${opt} ${url || '<url>'}`

  function handleSubmit() {
    if (!url.trim()) return
    onRun('curl', cmdStr, simulateCurl(url.trim(), opt))
  }

  return (
    <div className="nd-modal-overlay" onClick={onClose}>
      <div className="nd-modal" onClick={e => e.stopPropagation()}>
        <div className="nd-modal-header">
          <div className="nd-modal-title">
            HTTP 테스트
            <span className="nd-modal-cmd-badge">curl</span>
          </div>
          <button className="nd-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="nd-modal-body">
          <div className="nd-cmd-preview">실행될 명령어: {cmdStr}</div>

          <div className="nd-modal-field">
            <label className="nd-modal-label">URL</label>
            <input
              className="nd-modal-input"
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="예: google.com"
              autoFocus
            />
          </div>

          <div className="nd-modal-field">
            <label className="nd-modal-label">옵션</label>
            <select
              className="nd-modal-select"
              value={opt}
              onChange={e => setOpt(e.target.value)}
            >
              <option value="-I">-I  헤더만</option>
              <option value="-v">-v  상세</option>
              <option value="-L">-L  리다이렉트 따라가기</option>
            </select>
          </div>
        </div>
        <div className="nd-modal-footer">
          <button className="nd-action-btn cancel" onClick={onClose}>취소</button>
          <button className="nd-action-btn confirm" onClick={handleSubmit}>실행</button>
        </div>
      </div>
    </div>
  )
}

export default NetworkDiagnostics
