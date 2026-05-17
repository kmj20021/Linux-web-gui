import { useEffect, useState } from 'react'
import CPUChart from '../components/CPUChart'
import { wsManager } from '../api/client'
import '../styles/Dashboard.css'

/**
 * 대시보드 페이지
 * - WebSocket 연결 상태 모니터링
 * - 실시간 시스템 메트릭 표시
 * - CPU 사용률 선 그래프
 */
function Dashboard() {
  const [metrics, setMetrics] = useState({
    cpu: { total: 0, per_core: [], core_count: 0, load_avg: [0, 0, 0] },
    memory: { total_gb: 0, used_gb: 0, free_gb: 0, usage_pct: 0 },
    top_processes: [],
    timestamp: ''
  })
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // WebSocket 연결은 AuthContext에서 관리하므로 여기서는 호출하지 않음
    // 이미 연결된 경우 즉시 로딩 해제
    setIsLoading(!wsManager.isConnected)

    // 연결 상태 변화 감지 - 연결되면 로딩 해제
    const unsubscribeStatus = wsManager.onStatusChange((newStatus) => {
      if (newStatus.isConnected) {
        setIsLoading(false)
      }
    })

    // WebSocket 데이터 수신
    const unsubscribe = wsManager.onData((data) => {
      if (data.type === 'monitor.snapshot') {
        setMetrics({
          cpu: data.cpu,
          memory: data.memory,
          top_processes: data.top_processes,
          timestamp: data.timestamp
        })
      }
    })

    return () => {
      unsubscribe()
      unsubscribeStatus()
      // 페이지 떠날 때 연결 유지 — AuthContext에서 생명주기 관리
    }
  }, [])

  return (
    <div className="dashboard">
      <div className="page-header">
        <h1>시스템 대시보드</h1>
        <p className="page-subtitle">실시간 시스템 모니터링</p>
      </div>

      {isLoading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>연결 중...</p>
        </div>
      )}

      <div className="dashboard-layout">
        {/* CPU 차트 - 전체 폭 */}
        <div className="dashboard-card cpu-chart-card">
          <CPUChart />
        </div>

        {/* CPU 카드 */}
        <div className="dashboard-card">
          <div className="card-header">CPU</div>
          <div className="card-body">
            <div className="metric-row">
              <span className="metric-label">전체 사용률</span>
              <div className="metric-value-with-bar">
                <span className="value">{metrics.cpu.total.toFixed(1)}%</span>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${metrics.cpu.total}%` }}
                  ></div>
                </div>
              </div>
            </div>
            <div className="metric-row">
              <span className="metric-label">코어 수</span>
              <span className="value">{metrics.cpu.core_count}</span>
            </div>
            <div className="metric-row">
              <span className="metric-label">로드 평균</span>
              <span className="value small">
                {metrics.cpu.load_avg.map(v => v.toFixed(2)).join(' / ')}
              </span>
            </div>
          </div>
        </div>

        {/* 메모리 카드 */}
        <div className="dashboard-card">
          <div className="card-header">메모리</div>
          <div className="card-body">
            <div className="metric-row">
              <span className="metric-label">사용률</span>
              <div className="metric-value-with-bar">
                <span className="value">{metrics.memory.usage_pct.toFixed(1)}%</span>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${metrics.memory.usage_pct}%` }}
                  ></div>
                </div>
              </div>
            </div>
            <div className="metric-row">
              <span className="metric-label">사용 중 / 전체</span>
              <span className="value">
                {metrics.memory.used_gb.toFixed(1)}GB / {metrics.memory.total_gb.toFixed(1)}GB
              </span>
            </div>
            <div className="metric-row">
              <span className="metric-label">여유 메모리</span>
              <span className="value">{metrics.memory.free_gb.toFixed(1)}GB</span>
            </div>
          </div>
        </div>

        {/* 상위 프로세스 카드 */}
        <div className="dashboard-card process-card">
          <div className="card-header">상위 프로세스 (CPU 기준)</div>
          <div className="card-body" style={{ padding: 0 }}>
            {metrics.top_processes.length === 0 ? (
              <p className="no-data">프로세스 데이터 로드 중...</p>
            ) : (
              <table className="process-table">
                <thead>
                  <tr>
                    <th className="col-pid">PID</th>
                    <th className="col-name">프로세스</th>
                    <th className="col-cpu">CPU %</th>
                    <th className="col-mem">MEM %</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.top_processes.map((proc, idx) => (
                    <tr key={idx}>
                      <td className="col-pid">{proc.pid}</td>
                      <td className="col-name" title={proc.name}>{proc.name}</td>
                      <td className="col-cpu">{proc.cpu_pct.toFixed(1)}%</td>
                      <td className="col-mem">{proc.mem_pct.toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* 타임스탬프 카드 */}
        <div className="dashboard-card timestamp-card">
          <div className="card-header">마지막 업데이트</div>
          <div className="card-body">
            {metrics.timestamp ? (
              <>
                <div className="timestamp">
                  {new Date(metrics.timestamp).toLocaleString('ko-KR')}
                </div>
                <div className="timestamp-note">UTC 시간</div>
              </>
            ) : (
              <p className="no-data">업데이트 대기 중...</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
