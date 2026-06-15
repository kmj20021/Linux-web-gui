import { useState, useEffect, useCallback } from 'react'
import { getAuthHeaders } from '../api/client'
import { useAuth } from '../context/AuthContext'
import '../styles/Processes.css'
import '../styles/UsersAdmin.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

// ============================================================
// API 호출 함수
// ============================================================
async function fetchUsers() {
  const res = await fetch(`${API_BASE_URL}/admin/users`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error(`사용자 목록 조회 실패: ${res.status}`)
  return res.json()
}

async function createUser(username, password, role) {
  const res = await fetch(`${API_BASE_URL}/admin/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ username, password, role }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = body.detail
    const message = Array.isArray(detail)
      ? detail.map(e => e.msg).join(', ')
      : (detail || `계정 생성 실패: ${res.status}`)
    throw new Error(message)
  }
  return res.json()
}

async function patchUser(id, payload) {
  const res = await fetch(`${API_BASE_URL}/admin/users/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `계정 수정 실패: ${res.status}`)
  }
  return res.json()
}

async function deleteUser(id) {
  const res = await fetch(`${API_BASE_URL}/admin/users/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `계정 삭제 실패: ${res.status}`)
  }
  return res.json()
}

// ============================================================
// 메인 컴포넌트
// ============================================================
function UsersPage() {
  const [tab, setTab] = useState('list') // 'list' | 'create'
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchUsers()
      setUsers(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const handleRoleChange = async (id, newRole) => {
    try {
      const updated = await patchUser(id, { role: newRole })
      setUsers(prev => prev.map(u => u.id === id ? { ...u, role: updated.role } : u))
    } catch (e) {
      alert(e.message)
    }
  }

  const handleToggleActive = async (id, currentActive) => {
    try {
      const updated = await patchUser(id, { is_active: !currentActive })
      setUsers(prev => prev.map(u => u.id === id ? { ...u, is_active: updated.is_active } : u))
    } catch (e) {
      alert(e.message)
    }
  }

  const handleDelete = async (id, username) => {
    if (!window.confirm(`'${username}' 계정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) return
    try {
      await deleteUser(id)
      setUsers(prev => prev.filter(u => u.id !== id))
    } catch (e) {
      alert(e.message)
    }
  }

  const handleCreate = async (username, password, role) => {
    try {
      const newUser = await createUser(username, password, role)
      setUsers(prev => [...prev, newUser])
      setTab('list')
    } catch (e) {
      throw e
    }
  }

  return (
    <div className="processes-page">
      <div className="page-header">
        <h1>사용자 관리</h1>
        <p className="page-subtitle">웹 GUI 계정을 관리합니다.</p>
      </div>

      {/* 탭 */}
      <div className="ua-tabs">
        <button
          className={`ua-tab${tab === 'list' ? ' active' : ''}`}
          onClick={() => setTab('list')}
        >
          사용자 목록
        </button>
        <button
          className={`ua-tab${tab === 'create' ? ' active' : ''}`}
          onClick={() => setTab('create')}
        >
          계정 생성
        </button>
      </div>

      {tab === 'list' && (
        <UserListPanel
          users={users}
          loading={loading}
          error={error}
          onRefresh={loadUsers}
          onRoleChange={handleRoleChange}
          onToggleActive={handleToggleActive}
          onDelete={handleDelete}
        />
      )}

      {tab === 'create' && (
        <CreateUserPanel onCreate={handleCreate} onDone={() => setTab('list')} />
      )}
    </div>
  )
}

