import { useState, useEffect, useCallback } from 'react'
import { getAuthHeaders } from '../api/client'
import '../styles/Processes.css'
import '../styles/Audit.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'
const PAGE_LIMIT = 20

async function fetchAuditLogs(page, limit) {
  const res = await fetch(
    `${API_BASE_URL}/admin/audit?page=${page}&limit=${limit}`,
    { headers: getAuthHeaders() }
  )
  if (!res.ok) throw new Error(`감사 로그 조회 실패: ${res.status}`)
  return res.json()
}

function AuditPage() {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadLogs = useCallback(async (pageNum) => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchAuditLogs(pageNum, PAGE_LIMIT)
      // 백엔드가 배열 또는 {items, total} 형태로 올 수 있음
      if (Array.isArray(data)) {
        setLogs(data)
        setTotal(data.length)
      } else {
        setLogs(data.items ?? data)
        setTotal(data.total ?? (data.items ?? data).length)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadLogs(page)
  }, [loadLogs, page])

  const totalPages = Math.max(1, Math.ceil(total / PAGE_LIMIT))

  const handlePrev = () => {
    if (page > 1) setPage(p => p - 1)
  }

  const handleNext = () => {
    if (page < totalPages) setPage(p => p + 1)
  }

  return (
    <div className="processes-page">
      <div className="page-header">
        <h1>감사 로그</h1>
        <p className="page-subtitle">로그인 이력을 조회합니다.</p>
      </div>

      <div className="processes-container">
        {loading && (
          <div className="loading">
            <div className="spinner" />
            <span>불러오는 중...</span>
          </div>
        )}

        {!loading && error && (
          <div className="no-data">
            오류: {error}
            <button
              className="audit-refresh-btn"
              onClick={() => loadLogs(page)}
              style={{ marginLeft: '12px' }}
            >
              다시 시도
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            <div className="table-wrapper">
              <table className="processes-table">
                <thead>
                  <tr>
                    <th>사용자명</th>
                    <th>역할</th>
                    <th>IP 주소</th>
                    <th>일시</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="no-data">로그인 이력이 없습니다.</td>
                    </tr>
                  ) : (
                    logs.map(log => (
                      <tr key={log.id}>
                        <td style={{ fontWeight: 500 }}>{log.username}</td>
                        <td>
                          <span className={`audit-role-badge audit-role-${log.role}`}>{log.role}</span>
                        </td>
                        <td style={{ fontFamily: 'monospace', color: '#4b5563' }}>{log.ip_address || '-'}</td>
                        <td style={{ color: '#6b7280', fontSize: '13px' }}>
                          {log.created_at
                            ? new Date(log.created_at).toLocaleString('ko-KR')
                            : '-'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="audit-pagination">
                <button
                  className="audit-page-btn"
                  onClick={handlePrev}
                  disabled={page === 1}
                >
                  이전
                </button>
                <span className="audit-page-info">{page} / {totalPages}</span>
                <button
                  className="audit-page-btn"
                  onClick={handleNext}
                  disabled={page === totalPages}
                >
                  다음
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default AuditPage
