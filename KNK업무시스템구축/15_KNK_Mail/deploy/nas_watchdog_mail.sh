#!/bin/sh
# ============================================================
# KNK Mail 외부 워치독 — DSM(NAS 호스트)에서 1분마다 실행 (컨테이너 밖)
# ------------------------------------------------------------
# 자동복구 표준 2단계. 컨테이너 안쪽 워치독(mail_watchdog.sh)이 못 잡는 경우 복구:
#   - 컨테이너 통째 멈춤(wedge) → docker restart
#   - NAS 재부팅 후 컨테이너 자체가 안 뜸 → docker start
#   - 내부 워치독까지 죽음 → 컨테이너 안 run.py 재기동
# 본보기: 10_KNK_Messenger/deploy/nas_watchdog_msg_new.sh (지시서 자동복구_표준방안_2026-07-06)
# Mail 특화: 앱=uvicorn(run.py·5053), 컨테이너에 curl 없음 → 생존확인은 앱 .venv python(urllib).
# 설치: /volume1/docker/knk_mail/nas_watchdog_mail.sh (chmod +x) + DSM 작업 스케줄러 root 1분.
# ============================================================
CONTAINER="KNKHAIST.MAIL"     # ★ docker ps 로 실제 이름 확인 후 수정
PORT="5053"
APP="/opt/knk_mail"
PY="${APP}/.venv/bin/python"
RUNPY="${APP}/run.py"
FAIL_THRESHOLD=2
STATE="/tmp/knk_watchdog_mail_fail"
LOG="/var/log/knk_watchdog_mail.log"

if [ -x /usr/local/bin/docker ]; then DOCKER=/usr/local/bin/docker
elif [ -x /usr/bin/docker ]; then DOCKER=/usr/bin/docker
else DOCKER=docker; fi
ts(){ date '+%Y-%m-%d %H:%M:%S'; }
log(){ echo "$(ts) $1" >> "$LOG" 2>/dev/null; }
notify(){ synodsmnotify @administrators "$1" "$2" 2>/dev/null || true; }
running(){ "$DOCKER" inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true; }
# 생존확인: 컨테이너 안 python urllib 로 healthz 200 (curl 없음)
healthy(){ "$DOCKER" exec "$CONTAINER" "$PY" -c "import sys,urllib.request as u; sys.exit(0 if u.urlopen('http://127.0.0.1:${PORT}/healthz',timeout=8).status==200 else 1)" >/dev/null 2>&1; }

# 0) 컨테이너 미기동 → 시작
if ! running; then
    log "컨테이너 미기동 → docker start $CONTAINER"
    "$DOCKER" start "$CONTAINER" >> "$LOG" 2>&1; sleep 20
    notify "KNK Mail 자동복구" "컨테이너가 내려가 있어 다시 시작했습니다. $(ts)"
fi
# 1) 정상이면 종료
if healthy; then [ -f "$STATE" ] && rm -f "$STATE"; exit 0; fi
# 2) 연속 실패 누적
N=0; [ -f "$STATE" ] && N=$(cat "$STATE" 2>/dev/null || echo 0); N=$((N + 1)); echo "$N" > "$STATE"
log "healthz FAIL ($N/$FAIL_THRESHOLD)"
[ "$N" -lt "$FAIL_THRESHOLD" ] && exit 0
# 3) 1차 복구: 컨테이너 안 run.py 재기동(.env 소싱 실패가 기동 막지 않게 분리)
log "RECOVERY-1: 컨테이너 내부 run.py 재기동"
"$DOCKER" exec "$CONTAINER" sh -c "pkill -TERM -f '[r]un.py' 2>/dev/null; sleep 3; pkill -9 -f '[r]un.py' 2>/dev/null; cd ${APP} || exit 0; if [ -r ./.env ]; then set -a; . ./.env 2>/dev/null || true; set +a; fi; setsid ${PY} ${RUNPY} >> ${APP}/logs/boot.log 2>&1 < /dev/null &" >> "$LOG" 2>&1
sleep 12
if healthy; then log "RECOVERED (내부 재기동)"; rm -f "$STATE"; notify "KNK Mail 자동복구" "앱 재기동으로 복구했습니다. $(ts)"; exit 0; fi
# 4) 2차 복구: 컨테이너 재시작
log "RECOVERY-2: docker restart $CONTAINER"
"$DOCKER" restart "$CONTAINER" >> "$LOG" 2>&1; sleep 25
if healthy; then log "RECOVERED (컨테이너 재시작)"; rm -f "$STATE"; notify "KNK Mail 자동복구" "컨테이너를 재시작해 복구했습니다. $(ts)"
else log "RECOVERY FAILED — 수동 점검 필요"; notify "[긴급] KNK Mail 복구 실패" "자동복구 실패. 즉시 점검 필요. $(ts)"; fi
exit 0
