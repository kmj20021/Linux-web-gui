import { useState, useEffect } from 'react'
import { Line, Pie } from 'react-chartjs-2'
import Chart from 'chart.js/auto'
import '../styles/Dashboard.css'

function Dashboard() {
  const [systemMetrics, setSystemMetrics] = useState(null)
  const [historyData, setHistoryData] = useState([])
  const [error, setError] = useState(null)

  // 실시간 WebSocket 연결 (나중에 구현)
  useEffect(() => {
    fetchCurrentMetrics()
    const interval = setInterval(fetchCurrentMetrics, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchCurrentMetrics = async () => {
    try {
      // 현재 시스템 메트릭 조회
      const cpuRes = await fetch('/api/monitor/cpu')
      const memRes = await fetch('/api/monitor/memory')
      
      if (!cpuRes.ok || !memRes.ok) throw new Error('API 요청 실패')
      
      const cpuData = await cpuRes.json()
      const memData = await memRes.json()

      setSystemMetrics({
        cpu: cpuData,
        memory: memData,
        timestamp: new Date().toLocaleTimeString()
      })
      
      setError(null)
    } catch (err) {
      setError(err.message)
      console.error('메트릭 조회 실패:', err)
    }
  }

  if (error) {
    return <div className="dashboard error">❌ 오류: {error}</div>
  }

  if (!systemMetrics) {
    return <div className="dashboard loading">로딩 중...</div>
  }

  // CPU 차트 데이터
  const cpuChart = {
    labels: systemMetrics.cpu.cpu_per_core.map((_, i) => `Core ${i}`),
    datasets: [{
      label: 'CPU 사용률 (%)',
      data: systemMetrics.cpu.cpu_per_core,
      backgroundColor: 'rgba(54, 162, 235, 0.5)',
      borderColor: 'rgba(54, 162, 235, 1)',
      borderWidth: 2,
      fill: true,
      tension: 0.3,
    }]
  }

  // 메모리 차트 데이터
  const memoryChart = {
    labels: ['사용 중', '여유', '버퍼/캐시'],
    datasets: [{
      data: [
        systemMetrics.memory.used_gb,
        systemMetrics.memory.free_gb,
        (systemMetrics.memory.buffers_gb + systemMetrics.memory.cached_gb)
      ],
      backgroundColor: [
        'rgba(255, 99, 132, 0.6)',
        'rgba(75, 192, 75, 0.6)',
        'rgba(154, 162, 235, 0.6)',
      ],
      borderColor: [
        'rgba(255, 99, 132, 1)',
        'rgba(75, 192, 75, 1)',
        'rgba(154, 162, 235, 1)',
      ],
      borderWidth: 2,
    }]
  }

  return (
    <div className="dashboard">
      <h1>🖥️ 시스템 모니터링 대시보드</h1>
      
      {/* 요약 정보 */}
      <div className="summary">
        <div className="metric-card cpu">
          <h3>CPU 사용률</h3>
          <p className="value">{systemMetrics.cpu.cpu_total.toFixed(1)}%</p>
          <p className="detail">평균 부하: {systemMetrics.cpu.load_avg[0].toFixed(2)}</p>
        </div>
        
        <div className="metric-card memory">
          <h3>메모리 사용률</h3>
          <p className="value">{systemMetrics.memory.usage_pct.toFixed(1)}%</p>
          <p className="detail">{systemMetrics.memory.used_gb.toFixed(2)}GB / {systemMetrics.memory.total_gb.toFixed(2)}GB</p>
        </div>

        <div className="metric-card timestamp">
          <h3>업데이트 시간</h3>
          <p className="value">{systemMetrics.timestamp}</p>
        </div>
      </div>

      {/* 차트 */}
      <div className="charts">
        <div className="chart-container cpu-chart">
          <h3>CPU 코어별 사용률</h3>
          <Line data={cpuChart} options={{
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
              legend: { position: 'top' }
            },
            scales: {
              y: {
                beginAtZero: true,
                max: 100,
                title: { display: true, text: '사용률 (%)' }
              }
            }
          }} />
        </div>

        <div className="chart-container memory-chart">
          <h3>메모리 분배</h3>
          <Pie data={memoryChart} options={{
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
              legend: { position: 'bottom' }
            }
          }} />
        </div>
      </div>
    </div>
  )
}

export default Dashboard
