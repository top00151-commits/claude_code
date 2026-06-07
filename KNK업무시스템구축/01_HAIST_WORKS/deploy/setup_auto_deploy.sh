#!/bin/bash
# ============================================================
# HAIST WORKS — 자동 배포 1회 설정
# v5H226z123 (2026-05-31)
# auto_deploy.sh 를 cron(매분)에 등록한다. (중복 방지 · 재실행 안전)
# 실행: ssh 후  bash /opt/knk_haist/deploy/setup_auto_deploy.sh
# ============================================================
set +e
WORKS_DIR=/opt/knk_haist
SCRIPT="$WORKS_DIR/deploy/auto_deploy.sh"

if [ ! -f "$SCRIPT" ]; then
  echo "[ERROR] $SCRIPT 없음 — 먼저 git pull 필요"
  exit 1
fi

chmod +x "$SCRIPT"
LINE="* * * * * /bin/bash $SCRIPT"

# 기존 auto_deploy 항목 제거 후 재등록 (중복 방지)
( crontab -l 2>/dev/null | grep -v 'auto_deploy.sh' ; echo "$LINE" ) | crontab -

echo "=== CRON INSTALLED ==="
crontab -l | grep 'auto_deploy.sh'

# cron 데몬 동작 점검 (보통 supervisord가 관리). 안 떠 있으면 안내.
if command -v pgrep >/dev/null 2>&1; then
  if ! pgrep -x cron >/dev/null 2>&1 && ! pgrep -x crond >/dev/null 2>&1; then
    echo "[WARN] cron 데몬이 안 보입니다. 'supervisorctl status' 로 cron 상태를 확인하세요."
  else
    echo "[OK] cron 데몬 동작 중"
  fi
fi

# 방금 git pull 로 받은 최신 코드를 즉시 활성화 (1회 재시작)
echo "--- 최신 코드 활성화: 앱 1회 재시작 ---"
supervisorctl restart knk-works
echo "[현재 버전]"
git -C "$WORKS_DIR" log --oneline -1
echo "=== SETUP DONE ==="
