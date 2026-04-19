import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts'
import { wsManager } from '../api/client'
import '../styles/CPUChart.css'

/**
 * 실시간 CPU 사용률 선 그래프
 * - 5초 주기로 업데이트
 * - 최근 12개 데이터 포인트 표시 (60초)
 */
function CPUChart() {
  const [cpuData, setCpuData] = useState([])
  const [stats, setStats] = useState({
    current: 0,
    average: 0,
    max: 0,
    min: 100
  })

  useEffect(() => {
    // WebSocket 데이터 수신
    const unsubscribe = wsManager.onData((data) => {
      if (data.type === 'monitor.snapshot') {
        const timestamp = new Date(data.timestamp)
        const timeStr = timestamp.toLocaleTimeString('ko-KR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })

        const cpuUsage = data.cpu.total

        setCpuData((prevData) => {
          // 최근 12개 데이터만 유지 (60초 = 12 * 5초)
          const newData = [
            ...prevData,
            {
              time: timeStr,
              cpu: parseFloat(cpuUsage.toFixed(1)),
              timestamp: timestamp.getTime()
            }
          ]

          // 12개를 초과하면 가장 오래된 것 제거
          if (newData.length > 12) {
            newData.shift()
          }

          // 통계 계산
          if (newData.length > 0) {
            const cpuValues = newData.map(d => d.cpu)
            const currentCpu = cpuValues[cpuValues.length - 1]
            const avgCpu = (cpuValues.reduce((a, b) => a + b, 0) / cpuValues.length).toFixed(1)
            const maxCpu = Math.max(...cpuValues).toFixed(1)
            const minCpu = Math.min(...cpuValues).toFixed(1)

            setStats({
              current: currentCpu,
              average: parseFloat(avgCpu),
              max: parseFloat(maxCpu),
              min: parseFloat(minCpu)
            })
          }

          return newData
        })
      }
    })

    return unsubscribe
  }, [])

  // 동적 Y축 설정
  const getYAxisDomain = () => {
    if (cpuData.length === 0) return [0, 100]
    const maxValue = Math.max(...cpuData.map(d => d.cpu))
    const minValue = Math.min(...cpuData.map(d => d.cpu))

    // 적당한 여유 공간
    const padding = (maxValue - minValue) * 0.2 || 10
    return [
      Math.max(0, Math.floor(minValue - padding)),
      Math.min(100, Math.ceil(maxValue + padding))
    ]
  }

  const yAxisDomain = getYAxisDomain()

  return (
    <div className="cpu-chart-container">
      <div className="chart-header">
        <h2>📊 실시간 CPU 사용률</h2>
        <div className="update-info">
          🔄 5초 주기 업데이트 | 최근 60초 데이터
        </div>
      </div>

      {/* 통계 정보 */}
      <div className="stats-grid">
        <div className="stat-card current">
          <div className="stat-label">현재</div>
          <div className="stat-value">{stats.current}%</div>
          <div className="stat-icon">⚡</div>
        </div>
        <div className="stat-card average">
          <div className="stat-label">평균</div>
          <div className="stat-value">{stats.average}%</div>
          <div className="stat-icon">📈</div>
        </div>
        <div className="stat-card max">
          <div className="stat-label">최대</div>
          <div className="stat-value">{stats.max}%</div>
          <div className="stat-icon">⬆️</div>
        </div>
        <div className="stat-card min">
          <div className="stat-label">최소</div>
          <div className="stat-value">{stats.min}%</div>
          <div className="stat-icon">⬇️</div>
        </div>
      </div>

      {/* 라인 차트 */}
      <div className="chart-wrapper">
        {cpuData.length === 0 ? (
          <div className="no-data">
            <p>데이터 수집 중...</p>
            <div className="spinner"></div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={cpuData}
              margin={{ top: 5, right: 30, left: 0, bottom: 5 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="#e0e0e0"
                vertical={true}
              />
              <XAxis
                dataKey="time"
                stroke="#7f8c8d"
                className="chart-axis"
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis
                domain={yAxisDomain}
                stroke="#7f8c8d"
                label={{
                  value: 'CPU 사용률 (%)',
                  angle: -90,
                  position: 'insideLeft',
                  className: 'chart-label'
                }}
              />
              <Tooltip
                contentStyle={{
                  background: 'rgba(255, 255, 255, 0.95)',
                  border: '2px solid #3498db',
                  borderRadius: '8px',
                  padding: '10px'
                }}
                formatter={(value) => `${value}%`}
                wrapperClassName="chart-tooltip"
              />
              <Legend
                wrapperStyle={{ fontSize: '13px', paddingTop: '20px' }}
              />
              <ReferenceLine
                y={50}
                stroke="#f39c12"
                strokeDasharray="5 5"
                label={{
                  value: '50% 기준선',
                  position: 'right',
                  fill: '#f39c12',
                  fontSize: 11
                }}
              />
              <Line
                type="monotone"
                dataKey="cpu"
                stroke="#3498db"
                strokeWidth={2.5}
                dot={{
                  fill: '#3498db',
                  r: 4
                }}
                activeDot={{
                  r: 6,
                  fill: '#2980b9'
                }}
                name="CPU 사용률"
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* 상세 정보 */}
      <div className="chart-info">
        <div className="info-item">
          <span className="info-label">📊 데이터 포인트:</span>
          <span className="info-value">{cpuData.length}개</span>
        </div>
        <div className="info-item">
          <span className="info-label">⏱️ 시간 범위:</span>
          <span className="info-value">
            {cpuData.length > 0
              ? `${cpuData[0].time} ~ ${cpuData[cpuData.length - 1].time}`
              : '데이터 없음'}
          </span>
        </div>
        <div className="info-item">
          <span className="info-label">🎯 업데이트 간격:</span>
          <span className="info-value">5초</span>
        </div>
      </div>
    </div>
  )
}

export default CPUChart
