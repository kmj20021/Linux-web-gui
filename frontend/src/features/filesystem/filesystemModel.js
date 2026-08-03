// 교육용 가상 파일시스템 모델.
//
// 모든 함수는 순수 함수다. 입력 트리를 변경하지 않고 새 트리를 돌려주며,
// 실행된 것처럼 보여줄 리눅스 명령 문자열을 함께 반환한다. 실제 서버
// 파일시스템에는 접근하지 않는다.
//
// 실패는 예외 대신 `{ ok: false, error }`로 표현해 호출부가 토스트 메시지로
// 그대로 쓸 수 있게 한다.

import { basename, dirname, isWithin, joinPath } from './paths'
import { DIRECTORY_PERMISSIONS, FILE_PERMISSIONS, permsToOctal } from './permissions'

// ============================================================
// 초기 가상 파일시스템 데이터
// ============================================================
export function buildInitialFS() {
  return {
    '/home/user': {
      type: 'directory',
      permissions: [...DIRECTORY_PERMISSIONS],
      owner: 'user',
      children: ['Documents', 'Pictures', 'Downloads', 'hello.txt'],
      expanded: true,
    },
    '/home/user/Documents': {
      type: 'directory',
      permissions: [...DIRECTORY_PERMISSIONS],
      owner: 'user',
      children: ['notes.txt', 'work'],
      expanded: false,
    },
    '/home/user/Documents/notes.txt': {
      type: 'file',
      permissions: [...FILE_PERMISSIONS],
      owner: 'user',
      content: '리눅스 파일시스템 학습 노트\n\n1. 모든 것은 파일이다\n2. 파일 경로는 /로 시작한다\n3. 디렉토리도 파일이다',
    },
    '/home/user/Documents/work': {
      type: 'directory',
      permissions: [...DIRECTORY_PERMISSIONS],
      owner: 'user',
      children: ['project.md'],
      expanded: false,
    },
    '/home/user/Documents/work/project.md': {
      type: 'file',
      permissions: [...FILE_PERMISSIONS],
      owner: 'user',
      content: '# 프로젝트 계획서\n\n## 목표\n- 리눅스 GUI 개발\n\n## 일정\n- 1주차: 설계\n- 2주차: 구현',
    },
    '/home/user/Pictures': {
      type: 'directory',
      permissions: [...DIRECTORY_PERMISSIONS],
      owner: 'user',
      children: ['vacation.jpg'],
      expanded: false,
    },
    '/home/user/Pictures/vacation.jpg': {
      type: 'file',
      permissions: [...FILE_PERMISSIONS],
      owner: 'user',
      content: '[이미지 파일 - JPEG 형식]',
    },
    '/home/user/Downloads': {
      type: 'directory',
      permissions: [...DIRECTORY_PERMISSIONS],
      owner: 'user',
      children: ['archive.tar.gz'],
      expanded: false,
    },
    '/home/user/Downloads/archive.tar.gz': {
      type: 'file',
      permissions: [...FILE_PERMISSIONS],
      owner: 'user',
      content: '[압축 파일 - tar.gz 형식]',
    },
    '/home/user/hello.txt': {
      type: 'file',
      permissions: [...FILE_PERMISSIONS],
      owner: 'user',
      content: 'Hello, Linux World!\n안녕하세요, 리눅스!',
    },
  }
}

// 루트 경로. 트리 패널은 여기서부터 렌더링한다.
export const ROOT_PATH = '/home/user'

// 부모의 children 목록에서 이름 하나를 붙이거나 뗀다.
function withChild(node, name) {
  return { ...node, children: [...(node.children || []), name], expanded: true }
}

function withoutChild(node, name) {
  return { ...node, children: (node.children || []).filter(c => c !== name) }
}

// 새 항목을 부모에 연결하며 삽입한다.
function insertEntry(fs, parentPath, name, entry) {
  return {
    ...fs,
    [parentPath]: withChild(fs[parentPath], name),
    [joinPath(parentPath, name)]: entry,
  }
}

// 폴더 펼침/접힘 토글
export function toggleDirectory(fs, path) {
  return {
    ...fs,
    [path]: { ...fs[path], expanded: !fs[path].expanded },
  }
}

