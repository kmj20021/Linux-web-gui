// Terminal/DOM에는 색상·커서 이동·링크 삽입 제어 시퀀스를 허용하지 않는다.
export function sanitizeTerminalText(value) {
  return String(value ?? '')
    .replace(/\x1b\][\s\S]*?(?:\x07|\x1b\\|$)/g, '')
    .replace(/\x9d[\s\S]*?(?:\x07|\x9c|$)/g, '')
    .replace(/\x1b\[[0-?]*[ -\/]*[@-~]/g, '')
    .replace(/\x9b[0-?]*[ -\/]*[@-~]/g, '')
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]/g, '')
}

export function formatSimulationLines(value) {
  return `[SIMULATION] ${sanitizeTerminalText(value).replace(/\r?\n/g, '\r\n[SIMULATION] ')}`
}

// xterm의 2,000줄 scrollback과 별개로 모드 전환용 문자열도 유한하게 유지한다.
export const TERMINAL_BUFFER_MAX_BYTES = 256 * 1024
export const TERMINAL_BUFFER_MAX_CHARS = TERMINAL_BUFFER_MAX_BYTES
export const TERMINAL_COMMAND_HISTORY_MAX_ITEMS = 200

const utf8Encoder = new TextEncoder()
const utf8Decoder = new TextDecoder()

function utf8Prefix(value, maxBytes) {
  const encoded = utf8Encoder.encode(value)
  if (encoded.length <= maxBytes) return value
  let end = Math.max(0, maxBytes)
  while (end > 0 && (encoded[end] & 0xc0) === 0x80) end -= 1
  return utf8Decoder.decode(encoded.slice(0, end))
}

function utf8Suffix(value, maxBytes) {
  const encoded = utf8Encoder.encode(value)
  if (encoded.length <= maxBytes) return value
  let start = Math.max(0, encoded.length - maxBytes)
  while (start < encoded.length && (encoded[start] & 0xc0) === 0x80) start += 1
  return utf8Decoder.decode(encoded.slice(start))
}

export function appendBoundedTerminalBuffer(current, addition, options = {}) {
  const maxBytes = options.maxBytes ?? options.maxChars ?? TERMINAL_BUFFER_MAX_BYTES
  const boundary = options.boundary ?? ''
  const combined = String(current ?? '') + String(addition ?? '')
  if (utf8Encoder.encode(combined).length <= maxBytes) return combined

  const safeBoundary = utf8Prefix(boundary, Math.max(0, maxBytes))
  const boundaryBytes = utf8Encoder.encode(safeBoundary).length
  const available = Math.max(0, maxBytes - boundaryBytes)
  let recent = available > 0 ? utf8Suffix(combined, available) : ''
  const lineBreak = recent.search(/[\r\n]/)
  if (lineBreak >= 0 && lineBreak < Math.min(1024, recent.length - 1)) {
    recent = recent.slice(lineBreak + 1).replace(/^\n/, '')
  }
  return safeBoundary + recent
}

export function appendBoundedCommandHistory(history, command, maxItems = TERMINAL_COMMAND_HISTORY_MAX_ITEMS) {
  return [...history, command].slice(-maxItems)
}

export function boundCommandHistory(history, maxItems = TERMINAL_COMMAND_HISTORY_MAX_ITEMS) {
  return history.slice(-maxItems)
}