// ============================================================
// 사용자 목록 패널
// ============================================================
function UserListPanel({ users, loading, error, onRefresh, onRoleChange, onToggleActive, onDelete }) {
  const { user: currentUser } = useAuth()

  if (loading) {
    return (
      <div className="processes-container">
        <div className="loading">
          <div className="spinner" />
          <span>불러오는 중...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="processes-container">
        <div className="no-data">
          오류: {error}
          <button className="ua-refresh-btn" onClick={onRefresh} style={{ marginLeft: '12px' }}>다시 시도</button>
        </div>
      </div>
    )
  }

  return (
    <div className="processes-container">
      <div className="table-wrapper">
        <table className="processes-table">
          <thead>
            <tr>
              <th>사용자명</th>
              <th>역할</th>
              <th>상태</th>
              <th>생성일</th>
              <th>역할 변경</th>
              <th>활성화</th>
              <th>삭제</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan={7} className="no-data">계정이 없습니다.</td>
              </tr>
            ) : (
              users.map(u => {
                const isMe = currentUser && u.username === currentUser.username
                return (
                  <tr key={u.id}>
                    <td style={{ fontWeight: 500 }}>
                      {u.username}
                      {isMe && <span className="ua-me-badge">내 계정</span>}
                    </td>
                    <td>
                      <span className={`ua-role-badge ua-role-${u.role}`}>{u.role}</span>
                    </td>
                    <td>
                      <span className={`ua-status-badge ${u.is_active ? 'ua-active' : 'ua-inactive'}`}>
                        {u.is_active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td style={{ color: '#6b7280', fontSize: '13px' }}>
                      {u.created_at ? new Date(u.created_at).toLocaleDateString('ko-KR') : '-'}
                    </td>
                    <td>
                      {!isMe && (
                        <select
                          className="ua-role-select"
                          value={u.role}
                          onChange={e => onRoleChange(u.id, e.target.value)}
                        >
                          <option value="admin">admin</option>
                          <option value="viewer">viewer</option>
                        </select>
                      )}
                    </td>
                    <td>
                      {!isMe && (
                        <button
                          className={`ua-toggle-btn ${u.is_active ? 'ua-toggle-on' : 'ua-toggle-off'}`}
                          onClick={() => onToggleActive(u.id, u.is_active)}
                        >
                          {u.is_active ? '비활성화' : '활성화'}
                        </button>
                      )}
                    </td>
                    <td>
                      {!isMe && (
                        <button
                          className="ua-delete-btn"
                          onClick={() => onDelete(u.id, u.username)}
                        >
                          삭제
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ============================================================
// 계정 생성 패널
// ============================================================
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
      await onCreate(trimmedName, password, role)
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
            <label className="ua-form-label">사용자명</label>
            <input
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
            <label className="ua-form-label">비밀번호</label>
            <input
              className="ua-form-input"
              type="password"
              value={password}
              onChange={e => { setPassword(e.target.value); setError('') }}
              placeholder="비밀번호 입력"
              disabled={submitting}
            />
          </div>
          <div className="ua-form-group">
            <label className="ua-form-label">비밀번호 확인</label>
            <input
              className="ua-form-input"
              type="password"
              value={passwordConfirm}
              onChange={e => { setPasswordConfirm(e.target.value); setError('') }}
              placeholder="비밀번호 재입력"
              disabled={submitting}
            />
          </div>
          <div className="ua-form-group">
            <label className="ua-form-label">역할</label>
            <select
              className="ua-form-select"
              value={role}
              onChange={e => setRole(e.target.value)}
              disabled={submitting}
            >
              <option value="viewer">viewer</option>
              <option value="admin">admin</option>
            </select>
          </div>
          {error && <div className="ua-form-error">{error}</div>}
          <div className="ua-form-actions">
            <button type="button" className="ua-cancel-btn" onClick={onDone} disabled={submitting}>
              취소
            </button>
            <button type="submit" className="ua-submit-btn" disabled={submitting}>
              {submitting ? '생성 중...' : '계정 생성'}
            </button>
          </div>
        </form>
        <CliPreview username={username} role={role} />
      </div>
    </div>
  )
}

// ============================================================
// CLI 미리보기 컴포넌트
// ============================================================
function CliPreview({ username, role }) {
  const [copied, setCopied] = useState(false)
  const displayName = username.trim() || '<username>'

  const lines = [
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

  const fullText = lines
    .map(l => l.type === 'empty' ? '' : l.text)
    .join('\n')

  const handleCopy = () => {
    navigator.clipboard.writeText(fullText).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className="ua-cli-preview">
      <div className="ua-cli-preview-header">
        <span className="ua-cli-preview-title">CLI 명령어 미리보기</span>
        <button
          type="button"
          className={`ua-cli-copy-btn${copied ? ' copied' : ''}`}
          onClick={handleCopy}
        >
          {copied ? '복사됨!' : '복사'}
        </button>
      </div>
      <div className="ua-cli-code">
        {lines.map((line, i) => (
          line.type === 'empty'
            ? <div key={i} className="ua-cli-line">&nbsp;</div>
            : <div key={i} className={`ua-cli-line ua-cli-${line.type}`}>{line.text}</div>
        ))}
      </div>
    </div>
  )
}

export default UsersPage
