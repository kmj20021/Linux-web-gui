import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [status, setStatus] = useState('로딩 중...')

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setStatus('✅ 서버 연결 성공'))
      .catch(() => setStatus('❌ 서버 연결 실패'))
  }, [])

  return (
    <div className="App">
      <h1>🖥️ Linux Web GUI</h1>
      <p>라즈베리 파이 기반 시스템 관리</p>
      <div className="status">{status}</div>
    </div>
  )
}

export default App
