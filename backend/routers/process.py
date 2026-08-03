"""
프로세스 모니터링 엔드포인트
"""
import os

from fastapi import APIRouter, Depends, HTTPException, status
import psutil
from typing import List

from core.models import WebUser
from core.security import get_current_admin, get_current_user
from schemas.process import ProcessInfo
from services import demo_procs

# 프로세스 목록은 호스트의 PID·실행 파일명·자원 사용률을 노출하므로
# 다른 모니터링 라우터와 같이 로그인 사용자에게만 제공한다(BASE-02 권한 행렬).
# 종료(kill)는 각 엔드포인트에서 admin 을 추가로 요구한다.
router = APIRouter(
    prefix="/monitor",
    tags=["프로세스"],
    dependencies=[Depends(get_current_user)],
)

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


@router.post("/processes/{pid}/kill")
async def kill_process(
    pid: int,
    _current_admin: WebUser = Depends(get_current_admin),
):
    """
    지정한 PID의 프로세스 종료

    - admin만 실행 가능
    - 이 서버가 생성해 관리 중인 demo-* 자식 프로세스만 종료 가능
    - SIGTERM 으로 먼저 종료 시도, 3초 안에 종료되지 않으면 SIGKILL
    - 존재하지 않는 PID 는 404
    - 권한 부족(AccessDenied) 은 403
    """
    # 1. 보호 대상 PID 확인 (init / 현재 서버 프로세스)
    current_pid = os.getpid()
    if pid == 1 or pid == current_pid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 프로세스는 종료할 수 없습니다",
        )

    # 2. 프로세스 존재 여부 확인
    try:
        proc = psutil.Process(pid)
        proc_name = proc.name()
    except psutil.NoSuchProcess:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PID {pid} 프로세스를 찾을 수 없습니다",
        )
    except psutil.AccessDenied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="프로세스를 종료할 권한이 없습니다",
        )

    # 3. 앱이 직접 생성해 관리하는 demo-* 자식인지 확인
    managed_name = next(
        (
            name
            for name, managed_proc in tuple(demo_procs._procs.items())
            if name.startswith("demo-")
            and managed_proc.pid == pid
            and managed_proc.poll() is None
        ),
        None,
    )
    try:
        is_child = proc.ppid() == current_pid
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        is_child = False

    if managed_name is None or proc_name != managed_name or not is_child:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리 중인 데모 프로세스만 종료할 수 있습니다",
        )

    # 4. SIGTERM -> wait -> SIGKILL
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)
    except psutil.NoSuchProcess:
        # 종료 직전에 이미 사라진 경우도 성공으로 간주
        pass
    except psutil.AccessDenied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="프로세스를 종료할 권한이 없습니다",
        )

    return {
        "success": True,
        "pid": pid,
        "message": f"프로세스 {pid}({proc_name}) 종료됨",
    }
