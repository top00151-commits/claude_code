#!/bin/bash
# ============================================================
# KNK 메신저 — NAS 자동 배포 (cron 1분 주기)  [01 WORKS auto_deploy.sh 기반]
# 2026-06-16 생성 (자동배포 전환 키트)
# ------------------------------------------------------------
# GitHub 최신 코드를 받아, 변경이 있을 때만 앱을 재시작한다.
# 등록(1회): deploy/setup_auto_deploy.sh
# 이후: 매분 자동 실행 → push(미러) 하면 ~1~2분 내 운영 반영.
#
# ⚠️ 전산담당자 확인/선행 필요 (현재 메신저는 sync_to_synology.ps1 수동 배포라 아래 전제가 필요):
#   (P1) /opt/knk_messenger 가 git clone 상태여야 함.
#        아니라면 1회: cd /opt && git clone git@github.com:top00151-commits/knk-messenger.git knk_messenger
#        (기존 데이터/.env/logs 보존 주의 — 백업 후 진행)
#   (P2) supervisord/컨테이너 환경에서 supervisorctl 이 동작해야 함 (PID1=bash 컨테이너 주의).
#   (P3) GitHub 미러(모노레포→knk-messenger)가 켜져 있어야 의미가 있음 (키트 README 참고).
# ============================================================
set +e

# ---------- CONFIG (전산담당자: 실제 값과 일치하는지 확인) ----------
APP_DIR=/opt/knk_messenger          # NAS 설치 경로 (supervisord directory= 와 동일)
SERVICE=knk-messenger               # supervisor program 이름
# -------------------------------------------------------------------

LOG="$APP_DIR/logs/auto_deploy.log"
LOCK=/tmp/knk_messenger_autodeploy.lock
VENV_PIP="$APP_DIR/.venv/bin/pip"
REQ="$APP_DIR/requirements.txt"
REQ_MARK="$APP_DIR/logs/.requirements.installed.sha"

mkdir -p "$APP_DIR/logs" 2>/dev/null

# 동시 실행 방지
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK"
  flock -n 9 || exit 0
fi

cd "$APP_DIR" || exit 0

before=$(git rev-parse HEAD 2>/dev/null)
git pull -q 2>>"$LOG"
after=$(git rev-parse HEAD 2>/dev/null)

code_changed=0
[ -n "$after" ] && [ "$before" != "$after" ] && code_changed=1

# 의존성 자동 설치 (requirements.txt 변경 감지)
deps_installed=0
if [ -f "$REQ" ] && [ -x "$VENV_PIP" ]; then
  cur=$(sha1sum "$REQ" 2>/dev/null | awk '{print $1}')
  prev=$(cat "$REQ_MARK" 2>/dev/null)
  if [ -n "$cur" ] && [ "$cur" != "$prev" ]; then
    echo "$(date '+%F %T') requirements 변경 — pip install" >> "$LOG"
    "$VENV_PIP" install -q -r "$REQ" >> "$LOG" 2>&1 && { echo "$cur" > "$REQ_MARK"; deps_installed=1; }
  fi
fi

if [ "$code_changed" = "1" ] || [ "$deps_installed" = "1" ]; then
  echo "$(date '+%F %T') 재시작 (code=$code_changed deps=$deps_installed) $before -> $after" >> "$LOG"
  supervisorctl restart "$SERVICE" >> "$LOG" 2>&1
  echo "$(date '+%F %T') 재시작 완료 (now $after)" >> "$LOG"
fi
