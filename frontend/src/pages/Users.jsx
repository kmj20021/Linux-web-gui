import { useState, useRef, useEffect, useCallback } from 'react'
import '../styles/Users.css'

// ============================================================
// 초기 데이터
// ============================================================
const INITIAL_USERS = [
  { id: 'root',     uid: 0,    gid: 0,    home: '/root',        shell: '/bin/bash',         groups: ['root'],                   system: true,  createdByUser: false },
  { id: 'ubuntu',   uid: 1000, gid: 1000, home: '/home/ubuntu', shell: '/bin/bash',         groups: ['ubuntu', 'sudo', 'docker'], system: true,  createdByUser: false },
  { id: 'www-data', uid: 33,   gid: 33,   home: '/var/www',     shell: '/usr/sbin/nologin', groups: ['www-data'],               system: true,  createdByUser: false },
]

const INITIAL_GROUPS = [
  { id: 'root',     gid: 0,    members: ['root'],    createdByUser: false },
  { id: 'sudo',     gid: 27,   members: ['ubuntu'],  createdByUser: false },
  { id: 'docker',   gid: 999,  members: ['ubuntu'],  createdByUser: false },
  { id: 'www-data', gid: 33,   members: ['www-data'], createdByUser: false },
  { id: 'ubuntu',   gid: 1000, members: ['ubuntu'],  createdByUser: false },
]

// ============================================================
// 유틸리티
// ============================================================
function now() {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function getNextUid(users) {
  const custom = users.filter(u => u.createdByUser).map(u => u.uid)
  if (custom.length === 0) return 1001
  return Math.max(...custom) + 1
}

function getNextGid(groups) {
  const custom = groups.filter(g => g.createdByUser).map(g => g.gid)
  if (custom.length === 0) return 1001
  return Math.max(...custom) + 1
}

// ============================================================
// SVG 아이콘 컴포넌트
// ============================================================
function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  )
}

function GroupIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 1-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function EmptyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
    </svg>
  )
}

