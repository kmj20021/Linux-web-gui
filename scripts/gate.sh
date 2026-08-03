#!/usr/bin/env bash
#
# scripts/gate.sh — docs/re-plan.md §3.2 표준 완료 게이트
#
# Phase 완료 게이트를 한 번에 실행하고 PASS/FAIL 을 요약한다.
# 목적은 게이트를 "약하게" 만드는 게 아니라, 매번 재발견하던 것들을 고정하는 것이다.
#
#   - Compose 필수 환경변수(SECRET_KEY / DATABASE_URL / DOMAIN_NAME)를 안전한 합성값으로 채운다.
#     이미 셸에 값이 있으면 그 값을 존중한다. 값은 출력하지 않는다.
#   - 운영·개발 두 Compose 프로필을 모두 검증한다.
#   - 공백 검사는 줄바꿈 규칙과 무관하게 수행한다. 이 저장소에는 index 가 CRLF 인 파일이
#     섞여 있어 `git diff --check` 가 추가된 모든 줄의 CR 을 후행 공백으로 오검출한다.
#     여기서는 CR 을 벗겨낸 뒤 실제 후행 공백과 space-before-tab 만 본다.
#   - `git diff --check` 가 보지 못하는 **미추적 파일**까지 검사한다(기존 게이트보다 넓다).
#   - npm ci 는 package-lock.json 해시가 바뀐 경우에만 한 번 실행한다.
#
# 사용법:
#   bash scripts/gate.sh          # Phase 완료 게이트 (전체)
#   bash scripts/gate.sh --fast   # 작업 중 빠른 확인 (npm ci·build 생략, 게이트 아님)
#
# 종료 코드: 0 = 전부 통과, 1 = 하나 이상 실패
#
# 보안 Phase(3: 인증·배포, 4: 셸 격리)는 이 스크립트에 더해 docs/re-plan.md 에 명시된
# 실제 구동 검증을 별도로 1회 수행해야 한다. 이 스크립트는 그것을 대신하지 않는다.

set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
ROOT="$(pwd)"

FAST=0
[ "${1:-}" = "--fast" ] && FAST=1

# Compose 보간용 합성값. 실제 비밀이 아니며 어디에도 출력하지 않는다.
export SECRET_KEY="${SECRET_KEY:-synthetic-gate-value-not-a-real-secret-0000000}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./synthetic-gate.db}"
export DOMAIN_NAME="${DOMAIN_NAME:-gate.invalid}"

PASSED=()
FAILED=()
SKIPPED=()
START=$SECONDS

c_pass=$'\033[32m'; c_fail=$'\033[31m'; c_skip=$'\033[33m'; c_off=$'\033[0m'
[ -t 1 ] || { c_pass=""; c_fail=""; c_skip=""; c_off=""; }

# run <라벨> <명령 문자열>
run() {
  local label="$1" cmd="$2" out rc
  printf '  %-34s ' "$label"
  out="$(bash -c "$cmd" 2>&1)"; rc=$?
  if [ $rc -eq 0 ]; then
    printf '%sPASS%s\n' "$c_pass" "$c_off"
    PASSED+=("$label")
  else
    printf '%sFAIL%s (exit %d)\n' "$c_fail" "$c_off" "$rc"
    FAILED+=("$label")
    printf '%s\n' "$out" | tail -n 25 | sed 's/^/      | /'
  fi
}

skip() {
  printf '  %-34s %sSKIP%s  %s\n' "$1" "$c_skip" "$c_off" "$2"
  SKIPPED+=("$1")
}

# ---------------------------------------------------------------- 공백 검사
#
# git 의 "LF will be replaced by CRLF" 경고는 진단이 아니라 잡음이므로 버린다.
# 결과에 섞이면 실제 발견을 가린다.
#
# 이미 알고 있는 기존 위반은 scripts/gate-whitespace-ignore.txt 에 한 줄씩 경로를
# 적어 제외할 수 있다. 새 파일은 계속 검사되므로 기준을 낮추는 게 아니라,
# 작업 범위 밖 파일을 사용자 결정 전까지 구분해 두는 장치다.
IGNORE_FILE="scripts/gate-whitespace-ignore.txt"

# 추가된 줄에서 CR 을 제거한 뒤 실제 후행 공백과 space-before-tab 을 찾는다.
# 이 저장소에는 index 가 CRLF 인 파일이 섞여 있어 `git diff --check` 는 여기서
# 추가된 모든 줄을 오검출한다. CR 제거가 그 오검출만 없애고 실제 위반은 남긴다.
check_tracked_whitespace() {
  git diff --no-color -U0 -- . 2>/dev/null | awk '
    /^\+\+\+ b\// { file = substr($0, 7); next }
    /^\+\+\+ /    { file = "?"; next }
    /^@@/ {
      if (match($0, /\+[0-9]+/)) ln = substr($0, RSTART + 1, RLENGTH - 1) + 0
      next
    }
    /^\+/ {
      line = substr($0, 2)
      sub(/\r$/, "", line)
      if (line ~ /[ \t]+$/)  printf "%s:%d: trailing whitespace\n", file, ln
      else if (line ~ / \t/) printf "%s:%d: space before tab\n", file, ln
      ln++
    }
  '
}

