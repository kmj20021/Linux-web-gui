import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthProvider, useAuth } from '../context/AuthContext'
import { authAPI, onAuthExpired, wsManager } from '../api/client'

vi.mock('../api/client', () => ({
  authAPI: {
    getMe: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  },
  onAuthExpired: vi.fn(() => vi.fn()),
  wsManager: {
    connect: vi.fn(),
    disconnect: vi.fn(),
  },
}))

function AuthState() {
  const { isAuthenticated, isLoading, user } = useAuth()

  return (
    <output data-testid="auth-state">
      {`${isLoading}:${isAuthenticated}:${user?.username ?? 'anonymous'}`}
    </output>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('finishes restoring an anonymous session without requesting user data', async () => {
    render(
      <MemoryRouter>
        <AuthProvider>
          <AuthState />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('false:false:anonymous')
    })
    expect(authAPI.getMe).not.toHaveBeenCalled()
  })

  it('clears the stored session when any request reports an expired authentication', async () => {
    localStorage.setItem('auth_token', 'synthetic-test-token')
    authAPI.getMe.mockResolvedValue({ username: 'ops-admin', role: 'admin' })
    wsManager.connect.mockResolvedValue(undefined)

    render(
      <MemoryRouter>
        <AuthProvider>
          <AuthState />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('false:true:ops-admin')
    })

    // AuthProvider 는 client 의 전역 401 알림 하나만 구독한다.
    const notifyAuthExpired = onAuthExpired.mock.calls.at(-1)[0]
    notifyAuthExpired()

    await waitFor(() => {
      expect(screen.getByTestId('auth-state')).toHaveTextContent('false:false:anonymous')
    })
    expect(localStorage.getItem('auth_token')).toBeNull()
    expect(wsManager.disconnect).toHaveBeenCalled()
  })
})
