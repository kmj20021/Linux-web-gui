// 관리자 사용자 API 클라이언트.
// 권한은 서버가 강제한다. JSON 파싱·401 처리·timeout·오류 타입은 apiFetch 가 맡는다.

import { apiFetch } from '../../api/client'

export function fetchUsers() {
  return apiFetch('/admin/users')
}

export function createUser({ username, password, role }) {
  return apiFetch('/admin/users', { method: 'POST', body: { username, password, role } })
}

export function patchUser(id, payload) {
  return apiFetch(`/admin/users/${id}`, { method: 'PATCH', body: payload })
}

export function deleteUser(id) {
  return apiFetch(`/admin/users/${id}`, { method: 'DELETE' })
}
