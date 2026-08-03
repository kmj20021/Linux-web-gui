import { useAuth } from '../../../context/AuthContext'

// 사용자 목록 표.
// 자기 계정은 역할 변경·비활성화·삭제 대상에서 제외한다(서버도 같은 규칙을 강제한다).
function UserListPanel({ users, loading, error, actionError, onRefresh, onRoleChange, onToggleActive, onDelete }) {
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
          <button className="ua-refresh-btn" onClick={onRefresh} style={{ marginLeft: '12px' }}>
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="processes-container">
      {actionError && (
        <div className="ua-action-error" role="alert">{actionError}</div>
      )}
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
                      <span className={`ua-role-badge ua-role-${u.role}`} data-testid="ua-role">
                        {u.role}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`ua-status-badge ${u.is_active ? 'ua-active' : 'ua-inactive'}`}
                        data-testid="ua-status"
                      >
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
                          aria-label={`${u.username} 역할 변경`}
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
                          onClick={() => onToggleActive(u.id, !u.is_active)}
                        >
                          {u.is_active ? '비활성화' : '활성화'}
                        </button>
                      )}
                    </td>
                    <td>
                      {!isMe && (
                        <button className="ua-delete-btn" onClick={() => onDelete(u)}>
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

export default UserListPanel
