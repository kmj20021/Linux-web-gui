---
name: network_connections_endpoint_blocked
description: GET /api/network/connections 엔드포인트 테스트 불가 - 백엔드 서버 재시작 필요
metadata:
  type: project
---

## 상황

task_id: network-ports-001-test 테스트 중 문제 발생

## 문제 현황

- `GET /api/network/connections` 엔드포인트가 404 반환
- 백엔드 코드: `/home/ubuntu/Linux-web-gui/backend/routers/network.py` 라인 169-222에 엔드포인트 정의 존재
- main.py 라인 136-140에 router 정상 등록됨
- 회귀 테스트 (`/api/network/interfaces`, `/api/network/traffic`, `/api/network/packets`) 모두 정상 동작

## 근본 원인

현재 실행 중인 uvicorn 프로세스가 **이전 버전의 코드**를 메모리에 로드하고 있음
- 프로세스: PID 184623, root 권한으로 실행 중 (`/usr/local/bin/python /root/.local/bin/uvicorn main:app`)
- 권한 제약으로 현재 사용자(ubuntu)에서 kill 불가

## 필요 조치

1. root 권한으로 서버 프로세스 재시작
2. 또는 supervisor/systemd 재시작

## 테스트 현황

- 프론트엔드 빌드: PASS ✓
- GET /api/network/interfaces: PASS ✓
- GET /api/network/traffic: PASS ✓
- GET /api/network/packets: PASS ✓
- GET /api/network/connections: BLOCKED (404 Not Found)

**Why:** 코드는 정상이지만 프로세스 메모리 때문에 새 엔드포인트가 노출되지 않음

**How to apply:** 담당 PM에게 보고 후 root 권한으로 서버 재시작 대기
