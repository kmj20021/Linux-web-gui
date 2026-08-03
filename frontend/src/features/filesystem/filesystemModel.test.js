import { describe, expect, it } from 'vitest'
import {
  buildInitialFS,
  changePermissions,
  createDirectory,
  createFile,
  listDirectories,
  moveEntry,
  removeEntry,
  toggleDirectory,
  writeFile,
} from './filesystemModel'
import { basename, dirname, joinPath } from './paths'
import {
  DIRECTORY_PERMISSIONS,
  FILE_PERMISSIONS,
  permsToOctal,
  permsToString,
} from './permissions'

describe('permission conversion utilities', () => {
  it('converts the default directory permissions to 755 / rwxr-xr-x', () => {
    expect(permsToOctal(DIRECTORY_PERMISSIONS)).toBe('755')
    expect(permsToString(DIRECTORY_PERMISSIONS)).toBe('rwxr-xr-x')
  })

  it('converts the default file permissions to 644 / rw-r--r--', () => {
    expect(permsToOctal(FILE_PERMISSIONS)).toBe('644')
    expect(permsToString(FILE_PERMISSIONS)).toBe('rw-r--r--')
  })

  it('converts an all-off and an all-on permission set', () => {
    expect(permsToOctal(Array(9).fill(false))).toBe('000')
    expect(permsToString(Array(9).fill(false))).toBe('---------')
    expect(permsToOctal(Array(9).fill(true))).toBe('777')
    expect(permsToString(Array(9).fill(true))).toBe('rwxrwxrwx')
  })
})

describe('path utilities', () => {
  it('extracts the basename', () => {
    expect(basename('/home/user/Documents/notes.txt')).toBe('notes.txt')
    expect(basename('/home/user')).toBe('user')
    expect(basename('/')).toBe('/')
  })

  it('extracts the parent directory', () => {
    expect(dirname('/home/user/Documents/notes.txt')).toBe('/home/user/Documents')
    expect(dirname('/home')).toBe('/')
  })

  it('joins a parent path and a child name', () => {
    expect(joinPath('/home/user', 'Documents')).toBe('/home/user/Documents')
    expect(joinPath('/', 'home')).toBe('/home')
  })
})

