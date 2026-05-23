import subprocess, threading, sys, os, time, logging

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEMOS = [
    ('demo-worker',    os.path.join(_BASE_DIR, 'demo_worker.py')),
    ('demo-scheduler', os.path.join(_BASE_DIR, 'demo_scheduler.py')),
    ('demo-logger',    os.path.join(_BASE_DIR, 'demo_logger.py')),
]
_procs: dict = {}
_stop_event = threading.Event()
_thread = None

def _launch(name, path):
    proc = subprocess.Popen([sys.executable, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info(f"데모 프로세스 시작: {name} PID={proc.pid}")
    return proc

def _watchdog():
    while not _stop_event.is_set():
        for name, path in _DEMOS:
            proc = _procs.get(name)
            if proc is None or proc.poll() is not None:
                _procs[name] = _launch(name, path)
        _stop_event.wait(timeout=3)

def start_demo_processes():
    global _thread
    _stop_event.clear()
    _thread = threading.Thread(target=_watchdog, daemon=True, name='demo-watchdog')
    _thread.start()

def stop_demo_processes():
    _stop_event.set()
    for proc in _procs.values():
        try:
            proc.terminate()
        except Exception:
            pass
