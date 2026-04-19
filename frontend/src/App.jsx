import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Processes from './pages/Processes'
import Filesystem from './pages/Filesystem'
import Users from './pages/Users'
import Network from './pages/Network'
import Audit from './pages/Audit'
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
      setStatus('✅ 서버 연결 성공')
    } catch (error) {
      setStatus(`❌ 서버 연결 실패: ${error.message}`)
    }
  }

  return (
    <div className="home">
      <h1>🖥️ Linux Web GUI</h1>
      <p>라즈베리 파이 기반 시스템 관리 시스템</p>
      <div className="status">{status}</div>
      <Link to="/dashboard" className="dashboard-link">
        대시보드로 이동 →
      </Link>
    </div>
  )
}

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/monitor/processes" element={<Processes />} />
          <Route path="/filesystem" element={<Filesystem />} />
          <Route path="/users" element={<Users />} />
          <Route path="/network" element={<Network />} />
          <Route path="/audit" element={<Audit />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App

