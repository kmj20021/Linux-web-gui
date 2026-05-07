import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import '../styles/Login.css'

function Login() {
  const { login, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // 이미 로그인된 경우 홈으로 이동
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (submitting) return

    setError('')

    if (!username.trim()) {
      setError('사용자명을 입력해주세요.')
      return
    }
    if (!password) {
      setError('비밀번호를 입력해주세요.')
      return
    }

    setSubmitting(true)
    try {
      await login(username.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      const status = err?.status
      if (status === 401) {
        setError('사용자명 또는 비밀번호가 올바르지 않습니다.')
      } else if (status === 403) {
        setError('계정이 비활성화 상태입니다. 관리자에게 문의하세요.')
      } else {
        setError('로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSubmit(e)
    }
  }

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner" />
      </div>
    )
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">
            <svg viewBox="0 0 26 26" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="3" y="3" width="8" height="8" rx="1.5" fill="white" opacity="0.9"/>
              <rect x="15" y="3" width="8" height="8" rx="1.5" fill="white" opacity="0.7"/>
              <rect x="3" y="15" width="8" height="8" rx="1.5" fill="white" opacity="0.7"/>
              <rect x="15" y="15" width="8" height="8" rx="1.5" fill="white" opacity="0.5"/>
            </svg>
          </div>
          <h1 className="login-title">LinuxViz</h1>
          <p className="login-subtitle">시스템 관리 콘솔에 로그인하세요</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="username">사용자명</label>
            <input
              id="username"
              type="text"
              className={`form-input${error ? ' input-error' : ''}`}
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError('') }}
              onKeyDown={handleKeyDown}
              placeholder="사용자명 입력"
              autoComplete="username"
              autoFocus
              disabled={submitting}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">비밀번호</label>
            <input
              id="password"
              type="password"
              className={`form-input${error ? ' input-error' : ''}`}
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError('') }}
              onKeyDown={handleKeyDown}
              placeholder="비밀번호 입력"
              autoComplete="current-password"
              disabled={submitting}
            />
          </div>

          {error && (
            <div className="login-error" role="alert">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={submitting}
          >
            {submitting ? (
              <span className="login-spinner">
                <span className="spinner-icon" />
                로그인 중...
              </span>
            ) : '로그인'}
          </button>

          <div className="login-footer">
            <span>계정이 없으신가요?</span>
            <Link to="/register">회원가입</Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Login
