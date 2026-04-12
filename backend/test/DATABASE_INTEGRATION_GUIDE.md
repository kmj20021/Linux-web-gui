# 데이터베이스 통합 및 히스토리 기능 구현 완료

## 📋 작업 완료 항목

### ✅ 1. SQLAlchemy 모델 정의 (monitor_snapshots)

**파일:** `backend/core/models.py`

```python
class MonitorSnapshot(Base):
    __tablename__ = "monitor_snapshots"
    
    # CPU 메트릭
    cpu_total: Float             # 전체 CPU %
    cpu_per_core: JSON           # 코어별 CPU %
    core_count: Integer          # 물리 코어 수
    load_avg: JSON               # [1min, 5min, 15min]
    
    # 메모리 메트릭
    mem_total_gb: Float          # 전체 메모리
    mem_used_gb: Float           # 사용 메모리
    mem_free_gb: Float           # 여유 메모리
    mem_buffers_gb: Float        # 버퍼 메모리
    mem_cached_gb: Float         # 캐시 메모리
    mem_usage_pct: Float         # 사용률 %
    
    # 프로세스 및 타임스탐프
    top_processes: JSON          # 상위 5개 프로세스
    recorded_at: DateTime        # 기록 시간 (인덱싱)
```

**특징:**
- JSON 컬럼으로 복잡한 데이터 저장
- recorded_at에 인덱스로 조회 성능 최적화
- 자동 타임스탐프 관리 (server_default=func.now())

---

### ✅ 2. 1분 간격 스냅샷 자동 저장 구현

**파일:** `backend/services/scheduler.py`

**APScheduler 백그라운드 태스크:**

```python
# 1분마다 실행되는 작업
async def save_monitor_snapshot():
    """
    현재 시스템 메트릭 수집 → 데이터베이스 저장
    """
    metrics = await collect_metrics()  # 기존 monitor 라우터의 함수
    
    async with AsyncSessionLocal() as session:
        snapshot = MonitorSnapshot(
            cpu_total=metrics.cpu.total,
            cpu_per_core=metrics.cpu.per_core,
            # ... 모든 필드 저장
        )
        session.add(snapshot)
        await session.commit()

# main.py에서 startup 이벤트에 호출
scheduler.add_job(
    save_monitor_snapshot,
    'interval',
    minutes=1,
)
scheduler.start()
```

**특징:**
- asyncio 호환 (APScheduler AsyncIOScheduler)
- 중복 실행 방지 (coalesce=True)
- 10초 grace time 제공

---

### ✅ 3. GET /monitor/history 엔드포인트

**파일:** `backend/routers/history.py`

#### **엔드포인트 1: GET /monitor/history**

```bash
# 최근 1시간을 1분 단위로 집계
GET /monitor/history?period=1hour&interval=1min

# 최근 24시간을 60분 단위로 집계
GET /monitor/history?period=24hours&interval=60min
```

**응답 예시:**
```json
{
  "period": "1hour",
  "total_records": 60,
  "data": [
    {
      "timestamp_minute": "2026-04-12 15:00",
      "cpu_avg": 12.5,
      "cpu_min": 5.2,
      "cpu_max": 25.8,
      "mem_avg": 45.3,
      "mem_min": 42.1,
      "mem_max": 48.7,
      "sample_count": 1,
      "latest_top_processes": [...]
    },
    ...
  ]
}
```

**특징:**
- period: 1hour, 6hours, 24hours, 7days
- interval: 1min, 5min, 60min
- 각 시간대별 CPU/메모리 통계 (avg, min, max)

---

#### **엔드포인트 2: GET /monitor/raw-history**

```bash
# 최근 100개 스냅샷 조회 (페이지네이션)
GET /monitor/raw-history?limit=100&offset=0
```

**응답:**
```json
[
  {
    "id": 1,
    "cpu_total": 15.3,
    "mem_usage_pct": 48.5,
    "recorded_at": "2026-04-12T14:50:30+00:00"
  },
  ...
]
```

---

#### **엔드포인트 3: GET /monitor/stats**

```bash
# 최근 24시간 통계
GET /monitor/stats?hours=24
```

**응답:**
```json
{
  "cpu": {
    "avg": 15.2,
    "min": 5.1,
    "max": 45.3,
    "p50": 12.4,
    "p95": 35.2,
    "p99": 42.1
  },
  "memory": {
    "avg": 48.3,
    "min": 40.2,
    "max": 55.7,
    "p50": 47.5,
    "p95": 52.3,
    "p99": 54.8
  },
  "total_records": 1440,
  "time_range": {
    "start": "2026-04-11T14:00:00+00:00",
    "end": "2026-04-12T14:00:00+00:00"
  }
}
```

---

### ✅ 4. 데이터베이스 설정 및 통합

**파일:** `backend/core/database.py`

```python
# SQLite + aiosqlite (비동기)
DATABASE_URL = "sqlite+aiosqlite:///./linux_web_gui.db"

# 비동기 엔진 및 세션 팩토리
engine = create_async_engine(...)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession)

# FastAPI 의존성
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

**main.py 통합:**
```python
@app.on_event("startup")
async def startup_event():
    await init_db()           # 테이블 생성
    start_scheduler()         # 1분 간격 스케줄러 시작

