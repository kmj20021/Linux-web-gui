import { useState } from 'react'
import CliPreview from './CliPreview'

// 입력값에 해당하는 CLI 명령 예시를 만든다.
function buildCliLines(username, role) {
  const displayName = username.trim() || '<username>'
  return [
    { type: 'comment', text: '# 1. 사용자 생성' },
    { type: 'cmd', text: `sudo useradd -m -s /bin/bash ${displayName}` },
    { type: 'empty' },
    { type: 'comment', text: '# 2. 비밀번호 설정' },
    { type: 'cmd', text: `sudo passwd ${displayName}` },
    ...(role === 'admin' ? [
      { type: 'empty' },
      { type: 'comment', text: '# 3. sudo 그룹 추가 (admin 역할)' },
      { type: 'cmd', text: `sudo usermod -aG sudo ${displayName}` },
    ] : []),
  ]
}

function CreateUserPanel({ onCreate, onDone }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [role, setRole] = useState('viewer')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const trimmedName = username.trim()
    if (!trimmedName) { setError('사용자명을 입력하세요.'); return }
    if (!password) { setError('비밀번호를 입력하세요.'); return }
    if (password !== passwordConfirm) { setError('비밀번호가 일치하지 않습니다.'); return }

    setSubmitting(true)
    try {
      await onCreate({ username: trimmedName, password, role })
      setSuccess(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="processes-container ua-form-container">
        <div className="ua-success-msg">계정이 생성되었습니다.</div>
        <button className="ua-back-btn" onClick={onDone}>목록으로 돌아가기</button>
      </div>
    )
  }

  return (
    <div className="processes-container ua-form-container">
      <div className="ua-create-layout">
        <form className="ua-form" onSubmit={handleSubmit}>
          <div className="ua-form-group">
            <label className="ua-form-label" htmlFor="ua-username">사용자명</label>
            <input
              id="ua-username"
              className="ua-form-input"
              type="text"
              value={username}
              onChange={e => { setUsername(e.target.value); setError('') }}
              placeholder="사용자명 입력"
              autoFocus
              disabled={submitting}
            />
          </div>
          <div className="ua-form-group">
            <label className="ua-form-label" htmlFor="ua-password">비밀번호</label>
            <input
              id="ua-password"
              className="ua-form-input"
              type="password"
              value={password}
              onChange={e => { setPassword(e.target.value); setError('') }}
              placeholder="비밀번호 입력"
              disabled={submitting}
            />
          </div>
          <div className="ua-form-group">
            <label className="ua-form-label" htmlFor="ua-password-confirm">비밀번호 확인</label>
            <input
              id="ua-password-confirm"
              className="ua-form-input"
              type="password"
              value={passwordConfirm}
              onChange={e => { setPasswordConfirm(e.target.value); setError('') }}
              placeholder="비밀번호 재입력"
              disabled={submitting}
            />
          </div>
          <div className="ua-form-group">
            <label className="ua-form-label" htmlFor="ua-role">역할</label>
            <select
              id="ua-role"
              className="ua-form-select"
              value={role}
              onChange={e => setRole(e.target.value)}
              disabled={submitting}
            >
              <option value="viewer">viewer</option>
              <option value="admin">admin</option>
            </select>
          </div>
          {error && <div className="ua-form-error" role="alert">{error}</div>}
          <div className="ua-form-actions">
            <button type="button" className="ua-cancel-btn" onClick={onDone} disabled={submitting}>
              취소
            </button>
            <button type="submit" className="ua-submit-btn" disabled={submitting}>
              {submitting ? '생성 중...' : '계정 생성'}
            </button>
          </div>
        </form>
        <CliPreview title="CLI 명령어 미리보기" lines={buildCliLines(username, role)} />
      </div>
    </div>
  )
}

export default CreateUserPanel