// 폴더 생성 (mkdir -p)
export function createDirectory(fs, parentPath, rawName) {
  const name = rawName.trim()
  if (!name) return { ok: false, error: '이름을 입력하세요.' }

  const path = joinPath(parentPath, name)
  if (fs[path]) return { ok: false, error: '이미 존재하는 이름입니다.' }

  return {
    ok: true,
    path,
    command: `mkdir -p ${path}`,
    fs: insertEntry(fs, parentPath, name, {
      type: 'directory',
      permissions: [...DIRECTORY_PERMISSIONS],
      owner: 'user',
      children: [],
      expanded: false,
    }),
  }
}

// 파일 생성 (touch)
export function createFile(fs, parentPath, rawName) {
  const name = rawName.trim()
  if (!name) return { ok: false, error: '파일 이름을 입력하세요.' }

  const path = joinPath(parentPath, name)
  if (fs[path]) return { ok: false, error: '이미 존재하는 이름입니다.' }

  return {
    ok: true,
    path,
    command: `touch ${path}`,
    fs: insertEntry(fs, parentPath, name, {
      type: 'file',
      permissions: [...FILE_PERMISSIONS],
      owner: 'user',
      content: '',
    }),
  }
}

// 파일/폴더 삭제 (rm, rm -rf)
export function removeEntry(fs, path) {
  const node = fs[path]
  if (!node) return { ok: false, error: '존재하지 않는 경로입니다.' }

  const isDir = node.type === 'directory'
  const name = basename(path)
  const parentPath = dirname(path)
  const removedPaths = Object.keys(fs).filter(p => isWithin(p, path))

  const next = { ...fs }
  removedPaths.forEach(p => delete next[p])
  if (next[parentPath]) {
    next[parentPath] = withoutChild(next[parentPath], name)
  }

  return {
    ok: true,
    fs: next,
    removedPaths,
    command: isDir ? `rm -rf ${path}` : `rm ${path}`,
  }
}

// 파일 내용 저장 (nano)
export function writeFile(fs, path, content) {
  if (!fs[path]) return { ok: false, error: '존재하지 않는 경로입니다.' }

  return {
    ok: true,
    command: `nano ${path}`,
    fs: { ...fs, [path]: { ...fs[path], content } },
  }
}

// 이동 (mv). 하위 경로 키를 모두 새 접두사로 다시 쓴다.
export function moveEntry(fs, srcPath, destDir) {
  if (isWithin(destDir, srcPath)) {
    return { ok: false, error: '이동할 수 없는 경로입니다.' }
  }

  const name = basename(srcPath)
  const destPath = joinPath(destDir, name)
  if (fs[destPath]) return { ok: false, error: '목적지에 같은 이름이 존재합니다.' }

  const srcParent = dirname(srcPath)
  const movedPaths = Object.keys(fs).filter(p => isWithin(p, srcPath))

  const next = { ...fs }
  movedPaths.forEach(p => delete next[p])
  movedPaths.forEach(p => {
    const adjusted = p === srcPath ? destPath : destPath + p.slice(srcPath.length)
    next[adjusted] = { ...fs[p] }
  })
  if (next[srcParent]) {
    next[srcParent] = withoutChild(next[srcParent], name)
  }
  if (next[destDir]) {
    next[destDir] = withChild(next[destDir], name)
  }

  return { ok: true, fs: next, path: destPath, command: `mv ${srcPath} ${destPath}` }
}

// 권한 변경 (chmod)
export function changePermissions(fs, path, permissions) {
  if (!fs[path]) return { ok: false, error: '존재하지 않는 경로입니다.' }

  return {
    ok: true,
    command: `chmod ${permsToOctal(permissions)} ${path}`,
    fs: { ...fs, [path]: { ...fs[path], permissions: [...permissions] } },
  }
}

// 이동 목적지 후보인 폴더 경로 목록
export function listDirectories(fs) {
  return Object.entries(fs)
    .filter(([, node]) => node.type === 'directory')
    .map(([path]) => path)
}
