import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import FilesystemPage from './Filesystem'

function tree() {
  return screen.getByTestId('fs-tree')
}

function selectEntry(name) {
  fireEvent.click(within(tree()).getByText(name))
}

function logPanel() {
  return screen.getByTestId('fs-command-log')
}

describe('FilesystemPage educational behaviour', () => {
  it('always states that the filesystem is a virtual simulation', () => {
    render(<FilesystemPage />)

    const notice = screen.getByTestId('fs-simulation-notice')
    expect(notice).toBeInTheDocument()
    expect(notice.textContent).toMatch(/교육용 가상 파일시스템/)
    expect(notice.textContent).toMatch(/실제 서버 파일시스템을 변경하지 않습니다/)
  })

  it('disables every action until an entry is selected', () => {
    render(<FilesystemPage />)

    expect(screen.getByRole('button', { name: /폴더 생성/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /파일 생성/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /폴더 삭제/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /파일 수정/ })).toBeDisabled()

    selectEntry('hello.txt')

    expect(screen.getByRole('button', { name: /파일 수정/ })).toBeEnabled()
  })

  it('shows permissions of the selected entry in both notations', () => {
    render(<FilesystemPage />)

    selectEntry('hello.txt')

    expect(screen.getByText('rw-r--r-- (644)')).toBeInTheDocument()
    expect(screen.getByText('/home/user/hello.txt')).toBeInTheDocument()
  })

  it('creates a folder through the mkdir modal and records the command', () => {
    render(<FilesystemPage />)

    selectEntry('Documents')
    fireEvent.click(screen.getByRole('button', { name: /폴더 생성/ }))

    fireEvent.change(screen.getByPlaceholderText('예: new-folder'), {
      target: { value: 'reports' },
    })
    fireEvent.click(screen.getByRole('button', { name: '생성' }))

    expect(within(tree()).getByText('reports')).toBeInTheDocument()
    expect(within(logPanel()).getByText('mkdir -p /home/user/Documents/reports')).toBeInTheDocument()
  })

  it('creates a file through the touch modal and records the command', () => {
    render(<FilesystemPage />)

    selectEntry('Pictures')
    fireEvent.click(screen.getByRole('button', { name: /파일 생성/ }))

    fireEvent.change(screen.getByPlaceholderText('예: newfile.txt'), {
      target: { value: 'memo.txt' },
    })
    fireEvent.click(screen.getByRole('button', { name: '생성' }))

    expect(within(tree()).getByText('memo.txt')).toBeInTheDocument()
    expect(within(logPanel()).getByText('touch /home/user/Pictures/memo.txt')).toBeInTheDocument()
  })

  it('rejects a duplicate name without touching the tree', () => {
    render(<FilesystemPage />)

    // 파일을 고르면 그 부모 폴더(/home/user)가 생성 대상이 된다.
    selectEntry('hello.txt')
    fireEvent.click(screen.getByRole('button', { name: /폴더 생성/ }))
    fireEvent.change(screen.getByPlaceholderText('예: new-folder'), {
      target: { value: 'Documents' },
    })
    fireEvent.click(screen.getByRole('button', { name: '생성' }))

    expect(screen.getByText('이미 존재하는 이름입니다.')).toBeInTheDocument()
    expect(within(logPanel()).queryByText(/mkdir/)).not.toBeInTheDocument()
  })

  it('edits file content through the nano modal and records the command', () => {
    render(<FilesystemPage />)

    selectEntry('hello.txt')
    fireEvent.click(screen.getByRole('button', { name: /파일 수정/ }))

    const textarea = screen.getByRole('textbox')
    expect(textarea).toHaveValue('Hello, Linux World!\n안녕하세요, 리눅스!')
    fireEvent.change(textarea, { target: { value: '수정된 내용' } })
    fireEvent.click(screen.getByRole('button', { name: '저장' }))

    expect(within(logPanel()).getByText('nano /home/user/hello.txt')).toBeInTheDocument()
    expect(screen.getByText('수정된 내용')).toBeInTheDocument()
  })

  it('deletes a file after confirmation and records the rm command', () => {
    render(<FilesystemPage />)

    selectEntry('hello.txt')
    fireEvent.click(screen.getByRole('button', { name: /파일 삭제/ }))
    fireEvent.click(screen.getByRole('button', { name: '삭제' }))

    expect(within(tree()).queryByText('hello.txt')).not.toBeInTheDocument()
    expect(within(logPanel()).getByText('rm /home/user/hello.txt')).toBeInTheDocument()
  })

  it('changes permissions through the chmod modal and records the octal mode', () => {
    render(<FilesystemPage />)

    selectEntry('hello.txt')
    fireEvent.click(screen.getByRole('button', { name: /권한 수정/ }))

    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[2]) // 소유자 실행 비트
    fireEvent.click(screen.getByRole('button', { name: '적용' }))

    expect(within(logPanel()).getByText('chmod 744 /home/user/hello.txt')).toBeInTheDocument()
    expect(screen.getByText('rwxr--r-- (744)')).toBeInTheDocument()
  })

  it('clears the command log on demand', () => {
    render(<FilesystemPage />)

    expect(within(logPanel()).getByText('# 파일시스템 탐색기 시작')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'clear' }))
    expect(within(logPanel()).queryByText('# 파일시스템 탐색기 시작')).not.toBeInTheDocument()
  })
})
