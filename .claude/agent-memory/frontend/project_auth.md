---
name: JWT Auth Implementation
description: 프론트엔드 JWT 인증 시스템 구현 상세 (AuthContext, Login, ProtectedRoute, client.js)
type: project
---

JWT 인증 시스템을 2026-05-05 구현 완료.

**구현 파일 목록:**
- `frontend/src/context/AuthContext.jsx` — React Context 전역 인증 상태 (신규)
- `frontend/src/pages/Login.jsx` — 로그인 페이지 (신규)
- `frontend/src/styles/Login.css` — 로그인 스타일, 로딩 스피너 포함 (신규)
- `frontend/src/components/ProtectedRoute.jsx` — 미인증 접근 차단 컴포넌트 (신규)
- `frontend/src/api/client.js` — AUTH_TOKEN 하드코딩 제거, authAPI·getAuthHeaders·getAuthToken 추가, WebSocket URL 동적화
- `frontend/src/App.jsx` — AuthProvider 감싸기, /login 라우트, 모든 기존 라우트 ProtectedRoute 적용
- `frontend/src/components/Sidebar.jsx` — useAuth 연결, 실제 user 표시, 로그아웃 버튼 추가, 이모지→SVG 아이콘 교체

**핵심 설계 결정:**
- localStorage key: `auth_token`
- 앱 시작 시 `GET /api/auth/me` 로 토큰 자동 검증
- WebSocket URL 빌드 시 매번 localStorage에서 토큰을 읽어 동적 생성 (`_buildUrl()`)
- 로그아웃 시 `_stopReconnect = true` 플래그로 WebSocket 재연결 차단

**Why:** 백엔드 JWT API가 이미 구현된 상태에서 프론트엔드 인증 레이어 추가 요청.

**How to apply:** 추후 인증 관련 변경 시 위 파일 목록 참조. authAPI 호출은 client.js의 authAPI 객체를 사용.
