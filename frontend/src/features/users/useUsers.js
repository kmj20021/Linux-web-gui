import { useCallback, useEffect, useState } from 'react'
import { createUser, deleteUser, fetchUsers, patchUser } from './usersApi'

// 사용자 목록과 CRUD를 담당하는 Hook.
//
// 목록 로드 실패(`error`)와 개별 조작 실패(`actionError`)를 나눠서 돌려준다.
// 조작이 실패하면 서버 상태를 그대로 두고 이유만 화면에 남긴다.
export function useUsers() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setUsers(await fetchUsers())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    reload()
  }, [reload])

  // 조작 실패는 목록을 바꾸지 않고 사유만 남긴다.
  const runAction = useCallback(async (action) => {
    setActionError(null)
    try {
      await action()
      return true
    } catch (e) {
      setActionError(e.message)
      return false
    }
  }, [])

  const changeRole = useCallback((id, role) => runAction(async () => {
    const updated = await patchUser(id, { role })
    setUsers(prev => prev.map(u => (u.id === id ? { ...u, role: updated.role } : u)))
  }), [runAction])

  const setActive = useCallback((id, isActive) => runAction(async () => {
    const updated = await patchUser(id, { is_active: isActive })
    setUsers(prev => prev.map(u => (u.id === id ? { ...u, is_active: updated.is_active } : u)))
  }), [runAction])

  const remove = useCallback((id) => runAction(async () => {
    await deleteUser(id)
    setUsers(prev => prev.filter(u => u.id !== id))
  }), [runAction])

  // 생성 폼은 자체 오류 표시가 있으므로 실패를 그대로 던진다.
  const create = useCallback(async (payload) => {
    const created = await createUser(payload)
    setUsers(prev => [...prev, created])
    return created
  }, [])

  return { users, loading, error, actionError, reload, changeRole, setActive, remove, create }
}
