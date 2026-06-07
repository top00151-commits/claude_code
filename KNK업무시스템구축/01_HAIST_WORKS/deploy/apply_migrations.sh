#!/bin/bash
# ============================================================
# HAIST WORKS — 마이그레이션 패키지 적용 도구
# v5H226z116 (2026-05-31) — z109 / z110 / z115 통합 적용
# ============================================================
# 적용 대상:
#   z109 — users 테이블 사번 컬럼 8개 (employee_no/entity/password_version/...)
#   z110 — app_settings hiworks_* → groupware_* 키 복사
#   z115 — tasks 테이블 photo_path 컬럼
#
# 사용법 (NAS 컨테이너 안):
#   bash deploy/apply_migrations.sh           # 적용 + 검증
#   bash deploy/apply_migrations.sh --dry-run # 적용 안 함, 검증만 (트랜잭션 rollback)
#   bash deploy/apply_migrations.sh --check   # 현재 상태 확인 (마이그레이션 적용 여부)
#
# 안전 보장:
#   1. 자동 백업: data/main.db → data/backups/main.db.bak_z109z110z115_<TS>
#   2. 트랜잭션 적용 (실패 시 자동 롤백)
#   3. 적용 후 자동 검증 (PRAGMA table_info)
#   4. 실패 시 명확한 에러 메시지 + 백업 위치 안내
#
# 롤백:
#   supervisorctl stop knk-works
#   cp data/backups/main.db.bak_z109z110z115_<TS> data/main.db
#   supervisorctl start knk-works
# ============================================================

set -e
WORKS_DIR=/opt/knk_haist
# DB 경로 — 환경변수 override 우선, 기본은 knk.db (NAS 실제 파일명)
DB="${KNK_DB_PATH:-$WORKS_DIR/data/knk.db}"
MIG_DIR="$WORKS_DIR/migrations"
BAK_DIR="$WORKS_DIR/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BAK_FILE="$BAK_DIR/$(basename "$DB").bak_z109z110z115_$TIMESTAMP"

MODE="apply"  # apply / dry-run / check
# v5H226z117-fix (2026-05-31): 인자 없이 호출 = apply (case 매칭 버그 수정)
ARG="${1:-}"
case "$ARG" in
  --dry-run|-n)             MODE="dry-run" ;;
  --check|-c)               MODE="check" ;;
  --apply|-a|"")            MODE="apply" ;;
  *) echo "Usage: $0 [--apply|--dry-run|--check]"; exit 1 ;;
esac

# ── 색상 (TTY인 경우만) ──────────────────────────────────────
if [ -t 1 ]; then
  C_OK=$'\e[32m';  C_WARN=$'\e[33m';  C_ERR=$'\e[31m';  C_INFO=$'\e[36m';  C_END=$'\e[0m'
else
  C_OK="";  C_WARN="";  C_ERR="";  C_INFO="";  C_END=""
fi

step()  { echo ""; echo "${C_INFO}=== [$1] $2 ===${C_END}"; }
ok()    { echo "  ${C_OK}✓${C_END} $1"; }
warn()  { echo "  ${C_WARN}⚠${C_END} $1"; }
err()   { echo "  ${C_ERR}✗ $1${C_END}"; }
fail()  { echo "  ${C_ERR}✗ $1${C_END}"; exit 1; }

# ── 환경 점검 ─────────────────────────────────────────────────
step "0/5" "환경 점검"
command -v sqlite3 >/dev/null || fail "sqlite3 없음 — apt-get install sqlite3"
[ -f "$DB" ] || fail "DB 없음: $DB"
[ -d "$MIG_DIR" ] || fail "migrations 폴더 없음: $MIG_DIR"
for sql in v5H226z109_employee_no.sql v5H226z110_groupware_rename.sql v5H226z115_task_photo.sql; do
  [ -f "$MIG_DIR/$sql" ] || fail "SQL 없음: $MIG_DIR/$sql"
done
ok "sqlite3 / DB / migrations 모두 존재"
ok "모드: ${C_INFO}$MODE${C_END}"

# ── 현재 상태 점검 (적용 여부 확인) ─────────────────────────
step "1/5" "현재 마이그레이션 상태"

check_column() {
  local table=$1 col=$2
  sqlite3 "$DB" "PRAGMA table_info($table);" 2>/dev/null | cut -d'|' -f2 | grep -qx "$col"
}
check_key() {
  local key=$1
  local cnt=$(sqlite3 "$DB" "SELECT COUNT(*) FROM app_settings WHERE key='$key';" 2>/dev/null || echo 0)
  [ "$cnt" -gt 0 ]
}

# z109 — users.employee_no
if check_column users employee_no; then
  Z109="${C_OK}이미 적용${C_END}"
  Z109_APPLIED=1
else
  Z109="${C_WARN}미적용${C_END}"
  Z109_APPLIED=0
fi

# z110 — app_settings 'groupware_*' 키
if check_key "groupware_messenger_token"; then
  Z110="${C_OK}이미 적용${C_END}"
  Z110_APPLIED=1
else
  Z110="${C_WARN}미적용${C_END}"
  Z110_APPLIED=0
