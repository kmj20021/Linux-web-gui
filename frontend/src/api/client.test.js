import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch, onAuthExpired } from './client'

// 베이스 경로는 빌드 환경 변수로 정해지므로 클라이언트와 같은 규칙으로 계산한다.
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

function jsonResponse(body, { status = 200 } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => 'application/json' },
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  }
}

function emptyResponse(status = 204) {
  return {
    ok: true,
    status,
    headers: { get: () => null },
    json: () => Promise.reject(new Error('no body')),
    text: () => Promise.resolve(''),
  }
}

describe('apiFetch', () => {
  beforeEach(() => {
    localStorage.clear()
    globalThis.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('parses a JSON body and prefixes the API base path', async () => {
    globalThis.fetch.mockResolvedValue(jsonResponse({ total: 3 }))

    await expect(apiFetch('/monitor/cpu')).resolves.toEqual({ total: 3 })
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/monitor/cpu`,
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('attaches the stored bearer token to authenticated calls only', async () => {
    localStorage.setItem('auth_token', 'synthetic-test-token')
    globalThis.fetch.mockResolvedValue(jsonResponse({}))

    await apiFetch('/monitor/cpu')
    expect(globalThis.fetch.mock.calls[0][1].headers.Authorization)
      .toBe('Bearer synthetic-test-token')

    await apiFetch('/auth/login', { method: 'POST', body: {}, auth: false })
    expect(globalThis.fetch.mock.calls[1][1].headers.Authorization).toBeUndefined()
  })

  it('serialises a JSON body and sets the content type', async () => {
    globalThis.fetch.mockResolvedValue(jsonResponse({}))

    await apiFetch('/admin/users', { method: 'POST', body: { username: 'new-op' } })

    const init = globalThis.fetch.mock.calls[0][1]
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(init.body).toBe(JSON.stringify({ username: 'new-op' }))
  })

  it('returns null for an empty success body', async () => {
    globalThis.fetch.mockResolvedValue(emptyResponse())

    await expect(apiFetch('/admin/users/2', { method: 'DELETE' })).resolves.toBeNull()
  })

  it('raises an ApiError carrying the status and the server detail', async () => {
    globalThis.fetch.mockResolvedValue(
      jsonResponse({ detail: '마지막 활성 관리자는 삭제할 수 없습니다.' }, { status: 409 }),
    )

    const error = await apiFetch('/admin/users/1', { method: 'DELETE' }).catch(e => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(409)
    expect(error.message).toBe('마지막 활성 관리자는 삭제할 수 없습니다.')
    expect(error.isAuthExpired).toBe(false)
  })

  it('flattens a FastAPI validation detail array into one message', async () => {
    globalThis.fetch.mockResolvedValue(
      jsonResponse({ detail: [{ msg: '비밀번호가 너무 짧습니다' }, { msg: '역할이 올바르지 않습니다' }] },
        { status: 422 }),
    )

    const error = await apiFetch('/admin/users', { method: 'POST', body: {} }).catch(e => e)

    expect(error.message).toBe('비밀번호가 너무 짧습니다, 역할이 올바르지 않습니다')
  })

  it('falls back to a readable message when the error body is not JSON', async () => {
    globalThis.fetch.mockResolvedValue({
      ok: false,
      status: 502,
      headers: { get: () => 'text/html' },
      json: () => Promise.reject(new Error('not json')),
      text: () => Promise.resolve('<html>bad gateway</html>'),
    })

    const error = await apiFetch('/monitor/cpu').catch(e => e)

    expect(error.status).toBe(502)
    expect(error.message).toBe('요청 실패 (502)')
  })
})

describe('authentication expiry handling', () => {
  beforeEach(() => {
    localStorage.clear()
    globalThis.fetch = vi.fn()
  })

  it('marks a 401 as an expired session and notifies every subscriber once', async () => {
    globalThis.fetch.mockResolvedValue(jsonResponse({ detail: 'Not authenticated' }, { status: 401 }))
    const first = vi.fn()
    const second = vi.fn()
    const unsubscribeFirst = onAuthExpired(first)
    onAuthExpired(second)

    const error = await apiFetch('/monitor/cpu').catch(e => e)

    expect(error.isAuthExpired).toBe(true)
    expect(error.status).toBe(401)
    expect(first).toHaveBeenCalledTimes(1)
    expect(second).toHaveBeenCalledTimes(1)

    unsubscribeFirst()
    await apiFetch('/monitor/cpu').catch(() => {})
    expect(first).toHaveBeenCalledTimes(1)
    expect(second).toHaveBeenCalledTimes(2)
  })

  it('does not treat a rejected login as an expired session', async () => {
    globalThis.fetch.mockResolvedValue(jsonResponse({ detail: '로그인 실패' }, { status: 401 }))
    const listener = vi.fn()
    onAuthExpired(listener)

    const error = await apiFetch('/auth/login', { method: 'POST', body: {}, auth: false }).catch(e => e)

    expect(error.status).toBe(401)
    expect(listener).not.toHaveBeenCalled()
  })
})

describe('request timeout', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('aborts a slow request and reports it as a timeout', async () => {
    globalThis.fetch = vi.fn((_url, init) => new Promise((_resolve, reject) => {
      init.signal.addEventListener('abort', () => {
        reject(Object.assign(new Error('aborted'), { name: 'AbortError' }))
      })
    }))

    const error = await apiFetch('/monitor/cpu', { timeoutMs: 10 }).catch(e => e)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.code).toBe('timeout')
    expect(error.message).toBe('요청 시간이 초과되었습니다.')
  })
})
