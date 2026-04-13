import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import './App.css'

function Home() {
  const [status, setStatus] = useState('로딩 중...')

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setStatus('✅ 서버 연결 성공'))
      .catch(() => setStatus('❌ 서버 연결 실패'))
  }, [])

  return (
    <div className="home">
      <h1>🖥️ Linux Web GUI</h1>
      <p>라즈베리 파이 기반 시스템 관리</p>
      <div className="status">{status}</div>
    </div>
  )
}

function App() {
  return (
    <Router>
      <nav className="navbar">
        <div className="nav-brand">
          <Link to="/">🖥️ Linux Web GUI</Link>
        </div>
        <ul className="nav-links">
          <li><Link to="/">홈</Link></li>
          <li><Link to="/dashboard">대시보드</Link></li>
        </ul>
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </Router>
  )
}

export default App

