# CLAUDE.md - 프로젝트 개발 가이드

## 📋 프로젝트 개요

**Linux Web GUI 관리 시스템** - EC2(Ubuntu)에서 실행되는 Docker 기반 웹 관리 대시보드

### 🏗️ 기술 스택

| 구성요소 | 기술 | 버전 |
|---------|------|------|
| **백엔드** | FastAPI + Python | 3.11 |
| **프론트엔드** | React + Vite | 18.2 / 5.0 |
| **API Gateway** | Nginx | 1.24 |
| **데이터베이스** | SQLite | - |
| **컨테이너** | Docker Compose | 3.8 |
| **플랫폼** | Linux AMD64 | - |

---

## 📁 디렉토리 구조

```
linux-web-gui/
├── backend/                  # FastAPI 백엔드
│   ├── main.py              # 진입점
│   ├── requirements.txt      # Python 의존성
│   ├── Dockerfile           # 백엔드 컨테이너
│   ├── core/                # 핵심 기능 (DB, 파서)
│   ├── routers/             # API 라우터 (auth, monitor, etc)
│   ├── schemas/             # Pydantic 스키마
│   ├── services/            # 비즈니스 로직
│   └── test/                # 테스트 코드
├── frontend/                 # React 프론트엔드
│   ├── src/
│   │   ├── main.jsx         # 진입점
│   │   ├── App.jsx          # 루트 컴포넌트
│   │   ├── components/      # React 컴포넌트
│   │   ├── pages/           # 페이지 컴포넌트
│   │   ├── styles/          # CSS 파일
│   │   ├── api/             # API 클라이언트
│   │   └── hooks/           # Custom hooks
│   ├── package.json         # Node 의존성
│   ├── vite.config.js       # Vite 설정
│   ├── Dockerfile           # 프론트엔드 컨테이너
│   └── nginx.conf           # Nginx 설정
├── nginx/                    # Nginx 리버스 프록시
│   └── nginx.conf           # 메인 Nginx 설정
├── docker-compose.yml       # 컨테이너 오케스트레이션
└── docs/                    # 문서
```

---

## 🚀 빌드 & 실행 명령어

### **1️⃣ 로컬 개발 (로컬 PC)**

#### 백엔드 실행
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 프론트엔드 실행
```bash
cd frontend
npm install
npm run dev
# 접속: http://localhost:5173
```

### **2️⃣ Docker Compose (전체 스택)**

```bash
# EC2 또는 로컬에서
docker-compose up -d --build     # 빌드 후 실행
docker-compose ps               # 상태 확인
docker-compose logs -f          # 로그 확인
docker-compose down             # 종료
docker-compose down -v          # 종료 + 볼륨 삭제
```

### **3️⃣ 개별 컨테이너 빌드**

```bash
# 백엔드만 빌드
docker build -f backend/Dockerfile -t minjegod/linux_gui_backend:latest ./backend

# 프론트엔드만 빌드
docker build -f frontend/Dockerfile -t minjegod/linux_gui_frontend:latest ./frontend

# 푸시 (Docker Hub)
docker push minjegod/linux_gui_backend:latest
docker push minjegod/linux_gui_frontend:latest
```

---

## 🧪 테스트 명령어

### **백엔드 테스트**

```bash
# 헬스 체크
curl http://localhost:8000/api/health

# Swagger UI (대화형 API 테스트)
# 브라우저: http://localhost:8000/docs

# API 문서 (ReDoc)
# 브라우저: http://localhost:8000/redoc

# 개별 테스트 파일 실행
cd backend/test
python -m pytest test_endpoints.py -v
python -m pytest test_database_integration.py -v
python -m pytest test_websocket.py -v
```

### **프론트엔드 테스트**

```bash
cd frontend

# 빌드 테스트
npm run build

# 빌드 결과 미리보기
npm run preview

# 개발 서버 실행 (핫 리로드)
npm run dev
```

### **Docker 컨테이너 테스트**

