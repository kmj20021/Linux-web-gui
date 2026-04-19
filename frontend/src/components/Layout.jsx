import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import WebSocketStatus from './WebSocketStatus'
import '../styles/Layout.css'

function Layout({ children }) {
  const location = useLocation()

  return (
    <div className="layout-container">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="main-wrapper">
        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-content">
            <h1 className="topbar-title">
              {getPageTitle(location.pathname)}
            </h1>
            <div className="topbar-right">
              <WebSocketStatus compact={true} />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="main-content">
          {children}
        </main>

        {/* Footer */}
        <footer className="footer">
          <p>&copy; 2026 Linux Web GUI - 라즈베리 파이 기반 시스템 관리</p>
        </footer>
      </div>
    </div>
  )
}

function getPageTitle(pathname) {
  const titles = {
    '/dashboard': '대시보드',
    '/monitor/processes': '프로세스',
    '/filesystem': '파일시스템',
    '/users': '사용자 관리',
    '/network': '네트워크',
    '/audit': '감사 로그',
  }
  return titles[pathname] || 'Linux Web GUI'
}

export default Layout
