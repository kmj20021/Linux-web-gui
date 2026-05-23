---
name: network_connections_endpoint_test
description: GET /api/network/connections 엔드포인트 테스트 완료, 모든 조건 충족
metadata:
  type: project
  date: 2026-05-23
---

## 테스트 결과

**task_id:** network-ports-001-test  
**상태:** ALL PASSED (11/11 tests)  
**날짜:** 2026-05-23

## 테스트 항목별 결과

### 성공한 테스트 (11/11)

1. ✓ GET /api/network/connections HTTP 200 응답
2. ✓ 응답이 배열이며 비어있지 않음 (30개 항목)
3. ✓ 모든 항목에 proto 필드 존재
4. ✓ 모든 항목에 local_ip 필드 존재
5. ✓ 모든 항목에 local_port 필드 존재
6. ✓ 모든 항목에 status 필드 존재
7. ✓ local_port 오름차순 정렬 ([22, 22, 22, 53, 53, ...])
8. ✓ proto 값이 'tcp' 또는 'udp'만 포함
9. ✓ GET /api/network/interfaces 회귀 테스트 (7 items)
10. ✓ GET /api/network/traffic 회귀 테스트 (7 items)
11. ✓ GET /api/network/packets 회귀 테스트 (7 items)
12. ✓ 프론트엔드 Network.jsx 빌드 성공

## 구현 파일

- `/home/ubuntu/Linux-web-gui/backend/routers/network.py` - /connections 엔드포인트 구현 (라인 169-222)
- `/home/ubuntu/Linux-web-gui/backend/main.py` - network router 등록 (라인 136-140)
- `/home/ubuntu/Linux-web-gui/frontend/src/pages/Network.jsx` - ConnectionsTab 컴포넌트
- `/home/ubuntu/Linux-web-gui/frontend/src/api/client.js` - networkAPI.getConnections() 메서드

## 기술 상세

### 응답 구조 검증
```json
{
  "proto": "tcp|udp",
  "local_ip": "172.31.33.247",
  "local_port": 22,
  "remote_ip": "182.231.179.136",
  "remote_port": 61857,
  "status": "ESTABLISHED",
  "pid": 12345,
  "process_name": "python3"
}
```

### 백엔드 구현 특징
- `psutil.net_connections(kind='inet')` 사용
- SOCK_STREAM → 'tcp', SOCK_DGRAM → 'udp'
- 프로세스 이름 캐싱으로 중복 조회 방지
- **local_port 기준 오름차순 정렬** (None은 끝에 배치)

### 프론트엔드 구현 특징
- ConnectionsTab에서 10초 간격 갱신
- 상태별 스타일링 (LISTEN: green, ESTABLISHED: blue, TIME_WAIT/CLOSE_WAIT: gray)
- 주소:포트 형식으로 표시

## 테스트 환경

- 백엔드 서버: Python/FastAPI (포트 8001에서 테스트)
- 시스템: Linux 6.17.0-1013-aws (Docker 환경)
- 동시 연결: 30개 (테스트 시점)

**Why:** 새로 추가된 /connections 엔드포인트가 정상 동작하고, 기존 기능이 손상되지 않았음을 확인

**How to apply:** 원래 포트 8000 서버 재시작 후 프로덕션 배포 가능
