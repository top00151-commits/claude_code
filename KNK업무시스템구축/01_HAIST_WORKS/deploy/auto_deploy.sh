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
# z1191z53 (대표 2026-11-18 규칙 「배포된걸 적용하기전에는 무조건 직전 상태를 저장하고 업데이트」):
#   재시작 직전 DB 사본(앱 공용 backup_db_file = sqlite backup API · WAL 안전) → 떠지면 재시작 · 실패하면 재시작 보류(다음 틱 다시).
#   보류 표시 = PENDING 파일(새 코드는 이미 받았으므로 다음 틱엔 HEAD 가 안 바뀜 — 표시가 없으면 영영 재시작 안 됨).
VENV_PY="$WORKS_DIR/.venv/bin/python"
PENDING="$WORKS_DIR/data/.restart_pending"

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

# 코드가 바뀌었거나 의존성이 새로 깔렸으면 재시작 — 그 전에 DB 사본(z1191z53)
if [ "$code_changed" = "1" ] || [ "$deps_installed" = "1" ]; then
  [ -f "$PENDING" ] || echo "$before" > "$PENDING"   # 보류 중이면 처음 바탕을 그대로 둔다
  echo "$(date '+%F %T') 새 코드 받음 (code=$code_changed deps=$deps_installed) $before -> $after" >> "$LOG"
fi
if [ -f "$PENDING" ]; then
  prev=$(cat "$PENDING" 2>/dev/null)
  if PYTHONIOENCODING=utf-8 "$VENV_PY" - "$prev" "$WORKS_DIR" >> "$LOG" 2>&1 <<'PY'
import os, sqlite3, sys, time
sys.path.insert(0, sys.argv[2] if len(sys.argv) > 2 else "/opt/knk_haist")
from app import database as D
bdir = os.path.join(os.path.dirname(D.DB_PATH), "backups")
os.makedirs(bdir, exist_ok=True)
tag = (sys.argv[1] if len(sys.argv) > 1 else "")[:7] or "x"
dst = os.path.join(bdir, "knk.db.bak_predeploy_%s_%s" % (tag, time.strftime("%Y%m%d_%H%M%S")))
t0 = time.time()
D.backup_db_file(dst)
c = sqlite3.connect("file:%s?mode=ro" % dst, uri=True)
n = c.execute("SELECT COUNT(*) FROM sqlite_master").fetchone()[0]
c.close()
if n < 10:
    raise SystemExit("사본이 비정상(표 %d개)" % n)
D.prune_db_backups(bdir, "knk.db.bak_predeploy_", D.BACKUP_KEEP_PER_KIND)
print("%s 배포 전 DB 사본 %s (%.0fMB · %.1f초 · 표 %d개)" % (time.strftime("%F %T"), os.path.basename(dst), os.path.getsize(dst) / 1048576.0, time.time() - t0, n))
PY
  then
    echo "$(date '+%F %T') 재시작 $prev -> $(git rev-parse HEAD 2>/dev/null)" >> "$LOG"
    supervisorctl restart knk-works >> "$LOG" 2>&1
    rm -f "$PENDING"
    echo "$(date '+%F %T') 재시작 완료 (now $(git rev-parse HEAD 2>/dev/null))" >> "$LOG"
  else
    echo "$(date '+%F %T') ⚠ DB 사본 실패 — 재시작 보류(다음 틱 다시 · 직전 상태 저장 규칙)" >> "$LOG"
  fi
fi