// ============================================================
// 메인 컴포넌트
// ============================================================
function UsersPage() {
  const [users, setUsers] = useState(INITIAL_USERS)
  const [groups, setGroups] = useState(INITIAL_GROUPS)
  const [selected, setSelected] = useState(null) // { type: 'user'|'group', id: string }
  const [usersOpen, setUsersOpen] = useState(true)
  const [groupsOpen, setGroupsOpen] = useState(true)
  const [cmdLog, setCmdLog] = useState([
    { id: Date.now(), time: now(), type: 'comment', text: '# 사용자 관리 시뮬레이션 시작' },
  ])

  // 모달 상태
  const [modal, setModal] = useState(null) // 'useradd' | 'userdel' | 'groupadd' | 'groupdel' | 'groupmod' | 'su'

  const logBodyRef = useRef(null)

  // 로그 자동 스크롤
  useEffect(() => {
    if (logBodyRef.current) {
      logBodyRef.current.scrollTop = logBodyRef.current.scrollHeight
    }
  }, [cmdLog])

  const addLog = useCallback((text, type = 'cmd') => {
    setCmdLog(prev => {
      const next = [...prev, { id: Date.now() + Math.random(), time: now(), type, text }]
      return next.length > 50 ? next.slice(next.length - 50) : next
    })
  }, [])

  // 선택된 항목 객체
  const selectedUser = selected?.type === 'user' ? users.find(u => u.id === selected.id) : null
  const selectedGroup = selected?.type === 'group' ? groups.find(g => g.id === selected.id) : null

  // 버튼 활성화 조건
  const canDeleteUser = selected?.type === 'user' && selectedUser?.createdByUser
  const canDeleteGroup = selected?.type === 'group' && selectedGroup?.createdByUser
  const canModifyGroup = selected?.type === 'group' && selectedGroup?.createdByUser
  const canLogin = selected?.type === 'user' && selectedUser?.createdByUser

  // ============================================================
  // useradd 핸들러
  // ============================================================
  function handleUserAdd(name, shell, extraGroups) {
    const newUid = getNextUid(users)
    const newGid = getNextGid(groups)
    const home = `/home/${name}`

    // 동명의 그룹 자동 생성
    const newGroup = { id: name, gid: newGid, members: [name], createdByUser: true }
    const allGroups = [name, ...extraGroups]

    const newUser = {
      id: name,
      uid: newUid,
      gid: newGid,
      home,
      shell,
      groups: allGroups,
      system: false,
      createdByUser: true,
    }

    setUsers(prev => [...prev, newUser])
    setGroups(prev => {
      // extraGroups에서 해당 그룹 멤버에 추가
      const updated = prev.map(g => {
        if (extraGroups.includes(g.id)) {
          return { ...g, members: [...new Set([...g.members, name])] }
        }
        return g
      })
      return [...updated, newGroup]
    })

    addLog(`useradd -m -s ${shell} ${name}`)
    setSelected({ type: 'user', id: name })
    setModal(null)
  }

  // ============================================================
  // userdel 핸들러
  // ============================================================
  function handleUserDel(userId) {
    const user = users.find(u => u.id === userId)
    if (!user) return

    setUsers(prev => prev.filter(u => u.id !== userId))
    // 동명 그룹도 제거, 다른 그룹 멤버에서도 제거
    setGroups(prev =>
      prev
        .filter(g => g.id !== userId)
        .map(g => ({ ...g, members: g.members.filter(m => m !== userId) }))
    )
    if (selected?.id === userId) setSelected(null)
    addLog(`userdel -r ${userId}`)
    setModal(null)
  }

  // ============================================================
  // groupadd 핸들러
  // ============================================================
  function handleGroupAdd(name) {
    const newGid = getNextGid(groups)
    const newGroup = { id: name, gid: newGid, members: [], createdByUser: true }
    setGroups(prev => [...prev, newGroup])
    addLog(`groupadd ${name}`)
    setSelected({ type: 'group', id: name })
    setModal(null)
  }

  // ============================================================
  // groupdel 핸들러
  // ============================================================
  function handleGroupDel(groupId) {
    setGroups(prev => prev.filter(g => g.id !== groupId))
    // 사용자 groups 목록에서 제거
    setUsers(prev =>
      prev.map(u => ({ ...u, groups: u.groups.filter(gn => gn !== groupId) }))
    )
    if (selected?.id === groupId) setSelected(null)
    addLog(`groupdel ${groupId}`)
    setModal(null)
  }

  // ============================================================
  // groupmod 핸들러
  // ============================================================
  function handleGroupRename(groupId, newName) {
    setGroups(prev =>
      prev.map(g => g.id === groupId ? { ...g, id: newName } : g)
    )
    setUsers(prev =>
      prev.map(u => ({ ...u, groups: u.groups.map(gn => gn === groupId ? newName : gn) }))
    )
    if (selected?.id === groupId) setSelected({ type: 'group', id: newName })
    addLog(`groupmod -n ${newName} ${groupId}`)
    setModal(null)
  }

  function handleGroupMembers(groupId, added, removed) {
    setGroups(prev =>
      prev.map(g => {
        if (g.id !== groupId) return g
        const members = [...new Set([...g.members.filter(m => !removed.includes(m)), ...added])]
        return { ...g, members }
      })
    )
    // 사용자 groups 동기화
    setUsers(prev =>
      prev.map(u => {
        if (added.includes(u.id) && !u.groups.includes(groupId)) {
          return { ...u, groups: [...u.groups, groupId] }
        }
        if (removed.includes(u.id)) {
          return { ...u, groups: u.groups.filter(gn => gn !== groupId) }
        }
        return u
      })
    )
    added.forEach(u => addLog(`gpasswd -a ${u} ${groupId}`))
    removed.forEach(u => addLog(`gpasswd -d ${u} ${groupId}`))
    setModal(null)
  }

  // ============================================================
  // 렌더링
  // ============================================================
  return (
    <div className="um-page">
      {/* 상단 툴바 */}
      <div className="um-toolbar">
        <span className="um-toolbar-title">사용자 관리</span>
        <div className="um-toolbar-divider" />

        <button className="um-btn success" onClick={() => setModal('useradd')}>
          <span className="um-btn-label">사용자 생성</span>
          <span className="um-btn-cmd">useradd</span>
        </button>

        <button
          className="um-btn danger"
          disabled={!canDeleteUser}
          onClick={() => setModal('userdel')}
        >
          <span className="um-btn-label">사용자 삭제</span>
          <span className="um-btn-cmd">userdel</span>
        </button>

        <div className="um-toolbar-divider" />

        <button className="um-btn success" onClick={() => setModal('groupadd')}>
          <span className="um-btn-label">그룹 생성</span>
          <span className="um-btn-cmd">groupadd</span>
        </button>

        <button
          className="um-btn danger"
          disabled={!canDeleteGroup}
          onClick={() => setModal('groupdel')}
        >
          <span className="um-btn-label">그룹 삭제</span>
          <span className="um-btn-cmd">groupdel</span>
        </button>

        <button
          className="um-btn warning"
          disabled={!canModifyGroup}
          onClick={() => setModal('groupmod')}
        >
          <span className="um-btn-label">그룹 수정</span>
          <span className="um-btn-cmd">groupmod</span>
        </button>

        <div className="um-toolbar-divider" />

        <button
          className="um-btn primary"
          disabled={!canLogin}
          onClick={() => setModal('su')}
        >
          <span className="um-btn-label">로그인 시뮬레이션</span>
          <span className="um-btn-cmd">su</span>
        </button>
      </div>

      {/* 메인 영역 */}
      <div className="um-main">
        {/* 좌측 목록 패널 */}
        <div className="um-list-panel">
          <div className="um-list-panel-header">사용자 및 그룹</div>
          <div className="um-list-body">
            {/* 사용자 섹션 */}
            <div
              className="um-section-header"
              onClick={() => setUsersOpen(o => !o)}
            >
              <span className={`um-section-toggle ${usersOpen ? 'open' : ''}`}>&#9654;</span>
              <span className="um-section-icon"><UserIcon /></span>
              사용자 ({users.length})
            </div>
            {usersOpen && users.map(user => (
              <div
                key={user.id}
                className={`um-list-item${user.system ? ' system-item' : ''}${selected?.type === 'user' && selected.id === user.id ? ' selected' : ''}${user.createdByUser ? ' fade-in' : ''}`}
                onClick={() => setSelected({ type: 'user', id: user.id })}
              >
                <span className="um-list-item-icon"><UserIcon /></span>
                <span className="um-list-item-name">{user.id}</span>
                {user.createdByUser && <span className="um-list-item-badge" title="사용자가 생성한 계정" />}
              </div>
            ))}

            {/* 그룹 섹션 */}
            <div
              className="um-section-header"
              onClick={() => setGroupsOpen(o => !o)}
              style={{ marginTop: '4px' }}
            >
              <span className={`um-section-toggle ${groupsOpen ? 'open' : ''}`}>&#9654;</span>
              <span className="um-section-icon"><GroupIcon /></span>
              그룹 ({groups.length})
            </div>
            {groupsOpen && groups.map(group => (
              <div
                key={group.id}
                className={`um-list-item${!group.createdByUser ? ' system-item' : ''}${selected?.type === 'group' && selected.id === group.id ? ' selected' : ''}${group.createdByUser ? ' fade-in' : ''}`}
                onClick={() => setSelected({ type: 'group', id: group.id })}
              >
                <span className="um-list-item-icon"><GroupIcon /></span>
                <span className="um-list-item-name">{group.id}</span>
                {group.createdByUser && <span className="um-list-item-badge" />}
              </div>
            ))}
          </div>
        </div>

        {/* 우측 상세 패널 */}
        <div className="um-detail-panel">
          {!selected && (
            <div className="um-detail-empty">
              <div className="um-detail-empty-icon"><EmptyIcon /></div>
              <span>항목을 선택하세요</span>
            </div>
          )}

          {selectedUser && (
            <>
              <div className="um-detail-section">
                <div className="um-detail-section-title">사용자 정보</div>
                <div className="um-detail-info-grid">
                  <span className="um-detail-info-label">사용자 이름</span>
                  <span className="um-detail-info-value highlight">{selectedUser.id}</span>

                  <span className="um-detail-info-label">UID</span>
                  <span className="um-detail-info-value">{selectedUser.uid}</span>

                  <span className="um-detail-info-label">GID</span>
                  <span className="um-detail-info-value">{selectedUser.gid}</span>

                  <span className="um-detail-info-label">홈 디렉토리</span>
                  <span className="um-detail-info-value">{selectedUser.home}</span>

                  <span className="um-detail-info-label">셸</span>
                  <span className="um-detail-info-value">{selectedUser.shell}</span>

                  <span className="um-detail-info-label">계정 상태</span>
                  <span className="um-detail-info-value">
                    <span className="um-status-badge">활성</span>
                  </span>
                </div>
              </div>

              <div className="um-detail-section">
                <div className="um-detail-section-title">소속 그룹</div>
                <div className="um-tag-list">
                  {selectedUser.groups.map(g => (
                    <span key={g} className="um-tag">{g}</span>
                  ))}
                </div>
              </div>
            </>
          )}

          {selectedGroup && (
            <div className="um-detail-section">
              <div className="um-detail-section-title">그룹 정보</div>
              <div className="um-detail-info-grid">
                <span className="um-detail-info-label">그룹 이름</span>
                <span className="um-detail-info-value highlight">{selectedGroup.id}</span>

                <span className="um-detail-info-label">GID</span>
                <span className="um-detail-info-value">{selectedGroup.gid}</span>

                <span className="um-detail-info-label">멤버 수</span>
                <span className="um-detail-info-value">{selectedGroup.members.length}명</span>
              </div>

              {selectedGroup.members.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div className="um-detail-section-title">멤버</div>
                  <div className="um-tag-list">
                    {selectedGroup.members.map(m => (
                      <span key={m} className="um-tag">{m}</span>
                    ))}
                  </div>
                </div>
              )}

              {selectedGroup.members.length === 0 && (
                <div style={{ marginTop: '10px', fontSize: '12px', color: '#9ca3af' }}>멤버 없음</div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 하단 커맨드 로그 */}
      <div className="um-log-panel">
        <div className="um-log-header">
          <span className="um-log-header-title">커맨드 로그</span>
          <button
            className="um-log-clear-btn"
            onClick={() => setCmdLog([{ id: Date.now(), time: now(), type: 'comment', text: '# 로그 지움' }])}
          >
            지우기
          </button>
        </div>
        <div className="um-log-body" ref={logBodyRef}>
          {cmdLog.map(entry => (
            <div key={entry.id} className="um-log-entry">
              <span className="um-log-time">{entry.time}</span>
              {entry.type === 'comment' ? (
                <span className="um-log-comment">{entry.text}</span>
              ) : (
                <>
                  <span className="um-log-prompt">$</span>
                  <span className="um-log-cmd">{entry.text}</span>
                </>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ===== 모달들 ===== */}

      {modal === 'useradd' && (
        <UserAddModal
          groups={groups}
          onConfirm={handleUserAdd}
          onClose={() => setModal(null)}
        />
      )}

      {modal === 'userdel' && selectedUser && (
        <UserDelModal
          user={selectedUser}
          onConfirm={() => handleUserDel(selectedUser.id)}
          onClose={() => setModal(null)}
        />
      )}

      {modal === 'groupadd' && (
        <GroupAddModal
          groups={groups}
          onConfirm={handleGroupAdd}
          onClose={() => setModal(null)}
        />
      )}

      {modal === 'groupdel' && selectedGroup && (
        <GroupDelModal
          group={selectedGroup}
          onConfirm={() => handleGroupDel(selectedGroup.id)}
          onClose={() => setModal(null)}
        />
      )}

      {modal === 'groupmod' && selectedGroup && (
        <GroupModModal
          group={selectedGroup}
          users={users}
          onRename={(newName) => handleGroupRename(selectedGroup.id, newName)}
          onMembers={(added, removed) => handleGroupMembers(selectedGroup.id, added, removed)}
          onClose={() => setModal(null)}
        />
      )}

      {modal === 'su' && selectedUser && (
        <SuModal
          user={selectedUser}
          groups={groups}
          onClose={() => {
            addLog(`# su 세션 종료 — ${selectedUser.id}`, 'comment')
            setModal(null)
          }}
          addLog={addLog}
        />
      )}
    </div>
  )
}

// ============================================================
// useradd 모달
// ============================================================
function UserAddModal({ groups, onConfirm, onClose }) {
  const [name, setName] = useState('')
  const [shell, setShell] = useState('/bin/bash')
  const [extraGroups, setExtraGroups] = useState([])
  const [error, setError] = useState('')

  function toggleGroup(gid) {
    setExtraGroups(prev =>
      prev.includes(gid) ? prev.filter(g => g !== gid) : [...prev, gid]
    )
  }

  function handleSubmit() {
    const trimmed = name.trim()
    if (!trimmed) { setError('사용자 이름을 입력하세요.'); return }
    if (!/^[a-z_][a-z0-9_-]*$/.test(trimmed)) {
      setError('사용자 이름은 소문자 영문, 숫자, _, - 만 사용할 수 있습니다.')
      return
    }
    onConfirm(trimmed, shell, extraGroups)
  }

  return (
    <div className="um-modal-overlay" onClick={onClose}>
      <div className="um-modal wide" onClick={e => e.stopPropagation()}>
        <div className="um-modal-header">
          <div className="um-modal-title">
            사용자 생성
            <span className="um-modal-cmd-badge">useradd</span>
          </div>
          <button className="um-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="um-modal-body">
          <div className="um-modal-field">
            <label className="um-modal-label">사용자 이름 (필수)</label>
            <input
              className="um-modal-input"
              value={name}
              onChange={e => { setName(e.target.value); setError('') }}
              placeholder="예: alice"
              autoFocus
            />
            {error && <div style={{ color: 'var(--danger-color)', fontSize: '12px', marginTop: '4px' }}>{error}</div>}
          </div>

          <div className="um-modal-field">
            <label className="um-modal-label">홈 디렉토리 (자동 설정)</label>
            <input
              className="um-modal-input"
              value={name.trim() ? `/home/${name.trim()}` : ''}
              readOnly
              style={{ opacity: 0.6 }}
              placeholder="/home/이름"
            />
          </div>

          <div className="um-modal-field">
            <label className="um-modal-label">셸</label>
            <select
              className="um-modal-select"
              value={shell}
              onChange={e => setShell(e.target.value)}
            >
              <option value="/bin/bash">/bin/bash</option>
              <option value="/bin/sh">/bin/sh</option>
              <option value="/usr/sbin/nologin">/usr/sbin/nologin</option>
            </select>
          </div>

          <div className="um-modal-field">
            <label className="um-modal-label">추가 소속 그룹 (선택)</label>
            <div className="um-checkbox-group">
              {groups.map(g => (
                <label key={g.id} className="um-checkbox-item">
                  <input
                    type="checkbox"
                    checked={extraGroups.includes(g.id)}
                    onChange={() => toggleGroup(g.id)}
                  />
                  <span>{g.id}</span>
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className="um-modal-footer">
          <button className="um-action-btn cancel" onClick={onClose}>취소</button>
          <button className="um-action-btn confirm" onClick={handleSubmit}>생성</button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// userdel 모달
// ============================================================
function UserDelModal({ user, onConfirm, onClose }) {
  return (
    <div className="um-modal-overlay" onClick={onClose}>
      <div className="um-modal" onClick={e => e.stopPropagation()}>
        <div className="um-modal-header">
          <div className="um-modal-title">
            사용자 삭제
            <span className="um-modal-cmd-badge">userdel</span>
          </div>
          <button className="um-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="um-modal-body">
          <div className="um-modal-warning">
            사용자 <strong>{user.id}</strong> 과 홈 디렉토리(<strong>{user.home}</strong>)를 삭제합니다.
            이 작업은 되돌릴 수 없습니다.
          </div>
        </div>
        <div className="um-modal-footer">
          <button className="um-action-btn cancel" onClick={onClose}>취소</button>
          <button className="um-action-btn confirm danger" onClick={onConfirm}>삭제</button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// groupadd 모달
// ============================================================
function GroupAddModal({ groups, onConfirm, onClose }) {
  const [name, setName] = useState('')
  const [error, setError] = useState('')

  function handleSubmit() {
    const trimmed = name.trim()
    if (!trimmed) { setError('그룹 이름을 입력하세요.'); return }
    if (!/^[a-z_][a-z0-9_-]*$/.test(trimmed)) {
      setError('그룹 이름은 소문자 영문, 숫자, _, - 만 사용할 수 있습니다.')
      return
    }
    if (groups.find(g => g.id === trimmed)) {
      setError('이미 존재하는 그룹 이름입니다.')
      return
    }
    onConfirm(trimmed)
  }

  return (
    <div className="um-modal-overlay" onClick={onClose}>
      <div className="um-modal" onClick={e => e.stopPropagation()}>
        <div className="um-modal-header">
          <div className="um-modal-title">
            그룹 생성
            <span className="um-modal-cmd-badge">groupadd</span>
          </div>
          <button className="um-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="um-modal-body">
          <div className="um-modal-field">
            <label className="um-modal-label">그룹 이름 (필수)</label>
            <input
              className="um-modal-input"
              value={name}
              onChange={e => { setName(e.target.value); setError('') }}
              placeholder="예: developers"
              autoFocus
            />
            {error && <div style={{ color: 'var(--danger-color)', fontSize: '12px', marginTop: '4px' }}>{error}</div>}
          </div>
        </div>
        <div className="um-modal-footer">
          <button className="um-action-btn cancel" onClick={onClose}>취소</button>
          <button className="um-action-btn confirm" onClick={handleSubmit}>생성</button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// groupdel 모달
// ============================================================
function GroupDelModal({ group, onConfirm, onClose }) {
  return (
    <div className="um-modal-overlay" onClick={onClose}>
      <div className="um-modal" onClick={e => e.stopPropagation()}>
        <div className="um-modal-header">
          <div className="um-modal-title">
            그룹 삭제
            <span className="um-modal-cmd-badge">groupdel</span>
          </div>
          <button className="um-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="um-modal-body">
          <div className="um-modal-warning">
            그룹 <strong>{group.id}</strong> 을 삭제합니다.
            멤버 <strong>{group.members.length}명</strong>은 그룹에서 제거됩니다.
          </div>
        </div>
        <div className="um-modal-footer">
          <button className="um-action-btn cancel" onClick={onClose}>취소</button>
          <button className="um-action-btn confirm danger" onClick={onConfirm}>삭제</button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// groupmod 모달 (탭: 이름 변경 / 멤버 관리)
// ============================================================
function GroupModModal({ group, users, onRename, onMembers, onClose }) {
  const [tab, setTab] = useState('rename')
  const [newName, setNewName] = useState(group.id)
  const [renameError, setRenameError] = useState('')
  const [memberChecks, setMemberChecks] = useState(() => {
    const init = {}
    users.forEach(u => { init[u.id] = group.members.includes(u.id) })
    return init
  })

  function handleRename() {
    const trimmed = newName.trim()
    if (!trimmed) { setRenameError('그룹 이름을 입력하세요.'); return }
    if (trimmed === group.id) { setRenameError('기존 이름과 동일합니다.'); return }
    if (!/^[a-z_][a-z0-9_-]*$/.test(trimmed)) {
      setRenameError('그룹 이름은 소문자 영문, 숫자, _, - 만 사용할 수 있습니다.')
      return
    }
    onRename(trimmed)
  }

  function handleMemberSave() {
    const added = users.filter(u => memberChecks[u.id] && !group.members.includes(u.id)).map(u => u.id)
    const removed = users.filter(u => !memberChecks[u.id] && group.members.includes(u.id)).map(u => u.id)
    onMembers(added, removed)
  }

  return (
    <div className="um-modal-overlay" onClick={onClose}>
      <div className="um-modal wide" onClick={e => e.stopPropagation()}>
        <div className="um-modal-header">
          <div className="um-modal-title">
            그룹 수정 — {group.id}
            <span className="um-modal-cmd-badge">groupmod</span>
          </div>
          <button className="um-modal-close" onClick={onClose}>x</button>
        </div>
        <div className="um-modal-body">
          <div className="um-tabs">
            <button className={`um-tab${tab === 'rename' ? ' active' : ''}`} onClick={() => setTab('rename')}>이름 변경</button>
            <button className={`um-tab${tab === 'members' ? ' active' : ''}`} onClick={() => setTab('members')}>멤버 관리</button>
          </div>

          {tab === 'rename' && (
            <div className="um-modal-field">
              <label className="um-modal-label">새 그룹 이름</label>
              <input
                className="um-modal-input"
                value={newName}
                onChange={e => { setNewName(e.target.value); setRenameError('') }}
                autoFocus
              />
              {renameError && <div style={{ color: 'var(--danger-color)', fontSize: '12px', marginTop: '4px' }}>{renameError}</div>}
            </div>
          )}

          {tab === 'members' && (
            <div className="um-modal-field">
              <label className="um-modal-label">멤버 선택</label>
              <div className="um-checkbox-group">
                {users.map(u => (
                  <label key={u.id} className="um-checkbox-item">
                    <input
                      type="checkbox"
                      checked={!!memberChecks[u.id]}
                      onChange={() => setMemberChecks(prev => ({ ...prev, [u.id]: !prev[u.id] }))}
                    />
                    <span>{u.id}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="um-modal-footer">
          <button className="um-action-btn cancel" onClick={onClose}>취소</button>
          {tab === 'rename' && (
            <button className="um-action-btn confirm" onClick={handleRename}>이름 변경</button>
          )}
          {tab === 'members' && (
            <button className="um-action-btn confirm" onClick={handleMemberSave}>저장</button>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// su 세션 모달
// ============================================================
function SuModal({ user, groups, onClose, addLog }) {
  const PRESET = {
    whoami: () => [user.id],
    id: () => {
      const gList = user.groups.map(gn => {
        const g = groups.find(gr => gr.id === gn)
        return g ? `${g.gid}(${g.id})` : gn
      }).join(',')
      return [`uid=${user.uid}(${user.id}) gid=${user.gid}(${user.id}) groups=${gList}`]
    },
    pwd: () => [user.home],
    ls: () => ['Documents  Downloads  Pictures'],
    'echo $HOME': () => [user.home],
    'echo $SHELL': () => [user.shell],
  }

  const TYPING_TEXT = `su - ${user.id}`

  const [lines, setLines] = useState([])
  const [inputVal, setInputVal] = useState('')
  const [phase, setPhase] = useState('typing') // 'typing' | 'password' | 'ready'
  const [typedChars, setTypedChars] = useState(0)
  const [showInput, setShowInput] = useState(false)

  const bodyRef = useRef(null)
  const inputRef = useRef(null)

  // 자동 스크롤
  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [lines])

  // 타이핑 애니메이션
  useEffect(() => {
    if (phase !== 'typing') return
    if (typedChars < TYPING_TEXT.length) {
      const timer = setTimeout(() => setTypedChars(c => c + 1), 50)
      return () => clearTimeout(timer)
    } else {
      // 타이핑 완료 → 비밀번호 단계
      const timer = setTimeout(() => setPhase('password'), 300)
      return () => clearTimeout(timer)
    }
  }, [phase, typedChars, TYPING_TEXT.length])

  // 비밀번호 단계
  useEffect(() => {
    if (phase !== 'password') return
    setLines([{ id: 1, cls: 'info', text: `[sudo] ${user.id}의 암호:` }])
    const timer = setTimeout(() => setPhase('ready'), 1000)
    return () => clearTimeout(timer)
  }, [phase, user.id])

  // 준비 단계
  useEffect(() => {
    if (phase !== 'ready') return
    setLines(prev => [...prev, { id: Date.now(), cls: 'prompt', text: `${user.id}@linux:~$` }])
    setShowInput(true)
    setTimeout(() => inputRef.current?.focus(), 50)
  }, [phase, user.id])

  // 초기 커맨드 로그
  useEffect(() => {
    addLog(`su - ${user.id}`)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function handleCommand(cmd) {
    const trimmed = cmd.trim()

    // 현재 프롬프트 행에 입력 표시
    setLines(prev => {
      // 마지막 prompt 행에 명령어 추가
      const updated = [...prev]
      const lastIdx = updated.length - 1
      if (updated[lastIdx]?.cls === 'prompt') {
        updated[lastIdx] = { ...updated[lastIdx], text: `${user.id}@linux:~$ ${trimmed}` }
      }
      return updated
    })

    if (trimmed === 'exit' || trimmed === 'logout') {
      addLog('exit')
      setTimeout(onClose, 300)
      return
    }

    let output = []
    if (trimmed === '') {
      output = []
    } else if (PRESET[trimmed]) {
      output = PRESET[trimmed]()
    } else {
      output = [`bash: ${trimmed}: command not found`]
    }

    setLines(prev => [
      ...prev,
      ...output.map((o, i) => ({
        id: Date.now() + i,
        cls: o.includes('command not found') ? 'error' : 'output',
        text: o,
      })),
      { id: Date.now() + 999, cls: 'prompt', text: `${user.id}@linux:~$` },
    ])
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      const val = inputVal
      setInputVal('')
      handleCommand(val)
    }
    if (e.key === 'd' && e.ctrlKey) {
      e.preventDefault()
      addLog('exit')
      onClose()
    }
  }

  return (
    <div className="um-su-modal-overlay" onClick={onClose}>
      <div className="um-su-modal" onClick={e => e.stopPropagation()}>
        <div className="um-su-modal-header">
          <span className="um-su-modal-title">su 세션 — {user.id}@linux:~</span>
          <button className="um-su-modal-close" onClick={onClose}>x</button>
        </div>

        <div className="um-su-terminal-body" ref={bodyRef}>
          {/* 타이핑 애니메이션 줄 */}
          <div className="um-su-line cmd">
            <span>$ </span>{TYPING_TEXT.slice(0, typedChars)}
            {phase === 'typing' && <span style={{ borderRight: '1px solid #79c0ff', marginLeft: '1px' }}>&nbsp;</span>}
          </div>

          {lines.map(line => (
            <div key={line.id} className={`um-su-line ${line.cls}`}>
              {line.text}
            </div>
          ))}
        </div>

        {showInput && (
          <div className="um-su-input-row">
            <span className="um-su-prompt-label">{user.id}@linux:~$ </span>
            <input
              ref={inputRef}
              className="um-su-input"
              value={inputVal}
              onChange={e => setInputVal(e.target.value)}
              onKeyDown={handleKeyDown}
              spellCheck={false}
              autoComplete="off"
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default UsersPage
