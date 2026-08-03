import { describe, expect, it } from 'vitest'
import {
  formatCurlCommand,
  formatNslookupCommand,
  formatPingCommand,
  formatSsCommand,
  formatTracerouteCommand,
} from './commands'
import {
  simulateCurl,
  simulateNslookup,
  simulatePing,
  simulateSs,
  simulateTraceroute,
} from './simulators'
import { TOOLS, findTool } from './tools'

describe('tool definitions', () => {
  it('exposes the five educational tools with a command and usage line', () => {
    expect(TOOLS.map(t => t.id)).toEqual(['ping', 'traceroute', 'ss', 'nslookup', 'curl'])
    TOOLS.forEach(tool => {
      expect(tool.label).toBeTruthy()
      expect(tool.cmd).toBeTruthy()
      expect(tool.usage).toBeTruthy()
      expect(tool.description).toBeTruthy()
    })
  })

  it('looks a tool up by id', () => {
    expect(findTool('curl').label).toBe('HTTP 테스트')
    expect(findTool('nope')).toBeUndefined()
  })
})

describe('command formatting', () => {
  it('formats each tool command from its inputs', () => {
    expect(formatPingCommand('google.com', 4)).toBe('ping -c 4 google.com')
    expect(formatTracerouteCommand('google.com')).toBe('traceroute google.com')
    expect(formatNslookupCommand('example.com')).toBe('nslookup example.com')
    expect(formatCurlCommand('example.com', '-I')).toBe('curl -I example.com')
  })

  it('shows a placeholder while an input is still empty', () => {
    expect(formatPingCommand('', 4)).toBe('ping -c 4 <host>')
    expect(formatTracerouteCommand('')).toBe('traceroute <host>')
    expect(formatNslookupCommand('')).toBe('nslookup <domain>')
    expect(formatCurlCommand('', '-v')).toBe('curl -v <url>')
  })

  it('joins the selected ss flags and falls back to -tuln', () => {
    expect(formatSsCommand({ t: true, u: true, l: true, n: true })).toBe('ss -tuln')
    expect(formatSsCommand({ t: true, u: false, l: true, n: false })).toBe('ss -tl')
    expect(formatSsCommand({ t: false, u: false, l: false, n: false })).toBe('ss -tuln')
  })
})

describe('simulated output', () => {
  it('produces one reply line per requested ping packet', () => {
    const lines = simulatePing('google.com', 3)

    expect(lines[0]).toMatch(/^PING google\.com \(/)
    expect(lines.filter(l => l.includes('icmp_seq='))).toHaveLength(3)
    expect(lines).toContain('--- google.com ping statistics ---')
    expect(lines).toContain('3 packets transmitted, 3 received, 0% packet loss')
  })

  it('produces a bounded traceroute path ending at the requested host', () => {
    const lines = simulateTraceroute('google.com')

    expect(lines[0]).toMatch(/^traceroute to google\.com /)
    expect(lines[lines.length - 1]).toContain('google.com')
  })

  it('keeps only listening sockets when the -l flag is set', () => {
    const all = simulateSs({ t: true, u: true, l: false, n: true })
    const listening = simulateSs({ t: true, u: true, l: true, n: true })

    expect(all.some(l => l.includes('ESTAB'))).toBe(true)
    expect(listening.some(l => l.includes('ESTAB'))).toBe(false)
    expect(listening[0]).toContain('Netid')
  })

  it('reports the queried domain in the nslookup answer', () => {
    const lines = simulateNslookup('example.com')

    expect(lines).toContain('Non-authoritative answer:')
    expect(lines.filter(l => l === 'Name:    example.com')).toHaveLength(2)
  })

  it('adds the request trace only for the verbose curl option', () => {
    const headersOnly = simulateCurl('example.com', '-I')
    const verbose = simulateCurl('example.com', '-v')

    expect(headersOnly[0]).toBe('HTTP/2 200')
    expect(verbose[0]).toMatch(/^\*\s+Trying /)
    expect(verbose).toContain('> GET / HTTP/1.1')
  })
})
