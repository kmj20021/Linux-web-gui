# Docker 없이 백엔드 로컬 개발 환경 준비 가이드

## 1️⃣ **필수 준비물**

### Windows에 설치되어야 할 것
- [x] Python 3.11+ (이미 설치됨)
- [x] Git (이미 설치됨)
- [x] pip (Python과 함께 설치됨)
- [x] SQLite (기본 내장)

### 확인 명령어
```powershell
python --version     # Python 3.11.x 이상
pip --version        # pip 23.x 이상
sqlite3 --version    # sqlite3를 사용하므로 필수
```

---

## 2️⃣ **Step-by-Step: 백엔드 로컬 환경 구성**

### 단계 1: 가상환경 생성 (Python venv)

**목적**: 프로젝트별 독립적인 Python 환경을 만들어 패키지 충돌 방지

```powershell
# 1. 백엔드 디렉토리로 이동
cd C:\Users\user\my_pj\linux-web-gui\backend

# 2. 가상환경 생성
python -m venv venv

# 3. 가상환경 활성화 (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 또는 cmd에서는:
# venv\Scripts\activate.bat

# 확인: 터미널 앞에 (venv)가 표시되어야 함
# (venv) PS C:\Users\user\my_pj\linux-web-gui\backend>
```

**만약 Activate.ps1 실행 권한 오류가 나면:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# 다시 시도: .\venv\Scripts\Activate.ps1
```

---

### 단계 2: 의존성 설치

```powershell
# 가상환경이 활성화된 상태에서:

# 1. pip 업그레이드
pip install --upgrade pip

# 2. requirements.txt에서 모든 패키지 설치
pip install -r requirements.txt

# 설치 시간: 약 2-3분 (인터넷 속도에 따라)

# 3. 설치 확인
pip list
# 다음이 보여야 함:
# fastapi     0.115.0
# uvicorn     0.30.0
# websockets  12.0
# ... 등등
```

---

### 단계 3: 데이터베이스 초기화

```powershell
# 같은 터미널에서 (venv 활성화 상태):

# Python 대화형 모드로 DB 테이블 생성
python -c "
import asyncio
from core.database import init_db

async def setup():
    await init_db()
    print('✅ 데이터베이스 테이블 생성 완료')

asyncio.run(setup())
"

# 또는 더 간단하게:
python -m pytest test/test_db.py  # (만약 테스트 코드가 있다면)
```

**생성되는 파일:**
```
backend/
└─ linux_web_gui.db  # SQLite 데이터베이스 파일 (약 16KB)
```

---

### 단계 4: 서버 시작

```powershell
# 가상환경 활성화 상태에서:

# FastAPI 개발 서버 실행
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 출력:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Application startup complete.

# 서버가 실행 중입니다!
# Ctrl+C로 종료 가능
```

**--reload 옵션**: 파일 변경 시 자동 재시작 (개발용)

**포트 변경 가능:**
```powershell
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## 3️⃣ **테스트 전 확인사항**

### 백엔드 시작 후 로그 확인

```
INFO:main:✅ auth, monitor, websocket, history 라우터 등록됨
INFO:     Application startup complete.
INFO:main:🚀 FastAPI 서버 시작
INFO:main:✅ 데이터베이스 접속 및 테이블 생성 완료
INFO:services.scheduler:🚀 모니터링 스케줄러 시작됨 (1분 간격)
INFO:main:✅ 백그라운드 스케줄러 시작됨
INFO:     Uvicorn running on http://0.0.0.0:8000
```

모두 보이면 ✅ 정상입니다!

---

## 4️⃣ **테스트 엔드포인트 (PowerShell에서)**

### 헬스 체크
```powershell
curl http://localhost:8000/api/health
# 응답: {"status":"healthy","message":"서버가 정상 작동 중입니다"}
```

### 로그인 (토큰 발급)
```powershell
curl -X POST http://localhost:8000/auth/login `
  -H "Content-Type: application/json" `
  -Body '{"username":"admin","password":"password"}'

# 응답:
# {
#   "access_token": "test_token_123",
#   "token_type": "bearer",
#   "expires_in": 900,
#   "user": {"username": "admin", "role": "admin"}
# }
```

### CPU 메트릭 조회
```powershell
curl http://localhost:8000/monitor/cpu
```

### 메모리 메트릭 조회
```powershell
curl http://localhost:8000/monitor/memory
```

---

## 5️⃣ **FastAPI 자동 API 문서**

### OpenAPI (Swagger UI)
```
http://localhost:8000/docs
```

### ReDoc (Alternative API 문서)
```
http://localhost:8000/redoc
```

브라우저에서 접속하면 모든 엔드포인트를 시각적으로 테스트할 수 있습니다!

---

## 6️⃣ **가상환경 비활성화 & 종료**

```powershell
# 개발 종료 후:
deactivate

# 또는 터미널 창 닫기
exit
```

---

## 🔧 **트러블슈팅**

### 문제 1: "No module named 'fastapi'"
```powershell
# 해결: 가상환경이 활성화되지 않음
.\venv\Scripts\Activate.ps1
```

### 문제 2: "Port 8000 already in use"
```powershell
# 포트 변경
uvicorn main:app --port 8001 --reload
```

### 문제 3: SQLite DB 손상
```powershell
# linux_web_gui.db 파일 삭제 후 재실행
rm linux_web_gui.db
# 서버 재시작하면 자동 재생성
```

### 문제 4: Python 경로 문제
```powershell
# 현재 경로 확인
Get-Location
# C:\Users\user\my_pj\linux-web-gui\backend 에 있어야 함
```

---

## 📊 **최종 확인 체크리스트**

```
✅ Python 3.11+ 설치
✅ 가상환경 생성 (venv)
✅ 가상환경 활성화 (Activate.ps1)
✅ requirements.txt 설치 (pip install -r requirements.txt)
✅ 데이터베이스 초기화 (init_db)
✅ 서버 시작 (uvicorn main:app)
✅ 헬스 체크 (curl http://localhost:8000/api/health)
✅ FastAPI 문서 접속 (http://localhost:8000/docs)
```

모두 완료되면 테스트 준비 완료! 🎉