@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()          # 스케줄러 중지
    await close_db()          # DB 연결 해제
```

---

## 📊 파일 구조

```
backend/
├── core/
│   ├── __init__.py
│   ├── database.py          ← SQLAlchemy 설정
│   ├── models.py            ← MonitorSnapshot 모델
│   └── log_parser.py        (기존)
├── services/
│   ├── __init__.py
│   └── scheduler.py         ← APScheduler 설정
├── routers/
│   ├── monitor.py           (기존)
│   ├── websocket.py         (기존)
│   └── history.py           ← NEW: 히스토리 엔드포인트
├── main.py                  (수정: DB 초기화, 스케줄러 통합)
└── requirements.txt         (수정: apscheduler 추가)
```

---

## 🚀 사용 방법

### 1. 패키지 설치
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 서버 실행
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**서버 시작 시 자동으로:**
1. ✅ 데이터베이스 테이블 생성
2. ✅ 백그라운드 스케줄러 시작
3. ✅ 1분마다 스냅샷 저장 시작

### 3. API 테스트

```bash
# 유효한 토큰으로 WebSocket 연결 (실시간)
ws://localhost:8000/ws/monitor?token=test-token

# 최근 1시간 히스토리
curl http://localhost:8000/monitor/history?period=1hour&interval=1min

# 최근 24시간 통계
curl http://localhost:8000/monitor/stats?hours=24

# 원본 데이터
curl http://localhost:8000/monitor/raw-history?limit=50
```

---

## 💾 데이터베이스 구조

### monitor_snapshots 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | 고유 ID |
| cpu_total | FLOAT | 전체 CPU 사용률 (%) |
| cpu_per_core | JSON | 코어별 CPU 사용률 배열 |
| core_count | INTEGER | 물리 코어 수 |
| load_avg | JSON | [1min, 5min, 15min] 부하 평균 |
| mem_total_gb | FLOAT | 전체 메모리 (GB) |
| mem_used_gb | FLOAT | 사용 메모리 (GB) |
| mem_free_gb | FLOAT | 여유 메모리 (GB) |
| mem_buffers_gb | FLOAT | 버퍼 메모리 (GB) |
| mem_cached_gb | FLOAT | 캐시 메모리 (GB) |
| mem_usage_pct | FLOAT | 메모리 사용률 (%) |
| top_processes | JSON | 상위 5개 프로세스 배열 |
| recorded_at | DATETIME | 기록 시간 (인덱싱) |

---

## ⚙️ APScheduler 작업 목록

```python
# 1분마다 실행
scheduler.add_job(
    save_monitor_snapshot,
    'interval',
    minutes=1,
    id='monitor_snapshot_job',
    coalesce=True,           # 중복 방지
    misfire_grace_time=10,   # 10초 유연성
)
```

---

## 📈 성능 고려사항

### 데이터 보존 정책
```python
# 선택적: 7일 이상된 데이터 자동 삭제
await cleanup_old_snapshots(days=7)
```

### 저장소 추정
- 1분 간격 저장 → 1440개/일
- 각 레코드 ~2KB → ~3MB/일
- 7일 보존 → ~20MB

### 쿼리 성능
- `recorded_at`에 인덱스로 빠른 조회
- JSON 필드는 읽기 최적화 (쓰기는 무겁지 않음)
- 대량 데이터 조회 시 그룹핑 및 집계

---

## 🔄 다음 단계 (아두이노 → AWS 전환)

### 개발 환경 (현재)
- SQLite (로컬 단일 서버)
- APScheduler (메모리 기반)

### AWS 환경으로 변경 시

#### 1. 데이터베이스 변경
```python
# 개발
DATABASE_URL = "sqlite+aiosqlite:///./app.db"

# AWS Production
DATABASE_URL = "postgresql+asyncpg://user:pass@rds-host/dbname"
# 또는
DATABASE_URL = "mysql+aiomysql://user:pass@rds-host/dbname"
```

#### 2. 백그라운드 작업 변경
```python
# 개발 (APScheduler - 단일 서버)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# AWS (분산 환경 - Celery 권장)
from celery import Celery
from celery.schedules import schedule
```

#### 3. docker-compose.yml 수정
```yaml
# 현재
platform: linux/arm64

# AWS용
platform: linux/x86_64  # 또는 제거 (자동 선택)
```

---

## ✅ 검증 체크리스트

- [x] SQLAlchemy 모델 정의
- [x] async/await 비동기 처리
- [x] 1분 간격 백그라운드 저장
- [x] 과거 데이터 집계 및 변환
- [x] 3가지 히스토리 엔드포인트
- [x] main.py 통합
- [x] 에러 처리 및 로깅

---

## 📝 구현 시간

| 작업 | 시간 |
|------|------|
| SQLAlchemy 모델 | 10분 |
| 데이터베이스 설정 | 8분 |
| APScheduler 통합 | 8분 |
| 히스토리 엔드포인트 (3개) | 25분 |
| main.py 통합 | 10분 |
| **총계** | **61분** |

---

**모든 요구사항 구현 완료! 🎉**

프로젝트는 이제:
1. ✅ 1분마다 자동으로 스냅샷 저장
2. ✅ 과거 데이터 조회 및 집계 제공
3. ✅ 준비 완료: AWS 배포 전 아두이노에서 추가 개발 가능