describe('virtual filesystem model', () => {
  it('builds an independent initial tree on every call', () => {
    const first = buildInitialFS()
    const second = buildInitialFS()

    expect(first['/home/user'].type).toBe('directory')
    expect(first['/home/user'].children).toEqual([
      'Documents',
      'Pictures',
      'Downloads',
      'hello.txt',
    ])
    expect(first['/home/user'].expanded).toBe(true)
    expect(first['/home/user/hello.txt'].type).toBe('file')
    expect(first).not.toBe(second)
    expect(first['/home/user']).not.toBe(second['/home/user'])
  })

  it('toggles a directory without mutating the previous state', () => {
    const fs = buildInitialFS()
    const next = toggleDirectory(fs, '/home/user/Documents')

    expect(next['/home/user/Documents'].expanded).toBe(true)
    expect(fs['/home/user/Documents'].expanded).toBe(false)
  })

  it('creates a directory, links it to its parent and reports the mkdir command', () => {
    const fs = buildInitialFS()
    const result = createDirectory(fs, '/home/user/Documents', 'reports')

    expect(result.ok).toBe(true)
    expect(result.path).toBe('/home/user/Documents/reports')
    expect(result.command).toBe('mkdir -p /home/user/Documents/reports')
    expect(result.fs['/home/user/Documents/reports']).toMatchObject({
      type: 'directory',
      owner: 'user',
      children: [],
      expanded: false,
    })
    expect(result.fs['/home/user/Documents'].children).toContain('reports')
    expect(result.fs['/home/user/Documents'].expanded).toBe(true)
    expect(fs['/home/user/Documents/reports']).toBeUndefined()
  })

  it('trims the new directory name and rejects blank or duplicate names', () => {
    const fs = buildInitialFS()

    expect(createDirectory(fs, '/home/user', '  spaced  ').path).toBe('/home/user/spaced')
    expect(createDirectory(fs, '/home/user', '   ')).toEqual({
      ok: false,
      error: '이름을 입력하세요.',
    })
    expect(createDirectory(fs, '/home/user', 'Documents')).toEqual({
      ok: false,
      error: '이미 존재하는 이름입니다.',
    })
  })

  it('creates an empty file and reports the touch command', () => {
    const fs = buildInitialFS()
    const result = createFile(fs, '/home/user/Pictures', 'note.txt')

    expect(result.ok).toBe(true)
    expect(result.command).toBe('touch /home/user/Pictures/note.txt')
    expect(result.fs['/home/user/Pictures/note.txt']).toMatchObject({
      type: 'file',
      owner: 'user',
      content: '',
    })
    expect(result.fs['/home/user/Pictures'].children).toContain('note.txt')
  })

  it('rejects a blank or duplicate file name', () => {
    const fs = buildInitialFS()

    expect(createFile(fs, '/home/user', '')).toEqual({
      ok: false,
      error: '파일 이름을 입력하세요.',
    })
    expect(createFile(fs, '/home/user', 'hello.txt')).toEqual({
      ok: false,
      error: '이미 존재하는 이름입니다.',
    })
  })

  it('removes a file with rm and unlinks it from its parent', () => {
    const fs = buildInitialFS()
    const result = removeEntry(fs, '/home/user/hello.txt')

    expect(result.ok).toBe(true)
    expect(result.command).toBe('rm /home/user/hello.txt')
    expect(result.removedPaths).toEqual(['/home/user/hello.txt'])
    expect(result.fs['/home/user/hello.txt']).toBeUndefined()
    expect(result.fs['/home/user'].children).not.toContain('hello.txt')
  })

  it('removes a directory recursively with rm -rf', () => {
    const fs = buildInitialFS()
    const result = removeEntry(fs, '/home/user/Documents')

    expect(result.command).toBe('rm -rf /home/user/Documents')
    expect(result.removedPaths.sort()).toEqual([
      '/home/user/Documents',
      '/home/user/Documents/notes.txt',
      '/home/user/Documents/work',
      '/home/user/Documents/work/project.md',
    ])
    expect(result.fs['/home/user/Documents/work/project.md']).toBeUndefined()
    expect(result.fs['/home/user'].children).not.toContain('Documents')
  })

  it('writes file content and reports the nano command', () => {
    const fs = buildInitialFS()
    const result = writeFile(fs, '/home/user/hello.txt', '새 내용')

    expect(result.ok).toBe(true)
    expect(result.command).toBe('nano /home/user/hello.txt')
    expect(result.fs['/home/user/hello.txt'].content).toBe('새 내용')
    expect(fs['/home/user/hello.txt'].content).not.toBe('새 내용')
  })

  it('moves a directory with all of its descendants', () => {
    const fs = buildInitialFS()
    const result = moveEntry(fs, '/home/user/Documents/work', '/home/user/Downloads')

    expect(result.ok).toBe(true)
    expect(result.path).toBe('/home/user/Downloads/work')
    expect(result.command).toBe('mv /home/user/Documents/work /home/user/Downloads/work')
    expect(result.fs['/home/user/Downloads/work/project.md'].content).toBe(
      fs['/home/user/Documents/work/project.md'].content,
    )
    expect(result.fs['/home/user/Documents/work']).toBeUndefined()
    expect(result.fs['/home/user/Documents'].children).not.toContain('work')
    expect(result.fs['/home/user/Downloads'].children).toContain('work')
    expect(result.fs['/home/user/Downloads'].expanded).toBe(true)
  })

  it('rejects moving an entry into itself or into its own descendant', () => {
    const fs = buildInitialFS()

    expect(moveEntry(fs, '/home/user/Documents', '/home/user/Documents')).toEqual({
      ok: false,
      error: '이동할 수 없는 경로입니다.',
    })
    expect(moveEntry(fs, '/home/user/Documents', '/home/user/Documents/work')).toEqual({
      ok: false,
      error: '이동할 수 없는 경로입니다.',
    })
  })

  it('rejects a move when the destination already holds the same name', () => {
    const fs = buildInitialFS()
    const seeded = createFile(fs, '/home/user/Pictures', 'hello.txt').fs

    expect(moveEntry(seeded, '/home/user/hello.txt', '/home/user/Pictures')).toEqual({
      ok: false,
      error: '목적지에 같은 이름이 존재합니다.',
    })
  })

  it('changes permissions and reports the chmod command with the octal mode', () => {
    const fs = buildInitialFS()
    const result = changePermissions(fs, '/home/user/hello.txt', Array(9).fill(true))

    expect(result.ok).toBe(true)
    expect(result.command).toBe('chmod 777 /home/user/hello.txt')
    expect(result.fs['/home/user/hello.txt'].permissions).toEqual(Array(9).fill(true))
    expect(fs['/home/user/hello.txt'].permissions).toEqual(FILE_PERMISSIONS)
  })

  it('lists every directory path for the move destination picker', () => {
    const dirs = listDirectories(buildInitialFS())

    expect(dirs).toContain('/home/user')
    expect(dirs).toContain('/home/user/Documents/work')
    expect(dirs).not.toContain('/home/user/hello.txt')
  })
})
