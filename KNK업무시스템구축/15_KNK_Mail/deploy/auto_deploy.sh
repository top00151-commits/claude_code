#!/bin/bash
# ============================================================
# KNK 메일 — NAS 자동 배포 (cron 1분 주기)  [01 WORKS auto_deploy.sh 기반]
# 2026-06-16 생성 (자동배포 전환 키트)
# ------------------------------------------------------------
# GitHub 최신 코드를 받아, 변경이 있을 때만 앱을 재시작한다.
# DEPLOY_RUNBOOK.md 가 권장한 "WORKS 와 동일한 1분 cron git pull" 방식 그대로.
# 등록(1회): deploy/setup_auto_deploy.sh
#
# ⚠️ 전산담당자 확인/선행 필요 (현재 메일은 sync_to_nas.ps1 tar 전송이라 아래 전제 필요):
#   (P1) 메일 전용 GitHub 저장소가 있어야 함 (예: knk-mail). 없으면 1회 생성 후
#        모노레포 15_KNK_Mail 내용을 올려둔다(키트 README의 미러 참고).
#   (P2) APP_DIR 가 그 저장소의 git clone 상태여야 함.
#        1회: cd /opt && git clone git@github.com:top00151-commits/<메일repo>.git knk_mail
#        (또는 runbook 경로 /volume1/web/knk-eum-mail — 둘 중 실제 운영 경로로 통일)
#   (P3) GitHub 미러(모노레포→메일repo)가 켜져 있어야 함 (키트 README 참고).
# ============================================================
set +e

# ---------- CONFIG (전산담당자: 실제 값과 일치하는지 확인) ----------
APP_DIR=/opt/knk_mail               # NAS 설치 경로 (sync_to_nas.ps1 기준; runbook은 /volume1/web/knk-eum-mail)
SERVICE=knk-mail                    # supervisor program 이름 (nginx conf=knk-mail; runbook 변형=knk-eum-mail)
# -------------------------------------------------------------------

LOG="$APP_DIR/logs/auto_deploy.log"
LOCK=/tmp/knk_mail_autodeploy.lock
VENV_PIP="$APP_DIR/.venv/bin/pip"
REQ="$APP_DIR/requirements.txt"
REQ_MARK="$APP_DIR/logs/.requirements.installed.sha"

mkdir -p "$APP_DIR/logs" 2>/dev/null

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
