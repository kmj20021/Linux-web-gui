---
name: Docker PTY Revalidation - 2026-05-06
description: Revalidation test for Docker PTY shell WebSocket after server restart
type: project
---

## Test Request Status: FAILED

**Date**: 2026-05-06  
**Task ID**: terminal_docker_test  
**Revalidation After**: Server code update

## Test Execution Results

### Test 1: WebSocket Initial Meta Message + Commands

**Status**: FAILED

#### Issue Found
The initial WebSocket message format does NOT match the code specification.

**Expected (per /backend/routers/shell.py line 199-204)**:
```json
{
  "type": "meta",
  "session_id": "admin-xxx",
  "cwd": "/home/user",
  "user": "user"
}
```

**Actual (received)**:
```json
{
  "session_id": "admin-1778064368151",
  "output": "Welcome to Linux Web Shell. session_id=admin-1778064368151\nType 'help' for available commands.\n",
  "cwd": "/home/admin",
  "user": "admin",
  "prompt": "admin@linux:~$ "
}
```

**Differences**:
1. **Missing**: `type` field (expected "meta")
2. **Unexpected**: `output` field (unexpected per code)
3. **Wrong cwd**: `/home/admin` instead of `/home/user`
4. **Wrong user**: `admin` instead of `user`
5. **Extra field**: `prompt`

#### Likely Root Cause
The server running at `http://localhost:8000` is not executing the current code in `/home/ubuntu/Linux-web-gui/backend/routers/shell.py`. 

Possibilities:
- Server is running old/cached bytecode
- Server was not restarted after code update
- Code file is not deployed to running server path

### Test 2: Docker Container Status

**Status**: PASS
- Container `test-webterm` is running
- Created 2 minutes ago
- Status: Up 2 minutes

### Test 3: Frontend Build Artifacts

**Status**: PASS
- Build artifact exists: `/home/ubuntu/Linux-web-gui/frontend/dist/assets/index-sYpeC6Jh.js`

## Recommendations

1. **For @backend**: Verify server is running the current shell.py code
   - Check if server process loads updated module
   - Restart server with `kill PID` + manual restart or systemd
   - Verify `type: 'meta'` message is being sent on connection

2. **For @pm**: Cannot complete validation until backend code is confirmed running

## Files Examined
- `/home/ubuntu/Linux-web-gui/backend/routers/shell.py` (lines 199-204)

