import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Processes from './pages/Processes'
import Filesystem from './pages/Filesystem'
import Users from './pages/Users'
import Network from './pages/Network'
import Audit from './pages/Audit'
import Terminal from './pages/Terminal'
import { monitoringAPI } from './api/client'
import './App.css'

function Home() {
  const [status, setStatus] = useState('로딩 중...')

  useEffect(() => {
    checkServerHealth()
    // 서버 상태를 주기적으로 확인 (5초마다)
    const interval = setInterval(checkServerHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  const checkServerHealth = async () => {
    try {
      const controller = new AbortController()
      const timeout = setTimeout(() => controller.abort(), 3000)

      await monitoringAPI.getCPU()
      clearTimeout(timeout)
      setStatus('서버 연결 성공')
    } catch (error) {
      setStatus(`서버 연결 실패: ${error.message}`)
    }
  }

  return (
    <div className="home">
      <h1>Linux Web GUI</h1>
      <p>라즈베리 파이 기반 시스템 관리 시스템</p>
      <div className="status">{status}</div>
      <Link to="/dashboard" className="dashboard-link">
        대시보드로 이동
      </Link>
    </div>
  )
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          {/* 공개 라우트 */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* 보호된 라우트 */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout>
                  <Home />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Layout>
                  <Dashboard />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/monitor/processes"
            element={
              <ProtectedRoute>
                <Layout>
                  <Processes />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/filesystem"
            element={
              <ProtectedRoute>
                <Layout>
                  <Filesystem />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute>
                <Layout>
                  <Users />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/network"
            element={
              <ProtectedRoute>
                <Layout>
                  <Network />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit"
            element={
              <ProtectedRoute>
                <Layout>
                  <Audit />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/terminal"
            element={
              <ProtectedRoute>
                <Layout>
                  <Terminal />
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </Router>
  )
}

export default App
