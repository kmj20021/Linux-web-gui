import { useEffect, useState, useRef } from 'react'
import { networkAPI } from '../api/client'
import '../styles/Processes.css'
import '../styles/Network.css'

// ── 유틸: bytes를 가독성 있는 단위로 변환 ──────────────────────
function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return '-'
  if (bytes >= 1024 * 1024 * 1024) return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  if (bytes >= 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return bytes + ' B'
}

// ── 유틸: 속도(KB/s) 포맷 ────────────────────────────────────
function formatRate(kbps) {
  if (kbps === null || kbps === undefined) return '-'
  if (kbps >= 1024) return (kbps / 1024).toFixed(2) + ' MB/s'
  return kbps.toFixed(2) + ' KB/s'
}

// ── 유틸: 현재 시각 HH:MM:SS ─────────────────────────────────
function nowTime() {
  return new Date().toLocaleTimeString('ko-KR', { hour12: false })
}

// ── 탭 1: 인터페이스 상태 ────────────────────────────────────
function InterfacesTab() {
  const [interfaces, setInterfaces] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)

  const fetchData = async () => {
    try {
      const data = await networkAPI.getInterfaces()
      setInterfaces(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    intervalRef.current = setInterval(fetchData, 30000)
    return () => clearInterval(intervalRef.current)
  }, [])

  const upCount = interfaces.filter(i => i.status === 'up').length

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>인터페이스 정보 로드 중...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="processes-container">
        <div className="no-data">
          <p>데이터를 불러오지 못했습니다: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="processes-container">
      <div className="info-bar">
        <div className="info-item">
          <span className="info-label">전체 인터페이스</span>
          <span className="info-value">{interfaces.length}</span>
        </div>
        <div className="info-item">
          <span className="info-label">활성 (UP)</span>
          <span className="info-value" style={{ color: '#16a34a' }}>{upCount}</span>
        </div>
        <div className="info-item">
          <span className="info-label">비활성 (DOWN)</span>
          <span className="info-value" style={{ color: '#dc2626' }}>{interfaces.length - upCount}</span>
        </div>
      </div>

      <div className="table-wrapper">
        {interfaces.length === 0 ? (
          <div className="no-data">인터페이스 데이터가 없습니다.</div>
        ) : (
          <table className="processes-table">
            <thead>
              <tr>
                <th>인터페이스</th>
                <th>상태</th>
                <th>IPv4 주소</th>
                <th>MAC 주소</th>
                <th className="mtu-cell">MTU</th>
              </tr>
            </thead>
            <tbody>
              {interfaces.map((iface, idx) => (
                <tr key={idx}>
                  <td className="iface-name-cell">{iface.name}</td>
                  <td>
                    <span className={`status-badge ${iface.status === 'up' ? 'up' : 'down'}`}>
                      {iface.status === 'up' ? 'UP' : 'DOWN'}
                    </span>
                  </td>
                  <td>{iface.ipv4 || '-'}</td>
                  <td className="mac-cell">{iface.mac || '-'}</td>
                  <td className="mtu-cell">{iface.mtu != null ? iface.mtu : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// ── 탭 2: 실시간 트래픽 ──────────────────────────────────────
function TrafficTab() {
  const [traffic, setTraffic] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const intervalRef = useRef(null)

  const fetchData = async () => {
    try {
      const data = await networkAPI.getTraffic()
      setTraffic(data)
      setUpdatedAt(nowTime())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    intervalRef.current = setInterval(fetchData, 3000)
    return () => clearInterval(intervalRef.current)
  }, [])

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>트래픽 데이터 로드 중...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="processes-container">
        <div className="no-data">
          <p>데이터를 불러오지 못했습니다: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="tab-content">
      {updatedAt && (
        <p className="last-updated">마지막 갱신: {updatedAt} (3초마다 자동 갱신)</p>
      )}

      {traffic.length === 0 ? (
        <div className="processes-container">
          <div className="no-data">트래픽 데이터가 없습니다.</div>
        </div>
      ) : (
        <div className="traffic-grid">
          {traffic.map((item, idx) => (
            <div className="traffic-card" key={idx}>
              <div className="traffic-card-header">
                <span className="traffic-card-title">{item.name}</span>
              </div>
              <div className="traffic-card-body">
                <div className="traffic-row">
                  <div className="traffic-direction rx">
                    <span className="traffic-direction-label">수신 (RX)</span>
                    <span className="traffic-bytes">{formatBytes(item.bytes_recv)}</span>
                    <span className="traffic-rate">{formatRate(item.bytes_recv_rate)}</span>
                  </div>
                  <div className="traffic-divider"></div>
                  <div className="traffic-direction tx">
                    <span className="traffic-direction-label">송신 (TX)</span>
                    <span className="traffic-bytes">{formatBytes(item.bytes_sent)}</span>
                    <span className="traffic-rate">{formatRate(item.bytes_sent_rate)}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── 탭 3: 패킷 통계 ─────────────────────────────────────────
function PacketsTab() {
  const [packets, setPackets] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const intervalRef = useRef(null)

  const fetchData = async () => {
    try {
      const data = await networkAPI.getPackets()
      setPackets(data)
      setUpdatedAt(nowTime())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    intervalRef.current = setInterval(fetchData, 3000)
    return () => clearInterval(intervalRef.current)
  }, [])

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>패킷 통계 로드 중...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="processes-container">
        <div className="no-data">
          <p>데이터를 불러오지 못했습니다: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="tab-content">
      {updatedAt && (
        <p className="last-updated">마지막 갱신: {updatedAt} (3초마다 자동 갱신)</p>
      )}

      <div className="processes-container">
        <div className="table-wrapper">
          {packets.length === 0 ? (
            <div className="no-data">패킷 데이터가 없습니다.</div>
          ) : (
            <table className="processes-table">
              <thead>
                <tr>
                  <th>인터페이스</th>
                  <th className="num-cell">수신 패킷</th>
                  <th className="num-cell">송신 패킷</th>
                  <th className="num-cell">수신 오류</th>
                  <th className="num-cell">송신 오류</th>
                  <th className="num-cell">수신 드롭</th>
                  <th className="num-cell">송신 드롭</th>
                </tr>
              </thead>
              <tbody>
                {packets.map((item, idx) => (
                  <tr key={idx}>
                    <td className="iface-name-cell">{item.name}</td>
                    <td className="num-cell">{item.packets_recv?.toLocaleString() ?? '-'}</td>
                    <td className="num-cell">{item.packets_sent?.toLocaleString() ?? '-'}</td>
                    <td className={`num-cell ${item.errin > 0 ? 'error-val' : ''}`}>
                      {item.errin?.toLocaleString() ?? '-'}
                    </td>
                    <td className={`num-cell ${item.errout > 0 ? 'error-val' : ''}`}>
                      {item.errout?.toLocaleString() ?? '-'}
                    </td>
                    <td className={`num-cell ${item.dropin > 0 ? 'drop-val' : ''}`}>
                      {item.dropin?.toLocaleString() ?? '-'}
                    </td>
                    <td className={`num-cell ${item.dropout > 0 ? 'drop-val' : ''}`}>
                      {item.dropout?.toLocaleString() ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

// ── 탭 4: 포트 현황 ──────────────────────────────────────────
function ConnectionsTab() {
  const [connections, setConnections] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [updatedAt, setUpdatedAt] = useState(null)
  const intervalRef = useRef(null)

  const fetchData = async () => {
    try {
      const data = await networkAPI.getConnections()
      setConnections(data)
      setUpdatedAt(nowTime())
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    intervalRef.current = setInterval(fetchData, 10000)
    return () => clearInterval(intervalRef.current)
  }, [])

  function getStatusClass(status) {
    if (!status) return ''
    const s = status.toUpperCase()
    if (s === 'LISTEN') return 'conn-listen'
    if (s === 'ESTABLISHED') return 'conn-established'
    if (s === 'TIME_WAIT' || s === 'CLOSE_WAIT') return 'conn-wait'
    return ''
  }

  if (isLoading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p>포트 현황 로드 중...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="processes-container">
        <div className="no-data">
          <p>데이터를 불러오지 못했습니다: {error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="tab-content">
      {updatedAt && (
        <p className="last-updated">마지막 갱신: {updatedAt} (10초마다 자동 갱신)</p>
      )}

      <div className="processes-container">
        <div className="info-bar">
          <div className="info-item">
            <span className="info-label">전체 연결</span>
            <span className="info-value">{connections.length}</span>
          </div>
          <div className="info-item">
            <span className="info-label">LISTEN</span>
            <span className="info-value" style={{ color: '#16a34a' }}>
              {connections.filter(c => c.status?.toUpperCase() === 'LISTEN').length}
            </span>
          </div>
          <div className="info-item">
            <span className="info-label">ESTABLISHED</span>
            <span className="info-value" style={{ color: '#2563eb' }}>
              {connections.filter(c => c.status?.toUpperCase() === 'ESTABLISHED').length}
            </span>
          </div>
        </div>

        <div className="table-wrapper">
          {connections.length === 0 ? (
            <div className="no-data">포트 데이터가 없습니다.</div>
          ) : (
            <table className="processes-table">
              <thead>
                <tr>
                  <th>프로토콜</th>
                  <th>로컬 주소:포트</th>
                  <th>원격 주소:포트</th>
                  <th>상태</th>
                  <th>프로세스</th>
                </tr>
              </thead>
              <tbody>
                {connections.map((conn, idx) => (
                  <tr key={idx}>
                    <td className="conn-proto-cell">{conn.proto || '-'}</td>
                    <td className="conn-addr-cell">
                      {conn.local_ip && conn.local_port != null
                        ? `${conn.local_ip}:${conn.local_port}`
                        : '-'}
                    </td>
                    <td className="conn-addr-cell">
                      {conn.remote_ip && conn.remote_port != null
                        ? `${conn.remote_ip}:${conn.remote_port}`
                        : '-'}
                    </td>
                    <td>
                      <span className={`status-badge ${getStatusClass(conn.status)}`}>
                        {conn.status || '-'}
                      </span>
                    </td>
                    <td className="conn-process-cell">{conn.process_name || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}

// ── 메인 페이지 ──────────────────────────────────────────────
const TABS = [
  { id: 'interfaces', label: '인터페이스 상태' },
  { id: 'traffic', label: '실시간 트래픽' },
  { id: 'packets', label: '패킷 통계' },
  { id: 'connections', label: '포트 현황' },
]

function NetworkPage() {
  const [activeTab, setActiveTab] = useState('interfaces')

  return (
    <div className="network-page">
      <div className="page-header">
        <h1>네트워크 모니터링</h1>
        <p className="page-subtitle">인터페이스 상태, 실시간 트래픽, 패킷 통계</p>
      </div>

      <nav className="tab-nav">
        {TABS.map(tab => (
          <button
            key={tab.id}
            className={`tab-btn${activeTab === tab.id ? ' active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === 'interfaces' && <InterfacesTab />}
      {activeTab === 'traffic' && <TrafficTab />}
      {activeTab === 'packets' && <PacketsTab />}
      {activeTab === 'connections' && <ConnectionsTab />}
    </div>
  )
}

export default NetworkPage
