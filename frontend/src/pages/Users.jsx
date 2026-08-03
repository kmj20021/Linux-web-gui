import { useState } from 'react'
import '../styles/Processes.css'
import '../styles/UsersAdmin.css'

import { useUsers } from '../features/users/useUsers'
import CreateUserPanel from '../features/users/components/CreateUserPanel'
import DeleteConfirmModal from '../features/users/components/DeleteConfirmModal'
import UserListPanel from '../features/users/components/UserListPanel'

// 웹 GUI 계정 관리 페이지.
// 데이터 접근과 권한은 서버가 강제하며, 이 페이지는 목록·폼·확인 모달만 조립한다.
function UsersPage() {
  const [tab, setTab] = useState('list')
  const [pendingDelete, setPendingDelete] = useState(null)

  const { users, loading, error, actionError, reload, changeRole, setActive, remove, create } =
    useUsers()

  const handleDeleteConfirm = async () => {
    const target = pendingDelete
    setPendingDelete(null)
    if (target) await remove(target.id)
  }

  const handleCreate = async (payload) => {
    await create(payload)
  }

  return (
    <div className="processes-page">
      {pendingDelete && (
        <DeleteConfirmModal
          user={pendingDelete}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setPendingDelete(null)}
        />
      )}

      <div className="page-header">
        <h1>사용자 관리</h1>
        <p className="page-subtitle">웹 GUI 계정을 관리합니다.</p>
      </div>

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
          actionError={actionError}
          onRefresh={reload}
          onRoleChange={changeRole}
          onToggleActive={setActive}
          onDelete={setPendingDelete}
        />
      )}

      {tab === 'create' && (
        <CreateUserPanel onCreate={handleCreate} onDone={() => setTab('list')} />
      )}
    </div>
  )
}

export default UsersPage
