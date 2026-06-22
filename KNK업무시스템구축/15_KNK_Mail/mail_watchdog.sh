#!/bin/sh
# ============================================================
# KNK Mail — 컨테이너 내부 자동복구 워치독 (대표 지시 2026-06-21 "앱 자동 재시작 강화")
# ------------------------------------------------------------
#   본보기: 메신저 msg_watchdog.sh 검증본(3관점 적대적 검증 13건 반영). 메일 특화 차이:
#   ① 메일 독립 컨테이너(KNKHAIST.MAIL)엔 supervisord·cron 이 없음 → 죽거나 멈추면 되살릴
#      주체가 없다(2026-06-21 kmail 502 장애 실제 원인). 이 루프가 healthz 감시·자동 재기동.
#   ② 컨테이너에 curl 이 없음 → 건강검사를 앱의 .venv python(urllib)로 수행(의존 0).
#   ③ 앱 = uvicorn 직접(/opt/knk_mail/run.py), gunicorn 아님. 재기동은 BOOT-START 와 동일 방식.
#   복구: run.py 만 TERM→KILL 종료 → .env 소싱(실패해도 기동 막지 않음) → setsid python run.py.
#   안전: ① flock 단일 인스턴스 ② 연속 실패 + 확정 재점검까지 실패해야 복구 ③ 콜드스타트 회복 대기
#         ④ 정상 시 로그 안 남김 + 1MB 캡 ⑤ 연속 복구 실패면 degraded(폭주 방지) ⑥ 부팅 워밍업
#         ⑦ 파일 갱신 시 self-restart(부분기록 방지: 5초 대기 + 구문검증).
# ============================================================
APP_DIR="/opt/knk_mail"
PORT="5053"
PY="${APP_DIR}/.venv/bin/python"
RUNPY="${APP_DIR}/run.py"
HEALTH="http://127.0.0.1:${PORT}/healthz"
LOGDIR="${APP_DIR}/logs"
LOG="${LOGDIR}/watchdog.log"
BOOTLOG="${LOGDIR}/boot.log"
LOCK="${LOGDIR}/watchdog.lock"
SELF="$0"
PYMATCH="[r]un.py"   # /opt/knk_mail/run.py 매칭(다른 서비스 무관)

INTERVAL=20          # 정상 시 점검 주기(초)
FAIL_THRESHOLD=2     # 연속 실패 N회 후 '확정 재점검' → 복구(오탐 방지)
PROBE_TIMEOUT=10     # healthz 1회 타임아웃(초)
READY_BUDGET=75      # 재기동 후 정상까지 기다리는 최대(초)
READY_STEP=3         # 재기동 후 점검 간격(초)
WARMUP=20            # 부팅 직후 첫 점검 전 워밍업(초)
MAX_RECOVERY=6       # 연속 복구 실패 N회면 degraded(강제재기동 중단·관찰)
LOG_CAP=1048576      # 로그 1MB 초과 시 마지막 부분만 보존

mkdir -p "$LOGDIR" 2>/dev/null

ts(){ date '+%Y-%m-%d %H:%M:%S'; }
cap_log(){ f="$1"; sz=$(wc -c < "$f" 2>/dev/null || echo 0); [ "$sz" -gt "$LOG_CAP" ] && tail -c 200000 "$f" > "${f}.tmp" 2>/dev/null && mv "${f}.tmp" "$f" 2>/dev/null; }
log(){ cap_log "$LOG"; echo "$(ts) $1" >> "$LOG" 2>/dev/null; }

# ── 단일 인스턴스 락(flock) ──
exec 9>"$LOCK" 2>/dev/null
flock -n 9 2>/dev/null || exit 0

# ── 건강검사: curl 없음 → 앱 python(urllib)로 healthz 200 확인 ──
healthy(){
    "$PY" -c "import sys,urllib.request as u; sys.exit(0 if u.urlopen('$HEALTH',timeout=$PROBE_TIMEOUT).status==200 else 1)" 2>/dev/null
}

