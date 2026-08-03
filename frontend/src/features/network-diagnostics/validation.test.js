import { describe, expect, it } from 'vitest'
import {
  validateDomain,
  validateHost,
  validatePingCount,
  validateUrl,
} from './validation'

describe('validateHost', () => {
  it('accepts a hostname or an IPv4 literal and trims it', () => {
    expect(validateHost(' google.com ')).toEqual({ ok: true, value: 'google.com' })
    expect(validateHost('192.168.1.1')).toEqual({ ok: true, value: '192.168.1.1' })
    expect(validateHost('web-01.internal')).toEqual({ ok: true, value: 'web-01.internal' })
  })

  it('rejects an empty host', () => {
    expect(validateHost('   ')).toEqual({ ok: false, error: '호스트를 입력하세요.' })
  })

  it('rejects embedded whitespace and shell metacharacters', () => {
    expect(validateHost('google.com; rm -rf /')).toEqual({
      ok: false,
      error: '호스트에는 영문, 숫자, 점(.), 하이픈(-)만 사용할 수 있습니다.',
    })
    expect(validateHost('google com').ok).toBe(false)
    expect(validateHost('google.com && ls').ok).toBe(false)
  })

  it('rejects a host longer than 253 characters', () => {
    expect(validateHost('a'.repeat(254))).toEqual({
      ok: false,
      error: '호스트는 253자를 넘을 수 없습니다.',
    })
  })
})

describe('validateDomain', () => {
  it('accepts a dotted domain name', () => {
    expect(validateDomain('example.com')).toEqual({ ok: true, value: 'example.com' })
    expect(validateDomain(' sub.example.co.kr ')).toEqual({ ok: true, value: 'sub.example.co.kr' })
  })

  it('rejects an empty domain', () => {
    expect(validateDomain('')).toEqual({ ok: false, error: '도메인을 입력하세요.' })
  })

  it('requires at least one dot so that a bare label is rejected', () => {
    expect(validateDomain('localhost')).toEqual({
      ok: false,
      error: '도메인 형식이 올바르지 않습니다. 예: example.com',
    })
    expect(validateDomain('example.').ok).toBe(false)
  })
})

describe('validateUrl', () => {
  it('accepts a bare host and an http(s) URL', () => {
    expect(validateUrl('example.com')).toEqual({ ok: true, value: 'example.com' })
    expect(validateUrl(' https://example.com/path ')).toEqual({
      ok: true,
      value: 'https://example.com/path',
    })
  })

  it('rejects an empty URL', () => {
    expect(validateUrl('  ')).toEqual({ ok: false, error: 'URL을 입력하세요.' })
  })

  it('rejects a non-http scheme and whitespace', () => {
    expect(validateUrl('file:///etc/passwd')).toEqual({
      ok: false,
      error: 'http 또는 https URL만 입력할 수 있습니다.',
    })
    expect(validateUrl('http://exa mple.com').ok).toBe(false)
  })
})

describe('validatePingCount', () => {
  it('accepts the supported packet counts as numbers', () => {
    expect(validatePingCount(4)).toEqual({ ok: true, value: 4 })
    expect(validatePingCount('16')).toEqual({ ok: true, value: 16 })
  })

  it('rejects values outside 1..16 and non-integers', () => {
    const error = '패킷 수는 1에서 16 사이의 정수여야 합니다.'
    expect(validatePingCount(0)).toEqual({ ok: false, error })
    expect(validatePingCount(17)).toEqual({ ok: false, error })
    expect(validatePingCount('abc')).toEqual({ ok: false, error })
    expect(validatePingCount(2.5)).toEqual({ ok: false, error })
  })
})
