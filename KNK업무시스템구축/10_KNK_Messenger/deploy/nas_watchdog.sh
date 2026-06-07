#!/bin/sh
# ============================================================
# KNK Messenger 외부 워치독 (Synology DSM 호스트에서 실행)
# ------------------------------------------------------------
# 목적: 컨테이너 '내부'의 supervisord/gunicorn 이 죽어 메신저가 다운(502)돼도
#       사람 개입 없이 '컨테이너 밖'에서 자동 복구한다. (대표 지시 2026-05-25)
#       → 컨테이너 내부가 어떻게 망가지든 무관하게 동작하는 최종 안전망.
#
# 왜 필요한가:
#   운영 컨테이너의 최상위 프로세스(PID 1)가 supervisord 가 아니라 bash 라,
#   supervisord 가 죽어도 컨테이너는 '실행 중'으로 보이고 아무도 supervisord 를
#   되살리지 못한다 → 앱이 영구 다운(502). 이 워치독이 그 공백을 메운다.
#
# 설치 (DSM 7 / Container Manager):
#   1) 이 파일을 NAS 의 /volume1/docker/knk-messenger/nas_watchdog.sh 로 복사
#   2) 아래 CONTAINER 값을 실제 컨테이너 이름으로 수정 (SSH: docker ps --format '{{.Names}}')
#   3) DSM > 제어판 > 작업 스케줄러 > 생성 > 예약된 작업 > 사용자 정의 스크립트
#        - 사용자: root
#        - 일정: 매일 / 반복: 1분 간격
#        - 실행 명령: sh /volume1/docker/knk-messenger/nas_watchdog.sh
#   4) 저장 후 '실행'으로 1회 수동 테스트 → /var/log/knk_watchdog.log 확인
#
# 동작 단계:
#   1) /healthz 점검 → 정상이면 종료
#   2) 연속 FAIL_THRESHOLD 회 실패해야 복구 시작 (일시적 깜빡임 무시)
#   3) 1차 복구: supervisord 재기동 + 앱 시작 (가벼움, 수초)
#   4) 2차 복구: 그래도 안되면 컨테이너 재시작
#   5) 복구/실패 시 관리자에게 DSM 알림
# ============================================================

# ── 설정 (환경에 맞게 수정) ─────────────────────────────────
CONTAINER="knk-messenger"        # ★ docker ps 로 실제 이름 확인 후 수정
FAIL_THRESHOLD=2                 # 연속 N회 실패 시 복구 (1분 간격 → 약 2분 내 복구)
HEALTH_PATH="http://127.0.0.1:5050/healthz"
STATE="/tmp/knk_watchdog_fail"
LOG="/var/log/knk_watchdog.log"

# docker 실행 파일 자동 탐색 (Synology 경로 편차 대응)
if [ -x /usr/local/bin/docker ]; then DOCKER=/usr/local/bin/docker
elif [ -x /usr/bin/docker ]; then DOCKER=/usr/bin/docker
else DOCKER=docker; fi

ts()  { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "$(ts) $1" >> "$LOG" 2>/dev/null; }
notify() { synodsmnotify @administrators "$1" "$2" 2>/dev/null || true; }

healthy() { "$DOCKER" exec "$CONTAINER" sh -c "curl -fsS --max-time 8 $HEALTH_PATH" >/dev/null 2>&1; }

# ── 1) 정상 점검 ────────────────────────────────────────────
if healthy; then
    [ -f "$STATE" ] && rm -f "$STATE"
    exit 0
fi

# ── 2) 실패 카운터 누적 (일시적 실패 무시) ──────────────────
N=0
[ -f "$STATE" ] && N=$(cat "$STATE" 2>/dev/null || echo 0)
N=$((N + 1))
echo "$N" > "$STATE"
log "healthz FAIL ($N/$FAIL_THRESHOLD)"
[ "$N" -lt "$FAIL_THRESHOLD" ] && exit 0

# ── 3) 1차 복구: supervisord 재기동 + 앱 시작 ───────────────
log "RECOVERY-1: supervisord 재기동 시도"
"$DOCKER" exec "$CONTAINER" sh -c 'pgrep -f supervisord >/dev/null 2>&1 || supervisord -c /etc/supervisor/supervisord.conf; sleep 5; supervisorctl start knk-messenger knk-nginx 2>&1' >> "$LOG" 2>&1
sleep 5
if healthy; then
    log "RECOVERED (supervisord 재기동)"
    rm -f "$STATE"
    notify "KNK 메신저 자동복구" "메신저가 일시 다운되어 자동복구했습니다 (supervisord 재기동). $(ts)"
    exit 0
fi

# ── 4) 2차 복구: 컨테이너 재시작 ────────────────────────────
log "RECOVERY-2: docker restart $CONTAINER"
"$DOCKER" restart "$CONTAINER" >> "$LOG" 2>&1
sleep 20
if healthy; then
    log "RECOVERED (컨테이너 재시작)"
    rm -f "$STATE"
    notify "KNK 메신저 자동복구" "메신저 컨테이너를 재시작해 복구했습니다. $(ts)"
else
    log "RECOVERY FAILED — 수동 점검 필요"
    notify "[긴급] KNK 메신저 복구 실패" "자동복구 실패. 즉시 수동 점검이 필요합니다. $(ts)"
fi
exit 0
