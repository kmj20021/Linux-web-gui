// 진단 도구 출력 시뮬레이터.
//
// 어떤 함수도 네트워크에 접근하지 않는다. 실제 명령을 실행했을 때 어떤 형태의
// 출력이 나오는지 보여주기 위해 고정된 예시 문자열을 만들어 낸다.

const SAMPLE_IPV4 = '142.250.196.142'
const SAMPLE_IPV6 = '2404:6800:4004:81b::200e'

export function simulatePing(host, count) {
  const lines = [`PING ${host} (${SAMPLE_IPV4}): 56 data bytes`]
  for (let i = 0; i < count; i++) {
    const ms = (10 + Math.random() * 15).toFixed(1)
    lines.push(`64 bytes from ${SAMPLE_IPV4}: icmp_seq=${i} ttl=117 time=${ms} ms`)
  }
  lines.push(`--- ${host} ping statistics ---`)
  lines.push(`${count} packets transmitted, ${count} received, 0% packet loss`)
  return lines
}

export function simulateTraceroute(host) {
  return [
    `traceroute to ${host} (${SAMPLE_IPV4}), 30 hops max, 60 byte packets`,
    ` 1  _gateway (192.168.1.1)  0.543 ms  0.512 ms  0.489 ms`,
    ` 2  10.0.0.1 (10.0.0.1)  1.234 ms  1.198 ms  1.267 ms`,
    ` 3  * * *`,
    ` 4  72.14.215.165 (72.14.215.165)  8.765 ms  8.712 ms  8.698 ms`,
    ` 5  ${host} (${SAMPLE_IPV4})  12.345 ms  12.312 ms  12.298 ms`,
  ]
}

export function simulateSs(options) {
  const rows = [
    'Netid  State    Recv-Q  Send-Q  Local Address:Port    Peer Address:Port',
    'tcp    LISTEN   0       128     0.0.0.0:22            0.0.0.0:*',
    'tcp    LISTEN   0       128     0.0.0.0:80            0.0.0.0:*',
    'tcp    LISTEN   0       128     0.0.0.0:8000          0.0.0.0:*',
    'tcp    LISTEN   0       128     0.0.0.0:443           0.0.0.0:*',
    'tcp    ESTAB    0       0       192.168.1.100:22      192.168.1.200:54321',
    'udp    UNCONN   0       0       0.0.0.0:68            0.0.0.0:*',
  ]
  if (options.l) {
    return rows.filter(r => r.includes('LISTEN') || r.includes('UNCONN') || r.includes('Netid'))
  }
  return rows
}

export function simulateNslookup(domain) {
  return [
    `Server:    8.8.8.8`,
    `Address:   8.8.8.8#53`,
    ``,
    `Non-authoritative answer:`,
    `Name:    ${domain}`,
    `Address: ${SAMPLE_IPV4}`,
    `Name:    ${domain}`,
    `Address: ${SAMPLE_IPV6}`,
  ]
}

export function simulateCurl(url, option) {
  const headers = [
    `HTTP/2 200`,
    `content-type: text/html; charset=utf-8`,
    `date: ${new Date().toUTCString()}`,
    `server: nginx`,
    `x-content-type-options: nosniff`,
    ``,
    `* Connection to ${url} left intact`,
  ]
  if (option === '-v') {
    return [
      `*   Trying ${SAMPLE_IPV4}:80...`,
      `* Connected to ${url} (${SAMPLE_IPV4}) port 80 (#0)`,
      `> GET / HTTP/1.1`,
      `> Host: ${url}`,
      `> User-Agent: curl/7.81.0`,
      `>`,
      ...headers,
    ]
  }
  return headers
}
