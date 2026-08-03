// 진단 도구 입력 검증.
//
// 명령은 시뮬레이션일 뿐이지만, 입력을 그대로 명령 문자열에 이어 붙여 화면에
// 보여주므로 셸 메타문자와 공백은 여기서 막는다. 실패는 화면에 그대로 쓸 수
// 있는 `{ ok: false, error }`로 돌려준다.

const HOST_PATTERN = /^[A-Za-z0-9.:_-]+$/
const DOMAIN_PATTERN = /^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$/
const URL_SCHEME_PATTERN = /^([A-Za-z][A-Za-z0-9+.-]*):\/\//
const URL_HOST_PATTERN = /^[A-Za-z0-9.-]+(:\d{1,5})?$/
const URL_PATH_PATTERN = /^[A-Za-z0-9._~:/?#[\]@!$&'()*+,;=%-]*$/

const MAX_HOST_LENGTH = 253
const MIN_PING_COUNT = 1
const MAX_PING_COUNT = 16

export function validateHost(raw) {
  const value = String(raw ?? '').trim()
  if (!value) return { ok: false, error: '호스트를 입력하세요.' }
  if (value.length > MAX_HOST_LENGTH) {
    return { ok: false, error: `호스트는 ${MAX_HOST_LENGTH}자를 넘을 수 없습니다.` }
  }
  if (!HOST_PATTERN.test(value)) {
    return {
      ok: false,
      error: '호스트에는 영문, 숫자, 점(.), 하이픈(-)만 사용할 수 있습니다.',
    }
  }
  return { ok: true, value }
}

export function validateDomain(raw) {
  const value = String(raw ?? '').trim()
  if (!value) return { ok: false, error: '도메인을 입력하세요.' }
  if (value.length > MAX_HOST_LENGTH) {
    return { ok: false, error: `도메인은 ${MAX_HOST_LENGTH}자를 넘을 수 없습니다.` }
  }
  if (!DOMAIN_PATTERN.test(value)) {
    return { ok: false, error: '도메인 형식이 올바르지 않습니다. 예: example.com' }
  }
  return { ok: true, value }
}

export function validateUrl(raw) {
  const value = String(raw ?? '').trim()
  if (!value) return { ok: false, error: 'URL을 입력하세요.' }

  // 스킴이 붙어 있으면 http/https만 허용한다. file:, javascript: 등은 거부한다.
  const scheme = value.match(URL_SCHEME_PATTERN)
  if (scheme && !['http', 'https'].includes(scheme[1].toLowerCase())) {
    return { ok: false, error: 'http 또는 https URL만 입력할 수 있습니다.' }
  }

  const rest = scheme ? value.slice(scheme[0].length) : value
  const separator = rest.indexOf('/')
  const host = separator === -1 ? rest : rest.slice(0, separator)
  const path = separator === -1 ? '' : rest.slice(separator)

  if (!URL_HOST_PATTERN.test(host) || !URL_PATH_PATTERN.test(path)) {
    return { ok: false, error: 'URL 형식이 올바르지 않습니다. 예: example.com/path' }
  }
  return { ok: true, value }
}

export function validatePingCount(raw) {
  const value = Number(raw)
  const invalid =
    !Number.isInteger(value) || value < MIN_PING_COUNT || value > MAX_PING_COUNT
  if (invalid) {
    return {
      ok: false,
      error: `패킷 수는 ${MIN_PING_COUNT}에서 ${MAX_PING_COUNT} 사이의 정수여야 합니다.`,
    }
  }
  return { ok: true, value }
}
