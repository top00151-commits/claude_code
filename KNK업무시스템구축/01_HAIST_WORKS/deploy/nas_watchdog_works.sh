#!/bin/sh
# ============================================================
# KNK WORKS 외부 워치독 — DSM(NAS 호스트)에서 1분마다 실행 (컨테이너 밖)
# ------------------------------------------------------------
# 자동복구 표준 2단계. 컨테이너 안쪽 워치독(works_watchdog.sh)이 못 잡는 경우 복구:
#   - 컨테이너 통째 멈춤(wedge) → docker restart
#   - NAS 재부팅 후 컨테이너 자체가 안 뜸 → docker start
#   - 내부 워치독까지 죽음 → 컨테이너 안 supervisorctl restart
# 본보기: 10_KNK_Messenger/deploy/nas_watchdog_msg_new.sh (지시서 자동복구_표준방안_2026-07-06)
# 설치: /volume1/docker/knk_haist/nas_watchdog_works.sh (chmod +x) + DSM 작업 스케줄러 root 1분.
# ★ 실제 컨테이너명은 `docker ps` 로 확인 후 CONTAINER= 수정 (WORK/WORKS/KNKHAIST 등 환경마다 다름).
# ============================================================
CONTAINER="KNKHAIST.WORK"      # ★ docker ps 로 실제 이름 확인 후 수정 (메모리 knk_container_split=KNKHAIST.WORK)
PORT="5051"
PROG="knk-works"               # supervisorctl 프로그램명 (docker exec <C> supervisorctl status 로 확인)
FAIL_THRESHOLD=2
STATE="/tmp/knk_watchdog_works_fail"
LOG="/var/log/knk_watchdog_works.log"

if [ -x /usr/local/bin/docker ]; then DOCKER=/usr/local/bin/docker
elif [ -x /usr/bin/docker ]; then DOCKER=/usr/bin/docker
else DOCKER=docker; fi
ts(){ date '+%Y-%m-%d %H:%M:%S'; }
log(){ echo "$(ts) $1" >> "$LOG" 2>/dev/null; }
notify(){ synodsmnotify @administrators "$1" "$2" 2>/dev/null || true; }
running(){ "$DOCKER" inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true; }
# 생존확인: 컨테이너 안 curl 로 루트. 000(무응답)만 실패로 본다(WORKS 는 미로그인 303 이 정상).
healthy(){ code=$("$DOCKER" exec "$CONTAINER" sh -c "curl -s -m 8 -o /dev/null -w '%{http_code}' http://127.0.0.1:${PORT}/" 2>/dev/null); [ -n "$code" ] && [ "$code" != "000" ]; }

# 0) 컨테이너 미기동 → 시작
if ! running; then
    log "컨테이너 미기동 → docker start $CONTAINER"
    "$DOCKER" start "$CONTAINER" >> "$LOG" 2>&1; sleep 20
    notify "KNK WORKS 자동복구" "컨테이너가 내려가 있어 다시 시작했습니다. $(ts)"
fi
# 1) 정상이면 종료
if healthy; then [ -f "$STATE" ] && rm -f "$STATE"; exit 0; fi
# 2) 연속 실패 누적
N=0; [ -f "$STATE" ] && N=$(cat "$STATE" 2>/dev/null || echo 0); N=$((N + 1)); echo "$N" > "$STATE"
log "생존확인 FAIL ($N/$FAIL_THRESHOLD)"
[ "$N" -lt "$FAIL_THRESHOLD" ] && exit 0
# 3) 1차 복구: 컨테이너 안 supervisorctl restart
log "RECOVERY-1: supervisorctl restart $PROG"
"$DOCKER" exec "$CONTAINER" supervisorctl restart "$PROG" >> "$LOG" 2>&1
sleep 12
if healthy; then log "RECOVERED (supervisorctl)"; rm -f "$STATE"; notify "KNK WORKS 자동복구" "앱 재시작으로 복구했습니다. $(ts)"; exit 0; fi
# 4) 2차 복구: 컨테이너 재시작
log "RECOVERY-2: docker restart $CONTAINER"
"$DOCKER" restart "$CONTAINER" >> "$LOG" 2>&1; sleep 25
if healthy; then log "RECOVERED (컨테이너 재시작)"; rm -f "$STATE"; notify "KNK WORKS 자동복구" "컨테이너를 재시작해 복구했습니다. $(ts)"
else log "RECOVERY FAILED — 수동 점검 필요"; notify "[긴급] KNK WORKS 복구 실패" "자동복구 실패. 즉시 점검 필요. $(ts)"; fi
exit 0
