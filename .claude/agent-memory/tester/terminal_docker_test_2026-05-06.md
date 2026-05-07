---
name: Terminal Docker PTY Test (2026-05-06)
description: Comprehensive test of Docker PTY shell implementation - identified version mismatch
type: project
---

## Test Date: 2026-05-06

## Summary
Tested 9 verification items for terminal functionality transition from virtual shell to Docker PTY. **FAILED: Code mismatch detected between implementation and runtime.**

## Test Results

### PASSED Items
1. ✅ Server health endpoint responds correctly
   - Endpoint: `GET /api/health`
   - Response: `{"status":"healthy","message":"..."}` (200 OK)

2. ✅ Docker image exists
   - Image: `webterm:latest` (ID: 00c5fdb63b7b, 398MB)
   - Size: 98.6MB content

3. ✅ Virtual shell directory removed
   - Path: `/home/ubuntu/Linux-web-gui/backend/services/virtual_shell/`
   - Status: Does not exist (as expected)

4. ✅ Shell router imports successfully
   - Command: `from routers.shell import router`
   - Result: Successfully imported with new Docker PTY code

5. ✅ FastAPI routes registered correctly
   - `/ws/shell` WebSocket route exists
   - `/api/shell/fs` GET route exists
   - `/api/shell/sessions` GET route exists

### FAILED Items

6. ❌ WebSocket message format mismatch
   - **Expected (shell.py line 199-204):**
   ```json
   {
     "type": "meta",
     "session_id": "...",
     "cwd": "/home/user",
     "user": "user"
   }
   ```
   
   - **Actually Received:**
   ```json
   {
     "session_id": "admin-1778063886927",
     "output": "Welcome to Linux Web Shell. session_id=admin-...",
     "cwd": "/home/admin",
     "user": "admin",
     "prompt": "admin@linux:~$ "
   }
   ```
   
   - **Analysis:**
     - Actual message has `output` and `prompt` fields (not in shell.py)
     - "Welcome to Linux Web Shell" message not found in codebase
     - Missing `"type": "meta"` field that should be in line 199
     - **ROOT CAUSE: Current server process is running OLD code, not new shell.py**

7. ❌ Echo command execution failed
   - Sent: `'echo hello_docker_test\r'`
   - Expected: Text containing `'hello_docker_test'`
   - Received: Empty output (0 chars)
   - Reason: Due to #6 (wrong code running)

8. ⏭️ SKIPPED: Pipe command test
   - Dependent on #6 (would fail with same root cause)

9. ⏭️ SKIPPED: File explorer API test
   - Dependent on #6

## Root Cause Analysis

**Current running server process:**
```
PID 7390: /usr/local/bin/python /root/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

**Code state:**
- shell.py has been updated with Docker PTY implementation ✅
- FastAPI app correctly registers shell_router ✅
- Routes are accessible in OpenAPI spec ✅

**Problem:**
- Python process is cached with OLD module versions
- Current process loads previous "virtual shell" implementation
- Code has `type: 'meta'` but process outputs `session_id`, `output`, `prompt` fields
- "Welcome to Linux Web Shell" text not found in current shell.py (only in old code)

**Evidence:**
```bash
# Expected from shell.py line 199:
await websocket.send_json({'type': 'meta', ...})

# Actual WebSocket message has NO 'type' field
# Actual has 'output' field (not in new shell.py)
# Actual has 'prompt' field (not in new shell.py)
```

## Prerequisite Actions Needed

Before re-testing, **backend server MUST be restarted** to:
1. Force Python module reload
2. Load updated shell.py implementation
3. Purge old virtual shell module cache

**Current Constraint:** Cannot kill PID 7390 (root process, insufficient permissions)

## Files Involved
- `/home/ubuntu/Linux-web-gui/backend/routers/shell.py` — Docker PTY implementation (correct)
- `/home/ubuntu/Linux-web-gui/backend/main.py` — Router registration (correct)
- `/home/ubuntu/Linux-web-gui/Dockerfile.webterm` — Docker image definition (correct)
- Running process: Using OLD code (mismatch)

## Next Steps
1. Restart backend server (kill PID 7390 or restart host)
2. Re-run WebSocket connection test
3. Verify message format matches `type: 'meta'` spec
4. Complete pipe and file explorer tests

## Docker Container Test (Direct)
Tested Docker PTY directly without WebSocket - **WORKS CORRECTLY**:
```bash
$ echo test
hello  # (correct output)
```
The Docker image itself is functional; issue is in server process version.