# ── run.py 종료: TERM 유예 후 KILL, 프로세스 부재까지 대기 ──
stop_app(){
    pkill -TERM -f "$PYMATCH" 2>/dev/null
    i=0; while [ "$i" -lt 5 ] && pgrep -f "$PYMATCH" >/dev/null 2>&1; do sleep 1; i=$((i + 1)); done
    if pgrep -f "$PYMATCH" >/dev/null 2>&1; then
        pkill -9 -f "$PYMATCH" 2>/dev/null
        i=0; while [ "$i" -lt 6 ] && pgrep -f "$PYMATCH" >/dev/null 2>&1; do sleep 1; i=$((i + 1)); done
    fi
    pgrep -f "$PYMATCH" >/dev/null 2>&1 && log "경고: run.py 종료 실패(포트 미해제 가능) — 재기동 실패 시 컨테이너 재시작 필요"
}

# ── run.py 기동: .env 소싱 실패가 기동을 막지 못하게 분리(BOOT-START 와 동일) ──
start_app(){
    cap_log "$BOOTLOG"
    ( cd "$APP_DIR" 2>/dev/null || exit 0
      if [ -r ./.env ]; then set -a; . ./.env 2>>"$BOOTLOG" || true; set +a; fi
      exec setsid "$PY" "$RUNPY" >>"$BOOTLOG" 2>&1 < /dev/null
    ) &
}

wait_ready(){
    t=0
    while [ "$t" -lt "$READY_BUDGET" ]; do
        sleep "$READY_STEP"; t=$((t + READY_STEP))
        if healthy; then return 0; fi
    done
    return 1
}

recover(){
    log "RECOVERY: 메일 비정상 → 재기동 시도"
    stop_app
    start_app
    if wait_ready; then
        log "복구 성공 (healthz 200)"
        return 0
    fi
    log "복구 후 ${READY_BUDGET}s 내 회복 실패"
    return 1
}

self_mtime(){ stat -c %Y "$SELF" 2>/dev/null || echo 0; }
ORIG_MTIME=$(self_mtime)

log "watchdog 시작 (interval=${INTERVAL}s threshold=${FAIL_THRESHOLD} ready=${READY_BUDGET}s port=${PORT})"
sleep "$WARMUP"

fails=0
rec_fail=0
degraded=0
while true; do
    if [ "$(self_mtime)" != "$ORIG_MTIME" ]; then
        sleep 5
        if /bin/sh -n "$SELF" 2>/dev/null; then
            log "watchdog 코드 갱신 감지 → self-restart"
            exec /bin/sh "$SELF"
        fi
        log "watchdog 파일 변경 감지·구문검증 실패 — self-restart 보류(기존 코드 유지)"
        ORIG_MTIME=$(self_mtime)
    fi

    if healthy; then
        if [ "$fails" -gt 0 ] || [ "$degraded" = "1" ]; then log "healthz 정상 회복"; fi
        fails=0; rec_fail=0; degraded=0
        sleep "$INTERVAL"; continue
    fi

    fails=$((fails + 1))
    if [ "$fails" -lt "$FAIL_THRESHOLD" ]; then
        log "healthz 실패 (${fails}/${FAIL_THRESHOLD})"
        sleep "$INTERVAL"; continue
    fi

    sleep 3
    if healthy; then
        log "확정 재점검: 정상(오탐) — 복구 보류"
        fails=0
        sleep "$INTERVAL"; continue
    fi

    if [ "$degraded" = "1" ]; then
        sleep 300; continue
    fi

    if recover; then
        fails=0; rec_fail=0
        sleep "$INTERVAL"
    else
        rec_fail=$((rec_fail + 1))
        fails=0
        if [ "$rec_fail" -ge "$MAX_RECOVERY" ]; then
            degraded=1
            log "DEGRADED: ${MAX_RECOVERY}회 연속 복구 실패 — 강제재기동 중단·관찰만. 앱 자체 문제 의심·즉시 점검 필요."
        fi
        sleep "$INTERVAL"
    fi
done
