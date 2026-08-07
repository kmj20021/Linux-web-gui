import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AITutor from './AITutor'
import { aiTutorAPI } from '../api/aiTutor'

vi.mock('../api/aiTutor', () => ({
  aiTutorAPI: {
    curriculum: vi.fn(),
    createSession: vi.fn(),
    getSession: vi.fn(),
    getHistory: vi.fn(),
    command: vi.fn(),
    narrateCommand: vi.fn(),
    chat: vi.fn(),
    hint: vi.fn(),
    grade: vi.fn(),
    reset: vi.fn(),
  },
  AITutorAPIError: class AITutorAPIError extends Error {
    constructor(message, status, retryAfter = 0) {
      super(message)
      this.status = status
      this.retryAfter = retryAfter
    }
  },
}))

const problem = {
  scenario_id: 'service_recovery', task_id: 'service_recovery_01',
  title: 'nginx 복구', difficulty: 'beginner', task_index: 1, total_tasks: 6,
  description: 'nginx를 복구하세요', learning_goal: 'systemctl 사용법',
}

const session = {
  id: 1, status: 'in_progress', current_problem: problem,
  virtual_state: { version: 1, state_json: {} },
}

async function startSession() {
  aiTutorAPI.curriculum.mockResolvedValue({ items: [problem] })
  aiTutorAPI.createSession.mockResolvedValue(session)
  render(<AITutor />)
  await screen.findByText('nginx 복구')
  fireEvent.click(screen.getByText('nginx 복구'))
  await screen.findByPlaceholderText('명령 입력 (예: systemctl status nginx)')
}

function runCommand(text) {
  const input = screen.getByPlaceholderText('명령 입력 (예: systemctl status nginx)')
  fireEvent.change(input, { target: { value: text } })
  fireEvent.click(screen.getByRole('button', { name: '실행' }))
}

// Scoped to each panel so terminal-vs-helper placement is asserted precisely.
function terminalLog() {
  return within(document.querySelector('.ai-log-terminal'))
}
function chatLog() {
  return within(document.querySelector('.ai-log-chat'))
}

describe('AITutor command narration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows the deterministic output in the terminal and the AI narration in the helper panel', async () => {
    await startSession()
    aiTutorAPI.command.mockResolvedValue({
      result_code: 'unsupported_syntax', output: 'unsupported_syntax',
      attempt_id: 42, version: 1,
    })
    let resolveNarrate
    aiTutorAPI.narrateCommand.mockReturnValue(new Promise((resolve) => { resolveNarrate = resolve }))

    runCommand('pwd')

    expect(await terminalLog().findByText('unsupported_syntax')).toBeInTheDocument()
    await waitFor(() => expect(aiTutorAPI.narrateCommand).toHaveBeenCalledWith(1, 42))
    expect(chatLog().queryByText('[SIMULATION] 현재 디렉터리 확인')).not.toBeInTheDocument()

    resolveNarrate({ narration: { degraded: false, terminal_output: '[SIMULATION] 현재 디렉터리 확인' } })

    expect(await chatLog().findByText('[SIMULATION] 현재 디렉터리 확인')).toBeInTheDocument()
    expect(chatLog().getByText('$ pwd')).toBeInTheDocument()
    // The terminal keeps showing the raw deterministic text unchanged.
    expect(terminalLog().getByText('unsupported_syntax')).toBeInTheDocument()
  })

  it('adds nothing to the helper panel when narration is degraded or fails', async () => {
    await startSession()
    aiTutorAPI.command.mockResolvedValue({
      result_code: 'unsupported_syntax', output: 'unsupported_syntax',
      attempt_id: 7, version: 1,
    })
    aiTutorAPI.narrateCommand.mockResolvedValue({ narration: { degraded: true, terminal_output: '' } })

    runCommand('whoami')

    await terminalLog().findByText('unsupported_syntax')
    await waitFor(() => expect(aiTutorAPI.narrateCommand).toHaveBeenCalled())
    expect(terminalLog().getByText('unsupported_syntax')).toBeInTheDocument()
    expect(chatLog().queryByText('$ whoami')).not.toBeInTheDocument()
  })

  it('never calls narrateCommand for a successful command', async () => {
    await startSession()
    aiTutorAPI.command.mockResolvedValue({
      result_code: 'success', output: 'active', attempt_id: 9, version: 2,
    })

    runCommand('systemctl status nginx')

    await screen.findByText('active')
    expect(aiTutorAPI.narrateCommand).not.toHaveBeenCalled()
  })
})
