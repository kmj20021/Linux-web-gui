import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import UsersPage from './Users'
import { useAuth } from '../context/AuthContext'
import * as usersApi from '../features/users/usersApi'

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../features/users/usersApi', () => ({
  fetchUsers: vi.fn(),
  createUser: vi.fn(),
  patchUser: vi.fn(),
  deleteUser: vi.fn(),
}))

const ADMIN = { id: 1, username: 'ops-admin', role: 'admin', is_active: true, created_at: '2026-01-02T00:00:00Z' }
const VIEWER = { id: 2, username: 'ops-viewer', role: 'viewer', is_active: true, created_at: '2026-01-03T00:00:00Z' }

function renderUsers(users = [ADMIN, VIEWER]) {
  useAuth.mockReturnValue({ user: { username: 'ops-admin', role: 'admin' } })
  usersApi.fetchUsers.mockResolvedValue(users)
  render(<UsersPage />)
}

function rowFor(username) {
  return screen.getByText(username).closest('tr')
}

// 탭 버튼과 폼 제출 버튼이 같은 이름이므로 제출 버튼만 골라낸다.
function submitCreateForm() {
  const submit = screen
    .getAllByRole('button', { name: '계정 생성' })
    .find(button => button.getAttribute('type') === 'submit')
  fireEvent.click(submit)
}

describe('UsersPage admin CRUD', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('lists accounts with their role and status', async () => {
    renderUsers()

    expect(await screen.findByText('ops-viewer')).toBeInTheDocument()
    expect(within(rowFor('ops-viewer')).getByTestId('ua-role')).toHaveTextContent('viewer')
    expect(within(rowFor('ops-viewer')).getByTestId('ua-status')).toHaveTextContent('활성')
  })

  it('marks the signed-in account and hides self-mutating controls', async () => {
    renderUsers()

    const myRow = within(await screen.findByText('ops-admin').then(el => el.closest('tr')))
    expect(myRow.getByText('내 계정')).toBeInTheDocument()
    expect(myRow.queryByRole('button', { name: '삭제' })).not.toBeInTheDocument()
    expect(myRow.queryByRole('combobox')).not.toBeInTheDocument()
  })

  it('surfaces a list load failure with a retry action', async () => {
    useAuth.mockReturnValue({ user: { username: 'ops-admin', role: 'admin' } })
    usersApi.fetchUsers.mockRejectedValueOnce(new Error('사용자 목록 조회 실패: 403'))
    render(<UsersPage />)

    expect(await screen.findByText(/사용자 목록 조회 실패: 403/)).toBeInTheDocument()

    usersApi.fetchUsers.mockResolvedValue([VIEWER])
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    expect(await screen.findByText('ops-viewer')).toBeInTheDocument()
  })

  it('changes another account role through the API', async () => {
    renderUsers()
    usersApi.patchUser.mockResolvedValue({ ...VIEWER, role: 'admin' })

    await screen.findByText('ops-viewer')
    fireEvent.change(within(rowFor('ops-viewer')).getByRole('combobox'), {
      target: { value: 'admin' },
    })

    await waitFor(() =>
      expect(within(rowFor('ops-viewer')).getByTestId('ua-role')).toHaveTextContent('admin'))
  })

  it('deactivates another account through the API', async () => {
    renderUsers()
    usersApi.patchUser.mockResolvedValue({ ...VIEWER, is_active: false })

    await screen.findByText('ops-viewer')
    fireEvent.click(within(rowFor('ops-viewer')).getByRole('button', { name: '비활성화' }))

    await waitFor(() =>
      expect(within(rowFor('ops-viewer')).getByTestId('ua-status')).toHaveTextContent('비활성'))
  })

  it('shows the userdel command before deleting and removes the row on confirm', async () => {
    renderUsers()
    usersApi.deleteUser.mockResolvedValue({})

    await screen.findByText('ops-viewer')
    fireEvent.click(within(rowFor('ops-viewer')).getByRole('button', { name: '삭제' }))

    expect(screen.getByText('sudo userdel -r ops-viewer')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '삭제 확인' }))

    await waitFor(() => expect(usersApi.deleteUser).toHaveBeenCalledWith(2))
    await waitFor(() => expect(screen.queryByText('ops-viewer')).not.toBeInTheDocument())
  })

  it('keeps the row and reports the reason when a delete is rejected', async () => {
    renderUsers()
    usersApi.deleteUser.mockRejectedValue(new Error('마지막 활성 관리자는 삭제할 수 없습니다.'))

    await screen.findByText('ops-viewer')
    fireEvent.click(within(rowFor('ops-viewer')).getByRole('button', { name: '삭제' }))
    fireEvent.click(screen.getByRole('button', { name: '삭제 확인' }))

    expect(await screen.findByText('마지막 활성 관리자는 삭제할 수 없습니다.')).toBeInTheDocument()
    expect(screen.getByText('ops-viewer')).toBeInTheDocument()
  })

  it('validates the creation form before calling the API', async () => {
    renderUsers()
    await screen.findByText('ops-viewer')

    fireEvent.click(screen.getByRole('button', { name: '계정 생성' }))
    fireEvent.change(screen.getByLabelText('사용자명'), { target: { value: 'new-op' } })
    fireEvent.change(screen.getByLabelText('비밀번호'), { target: { value: 'correct horse' } })
    fireEvent.change(screen.getByLabelText('비밀번호 확인'), { target: { value: 'different' } })
    submitCreateForm()

    expect(await screen.findByText('비밀번호가 일치하지 않습니다.')).toBeInTheDocument()
    expect(usersApi.createUser).not.toHaveBeenCalled()
  })

  it('creates an account and shows it in the list', async () => {
    renderUsers()
    usersApi.createUser.mockResolvedValue({
      id: 3, username: 'new-op', role: 'viewer', is_active: true, created_at: '2026-02-01T00:00:00Z',
    })
    await screen.findByText('ops-viewer')

    fireEvent.click(screen.getByRole('button', { name: '계정 생성' }))
    fireEvent.change(screen.getByLabelText('사용자명'), { target: { value: '  new-op  ' } })
    fireEvent.change(screen.getByLabelText('비밀번호'), { target: { value: 'correct horse' } })
    fireEvent.change(screen.getByLabelText('비밀번호 확인'), { target: { value: 'correct horse' } })
    submitCreateForm()

    await waitFor(() => expect(usersApi.createUser).toHaveBeenCalledWith({
      username: 'new-op',
      password: 'correct horse',
      role: 'viewer',
    }))

    fireEvent.click(await screen.findByRole('button', { name: '목록으로 돌아가기' }))
    expect(await screen.findByText('new-op')).toBeInTheDocument()
  })

  it('previews the CLI equivalent of the account being created', async () => {
    renderUsers()
    await screen.findByText('ops-viewer')

    fireEvent.click(screen.getByRole('button', { name: '계정 생성' }))
    fireEvent.change(screen.getByLabelText('사용자명'), { target: { value: 'new-op' } })

    expect(screen.getByText('sudo useradd -m -s /bin/bash new-op')).toBeInTheDocument()
    expect(screen.queryByText(/usermod -aG sudo/)).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('역할'), { target: { value: 'admin' } })
    expect(screen.getByText('sudo usermod -aG sudo new-op')).toBeInTheDocument()
  })
})