# `git diff --check` 는 미추적 파일을 전혀 보지 않는다. 새 Phase 산출물이 여기 걸린다.
check_untracked_whitespace() {
  local ignore_paths=()
  if [ -s "$IGNORE_FILE" ]; then
    while IFS= read -r p; do
      case "$p" in ''|\#*) continue ;; esac
      ignore_paths+=("$p")
    done < "$IGNORE_FILE"
  fi

  git ls-files --others --exclude-standard 2>/dev/null \
    | grep -Ev '(^|/)(node_modules|dist|build|\.venv|venv|__pycache__)/' \
    | grep -Ev '\.(db|sqlite3?|png|jpg|jpeg|gif|ico|woff2?|ttf|pdf|zip|gz)$' \
    | while IFS= read -r f; do
        [ -f "$f" ] || continue
        for ig in ${ignore_paths+"${ignore_paths[@]}"}; do
          [ "$f" = "$ig" ] && continue 2
        done
        awk -v f="$f" '
          { line = $0; sub(/\r$/, "", line)
            if (line ~ /[ \t]+$/)  printf "%s:%d: trailing whitespace\n", f, NR
            else if (line ~ / \t/) printf "%s:%d: space before tab\n", f, NR }
        ' "$f"
      done
}

# 추적 파일(이번 변경분)과 미추적 파일(새 산출물·기존 파일)을 나눠 보고한다.
# 어느 쪽이 실패했는지가 곧 원인 구분이다.
tracked_whitespace_gate() {
  local found; found="$(check_tracked_whitespace | head -n 30)"
  [ -z "$found" ] && return 0
  printf '%s\n' "$found"; return 1
}

untracked_whitespace_gate() {
  local found; found="$(check_untracked_whitespace | head -n 30)"
  [ -z "$found" ] && return 0
  printf '%s\n' "$found"
  echo "  (작업 범위 밖 기존 파일이면 $IGNORE_FILE 에 경로를 추가하고 진행 기록에 남길 것)"
  return 1
}

export IGNORE_FILE
export -f check_tracked_whitespace check_untracked_whitespace
export -f tracked_whitespace_gate untracked_whitespace_gate

# ---------------------------------------------------------------- npm ci
#
# lockfile 해시당 한 번만 설치한다. 마커는 node_modules 안에 두어
# 새로 설치하면 자연히 사라지고 git 에도 잡히지 않는다.
npm_install_if_needed() {
  local lock="frontend/package-lock.json"
  local marker="frontend/node_modules/.gate-lock-hash"
  local now prev

  [ -f "$lock" ] || { echo "package-lock.json 없음"; return 1; }
  now="$(sha256sum "$lock" | cut -d' ' -f1)"
  prev="$(cat "$marker" 2>/dev/null || true)"

  if [ -d frontend/node_modules ] && [ "$now" = "$prev" ]; then
    echo "lockfile 무변경 — 기존 설치 재사용"
    return 0
  fi

  npm --prefix frontend ci --no-audit --fund=false || return 1
  printf '%s' "$now" > "$marker"
}
export -f npm_install_if_needed

# ---------------------------------------------------------------- 실행
echo
if [ $FAST -eq 1 ]; then
  echo "게이트 (FAST) — npm ci·build 생략. Phase 완료 게이트가 아닙니다."
else
  echo "Phase 완료 게이트 — docs/re-plan.md §3.2"
fi
echo "저장소: $ROOT"
echo

run "backend pytest"            "python -m pytest backend/tests -q"

if [ $FAST -eq 1 ]; then
  skip "frontend npm ci" "--fast"
else
  run "frontend npm ci"         "npm_install_if_needed"
fi

run "frontend lint"             "npm --prefix frontend run lint"
run "frontend test"             "npm --prefix frontend test -- --run"

if [ $FAST -eq 1 ]; then
  skip "frontend build" "--fast"
else
  run "frontend build"          "npm --prefix frontend run build"
fi

run "compose config (production)" "docker compose config --quiet"
if [ -f docker-compose.dev.yml ]; then
  run "compose config (development)" \
      "docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet"
fi

run "security scan"             "python scripts/security_scan.py"
run "whitespace (tracked diff)"    "tracked_whitespace_gate"
run "whitespace (untracked)"       "untracked_whitespace_gate"

# ---------------------------------------------------------------- 요약
ELAPSED=$((SECONDS - START))
echo
echo "----------------------------------------------------------"
printf 'PASS %d   FAIL %d   SKIP %d   (%ds)\n' \
  "${#PASSED[@]}" "${#FAILED[@]}" "${#SKIPPED[@]}" "$ELAPSED"

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo
  echo "실패:"
  printf '  - %s\n' "${FAILED[@]}"
  echo
  echo "게이트 실패는 원인 작업을 FAIL 로 되돌려 수정한다 (CLAUDE.md)."
  exit 1
fi

if [ $FAST -eq 1 ]; then
  echo
  echo "FAST 모드입니다. Phase 완료 게이트로 기록하지 마십시오."
  exit 0
fi

echo
echo "표준 게이트 통과. Phase 3(인증·배포)·4(셸 격리)는 실제 구동 검증 1회가 추가로 필요합니다."
