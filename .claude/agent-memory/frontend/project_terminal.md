---
name: Project: Terminal Page
description: 터미널+파일탐색기 통합 페이지 구현 완료 (xterm.js, WebSocket /ws/shell, REST /api/shell/fs)
type: project
---

터미널+파일탐색기 통합 페이지 구현 완료.

**Why:** 가상 Linux 셸 환경을 웹에서 조작하기 위한 UI 필요.

**How to apply:** /terminal 라우트로 접근. Layout 내 main-content에서 `:has(.terminal-page)` CSS selector로 padding 제거 처리.

## 핵심 파일
- `frontend/src/components/Terminal.jsx` — xterm.js + WebSocket(ws/shell) 터미널
- `frontend/src/components/FileExplorer.jsx` — REST(/api/shell/fs) 파일트리
- `frontend/src/pages/Terminal.jsx` — 통합 레이아웃 페이지
- `frontend/src/styles/Terminal.css` — 다크 테마 전용 CSS

## 패턴
- xterm.js: `@xterm/xterm` v6, `@xterm/addon-fit`
- WS URL: `${wsProtocol}//${window.location.host}/ws/shell?token=${token}`
- FS API: `GET /api/shell/fs?session_id={id}`, Authorization Bearer 헤더
- 비밀번호 마스킹: output에 "password:" 포함 시 passwordModeRef=true → 입력을 * 표시
- 부모→터미널 명령 주입: `useImperativeHandle` + `ref.sendCommand(cmd)`
- 파일탐색기 갱신: refreshTrigger(숫자) prop 변경 시 재조회

## vite.config.js 변경
`/ws` proxy 추가 (`ws: true`)로 개발 시 WebSocket을 localhost:8000으로 프록시

## Layout 변경
- `main-wrapper`: min-height → height: 100vh + overflow: hidden
- `.main-content:has(.terminal-page)`: padding: 0, display: flex, flex-direction: column
- 기존 Layout.css 고아 CSS 버그 수정 (133~135번째 줄 불필요한 규칙 제거)
