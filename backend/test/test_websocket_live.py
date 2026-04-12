#!/usr/bin/env python3
"""
WebSocket 동적 테스트
실제 서버를 실행하고 클라이언트가 연결해서 메시지를 수신하는지 검증
"""
import asyncio
import json
import websockets
import sys
from datetime import datetime

print("=" * 70)
print("WebSocket /ws/monitor 동적 테스트")
print("=" * 70)

# ============================================================
# 테스트 1: 토큰 없이 연결 시도 (실패해야 함)
# ============================================================
async def test_no_token():
    print("\n[1] 토큰 없이 연결 시도")
    try:
        async with websockets.connect("ws://localhost:8000/ws/monitor") as ws:
            print("  ❌ 연결 성공 (이상): 토큰 없이 연결되면 안 됨")
            return False
    except Exception as e:
        # websockets.exceptions.InvalidStatus (토큰 없을 때)
        error_str = str(e).lower()
        if "401" in error_str or "403" in error_str or "404" in error_str or "unauthorized" in error_str or "rejected" in error_str:
            print(f"  ✅ 연결 거부됨: {e}")
            return True
        else:
            print(f"  ⚠️  예외 발생: {type(e).__name__}: {e}")
            # 서버가 안 켜져 있을 수 있음
            return None

# ============================================================
# 테스트 2: 잘못된 토큰으로 연결 시도 (실패해야 함)
# ============================================================
async def test_invalid_token():
    print("\n[2] 잘못된 토큰으로 연결 시도")
    try:
        async with websockets.connect("ws://localhost:8000/ws/monitor?token=wrong-token") as ws:
            print("  ❌ 연결 성공 (이상): 잘못된 토큰으로 연결되면 안 됨")
            return False
    except Exception as e:
        error_str = str(e).lower()
        if "401" in error_str or "403" in error_str or "unauthorized" in error_str or "rejected" in error_str:
            print(f"  ✅ 연결 거부됨: {e}")
            return True
        else:
            print(f"  ⚠️  예외 발생: {type(e).__name__}: {e}")
            return None

