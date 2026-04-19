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
    // WebSocket 연결
    wsManager.connect()
      .then(() => {
        setIsLoading(false)
      })
      .catch(error => {
        console.error('WebSocket 연결 실패:', error)
        setIsLoading(false)
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
      // 페이지 떠날 때 연결 유지 (다른 페이지에서도 필요할 수 있음)
    }
  }, [])

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>📊 시스템 대시보드</h1>
        <p className="dashboard-subtitle">실시간 시스템 모니터링</p>
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
          <h2>🖥️ CPU</h2>
          <div className="card-content">
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
          <h2>🧠 메모리</h2>
          <div className="card-content">
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
          <h2>⚙️ 상위 프로세스 (CPU 기준)</h2>
          <div className="card-content">
            {metrics.top_processes.length === 0 ? (
              <p className="no-data">프로세스 데이터 로드 중...</p>
            ) : (
              <div className="process-table">
                <div className="table-header">
                  <div className="col-pid">PID</div>
                  <div className="col-name">프로세스</div>
                  <div className="col-cpu">CPU %</div>
                  <div className="col-mem">MEM %</div>
                </div>
                {metrics.top_processes.map((proc, idx) => (
                  <div key={idx} className="table-row">
                    <div className="col-pid">{proc.pid}</div>
                    <div className="col-name" title={proc.name}>
                      {proc.name}
                    </div>
                    <div className="col-cpu">{proc.cpu_pct.toFixed(1)}%</div>
                    <div className="col-mem">{proc.mem_pct.toFixed(1)}%</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 타임스탐프 카드 */}
        <div className="dashboard-card timestamp-card">
          <h2>🕐 마지막 업데이트</h2>
          <div className="card-content">
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
