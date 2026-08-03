import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProcessesPage from './Processes'
import { useAuth } from '../context/AuthContext'
import { wsManager } from '../api/client'

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../api/client', () => ({
  getAuthHeaders: vi.fn(() => ({ Authorization: 'Bearer synthetic-test-token' })),
  wsManager: {
    connect: vi.fn(() => Promise.resolve()),
    onData: vi.fn(),
  },
}))

const processSnapshot = {
  type: 'monitor.snapshot',
  top_processes: [
    {
      pid: 34567,
      name: 'demo-worker',
      cpu_pct: 1.5,
      mem_pct: 0.5,
    },
  ],
}

function renderProcesses(role) {
  useAuth.mockReturnValue({ user: { role } })
  wsManager.onData.mockImplementation((callback) => {
    callback(processSnapshot)
    return vi.fn()
  })

  render(<ProcessesPage />)
}

describe('ProcessesPage authorization controls', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('keeps process monitoring visible but removes kill actions for viewers', async () => {
    renderProcesses('viewer')

    expect(await screen.findByText('demo-worker')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Kill' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'kill 34567' })).not.toBeInTheDocument()
    expect(screen.queryByText('액션')).not.toBeInTheDocument()
  })

  it('shows kill actions for administrators', async () => {
    renderProcesses('admin')

    expect(await screen.findByText('demo-worker')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Kill' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'kill 34567' })).toBeInTheDocument()
  })
})
