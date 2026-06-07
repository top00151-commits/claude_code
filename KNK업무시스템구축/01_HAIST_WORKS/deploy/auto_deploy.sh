#!/bin/bash
# ============================================================
# HAIST WORKS — NAS 자동 배포 (cron 1분 주기)
# v5H226z145 (2026-06-02)
# ------------------------------------------------------------
# GitHub 최신 코드를 받아, 변경이 있을 때만 앱을 재시작한다.
# + requirements.txt 가 바뀌면 컨테이너 venv 에 자동 pip 설치 (SSH 불필요).
#   → 라이브러리 추가(openpyxl 등)가 푸시만으로 자동 반영.
#
# 등록(1회): deploy/setup_auto_deploy.sh  또는  WORKS_자동배포_설정.bat
# 이후: 매분 자동 실행 → push 하면 ~1~2분 내 운영 반영.
# 로그: /opt/knk_haist/data/auto_deploy.log
# ============================================================
set +e
WORKS_DIR=/opt/knk_haist
LOG="$WORKS_DIR/data/auto_deploy.log"
LOCK=/tmp/knk_works_autodeploy.lock
VENV_PIP="$WORKS_DIR/.venv/bin/pip"
REQ="$WORKS_DIR/requirements.txt"
REQ_MARK="$WORKS_DIR/data/.requirements.installed.sha"

# 동시 실행 방지 (pull/pip 이 1분 넘게 걸려도 겹치지 않게)
if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK"
  flock -n 9 || exit 0
fi

cd "$WORKS_DIR" || exit 0

before=$(git rev-parse HEAD 2>/dev/null)
git pull -q 2>>"$LOG"
after=$(git rev-parse HEAD 2>/dev/null)

code_changed=0
[ -n "$after" ] && [ "$before" != "$after" ] && code_changed=1

# ── 의존성 자동 설치 (requirements.txt 변경 감지 — HEAD 변경과 독립) ──
#   HEAD 변경과 분리한 이유: 개선된 이 스크립트는 pull 다음 cron 틱부터 동작하는데,
#   그 틱엔 보통 HEAD 가 안 바뀐다. 그래도 requirements 해시로 누락을 자가복구.
deps_installed=0
if [ -f "$REQ" ] && [ -x "$VENV_PIP" ]; then
  cur=$(sha1sum "$REQ" 2>/dev/null | awk '{print $1}')
  prev=$(cat "$REQ_MARK" 2>/dev/null)
  if [ -n "$cur" ] && [ "$cur" != "$prev" ]; then
    echo "$(date '+%F %T') requirements 변경 감지 — pip install 시작" >> "$LOG"
    "$VENV_PIP" install -q -r "$REQ" >> "$LOG" 2>&1
    if [ $? -eq 0 ]; then
      echo "$cur" > "$REQ_MARK"
      deps_installed=1
      echo "$(date '+%F %T') pip install 완료" >> "$LOG"
    else
      echo "$(date '+%F %T') pip install 실패 — 다음 틱 재시도" >> "$LOG"
    fi
  fi
fi

# 코드가 바뀌었거나 의존성이 새로 깔렸으면 재시작
if [ "$code_changed" = "1" ] || [ "$deps_installed" = "1" ]; then
  echo "$(date '+%F %T') 재시작 (code=$code_changed deps=$deps_installed) $before -> $after" >> "$LOG"
  supervisorctl restart knk-works >> "$LOG" 2>&1
  echo "$(date '+%F %T') 재시작 완료 (now $after)" >> "$LOG"
fi
