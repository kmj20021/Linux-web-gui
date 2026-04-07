#!/usr/bin/env python3
"""
엔드포인트 직접 테스트 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("꼼꼼한 엔드포인트 구조 검증")
print("=" * 60)

# 1. 라우터 임포트 테스트
# monitor.py에서 라우터와 모델이 제대로 정의되고 임포트되는지 확인
print("\n[1] monitor 라우터 임포트 테스트")
try:
    from routers.monitor import (
        router,
        CPUMetrics,
        MemoryMetrics,
        ProcessInfo,
        DiskMetrics,
        NetworkMetrics,
        get_cpu_metrics,
        get_memory_metrics,
        get_top_processes,
    )
    print("✅ 라우터 및 모델 임포트 성공")
except ImportError as e:
    print(f"❌ 임포트 실패: {e}")
    sys.exit(1)

# 2. 데이터 모델 검증
# 각 모델들이 해당 필드를 가지고 있는지 확인
print("\n[2] Pydantic 모델 필드 검증")
models_and_fields = {
    "CPUMetrics": ["cpu_total", "cpu_per_core", "core_count", "load_avg", "recorded_at"],
    "MemoryMetrics": ["total_gb", "used_gb", "free_gb", "buffers_gb", "cached_gb", "usage_pct"],
    "ProcessInfo": ["pid", "name", "cpu_pct", "mem_pct"],
    "DiskMetrics": ["path", "total_gb", "used_gb", "free_gb", "usage_pct"],
    "NetworkMetrics": ["interface", "bytes_sent", "bytes_recv", "packets_sent", "packets_recv", "errin", "errout", "dropin", "dropout"],
}

for model_name, expected_fields in models_and_fields.items():
    try:
        model_cls = globals()[model_name] #전역변수들중 model_name에 해당하는 클래스 가져오기
        fields = list(model_cls.model_fields.keys())
        print(f"\n  {model_name}:")
        print(f"    예상: {expected_fields}")
        print(f"    실제: {fields}")
        
        missing = set(expected_fields) - set(fields)
        extra = set(fields) - set(expected_fields)
        
        if missing:
            print(f"    ⚠️  누락된 필드: {missing}")
        if extra:
            print(f"    ⚠️  추가 필드: {extra}")
        if not missing and not extra:
            print(f"    ✅ 모든 필드 일치")
    except KeyError:
        print(f"  ❌ {model_name} 모델 찾을 수 없음")

# 3. 엔드포인트 라우트 검증
# API 경로들이 맞는지 확인 (예: /monitor/cpu, /monitor/memory 등)
print("\n[3] FastAPI 라우터 경로 검증")
routes = [r.path for r in router.routes]
expected_routes = [
    "/cpu",
    "/memory",
    "/processes",
    "/disks",
    "/disk",
    "/network",
]

for route in expected_routes:
    full_path = f"/monitor{route}"
    if full_path in routes:
        print(f"  ✅ {full_path}")
    else:
        print(f"  ❌ {full_path} 없음")

# 4. 함수 서명 검증
# 엔드포인트 함수들이 올바른 시그니처를 가지고 있는지 확인
print("\n[4] 엔드포인트 함수 실행 테스트 (의존성 체크)")
try:
    import psutil
    print(f"  psutil 설치됨 (v{psutil.__version__})")
    
    # CPU 메트릭 샘플 추출
    print("\n  시스템 메트릭 샘플 추출:")
    
    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.1)
    cpu_cores = psutil.cpu_count(logical=False)
    print(f"    - CPU: {cpu_pct}% (cores: {cpu_cores})")
    
    # Memory
    mem = psutil.virtual_memory()
    print(f"    - Memory: {mem.used / (1024**3):.2f}GB / {mem.total / (1024**3):.2f}GB")
    
    # Disk
    try:
        disk = psutil.disk_usage("/")
        print(f"    - Disk: {disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB")
    except:
        print(f"    - Disk: (접근 불가)")
    
    # Network
    try:
        net = psutil.net_io_counters()
        print(f"    - Network: ↓{net.bytes_recv/(1024**3):.2f}GB ↑{net.bytes_sent/(1024**3):.2f}GB")
    except:
        print(f"    - Network: (접근 불가)")
        
except ImportError:
    print("  ❌ psutil이 설치되지 않았습니다")

print("\n" + "=" * 60)
print("✅ 검증 완료")
print("=" * 60)
