import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import NetworkDiagnostics from './NetworkDiagnostics'

function selectTool(label) {
  fireEvent.click(within(screen.getByTestId('nd-tool-list')).getByText(label))
}

describe('NetworkDiagnostics simulation page', () => {
  it('always states that the output is simulated and sends no network request', () => {
    render(<NetworkDiagnostics />)

    const notice = screen.getByTestId('nd-simulation-notice')
    expect(notice.textContent).toMatch(/교육용 시뮬레이션/)
    expect(notice.textContent).toMatch(/실제\s*네트워크 요청을 보내지 않습니다/)
  })

  it('labels the action and the log as simulation rather than execution', () => {
    render(<NetworkDiagnostics />)

    expect(screen.getByRole('button', { name: /시뮬레이션/ })).toBeInTheDocument()
    expect(screen.queryByText('커맨드 로그')).not.toBeInTheDocument()
    expect(screen.getByText('시뮬레이션한 명령 기록')).toBeInTheDocument()
    expect(within(screen.getByTestId('nd-log')).getByText(/시뮬레이션/)).toBeInTheDocument()
  })

  it('keeps the run action disabled until a tool is selected', () => {
    render(<NetworkDiagnostics />)

    expect(screen.getByRole('button', { name: /시뮬레이션/ })).toBeDisabled()

    selectTool('Ping')

    expect(screen.getByRole('button', { name: /시뮬레이션/ })).toBeEnabled()
  })

  it('runs a ping simulation and records the command', () => {
    render(<NetworkDiagnostics />)

    selectTool('Ping')
    fireEvent.click(screen.getByRole('button', { name: /시뮬레이션 ping/ }))
    fireEvent.click(screen.getByRole('button', { name: '시뮬레이션' }))

    expect(within(screen.getByTestId('nd-log')).getByText('ping -c 4 google.com')).toBeInTheDocument()
    expect(screen.getByTestId('nd-result').textContent).toMatch(/PING google\.com/)
    expect(screen.getByText('시뮬레이션 결과 (실제 응답 아님)')).toBeInTheDocument()
  })

  it('shows the command preview as something to simulate, not to execute', () => {
    render(<NetworkDiagnostics />)

    selectTool('Ping')
    fireEvent.click(screen.getByRole('button', { name: /시뮬레이션 ping/ }))

    expect(screen.getByText('시뮬레이션할 명령어: ping -c 4 google.com')).toBeInTheDocument()
    expect(screen.queryByText(/실행될 명령어/)).not.toBeInTheDocument()
  })

  it('rejects a host containing shell metacharacters and produces no output', () => {
    render(<NetworkDiagnostics />)

    selectTool('Ping')
    fireEvent.click(screen.getByRole('button', { name: /시뮬레이션 ping/ }))
    fireEvent.change(screen.getByLabelText('호스트'), {
      target: { value: 'google.com; rm -rf /' },
    })
    fireEvent.click(screen.getByRole('button', { name: '시뮬레이션' }))

    expect(screen.getByRole('alert')).toHaveTextContent(
      '호스트에는 영문, 숫자, 점(.), 하이픈(-)만 사용할 수 있습니다.',
    )
    expect(screen.queryByTestId('nd-result')).not.toBeInTheDocument()
    expect(within(screen.getByTestId('nd-log')).queryByText(/rm -rf/)).not.toBeInTheDocument()
  })

  it('rejects a bare label in the DNS lookup form', () => {
    render(<NetworkDiagnostics />)

    selectTool('DNS 조회')
    fireEvent.click(screen.getByRole('button', { name: /시뮬레이션 nslookup/ }))
    fireEvent.change(screen.getByLabelText('도메인'), { target: { value: 'localhost' } })
    fireEvent.click(screen.getByRole('button', { name: '시뮬레이션' }))

    expect(screen.getByRole('alert')).toHaveTextContent('도메인 형식이 올바르지 않습니다')
    expect(screen.queryByTestId('nd-result')).not.toBeInTheDocument()
  })

  it('clears the result of the selected tool only', () => {
    render(<NetworkDiagnostics />)

    selectTool('Ping')
    fireEvent.click(screen.getByRole('button', { name: /시뮬레이션 ping/ }))
    fireEvent.click(screen.getByRole('button', { name: '시뮬레이션' }))
    expect(screen.getByTestId('nd-result')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '결과 지우기' }))
    expect(screen.queryByTestId('nd-result')).not.toBeInTheDocument()
  })
})