```bash
# 컨테이너 상태 확인
docker-compose ps
docker logs linux-web-gui-backend-1
docker logs linux-web-gui-frontend-1

# 포트 연결 확인
docker port linux-web-gui-backend-1
docker port linux-web-gui-frontend-1

# 네트워크 테스트
docker exec linux-web-gui-backend-1 curl http://localhost:8000/api/health
docker exec linux-web-gui-frontend-1 curl http://localhost
```

---

### **프론트엔드 (JavaScript/React)**

**현재 설정 상태:** 린트 도구 미설정

```bash
# 권장: ESLint + Prettier 설치
npm install --save-dev eslint prettier eslint-config-prettier eslint-plugin-react

# Prettier - 코드 포맷팅
npx prettier --write "src/**/*"

# ESLint - 린트
npx eslint src/
```

---

## 📝 환경 변수

### **EC2 배포 시**

```bash
# .env 파일 또는 docker-compose 환경 변수 설정
export DATABASE_URL="sqlite:///./database.db"
export SECRET_KEY="your-secret-key-here"
export ALGORITHM="HS256"
export DOMAIN_NAME="your-domain.com"  # 선택사항

# docker-compose 실행
docker-compose up -d
```

---

## 🔧 개발 워크플로우

### **로컬 개발**
```bash
# 1. 백엔드 터미널
cd backend
source venv/bin/activate
uvicorn main:app --reload

# 2. 프론트엔드 터미널
cd frontend
npm run dev

# 3. 접속
# 프론트엔드: http://localhost:5173
# 백엔드 API: http://localhost:8000/api/
```

### **EC2 개발/배포**
```bash
# 1. Git 클론
git clone <repo-url>
cd linux-web-gui

# 2. 권한 설정 (필수)
sudo usermod -aG docker ubuntu
newgrp docker

# 3. Docker Compose 실행
docker-compose up -d --build

# 4. 접속
# http://52.79.126.164 (프론트엔드)
# http://52.79.126.164:8000/api/health (백엔드)
```

---

## 🐛 문제 해결

### Docker 권한 오류
```bash
# 해결방법
sudo usermod -aG docker $USER
newgrp docker
```

### Port 충돌
```bash
# 포트 상태 확인
lsof -i :8000
lsof -i :5173
lsof -i :80

# 컨테이너 재시작
docker-compose restart
```

### 데이터베이스 초기화
```bash
# SQLite 초기화 (주의!)
rm backend/database.db
docker-compose restart backend
```

---

## 📌 핵심 파일 위치

| 파일 | 경로 | 설명 |
|------|------|------|
| 메인 진입점 (백엔드) | `backend/main.py` | FastAPI 앱 |
| 메인 진입점 (프론트엔드) | `frontend/src/main.jsx` | React 앱 |
| API 라우터 | `backend/routers/` | API 엔드포인트 |
| React 컴포넌트 | `frontend/src/components/` | UI 컴포넌트 |
| 데이터베이스 | `backend/core/database.py` | DB 설정 |
| Nginx 설정 | `frontend/nginx.conf` | 정적 파일 서빙 |

---

## Rules & Verification

- **IMPORTANT: 코드를 생성하거나 수정한 후에는 답변하기 전에 반드시 해당 기능이 정상 작동하는지 테스트해야 합니다.** 
- **검증 철칙:** 테스트 결과가 'Pass'이고 에러가 0건이라는 객관적인 증거(터미널 출력값)를 확인하기 전에는 답변을 완료하지 마십시오.
- **테스트 실행:** 프로젝트의 기본 테스트 명령을 사용하여 변경 사항을 직접 확인하십시오. 
- 추측성 단어(예: "아마도", "~할 것 같습니다")를 사용하지 말고, 실제 실행 결과를 바탕으로 답변하십시오.

---

## 추가 문서

- [BACKEND_LOCAL_SETUP.md](BACKEND_LOCAL_SETUP.md) - 백엔드 로컬 설정
- [LETSENCRYPT_SETUP.md](LETSENCRYPT_SETUP.md) - SSL 인증서 설정
- [docs/](docs/) - 기술 문서

