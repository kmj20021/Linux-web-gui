#!/usr/bin/env python3
"""
WebSocket 메시지 형식 및 구조 검증 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 70)
print("WebSocket /ws/monitor 엔드포인트 검증")
print("=" * 70)

# ============================================================
# 1. WebSocket 모듈 임포트 테스트
# ============================================================
print("\n[1] WebSocket 라우터 임포트 테스트")
try:
    from routers.websocket import (
        router,
        MonitorMessage,
        CPUSnapshot,
        MemorySnapshot,
        ProcessSnapshot,
        verify_token,
        collect_metrics,
    )
    print("✅ WebSocket 라우터, 모델, 헬퍼 함수 임포트 성공")
except ImportError as e:
    print(f"❌ 임포트 실패: {e}")
    sys.exit(1)

# ============================================================
# 2. 토큰 검증 함수 테스트
# ============================================================
print("\n[2] 토큰 검증 함수 테스트")
test_cases = [
    (None, False, "None 토큰"),
    ("", False, "빈 문자열"),
    ("invalid-token", False, "유효하지 않은 토큰"),
    ("test-token", True, "유효한 토큰 (test-token)"),
    ("demo-token", True, "유효한 토큰 (demo-token)"),
]

for token, expected, description in test_cases:
    result = verify_token(token)
    status = "✅" if result == expected else "❌"
    print(f"  {status} {description}: {token} → {result}")

# ============================================================
# 3. Pydantic 모델 필드 검증
# ============================================================
print("\n[3] Pydantic 모델 필드 검증")

models_and_fields = {
    "CPUSnapshot": ["total", "per_core", "core_count", "load_avg"],
    "MemorySnapshot": ["total_gb", "used_gb", "free_gb", "buffers_gb", "cached_gb", "usage_pct"],
    "ProcessSnapshot": ["pid", "name", "cpu_pct", "mem_pct"],
    "MonitorMessage": ["type", "cpu", "memory", "top_processes", "timestamp"],
}

all_valid = True
for model_name, expected_fields in models_and_fields.items():
    try:
        model_cls = globals()[model_name]
        fields = list(model_cls.model_fields.keys())
        
        missing = set(expected_fields) - set(fields)
        extra = set(fields) - set(expected_fields)
        
        if not missing and not extra:
            print(f"  ✅ {model_name}: {fields}")
        else:
            all_valid = False
            print(f"  ❌ {model_name}")
            if missing:
                print(f"     누락된 필드: {missing}")
            if extra:
                print(f"     추가 필드: {extra}")
                
    except KeyError:
        all_valid = False
        print(f"  ❌ {model_name} 모델을 찾을 수 없음")

# ============================================================
# 4. 메시지 형식 검증 (샘플 메트릭 수집)
# ============================================================
print("\n[4] 메시지 형식 검증 (시스템 메트릭 샘플 추출)")
try:
    import asyncio
    import json
    
    async def test_message_format():
        try:
            metrics = await collect_metrics()
            
            # 메시지 덤프
            print(f"  ✅ 메트릭 수집 성공")
            
            # JSON 직렬화 테스트
            message_dict = metrics.model_dump()
            message_json = json.dumps(message_dict, indent=2)
            
            # 필수 필드 검증
            required_keys = {"type", "cpu", "memory", "top_processes", "timestamp"}
            message_keys = set(message_dict.keys())
            
            if required_keys == message_keys:
                print(f"  ✅ 메시지 최상위 필드 일치: {required_keys}")
            else:
                missing = required_keys - message_keys
                extra = message_keys - required_keys
                if missing:
                    print(f"  ⚠️  누락된 필드: {missing}")
                if extra:
                    print(f"  ⚠️  추가 필드: {extra}")
            
            # 타입 검증
            print(f"\n  📊 메시지 샘플:")
            print(f"     type: {message_dict['type']}")
            print(f"     cpu.total: {message_dict['cpu']['total']}")
            print(f"     memory.total_gb: {message_dict['memory']['total_gb']}")
            print(f"     top_processes 개수: {len(message_dict['top_processes'])}")
            print(f"     timestamp: {message_dict['timestamp']}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ 메트릭 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    success = asyncio.run(test_message_format())
    if not success:
        all_valid = False
        
except Exception as e:
    print(f"  ❌ asyncio 테스트 실패: {e}")
    all_valid = False

# ============================================================
# 5. WebSocket 라우터 엔드포인트 검증
# ============================================================
print("\n[5] FastAPI 라우터 엔드포인트 검증")
routes = [r.path for r in router.routes]
expected_route = "/ws/monitor"  # 전체 경로 (prefix + path)

if expected_route in routes:
    print(f"  ✅ WebSocket 경로: {expected_route}")
    # 라우트 상세 정보
    for r in router.routes:
        if r.path == expected_route:
            print(f"     - Type: WebSocket")
            print(f"     - Query Parameters: ?token=<valid_token>")
else:
    all_valid = False
    print(f"  ❌ 예상 경로: {expected_route}")
    print(f"     실제 경로: {routes}")

# ============================================================
# 최종 결과
# ============================================================
print("\n" + "=" * 70)
if all_valid:
    print("✅ 모든 검증 통과!")
    print("\n📝 WebSocket 사용 방법:")
    print("  1. 클라이언트가 ws://localhost:8000/ws/monitor?token=test-token 연결")
    print("  2. 서버가 1초마다 JSON 메시지 브로드캐스트:")
    print("""    {
      "type": "monitor.snapshot",
      "cpu": {"total": float, "per_core": [...], "core_count": int, "load_avg": [...]},
      "memory": {"total_gb": float, ...},
      "top_processes": [{"pid": int, "name": str, "cpu_pct": float, ...}, ...],
      "timestamp": "ISO 8601 string"
    }""")
else:
    print("❌ 일부 검증 실패")
    sys.exit(1)

print("=" * 70)
