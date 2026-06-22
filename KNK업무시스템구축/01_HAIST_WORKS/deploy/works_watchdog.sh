#!/bin/sh
# ============================================================
# KNK WORKS — 컨테이너 내부 자동복구 워치독 (대표 지시 2026-06-21 "앱 자동 재시작 강화")
# ------------------------------------------------------------
#   본보기: 메신저 msg_watchdog.sh 검증본(3관점 적대적 검증 13건 반영). WORKS 특화 차이:
#   ① WORKS 컨테이너엔 supervisord 가 있음 → 복구는 'supervisorctl restart knk-works'.
#      (프로세스 생명주기는 supervisord 가 책임지고, 워치독은 '행 감지 → 재시작 트리거'만 — 더 단순·안전)
#   ② WORKS 엔 healthz 전용 엔드포인트가 없어 루트(/) 로 생존확인:
#      미로그인 303(또는 어떤 HTTP 코드든) = 앱 살아있음 / 000(무응답·타임아웃) = 죽음 or 행.
#   왜 필요한가: supervisord 의 autorestart 는 프로세스가 '죽을 때'만 살림. 죽지 않고 '멈추면(행)'
#      (예: 단일 워커가 외부 호출/락에 막힘) 못 잡는다 → 이 워치독이 그 구멍을 메운다.
#   한계(정직): 앱이 완전히 멈추거나 죽은 경우를 복구한다. 특정 기능만 막히는 '부분 장애'
#      (예: 한 라우트만 DB 락)는 루트가 정상 응답하면 못 잡으며 그건 코드 수정이 답이다.
#   안전: ① flock 단일 인스턴스 ② 연속 실패 + 확정 재점검까지 실패해야 복구(오탐 방지)
#         ③ 콜드스타트 회복 대기 ④ 정상일 땐 로그 안 남김 + 1MB 캡 ⑤ 연속 복구 실패면
#         degraded(강제재기동 중단·관찰만)로 폭주 방지 ⑥ 부팅 워밍업 ⑦ 파일 갱신 시 self-restart.
# ============================================================
APP="knk-works"
PORT="5051"
HEALTH="http://127.0.0.1:${PORT}/"
SUPERVISORCTL="$(command -v supervisorctl || echo /usr/bin/supervisorctl)"
LOGDIR="/opt/knk_haist/logs"
LOG="${LOGDIR}/watchdog.log"
LOCK="${LOGDIR}/watchdog.lock"
SELF="$0"

INTERVAL=20          # 정상 시 점검 주기(초)
FAIL_THRESHOLD=2     # 연속 실패 N회 후 '확정 재점검' → 복구(오탐 방지)
PROBE_TIMEOUT=10     # 생존확인 1회 타임아웃(초)
READY_BUDGET=75      # 재기동 후 정상까지 기다리는 최대(초)
READY_STEP=3         # 재기동 후 점검 간격(초)
WARMUP=20            # 부팅 직후 첫 점검 전 워밍업(초)
MAX_RECOVERY=6       # 연속 복구 실패 N회면 degraded(강제재기동 중단·관찰)
LOG_CAP=1048576      # 로그 1MB 초과 시 마지막 부분만 보존

mkdir -p "$LOGDIR" 2>/dev/null

ts(){ date '+%Y-%m-%d %H:%M:%S'; }
cap_log(){ f="$1"; sz=$(wc -c < "$f" 2>/dev/null || echo 0); [ "$sz" -gt "$LOG_CAP" ] && tail -c 200000 "$f" > "${f}.tmp" 2>/dev/null && mv "${f}.tmp" "$f" 2>/dev/null; }
log(){ cap_log "$LOG"; echo "$(ts) $1" >> "$LOG" 2>/dev/null; }

# ── 단일 인스턴스 락(flock) — setsid 재배치·중복 기동에 견고 ──
exec 9>"$LOCK" 2>/dev/null
flock -n 9 2>/dev/null || exit 0

# ── 생존확인: 연결돼 HTTP 상태코드를 받으면(2xx/3xx/4xx 무엇이든) 살아있음. 000=무응답/타임아웃=비정상 ──
healthy(){
    code=$(curl -s -m "$PROBE_TIMEOUT" -o /dev/null -w "%{http_code}" "$HEALTH" 2>/dev/null)
    [ -n "$code" ] && [ "$code" != "000" ]
}

# ── 복구: supervisord 가 knk-works 를 재시작(stop→start 보장·포트 해제·환경 일관) ──
recover(){
    log "RECOVERY: WORKS 무응답 → $SUPERVISORCTL restart $APP"
    "$SUPERVISORCTL" restart "$APP" >>"$LOG" 2>&1
    t=0
    while [ "$t" -lt "$READY_BUDGET" ]; do
        sleep "$READY_STEP"; t=$((t + READY_STEP))
        if healthy; then log "복구 성공 (HTTP 응답 정상)"; return 0; fi
    done
    log "복구 후 ${READY_BUDGET}s 내 회복 실패"
    return 1
}

# ── 배포로 이 파일이 갱신되면 새 코드로 self-restart(부분기록 방지: 5초 대기 + 구문검증) ──
self_mtime(){ stat -c %Y "$SELF" 2>/dev/null || echo 0; }
ORIG_MTIME=$(self_mtime)

log "watchdog 시작 (interval=${INTERVAL}s threshold=${FAIL_THRESHOLD} ready=${READY_BUDGET}s port=${PORT} app=${APP})"
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
        if [ "$fails" -gt 0 ] || [ "$degraded" = "1" ]; then log "생존확인 정상 회복"; fi
        fails=0; rec_fail=0; degraded=0
        sleep "$INTERVAL"; continue
    fi

    fails=$((fails + 1))
    if [ "$fails" -lt "$FAIL_THRESHOLD" ]; then
        log "생존확인 실패 (${fails}/${FAIL_THRESHOLD})"
        sleep "$INTERVAL"; continue
    fi

    # 임계 도달 → 강제재기동 직전 확정 재점검(일시 깜빡임/장기요청 오탐 방지)
    sleep 3
    if healthy; then
        log "확정 재점검: 정상(오탐) — 복구 보류"
        fails=0
        sleep "$INTERVAL"; continue
    fi

    if [ "$degraded" = "1" ]; then
        sleep 300; continue   # 더는 죽이지 않고 관찰만(자연 회복은 위 healthy 분기서 처리)
    fi

    if recover; then
        fails=0; rec_fail=0
        sleep "$INTERVAL"
    else
        rec_fail=$((rec_fail + 1))
        fails=0   # 다음 임계까지 다시 세며 새 프로세스에 충분한 시간 부여(연속 즉살 방지)
        if [ "$rec_fail" -ge "$MAX_RECOVERY" ]; then
            degraded=1
            log "DEGRADED: ${MAX_RECOVERY}회 연속 복구 실패 — 강제재기동 중단·관찰만. 앱 자체 문제 의심·즉시 점검 필요."
        fi
        sleep "$INTERVAL"
    fi
done
