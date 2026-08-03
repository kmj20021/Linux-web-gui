// 화면에 보여줄 명령 문자열을 만든다.
// 이 문자열은 사용자가 직접 터미널에서 따라 칠 수 있는 예시일 뿐, 이 앱이
// 실행하는 명령이 아니다.

const SS_FLAG_ORDER = [
  ['t', '-t'],
  ['u', '-u'],
  ['l', '-l'],
  ['n', '-n'],
]

export function formatPingCommand(host, count) {
  return `ping -c ${count} ${host || '<host>'}`
}

export function formatTracerouteCommand(host) {
  return `traceroute ${host || '<host>'}`
}

export function formatNslookupCommand(domain) {
  return `nslookup ${domain || '<domain>'}`
}

export function formatCurlCommand(url, option) {
  return `curl ${option} ${url || '<url>'}`
}

export function formatSsCommand(options) {
  const flags = SS_FLAG_ORDER
    .filter(([key]) => options[key])
    .map(([, flag]) => flag.slice(1))
    .join('')
  return `ss ${flags ? `-${flags}` : '-tuln'}`
}
