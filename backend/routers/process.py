"""
프로세스 모니터링 엔드포인트
"""
from fastapi import APIRouter
import psutil
from typing import List

from schemas.process import ProcessInfo

router = APIRouter(prefix="/monitor", tags=["프로세스"])

# ============================================================
# 프로세스 엔드포인트
# ============================================================

@router.get("/processes", response_model=List[ProcessInfo])
async def get_top_processes():
    """상위 30개 프로세스 조회 (CPU/메모리 기준)"""
    try:
        processes = []

        # 1. 모든 프로세스 수집
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = {
                    "pid": proc.info['pid'],
                    "name": proc.info['name'],
                    "cpu_pct": proc.info['cpu_percent'] or 0.0,
                    "mem_pct": proc.info['memory_percent'] or 0.0
                }
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # 2. 로그: 수집된 프로세스 개수
        print(f"\n📊 프로세스 수집 완료: 총 {len(processes)}개")

        # 3. CPU 기준 정렬
        sorted_processes = sorted(processes, key=lambda x: x['cpu_pct'], reverse=True)

        # 4. 상위 30개 선택
        top_30 = sorted_processes[:30]

        # 5. 로그: 상위 프로세스 출력
        print(f"✅ 상위 30개 프로세스:")
        for i, proc in enumerate(top_30, 1):
            print(f"   {i:2d}. PID: {proc['pid']:6d} | CPU: {proc['cpu_pct']:6.1f}% | MEM: {proc['mem_pct']:6.2f}% | {proc['name']}")

        print(f"\n🔄 API 응답: {len(top_30)}개 프로세스 반환\n")

        return top_30
    except Exception as e:
        print(f"❌ 프로세스 조회 실패: {e}")
        return []
