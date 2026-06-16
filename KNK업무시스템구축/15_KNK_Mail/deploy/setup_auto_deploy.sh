#!/bin/bash
# ============================================================
# KNK 메일 — 자동 배포 1회 설정 (auto_deploy.sh 를 cron 매분 등록)
# 실행(NAS, git clone 된 /opt/knk_mail 안에서): bash deploy/setup_auto_deploy.sh
# 선행 전제는 deploy/auto_deploy.sh 상단 주석(P1~P3) 참고.
# ============================================================
set +e
APP_DIR=/opt/knk_mail
SERVICE=knk-mail
SCRIPT="$APP_DIR/deploy/auto_deploy.sh"

if [ ! -f "$SCRIPT" ]; then echo "[ERROR] $SCRIPT 없음 — 먼저 git clone/pull 필요"; exit 1; fi
chmod +x "$SCRIPT"

LINE="* * * * * /bin/bash $SCRIPT"
( crontab -l 2>/dev/null | grep -v 'knk_mail/deploy/auto_deploy.sh' ; echo "$LINE" ) | crontab -
echo "=== CRON INSTALLED ==="; crontab -l | grep 'auto_deploy.sh'

if command -v pgrep >/dev/null 2>&1; then
  pgrep -x cron >/dev/null 2>&1 || pgrep -x crond >/dev/null 2>&1 \
    && echo "[OK] cron 데몬 동작 중" \
    || echo "[WARN] cron 데몬 안 보임 — supervisorctl status 로 cron 확인"
fi

echo "--- 최신 코드 활성화: 1회 재시작 ---"
supervisorctl restart "$SERVICE"
echo "[현재 버전]"; git -C "$APP_DIR" log --oneline -1
echo "=== SETUP DONE ==="
