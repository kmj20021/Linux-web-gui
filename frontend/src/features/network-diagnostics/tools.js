// 네트워크 진단 도구 정의.
// 여기 있는 도구는 모두 교육용 시뮬레이션이며 실제 네트워크 요청을 보내지 않는다.

export const TOOLS = [
  {
    id: 'ping',
    label: 'Ping',
    cmd: 'ping',
    description: '특정 호스트에 ICMP 패킷을 보내 응답 시간을 측정합니다.',
    usage: 'ping -c <count> <host>',
  },
  {
    id: 'traceroute',
    label: '경로 추적',
    cmd: 'traceroute',
    description: '패킷이 목적지까지 거치는 네트워크 경로를 추적합니다.',
    usage: 'traceroute <host>',
  },
  {
    id: 'ss',
    label: '포트/소켓',
    cmd: 'ss',
    description: '시스템에서 열려 있는 포트와 소켓 연결 상태를 표시합니다.',
    usage: 'ss -tuln',
  },
  {
    id: 'nslookup',
    label: 'DNS 조회',
    cmd: 'nslookup',
    description: '도메인 이름의 IP 주소와 DNS 레코드를 조회합니다.',
    usage: 'nslookup <domain>',
  },
  {
    id: 'curl',
    label: 'HTTP 테스트',
    cmd: 'curl',
    description: 'HTTP 요청을 보내 서버 응답 헤더와 상태 코드를 확인합니다.',
    usage: 'curl -I <url>',
  },
]

export function findTool(id) {
  return TOOLS.find(t => t.id === id)
}
