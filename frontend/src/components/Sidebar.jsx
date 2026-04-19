import { Link, useLocation } from 'react-router-dom'
import '../styles/Sidebar.css'

function Sidebar() {
  const location = useLocation()

  const menuSections = [
    {
      label: '모니터링',
      items: [
        { path: '/dashboard', label: '대시보드', icon: '📊' },
        { path: '/monitor/processes', label: '프로세스', icon: '⚙️' },
        { path: '/network', label: '네트워크', icon: '🌐' },
      ]
    },
    {
      label: '시스템',
      items: [
        { path: '/filesystem', label: '파일시스템', icon: '📁' },
        { path: '/users', label: '사용자 관리', icon: '👥', badge: '3' },
      ]
    },
    {
      label: '관리',
      items: [
        { path: '/audit', label: '감사 로그', icon: '📋', badge: '2' },
      ]
    }
  ]

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

      {/* User Chip */}
      <div className="sidebar-bottom">
        <div className="user-chip">
          <div className="avatar">관</div>
          <div className="user-info">
            <div className="user-name">admin</div>
            <div className="user-role">관리자</div>
          </div>
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M4 2l4 4-4 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
