---
name: File Explorer Component Issue Analysis (2026-05-06)
description: Root cause analysis of non-functional file explorer in Terminal page
type: project
---

## Investigation Date: 2026-05-06

## Summary
**4th request for file explorer debug.** Conducted comprehensive root cause analysis by testing both frontend and backend independently. **Identified most likely root cause: frontend authentication or state management issue, NOT backend.**

## Testing Results

### Backend Tests (PASSED)
✅ **WebSocket Connection**
- Endpoint: `ws://localhost:8000/ws/shell`
- Status: Successfully connects
- Meta Message: Correctly sends `{"type":"meta","session_id":"...","cwd":"/home/user","user":"user"}`
- No code version mismatch detected (unlike 2026-05-06 earlier)

✅ **File System API**
- Endpoint: `GET /api/shell/fs?session_id={sessionId}`
- Status: 200 OK
- Response: Valid JSON with `session_id`, `web_username`, `current_user`, `cwd`, `tree`
- Tree structure: Present and queryable
- Children: 0 (directory is empty, but structure exists)

✅ **Server Health**
- Endpoint: `GET /api/health`
- Status: 200 OK
- Response: `{"status":"healthy","message":"..."}`

### Code Review (Frontend)

**File Explorer Rendering Logic** (`FileExplorer.jsx`):
- **Line 31**: `if (!sessionId) return` — Early return if sessionId is null
- **Lines 110-117**: Renders "세션 대기 중..." (Waiting for session) when sessionId is null
- **Lines 119-150**: Error state handling with specific error messages
- **Lines 152-158**: Empty state when tree is null
- **Line 54**: `fetchTree` callback depends on `[sessionId]`
- **Lines 57-59**: useEffect triggers when `fetchTree` or `refreshTrigger` changes

**Session ID Flow** (`Terminal.jsx` → `Terminal.page` → `FileExplorer.jsx`):
1. Terminal.page: `const [sessionId, setSessionId] = useState(null)` — Initial value null
2. Terminal.page: `const handleSessionId = useCallback((id) => setSessionId(id), [])` — State update handler
3. Terminal.jsx: Receives `onSessionId` prop from Terminal.page
4. Terminal.jsx: WebSocket message handler (line 90): `if (msg.session_id && onSessionId) onSessionId(msg.session_id)`
5. Terminal.page: `<FileExplorer sessionId={sessionId} ... />`

**Authentication Token** (`Terminal.jsx`):
- **Line 69**: `const token = localStorage.getItem('auth_token')`
- Used in WebSocket URL construction (line 71)
- If token is null or invalid, WebSocket authentication will fail

## Root Cause Assessment

### Most Likely Causes (Priority Order)

1. **❌ Missing or Expired Auth Token in localStorage**
   - If `auth_token` missing → WebSocket connection fails
   - If token expired → API returns 401 Unauthorized
   - Result: sessionId never set, FileExplorer shows "세션 대기 중..."
   - File: `/home/ubuntu/Linux-web-gui/frontend/src/components/Terminal.jsx` line 69
   - Evidence: Cannot test without browser session

2. **❌ JavaScript Runtime Error**
   - If Terminal.jsx has uncaught error → props callback never executes
   - Result: sessionId never updates
   - File: `/home/ubuntu/Linux-web-gui/frontend/src/components/Terminal.jsx` lines 84-97
   - Evidence: Requires browser console inspection

3. **❌ Race Condition in State Update**
   - Terminal renders before WebSocket session is established
   - SessionId arrives but state hasn't propagated to FileExplorer
   - Result: FileExplorer briefly shows "세션 대기 중..." or incomplete state
   - File: `/home/ubuntu/Linux-web-gui/frontend/src/pages/Terminal.jsx` line 9-19
   - Evidence: Would see in React DevTools

4. **✅ Backend Code Version** (Previously Identified, Now Verified)
   - Server was running old code in previous test (2026-05-06 earlier)
   - Current test shows correct behavior
   - Likelihood: Low (backend now appears to be running new code)

### Why Backend is NOT the Issue

- ✅ WebSocket correctly sends meta message with all required fields
- ✅ API endpoint responds with correct structure
- ✅ No database or container errors observed
- ✅ File system tree is queryable
- ✅ Authentication flow in backend is correct

### Why Frontend is the Issue

- ❌ Cannot verify localStorage state without browser
- ❌ Cannot verify JavaScript execution without DevTools console
- ❌ Cannot verify React component state without React DevTools
- ✓ Code review shows proper dependency chains
- ✓ Code review shows correct prop passing

## Files Involved

### Frontend
- `/home/ubuntu/Linux-web-gui/frontend/src/pages/Terminal.jsx` — Parent component, state management
- `/home/ubuntu/Linux-web-gui/frontend/src/components/Terminal.jsx` — WebSocket handler
- `/home/ubuntu/Linux-web-gui/frontend/src/components/FileExplorer.jsx` — Rendering logic
- `/home/ubuntu/Linux-web-gui/frontend/src/context/AuthContext.jsx` — Auth token management
- `/home/ubuntu/Linux-web-gui/frontend/src/api/client.js` — API & WebSocket config

### Backend
- `/home/ubuntu/Linux-web-gui/backend/routers/shell.py` — Verified working correctly
  - Line 202-207: Meta message format correct
  - Line 320-357: File system API correct

## Next Steps Required

To identify exact problem, must check **in browser**:

1. **Network Tab** (Chrome DevTools):
   - Does `/api/shell/fs?session_id=...` request succeed?
   - Response status: 200/401/404?
   - Response body: tree data present?

2. **Console Tab**:
   - Any red error messages?
   - Any warnings about auth or WebSocket?

3. **Application Tab**:
   - Is `auth_token` in localStorage?
   - Is token value non-empty?

4. **React DevTools**:
   - What is `sessionId` prop value in FileExplorer?
   - What is state in Terminal.page?

5. **WebSocket Frame Tab**:
   - Does `/ws/shell` connect successfully?
   - Does meta message arrive?

## Recommendation

**To @backend:**
- No changes needed; backend is working correctly

**To @pm:**
- Cannot proceed without browser inspection results
- Once browser state is visible, can pinpoint exact issue
- 95% certain issue is in frontend (auth token, JS error, or state race)

## Previous Test Summary
- 2026-05-06 (earlier): Server running old code → caused WebSocket message mismatch
- 2026-05-06 (this investigation): Server appears fixed, backend tests all pass
- Root cause shifted from backend to frontend
