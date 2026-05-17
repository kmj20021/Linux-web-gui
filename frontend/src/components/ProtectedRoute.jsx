import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import '../styles/Login.css'
import '../styles/ProtectedRoute.css'

function ProtectedRoute({ children, requiredRole }) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRole && user?.role !== requiredRole) {
    return (
      <div className="forbidden-page">
        <div className="forbidden-card">
          <div className="forbidden-icon">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="20" cy="20" r="18" stroke="#d1d5db" strokeWidth="1.5"/>
              <path d="M13 20h14" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round"/>
              <circle cx="20" cy="13" r="2" fill="#9ca3af"/>
              <path d="M20 17v6" stroke="#9ca3af" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <div className="forbidden-title">접근 권한이 없습니다</div>
          <div className="forbidden-desc">이 페이지는 관리자만 접근할 수 있습니다.</div>
          <button
            className="forbidden-btn"
            onClick={() => navigate('/dashboard')}
          >
            대시보드로 이동
          </button>
        </div>
      </div>
    )
  }

  return children
}

export default ProtectedRoute
