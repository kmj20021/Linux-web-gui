import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import '../styles/Sidebar.css'

function Sidebar() {
  const location = useLocation()
  const { user, logout } = useAuth()

  const menuSections = [
    {
      label: '모니터링',
      items: [
        { path: '/dashboard', label: '대시보드', icon: dashboardIcon() },
        { path: '/monitor/processes', label: '프로세스', icon: processIcon() },
        { path: '/network', label: '네트워크', icon: networkIcon() },
      ]
    },
    {
      label: '시스템',
      items: [
        { path: '/filesystem', label: '파일시스템', icon: filesystemIcon() },
        { path: '/users', label: '사용자 관리', icon: usersIcon() },
        { path: '/terminal', label: '터미널', icon: terminalIcon() },
      ]
    },
    {
      label: '관리',
      items: [
        { path: '/audit', label: '감사 로그', icon: auditIcon() },
      ]
    }
  ]

  const displayName = user?.username || 'admin'
  const displayRole = user?.role || '관리자'
  const avatarChar = displayName.charAt(0).toUpperCase()

  const handleLogout = async () => {
    try {
      await logout()
    } catch (e) {
      console.error('로그아웃 오류:', e)
    }
  }

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="brand-icon">
          <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="2" width="5" height="5" rx="1" fill="white" opacity="0.9"/>
            <rect x="9" y="2" width="5" height="5" rx="1" fill="white" opacity="0.7"/>
            <rect x="2" y="9" width="5" height="5" rx="1" fill="white" opacity="0.7"/>
            <rect x="9" y="9" width="5" height="5" rx="1" fill="white" opacity="0.5"/>
          </svg>
        </div>
        <div>
          <div className="brand-text">LinuxViz</div>
          <div className="brand-sub">AWS EC2 · Ubuntu</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {menuSections.map((section, idx) => (
          <div key={idx}>
            <div className="nav-section-title">{section.label}</div>
            {section.items.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
                {item.badge && <span className="nav-badge">{item.badge}</span>}
              </Link>
            ))}
          </div>
        ))}
      </nav>

      {/* User Chip + Logout */}
      <div className="sidebar-bottom">
        <div className="user-chip">
          <div className="avatar">{avatarChar}</div>
          <div className="user-info">
            <div className="user-name">{displayName}</div>
            <div className="user-role">{displayRole}</div>
          </div>
          <button
            className="logout-button"
            onClick={handleLogout}
            title="로그아웃"
            aria-label="로그아웃"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M5 2H2.5A1.5 1.5 0 0 0 1 3.5v7A1.5 1.5 0 0 0 2.5 12H5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
              <path d="M9.5 9.5L13 7l-3.5-2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M13 7H5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
      </div>
    </aside>
  )
}

// SVG 아이콘 헬퍼 함수 (이모지 대체)
function dashboardIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="1" y="1" width="5" height="5" rx="1" fill="currentColor" opacity="0.8"/>
      <rect x="8" y="1" width="5" height="5" rx="1" fill="currentColor" opacity="0.6"/>
      <rect x="1" y="8" width="5" height="5" rx="1" fill="currentColor" opacity="0.6"/>
      <rect x="8" y="8" width="5" height="5" rx="1" fill="currentColor" opacity="0.4"/>
    </svg>
  )
}

function processIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3"/>
      <circle cx="7" cy="7" r="2" fill="currentColor" opacity="0.7"/>
    </svg>
  )
}

function networkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="2" r="1.5" fill="currentColor" opacity="0.8"/>
      <circle cx="2" cy="11" r="1.5" fill="currentColor" opacity="0.8"/>
      <circle cx="12" cy="11" r="1.5" fill="currentColor" opacity="0.8"/>
      <path d="M7 3.5v2M7 5.5L2 9.5M7 5.5L12 9.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  )
}

function filesystemIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M1 4a1 1 0 0 1 1-1h3l1.5 2H12a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V4z" stroke="currentColor" strokeWidth="1.3" fill="none"/>
    </svg>
  )
}

function usersIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="5.5" cy="4.5" r="2" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M1 12c0-2.21 2.015-4 4.5-4s4.5 1.79 4.5 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <circle cx="10.5" cy="4" r="1.5" stroke="currentColor" strokeWidth="1.2" opacity="0.7"/>
      <path d="M12.5 11c0-1.657-1.343-3-2-3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.7"/>
    </svg>
  )
}

function auditIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="2" y="1" width="10" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M4.5 5h5M4.5 7.5h5M4.5 10h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  )
}

function terminalIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="1" y="2" width="12" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.2"/>
      <path d="M3.5 5L5.5 7L3.5 9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M7 9h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    </svg>
  )
}

export default Sidebar
