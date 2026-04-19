import { useEffect, useState } from 'react'
import { wsManager } from '../api/client'
import '../styles/Processes.css'

function ProcessesPage() {
  const [processes, setProcesses] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [sortBy, setSortBy] = useState('cpu') // 'cpu', 'memory', 'pid', 'name'
  const [sortOrder, setSortOrder] = useState('desc') // 'asc', 'desc'

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
      if (data.type === 'monitor.snapshot' && data.top_processes) {
        setProcesses(data.top_processes)
      }
    })

    return () => {
      unsubscribe()
    }
  }, [])

  // 정렬 함수
  const getSortedProcesses = () => {
    const sorted = [...processes].sort((a, b) => {
      let aVal, bVal

      switch (sortBy) {
        case 'cpu':
          aVal = a.cpu_pct
          bVal = b.cpu_pct
          break
        case 'memory':
          aVal = a.mem_pct
          bVal = b.mem_pct
          break
        case 'pid':
          aVal = a.pid
          bVal = b.pid
          break
        case 'name':
          aVal = a.name.toLowerCase()
          bVal = b.name.toLowerCase()
          break
        default:
          return 0
      }

      if (sortOrder === 'asc') {
        return aVal < bVal ? -1 : aVal > bVal ? 1 : 0
      } else {
        return aVal > bVal ? -1 : aVal < bVal ? 1 : 0
      }
    })

    return sorted
  }

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
  }

  const sortedProcesses = getSortedProcesses()

  return (
    <div className="processes-page">
      <div className="page-header">
        <h1>⚙️ 프로세스 모니터링</h1>
        <p className="page-subtitle">상위 프로세스 목록 (PID·CPU·메모리 사용률)</p>
      </div>

      {isLoading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>데이터 로드 중...</p>
        </div>
      )}

      <div className="processes-container">
        <div className="info-bar">
          <div className="info-item">
            <span className="info-label">총 프로세스</span>
            <span className="info-value">{processes.length}</span>
          </div>
        </div>

        <div className="table-wrapper">
          {processes.length === 0 ? (
            <div className="no-data">
              <p>프로세스 데이터를 받는 중입니다...</p>
            </div>
          ) : (
            <table className="processes-table">
              <thead>
                <tr>
                  <th 
                    className={`sortable ${sortBy === 'pid' ? 'active' : ''}`}
                    onClick={() => handleSort('pid')}
                  >
                    PID {sortBy === 'pid' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    className={`sortable ${sortBy === 'name' ? 'active' : ''}`}
                    onClick={() => handleSort('name')}
                  >
                    프로세스명 {sortBy === 'name' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    className={`sortable cpu-col ${sortBy === 'cpu' ? 'active' : ''}`}
                    onClick={() => handleSort('cpu')}
                  >
                    CPU % {sortBy === 'cpu' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th 
                    className={`sortable mem-col ${sortBy === 'memory' ? 'active' : ''}`}
                    onClick={() => handleSort('memory')}
                  >
                    메모리 % {sortBy === 'memory' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedProcesses.map((proc, idx) => (
                  <tr key={idx} className={`process-row ${proc.cpu_pct > 50 ? 'high-cpu' : ''} ${proc.mem_pct > 50 ? 'high-mem' : ''}`}>
                    <td className="pid-cell">{proc.pid}</td>
                    <td className="name-cell" title={proc.name}>{proc.name}</td>
                    <td className="cpu-cell">
                      <div className="cell-content">
                        <span className="value">{proc.cpu_pct.toFixed(1)}%</span>
                        <div className="bar-bg">
                          <div 
                            className="bar-fill cpu-bar"
                            style={{ width: `${Math.min(proc.cpu_pct, 100)}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>
                    <td className="mem-cell">
                      <div className="cell-content">
                        <span className="value">{proc.mem_pct.toFixed(1)}%</span>
                        <div className="bar-bg">
                          <div 
                            className="bar-fill mem-bar"
                            style={{ width: `${Math.min(proc.mem_pct, 100)}%` }}
                          ></div>
                        </div>
                      </div>
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

export default ProcessesPage
