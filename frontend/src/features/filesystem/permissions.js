// 권한 변환 유틸리티.
// 권한은 소유자/그룹/기타 순서의 rwx 9칸 boolean 배열로 표현한다.

// rwxr-xr-x (755)
export const DIRECTORY_PERMISSIONS = [true, true, true, true, false, true, true, false, true]

// rw-r--r-- (644)
export const FILE_PERMISSIONS = [true, true, false, true, false, false, true, false, false]

// permissions 배열(9개) -> octal 문자열 (예: "755")
export function permsToOctal(p) {
  const toDigit = (r, w, x) => (r ? 4 : 0) + (w ? 2 : 0) + (x ? 1 : 0)
  return `${toDigit(p[0], p[1], p[2])}${toDigit(p[3], p[4], p[5])}${toDigit(p[6], p[7], p[8])}`
}

// permissions 배열 -> rwx 문자열 (예: "rwxr-xr-x")
export function permsToString(p) {
  const ch = (v, c) => (v ? c : '-')
  return (
    ch(p[0], 'r') + ch(p[1], 'w') + ch(p[2], 'x') +
    ch(p[3], 'r') + ch(p[4], 'w') + ch(p[5], 'x') +
    ch(p[6], 'r') + ch(p[7], 'w') + ch(p[8], 'x')
  )
}
