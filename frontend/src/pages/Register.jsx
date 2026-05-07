import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authAPI } from '../api/client'
import '../styles/Login.css'

function Register() {
  const { isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // 이미 로그인된 경우 홈으로 이동
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate])

  const validate = () => {
    if (!username.trim()) {
      setError('사용자명을 입력해주세요.')
      return false
    }
    if (username.trim().length < 3 || username.trim().length > 20) {
      setError('사용자명은 3~20자 사이여야 합니다.')
      return false
    }
    if (!password) {
      setError('비밀번호를 입력해주세요.')
      return false
    }
    if (password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.')
      return false
    }
    if (!passwordConfirm) {
      setError('비밀번호 확인을 입력해주세요.')
      return false
    }
    if (password !== passwordConfirm) {
      setError('비밀번호가 일치하지 않습니다.')
      return false
    }
    return true
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (submitting || success) return

    setError('')

    if (!validate()) return

    setSubmitting(true)
    try {
      await authAPI.register(username.trim(), password, passwordConfirm)
      setSuccess(true)
      setTimeout(() => {
        navigate('/login', { replace: true })
      }, 2000)
    } catch (err) {
      if (err.status === 400) {
        setError('이미 사용 중인 사용자명입니다.')
      } else {
        setError(err.message || '회원가입 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')
      }
    } finally {
      setSubmitting(false)
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
          <p className="login-subtitle">새 계정을 만드세요</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <div className="form-group">
            <label className="form-label" htmlFor="username">사용자명</label>
            <input
              id="username"
              type="text"
              className={`form-input${error && !success ? ' input-error' : ''}`}
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError('') }}
              placeholder="3~20자 사용자명 입력"
              autoComplete="username"
              autoFocus
              disabled={submitting || success}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">비밀번호</label>
            <input
              id="password"
              type="password"
              className={`form-input${error && !success ? ' input-error' : ''}`}
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError('') }}
              placeholder="8자 이상 입력"
              autoComplete="new-password"
              disabled={submitting || success}
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password_confirm">비밀번호 확인</label>
            <input
              id="password_confirm"
              type="password"
              className={`form-input${error && !success ? ' input-error' : ''}`}
              value={passwordConfirm}
              onChange={(e) => { setPasswordConfirm(e.target.value); setError('') }}
              placeholder="비밀번호 재입력"
              autoComplete="new-password"
              disabled={submitting || success}
            />
          </div>

          {error && (
            <div className="login-error" role="alert">
              {error}
            </div>
          )}

          {success && (
            <div className="register-success" role="status">
              회원가입이 완료되었습니다. 로그인 페이지로 이동합니다.
            </div>
          )}

          <button
            type="submit"
            className="login-button"
            disabled={submitting || success}
          >
            {submitting ? (
              <span className="login-spinner">
                <span className="spinner-icon" />
                처리 중...
              </span>
            ) : '회원가입'}
          </button>

          <div className="login-footer">
            <span>이미 계정이 있으신가요?</span>
            <Link to="/login">로그인</Link>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Register