# ============================================================
# 테스트 3: 유효한 토큰으로 연결 및 메시지 수신
# ============================================================
async def test_valid_token():
    print("\n[3] 유효한 토큰으로 연결 및 메시지 수신")
    try:
        messages = []
        async with websockets.connect("ws://localhost:8000/ws/monitor?token=test-token") as ws:
            print("  ✅ 연결 성공")
            
            # 3-5개 메시지 수신 (1초 × 3 = 최소 3초)
            try:
                for i in range(5):
                    msg_text = await asyncio.wait_for(ws.recv(), timeout=3)
                    msg = json.loads(msg_text)
                    messages.append(msg)
                    print(f"     [{i+1}] {datetime.now().strftime('%H:%M:%S.%f')[:-3]} - CPU: {msg['cpu']['total']:.1f}%")
            except asyncio.TimeoutError:
                print(f"     ⏱️  3초 타임아웃 (수신한 메시지: {len(messages)}개)")
        
        return messages
        
    except Exception as e:
        print(f"  ❌ 예외 발생: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================
# 테스트 4: 메시지 형식 검증
# ============================================================
def test_message_format(messages):
    print("\n[4] 메시지 형식 검증")
    if not messages:
        print("  ❌ 수신한 메시지 없음")
        return False
    
    all_valid = True
    first_msg = messages[0]
    
    # 필수 필드 확인
    required_fields = {"type", "cpu", "memory", "top_processes", "timestamp"}
    actual_fields = set(first_msg.keys())
    
    if required_fields == actual_fields:
        print(f"  ✅ 최상위 필드 일치: {required_fields}")
    else:
        all_valid = False
        missing = required_fields - actual_fields
        extra = actual_fields - required_fields
        if missing:
            print(f"  ❌ 누락된 필드: {missing}")
        if extra:
            print(f"  ❌ 추가 필드: {extra}")
    
    # CPU 필드 확인
    cpu_fields = {"total", "per_core", "core_count", "load_avg"}
    actual_cpu = set(first_msg["cpu"].keys())
    if cpu_fields == actual_cpu:
        print(f"  ✅ CPU 필드 일치: {cpu_fields}")
    else:
        all_valid = False
        print(f"  ❌ CPU 필드 불일치: {actual_cpu}")
    
    # Memory 필드 확인
    mem_fields = {"total_gb", "used_gb", "free_gb", "buffers_gb", "cached_gb", "usage_pct"}
    actual_mem = set(first_msg["memory"].keys())
    if mem_fields == actual_mem:
        print(f"  ✅ Memory 필드 일치: {mem_fields}")
    else:
        all_valid = False
        print(f"  ❌ Memory 필드 불일치: {actual_mem}")
    
    # ProcessSnapshot 필드 확인
    if first_msg["top_processes"]:
        proc_fields = {"pid", "name", "cpu_pct", "mem_pct"}
        actual_proc = set(first_msg["top_processes"][0].keys())
        if proc_fields == actual_proc:
            print(f"  ✅ Process 필드 일치: {proc_fields}")
        else:
            all_valid = False
            print(f"  ❌ Process 필드 불일치: {actual_proc}")
    
    # Type 필드 확인
    if first_msg["type"] == "monitor.snapshot":
        print(f"  ✅ 타입이 정확함: 'monitor.snapshot'")
    else:
        all_valid = False
        print(f"  ❌ 타입이 잘못됨: {first_msg['type']}")
    
    # 타임스탐프 형식 확인
    try:
        ts = first_msg["timestamp"]
        datetime.fromisoformat(ts.replace('Z', '+00:00'))
        print(f"  ✅ 타임스탐프 형식 정상: {ts}")
    except:
        all_valid = False
        print(f"  ❌ 타임스탐프 형식 오류: {first_msg['timestamp']}")
    
    return all_valid

# ============================================================
# 테스트 5: 1초 간격 확인
# ============================================================
def test_interval(messages):
    print("\n[5] 1초 간격 확인")
    if len(messages) < 2:
        print("  ⚠️  메시지 2개 이상 필요 (현재: {})".format(len(messages)))
        return False
    
    # 타임스탐프 추출
    try:
        timestamps = []
        for msg in messages:
            ts_str = msg["timestamp"]
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            timestamps.append(ts)
        
        # 간격 확인
        intervals = []
        for i in range(1, len(timestamps)):
            delta = (timestamps[i] - timestamps[i-1]).total_seconds()
            intervals.append(delta)
            print(f"  [{i}→{i+1}] {delta:.2f}초")
        
        # 평균적으로 약 1초인지 확인
        avg_interval = sum(intervals) / len(intervals)
        if 0.9 <= avg_interval <= 1.5:
            print(f"  ✅ 평균 간격: {avg_interval:.2f}초 (정상)")
            return True
        else:
            print(f"  ⚠️  평균 간격: {avg_interval:.2f}초 (1초 근처 권장)")
            return False
            
    except Exception as e:
        print(f"  ❌ 타임스탐프 파싱 오류: {e}")
        return False

# ============================================================
# 메인 테스트 루틴
# ============================================================
async def main():
    # 서버 연결 가능 여부 확인
    try:
        result = await asyncio.wait_for(test_no_token(), timeout=5)
        if result is None:
            print("\n" + "=" * 70)
            print("❌ 서버에 연결할 수 없습니다!")
            print("   다음 명령으로 서버를 실행해주세요:")
            print("   cd /path/to/backend && source .venv/bin/activate")
            print("   fastapi dev main.py")
            print("=" * 70)
            return False
    except asyncio.TimeoutError:
        print("\n" + "=" * 70)
        print("❌ 서버 응답 타임아웃")
        print("=" * 70)
        return False
    
    # 테스트 실행
    test2_result = await test_invalid_token()
    test3_result = await test_valid_token()
    
    if test3_result:
        test4_result = test_message_format(test3_result)
        test5_result = test_interval(test3_result)
    else:
        test4_result = False
        test5_result = False
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("테스트 결과 요약")
    print("=" * 70)
    print(f"  [1] 토큰 없이 연결 차단: {'✅' if result else '❌'}")
    print(f"  [2] 잘못된 토큰 차단: {'✅' if test2_result else '❌'}")
    print(f"  [3] 유효한 토큰 연결: {'✅' if test3_result else '❌'}")
    print(f"  [4] 메시지 형식: {'✅' if test4_result else '❌'}")
    print(f"  [5] 1초 간격: {'✅' if test5_result else '⚠️'}")
    
    if result and test2_result and test3_result and test4_result:
        print("\n✅ 모든 핵심 테스트 통과!")
        return True
    else:
        print("\n❌ 일부 테스트 실패")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  테스트 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 테스트 중 예외: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
