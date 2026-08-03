import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi } from 'vitest'
import ProtectedRoute from '../components/ProtectedRoute'
import { useAuth } from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

function renderRoute(authState) {
  useAuth.mockReturnValue(authState)

  render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route
          path="/admin"
          element={(
            <ProtectedRoute requiredRole="admin">
              <div>Protected content</div>
            </ProtectedRoute>
          )}
        />
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('redirects unauthenticated users to the login route', () => {
    renderRoute({ isAuthenticated: false, isLoading: false, user: null })

    expect(screen.getByText('Login page')).toBeInTheDocument()
  })

  it('shows the permission error when a viewer opens an admin route', () => {
    renderRoute({ isAuthenticated: true, isLoading: false, user: { role: 'viewer' } })

    expect(screen.getByText('접근 권한이 없습니다')).toBeInTheDocument()
  })

  it('renders children for an authenticated admin', () => {
    renderRoute({ isAuthenticated: true, isLoading: false, user: { role: 'admin' } })

    expect(screen.getByText('Protected content')).toBeInTheDocument()
  })
})
