import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'

import Dashboard from '../pages/Dashboard'
import FilesystemPage from '../pages/Filesystem'
import NetworkDiagnostics from '../pages/NetworkDiagnostics'
import NetworkPage from '../pages/Network'
import ProcessesPage from '../pages/Processes'
import UsersPage from '../pages/Users'
import FileExplorer from '../components/FileExplorer'
import { useAuth } from '../context/AuthContext'
import { apiFetch, networkAPI, wsManager } from '../api/client'
import * as usersApi from '../features/users/usersApi'

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(() => ({ user: { username: 'ops-admin', role: 'admin' } })),
}))

vi.mock('../api/client', () => ({
  getAuthHeaders: vi.fn(() => ({ Authorization: 'Bearer synthetic-test-token' })),
  apiFetch: vi.fn(),
  wsManager: {
    isConnected: true,
    connect: vi.fn(() => Promise.resolve()),
    onData: vi.fn(() => vi.fn()),
    onStatusChange: vi.fn(() => vi.fn()),
  },
  networkAPI: {
    getInterfaces: vi.fn(),
    getTraffic: vi.fn(),
    getPackets: vi.fn(),
    getConnections: vi.fn(),
  },
}))

vi.mock('../features/users/usersApi', () => ({
  fetchUsers: vi.fn(),
  createUser: vi.fn(),
  patchUser: vi.fn(),
  deleteUser: vi.fn(),
}))

const SNAPSHOT = {
  type: 'monitor.snapshot',
  cpu: { total: 12.5, per_core: [10, 15], core_count: 2, load_avg: [0.1, 0.2, 0.3] },
  memory: { total_gb: 8, used_gb: 3, free_gb: 5, usage_pct: 37.5 },
  timestamp: '2026-02-01T00:00:00Z',
  top_processes: [
    { pid: 1010, name: 'demo-worker', cpu_pct: 22.5, mem_pct: 3.5 },
    { pid: 2020, name: 'demo-indexer', cpu_pct: 8.25, mem_pct: 11.5 },
  ],
}

const INTERFACES = [
  { name: 'eth0', status: 'up', ipv4: '10.0.0.5', mac: '02:aa:bb:cc:dd:ee', mtu: 1500 },
  { name: 'lo', status: 'up', ipv4: '127.0.0.1', mac: '00:00:00:00:00:00', mtu: 65536 },
]

// 실제 접근성 위반 중 심각도가 높은 것만 게이트로 삼는다.
const SERIOUS_IMPACTS = new Set(['serious', 'critical'])

async function expectNoSeriousViolations(container) {
  const results = await axe(container)
  const serious = results.violations.filter(v => SERIOUS_IMPACTS.has(v.impact))
  expect(serious.map(v => `${v.id}: ${v.help}`)).toEqual([])
  expect(results).toHaveNoViolations()
}

function mockSnapshotStream() {
  wsManager.onData.mockImplementation((callback) => {
    callback(SNAPSHOT)
    return vi.fn()
  })
}

describe('automated accessibility checks', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { username: 'ops-admin', role: 'admin' } })
    wsManager.isConnected = true
    wsManager.onStatusChange.mockReturnValue(vi.fn())
    mockSnapshotStream()
    usersApi.fetchUsers.mockResolvedValue([
      { id: 1, username: 'ops-admin', role: 'admin', is_active: true, created_at: '2026-01-02T00:00:00Z' },
      { id: 2, username: 'ops-viewer', role: 'viewer', is_active: true, created_at: '2026-01-03T00:00:00Z' },
    ])
    networkAPI.getInterfaces.mockResolvedValue(INTERFACES)
    networkAPI.getTraffic.mockResolvedValue([])
    networkAPI.getPackets.mockResolvedValue([])
    networkAPI.getConnections.mockResolvedValue([])
  })

  it('dashboard has no serious violations', async () => {
    const { container } = render(<Dashboard />)
    await expectNoSeriousViolations(container)
  })

  it('processes page has no serious violations', async () => {
    const { container } = render(<ProcessesPage />)
    await screen.findByText('demo-worker')
    await expectNoSeriousViolations(container)
  })

  it('filesystem page has no serious violations', async () => {
    const { container } = render(<FilesystemPage />)
    await expectNoSeriousViolations(container)
  })

  it('network diagnostics page has no serious violations', async () => {
    const { container } = render(<NetworkDiagnostics />)
    await expectNoSeriousViolations(container)
  })

  it('network page has no serious violations', async () => {
    const { container } = render(<NetworkPage />)
    await screen.findByText('eth0')
    await expectNoSeriousViolations(container)
  })

  it('users page has no serious violations', async () => {
    const { container } = render(<UsersPage />)
    await screen.findByText('ops-viewer')
    await expectNoSeriousViolations(container)
  })
})

