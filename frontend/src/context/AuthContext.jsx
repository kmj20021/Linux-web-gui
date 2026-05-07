import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI, wsManager } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

  // 앱 시작 시 localStorage 토큰 검증
  useEffect(() => {
    const restoreSession = async () => {
      const savedToken = localStorage.getItem('auth_token')
      if (!savedToken) {
        setIsLoading(false)
        return
      }

      try {
        const userData = await authAPI.getMe(savedToken)
        setToken(savedToken)
        setUser(userData)
        setIsAuthenticated(true)
        // 세션 복원 성공 시 WebSocket 연결
        wsManager.connect().catch(err => {
          console.error('세션 복원 후 WebSocket 연결 실패:', err)
        })
      } catch (error) {
        // 토큰이 유효하지 않으면 제거
        localStorage.removeItem('auth_token')
      } finally {
        setIsLoading(false)
      }
    }

    restoreSession()
  }, [])

  const login = useCallback(async (username, password) => {
    const data = await authAPI.login(username, password)
    const { access_token, user: userData } = data

    localStorage.setItem('auth_token', access_token)
    setToken(access_token)
    setUser(userData)
    setIsAuthenticated(true)

    // 로그인 성공 시 WebSocket 연결
    wsManager.connect().catch(err => {
      console.error('로그인 후 WebSocket 연결 실패:', err)
    })

    return data
  }, [])

  const logout = useCallback(async () => {
    const savedToken = localStorage.getItem('auth_token')
    try {
      if (savedToken) {
        await authAPI.logout(savedToken)
      }
    } catch (error) {
      // 로그아웃 API 실패해도 로컬 상태는 초기화
      console.error('로그아웃 API 오류:', error)
    } finally {
      // 로그아웃 시 WebSocket 연결 해제
      wsManager.disconnect()
      localStorage.removeItem('auth_token')
      setToken(null)
      setUser(null)
      setIsAuthenticated(false)
      navigate('/login')
    }
  }, [navigate])

  const value = {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    logout,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth는 AuthProvider 내부에서만 사용할 수 있습니다.')
  }
  return context
}
