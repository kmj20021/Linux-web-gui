import time
import ctypes
import ctypes.util

libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
libc.prctl(15, b'demo-scheduler', 0, 0, 0)

while True:
    time.sleep(2)