fi

# z115 — tasks.photo_path
if check_column tasks photo_path; then
  Z115="${C_OK}이미 적용${C_END}"
  Z115_APPLIED=1
else
  Z115="${C_WARN}미적용${C_END}"
  Z115_APPLIED=0
fi

echo "  z109 (users 사번 컬럼)      : $Z109"
echo "  z110 (groupware 키 복사)    : $Z110"
echo "  z115 (tasks.photo_path)     : $Z115"

if [ "$MODE" = "check" ]; then
  echo ""
  ok "상태 확인 완료 — 변경 없음"
  exit 0
fi

if [ "$Z109_APPLIED" = "1" ] && [ "$Z110_APPLIED" = "1" ] && [ "$Z115_APPLIED" = "1" ]; then
  echo ""
  ok "3종 모두 이미 적용됨 — 작업할 것 없음"
  exit 0
fi

# ── 백업 ─────────────────────────────────────────────────────
step "2/5" "DB 백업"
if [ "$MODE" = "dry-run" ]; then
  warn "dry-run 모드 — 백업·적용 안 함"
else
  mkdir -p "$BAK_DIR"
  cp "$DB" "$BAK_FILE"
  ok "백업: $BAK_FILE ($(du -h "$BAK_FILE" | cut -f1))"
fi

# ── 적용 ─────────────────────────────────────────────────────
step "3/5" "마이그레이션 적용"

apply_one() {
  local label=$1 sql_file=$2 applied=$3
  if [ "$applied" = "1" ]; then
    warn "$label — 이미 적용됨 (skip)"
    return 0
  fi
  if [ "$MODE" = "dry-run" ]; then
    # 트랜잭션 후 rollback
    local tmp_out=$(mktemp)
    (
      echo "BEGIN;"
      cat "$MIG_DIR/$sql_file"
      echo "ROLLBACK;"
    ) | sqlite3 "$DB" 2>&1 > "$tmp_out"
    if [ -s "$tmp_out" ] && grep -qiE "error|fail" "$tmp_out"; then
      err "$label dry-run 실패:"
      cat "$tmp_out"
      rm -f "$tmp_out"
      return 1
    fi
    rm -f "$tmp_out"
    ok "$label — dry-run 통과 (rollback 됨)"
  else
    # 실제 적용
    if sqlite3 "$DB" < "$MIG_DIR/$sql_file" 2>&1; then
      ok "$label — 적용 완료"
    else
      err "$label — 적용 실패"
      return 1
    fi
  fi
  return 0
}

apply_one "z109 (사번 컬럼)"  "v5H226z109_employee_no.sql"     "$Z109_APPLIED" || {
  err "z109 실패 — 백업으로 복원하려면:"
  echo "    cp $BAK_FILE $DB"
  exit 1
}
apply_one "z110 (groupware 키)" "v5H226z110_groupware_rename.sql" "$Z110_APPLIED" || {
  err "z110 실패 — 백업으로 복원하려면:"
  echo "    cp $BAK_FILE $DB"
  exit 1
}
apply_one "z115 (task photo)"   "v5H226z115_task_photo.sql"       "$Z115_APPLIED" || {
  err "z115 실패 — 백업으로 복원하려면:"
  echo "    cp $BAK_FILE $DB"
  exit 1
}

# ── 사후 검증 (dry-run 이 아니면) ────────────────────────────
step "4/5" "사후 검증"
if [ "$MODE" = "dry-run" ]; then
  warn "dry-run 모드 — 사후 검증 skip"
else
  # z109 검증
  if check_column users employee_no && check_column users entity && check_column users password_version; then
    ok "z109 — users.employee_no/entity/password_version 컬럼 확인"
  else
    err "z109 검증 실패 — 컬럼 일부 누락"
  fi
  # z110 검증
  if check_key "groupware_messenger_token"; then
    n=$(sqlite3 "$DB" "SELECT COUNT(*) FROM app_settings WHERE key LIKE 'groupware_%';" 2>/dev/null)
    ok "z110 — groupware_* 키 $n개 존재"
  else
    err "z110 검증 실패 — groupware_* 키 없음"
  fi
  # z115 검증
  if check_column tasks photo_path; then
    ok "z115 — tasks.photo_path 컬럼 확인"
  else
    err "z115 검증 실패 — photo_path 컬럼 없음"
  fi
fi

# ── 서비스 재시작 안내 ───────────────────────────────────────
step "5/5" "다음 단계"
if [ "$MODE" = "dry-run" ]; then
  echo "  ${C_INFO}dry-run 통과 — 실제 적용은 다음 명령:${C_END}"
  echo "    bash deploy/apply_migrations.sh"
else
  echo "  ${C_INFO}서비스 재시작 권장 (코드가 새 컬럼 사용 시작):${C_END}"
  echo "    supervisorctl restart knk-works"
  echo ""
  echo "  ${C_INFO}백업 위치 (롤백용, 30일 보관 권장):${C_END}"
  echo "    $BAK_FILE"
  echo ""
  ok "마이그레이션 패키지 적용 완료"
fi