describe('keyboard operability', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ user: { username: 'ops-admin', role: 'admin' } })
    mockSnapshotStream()
  })

  it('exposes sortable process columns as buttons carrying aria-sort', async () => {
    render(<ProcessesPage />)
    await screen.findByText('demo-worker')

    const cpuHeader = screen.getByRole('columnheader', { name: /CPU %/ })
    expect(cpuHeader).toHaveAttribute('aria-sort', 'descending')

    const pidHeader = screen.getByRole('columnheader', { name: /PID/ })
    expect(pidHeader).toHaveAttribute('aria-sort', 'none')
    expect(within(pidHeader).getByRole('button')).toBeInTheDocument()
  })

  it('sorts from the keyboard alone', async () => {
    render(<ProcessesPage />)
    await screen.findByText('demo-worker')

    const pidButton = within(screen.getByRole('columnheader', { name: /PID/ })).getByRole('button')
    pidButton.focus()
    expect(pidButton).toHaveFocus()

    fireEvent.click(pidButton) // Enter/Space 는 브라우저가 button 에서 click 으로 변환한다
    expect(screen.getByRole('columnheader', { name: /PID/ })).toHaveAttribute('aria-sort', 'descending')

    const rows = screen.getAllByRole('row').slice(1)
    expect(within(rows[0]).getByText('2020')).toBeInTheDocument()
  })

  it('keeps a row bound to its process when the sort order changes', async () => {
    render(<ProcessesPage />)
    await screen.findByText('demo-worker')

    const workerRow = screen.getByText('demo-worker').closest('tr')
    fireEvent.click(within(screen.getByRole('columnheader', { name: /PID/ })).getByRole('button'))

    // index 를 key 로 쓰면 재정렬 뒤 같은 자리의 다른 DOM 노드가 재사용된다.
    expect(screen.getByText('demo-worker').closest('tr')).toBe(workerRow)
  })

  it('lets the network tabs be reached and switched as an ARIA tablist', async () => {
    networkAPI.getInterfaces.mockResolvedValue(INTERFACES)
    networkAPI.getTraffic.mockResolvedValue([])
    networkAPI.getPackets.mockResolvedValue([])
    networkAPI.getConnections.mockResolvedValue([])

    render(<NetworkPage />)
    await screen.findByText('eth0')

    const tabs = within(screen.getByRole('tablist')).getAllByRole('tab')
    expect(tabs[0]).toHaveAttribute('aria-selected', 'true')

    tabs[1].focus()
    fireEvent.click(tabs[1])

    await waitFor(() => expect(tabs[1]).toHaveAttribute('aria-selected', 'true'))
    expect(tabs[0]).toHaveAttribute('aria-selected', 'false')
    expect(screen.getByRole('tabpanel')).toBeInTheDocument()
  })
})

describe('file explorer tree accessibility', () => {
  const TREE = {
    path: '/home/user',
    name: 'user',
    type: 'directory',
    children: [
      { path: '/home/user/notes.txt', name: 'notes.txt', type: 'file' },
      { path: '/home/user/work', name: 'work', type: 'directory', children: [] },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    apiFetch.mockResolvedValue({ tree: TREE })
  })

  it('exposes the tree with keyboard-focusable items and no serious violations', async () => {
    const onNavigate = vi.fn()
    const { container } = render(
      <FileExplorer sessionId="synthetic-session" currentCwd="/home/user" onNavigate={onNavigate} />,
    )

    const tree = await screen.findByRole('tree')
    expect(tree).toBeInTheDocument()

    const items = within(tree).getAllByRole('treeitem')
    expect(items.length).toBeGreaterThan(1)
    items.forEach(item => expect(item).toHaveAttribute('tabindex', '0'))

    const workItem = items.find(item => item.textContent.includes('work'))
    workItem.focus()
    expect(workItem).toHaveFocus()

    fireEvent.keyDown(workItem, { key: 'Enter' })
    await waitFor(() => expect(onNavigate).toHaveBeenCalledWith('/home/user/work'))

    const results = await axe(container)
    const serious = results.violations.filter(v => SERIOUS_IMPACTS.has(v.impact))
    expect(serious.map(v => `${v.id}: ${v.help}`)).toEqual([])
  })

  it('activates a file entry with the space key', async () => {
    const onFileClick = vi.fn()
    render(
      <FileExplorer sessionId="synthetic-session" currentCwd="/home/user" onFileClick={onFileClick} />,
    )

    const tree = await screen.findByRole('tree')
    const fileItem = within(tree)
      .getAllByRole('treeitem')
      .find(item => item.textContent.includes('notes.txt'))

    fireEvent.keyDown(fileItem, { key: ' ' })
    await waitFor(() => expect(onFileClick).toHaveBeenCalledWith('/home/user/notes.txt'))
  })
})
