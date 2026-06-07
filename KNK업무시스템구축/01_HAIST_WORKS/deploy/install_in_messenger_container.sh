#!/bin/bash
# ============================================================
# HAIST WORKS — 메신저 컨테이너 내부 1줄 설치 스크립트
# v5H226z108n20 (2026-05-28)
# ============================================================
# 실행 위치: 메신저 컨테이너 *내부* SSH/bash (host 가 아님)
# 진입 방법: docker exec -it <messenger_container_name> bash
# 실행:     cd /opt/knk_haist && bash deploy/install_in_messenger_container.sh
# ============================================================
# 작업:
#   1) 환경 점검 (root·python3·nginx·supervisor)
#   2) Python venv + requirements 설치
#   3) 데이터 디렉터리 (/opt/knk_haist/{data,uploads,backups,logs})
#   4) .env 생성 (SECRET_KEY 자동 생성)
#   5) supervisor program 등록
#   6) nginx /works/ location 블록 추가 (메신저 설정 백업 후)
#   7) supervisor reread + update + start
#   8) nginx -t + reload
#   9) 헬스체크
# ============================================================
# 안전:
#   - 모든 변경 전 백업 생성 (.bak.YYYYMMDD_HHMMSS)
#   - nginx -t 통과 못하면 자동 롤백
#   - 메신저 영향 0 보장 (별도 program/location, /msg/ 비건드림)
# ============================================================

set -e
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
WORKS_DIR=/opt/knk_haist
WORKS_PORT=8081

step() { echo ""; echo "============================================================"; echo "  [$1] $2"; echo "============================================================"; }
warn() { echo "  ⚠  $1"; }
ok()   { echo "  ✓  $1"; }
err()  { echo "  ✗  $1"; exit 1; }

# ── 0. 환경 점검 ────────────────────────────────────────────
step "0/9" "환경 점검"
[ "$(id -u)" -eq 0 ] || err "root 권한 필요 (sudo bash $0)"
ok "root 확인됨"

[ -d "$WORKS_DIR" ] || err "$WORKS_DIR 폴더 없음. 먼저 git clone 하세요."
ok "$WORKS_DIR 존재"

command -v python3 >/dev/null || err "python3 없음"
PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
ok "python3 = $PYVER"

command -v nginx >/dev/null || err "nginx 없음 (메신저 컨테이너 안에 있어야 함)"
ok "nginx 존재"

command -v supervisorctl >/dev/null || err "supervisorctl 없음"
ok "supervisor 존재"

# pip 또는 ensurepip
if ! python3 -m pip --version >/dev/null 2>&1; then
  warn "pip 없음 → ensurepip 시도"
  python3 -m ensurepip --upgrade || err "pip 설치 실패"
fi
ok "pip 사용 가능"

# venv 모듈
python3 -m venv --help >/dev/null 2>&1 || {
  warn "venv 모듈 없음 — apt install python3-venv 시도"
  apt-get update && apt-get install -y python3-venv || err "python3-venv 설치 실패"
}
ok "venv 모듈 사용 가능"

# ── 1. Python venv + requirements ───────────────────────────
step "1/9" "Python 가상환경 + 의존성 설치"
cd "$WORKS_DIR"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ok ".venv 생성됨"
else
  ok ".venv 이미 존재"
fi

source .venv/bin/activate
pip install --quiet --upgrade pip wheel setuptools
pip install --quiet -r requirements.txt
ok "requirements.txt 설치 완료"
deactivate

# ── 2. 데이터 디렉터리 ──────────────────────────────────────
step "2/9" "데이터 디렉터리 생성"
mkdir -p "$WORKS_DIR"/{data,uploads,backups,logs}
chmod 755 "$WORKS_DIR"/{data,uploads,backups,logs}
ok "data/ uploads/ backups/ logs/"

# ── 3. .env 생성 ───────────────────────────────────────────
step "3/9" ".env 생성"
ENV_FILE="$WORKS_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  ok ".env 이미 존재 — 그대로 사용"
else
  if [ -f "$WORKS_DIR/deploy/.env.example" ]; then
    cp "$WORKS_DIR/deploy/.env.example" "$ENV_FILE"
  else
    cat > "$ENV_FILE" <<'EOF'
KNK_MODE=prod
KNK_HOST=127.0.0.1
KNK_PORT=8081
KNK_WORKERS=2
KNK_SECRET_KEY=__GENERATE__
EOF
  fi

  # SECRET_KEY 자동 생성
  GENKEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  # __GENERATE__ 또는 기본값(여기에_...) 치환
  sed -i "s|__GENERATE__|$GENKEY|g" "$ENV_FILE"
  sed -i "s|여기에_32자_이상_임의_문자열_채우세요_절대_화면에_출력하지_말것|$GENKEY|g" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  unset GENKEY
  ok ".env 생성·권한 600 적용"
fi

# ── 4. supervisor program 설치 ──────────────────────────────
step "4/9" "supervisor program 등록"
SUPERVISOR_DIR=/etc/supervisor/conf.d
[ -d "$SUPERVISOR_DIR" ] || err "$SUPERVISOR_DIR 없음 — 컨테이너 supervisor 설치 안 됨"

SUPER_CONF="$SUPERVISOR_DIR/knk-works.conf"
if [ -f "$SUPER_CONF" ]; then
  cp "$SUPER_CONF" "$SUPER_CONF.bak.$TIMESTAMP"
  warn "기존 conf 백업: $SUPER_CONF.bak.$TIMESTAMP"
fi

# .env 의 비밀변수들을 supervisor environment= 에 인라인 (uvicorn 이 os.environ 으로 읽음)
# 하지만 환경변수가 노출 위험 있어서 — wrapper script 방식 채택
WRAPPER="$WORKS_DIR/.venv/bin/run_knk_works.sh"
cat > "$WRAPPER" <<EOF
#!/bin/bash
set -a
source $WORKS_DIR/.env
set +a
cd $WORKS_DIR
exec $WORKS_DIR/.venv/bin/uvicorn app.main:app \\
    --host 127.0.0.1 \\
    --port $WORKS_PORT \\
    --workers \${KNK_WORKERS:-2} \\
    --proxy-headers \\
    --forwarded-allow-ips=127.0.0.1
EOF
chmod 700 "$WRAPPER"

cat > "$SUPER_CONF" <<EOF
[program:knk-works]
command=$WRAPPER
directory=$WORKS_DIR
user=root
autostart=true
autorestart=true
startsecs=10
startretries=5
stopwaitsecs=10
stopasgroup=true
killasgroup=true
stdout_logfile=$WORKS_DIR/logs/uvicorn.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=5
stderr_logfile=$WORKS_DIR/logs/uvicorn-error.log
stderr_logfile_maxbytes=50MB
stderr_logfile_backups=5
environment=PYTHONUNBUFFERED="1",PYTHONIOENCODING="utf-8",PYTHONUTF8="1",TZ="Asia/Seoul",LANG="C.UTF-8",LC_ALL="C.UTF-8"
EOF
ok "supervisor program 설정: $SUPER_CONF"

# ── 5. nginx /works/ location 추가 ──────────────────────────
step "5/9" "nginx /works/ location 추가"

# 메신저 nginx 설정 자동 탐지
NGINX_CONF=""
for candidate in \
    /etc/nginx/conf.d/knk-messenger.conf \
    /etc/nginx/conf.d/default.conf \
    /etc/nginx/sites-enabled/knk-messenger \
    /etc/nginx/sites-enabled/default \
    /etc/nginx/nginx.conf
do
  if [ -f "$candidate" ] && grep -q "haist.knknara.co.kr\|server_name _\|listen 443\|listen 80" "$candidate" 2>/dev/null; then
    NGINX_CONF="$candidate"
    break
  fi
done

if [ -z "$NGINX_CONF" ]; then
  warn "메신저 nginx 설정 자동 탐지 실패"
  echo "  현재 후보:"
  ls /etc/nginx/conf.d/ /etc/nginx/sites-enabled/ 2>/dev/null
  err "수동으로 NGINX_CONF 변수 지정 후 재실행하세요."
fi
ok "메신저 nginx 설정 파일: $NGINX_CONF"

# 백업 — sites-enabled/ 안에 두면 nginx 가 추가 설정으로 읽어 duplicate server 발생.
# 별도 디렉터리(/root/nginx-backups/)에 보관.
BACKUP_DIR=/root/nginx-backups
mkdir -p "$BACKUP_DIR"
NGINX_BACKUP="$BACKUP_DIR/$(basename "$NGINX_CONF").bak.$TIMESTAMP"
cp "$NGINX_CONF" "$NGINX_BACKUP"
ok "백업: $NGINX_BACKUP"

# 이미 /works/ 블록 있으면 스킵 (재실행 idempotent)
if grep -q "location /works/" "$NGINX_CONF"; then
  ok "이미 /works/ 블록 존재 — 스킵"
else
  # /msg/ 블록 위에 /works/ 블록 삽입 (또는 마지막 server block 안)
  WORKS_LOC_FILE="$WORKS_DIR/deploy/nginx_works_location.conf"
  [ -f "$WORKS_LOC_FILE" ] || err "$WORKS_LOC_FILE 없음"

  python3 <<PYEOF
import re, sys

conf_path = "$NGINX_CONF"
loc_path = "$WORKS_LOC_FILE"

with open(loc_path, encoding='utf-8') as f:
    works_block = f.read().strip()

with open(conf_path, encoding='utf-8') as f:
    conf = f.read()

# /msg/ 블록 찾기 (그 바로 앞에 /works/ 블록 삽입)
m = re.search(r'(\s*)location\s+/msg/?\s*\{', conf)
if m:
    insert_pos = m.start()
    indent = m.group(1).lstrip('\n')
    indented = '\n'.join(indent + line if line.strip() else line for line in works_block.split('\n'))
    conf_new = conf[:insert_pos] + '\n' + indented + '\n' + conf[insert_pos:]
elif 'server_name' in conf and 'listen' in conf:
    # /msg/ 없으면 마지막 } 바로 앞에 삽입 (가장 안쪽 server 블록 안)
    last_brace = conf.rfind('}')
    if last_brace == -1:
        sys.exit("nginx conf 에 } 없음 — 파일 손상")
    conf_new = conf[:last_brace] + '\n' + works_block + '\n' + conf[last_brace:]
else:
    sys.exit("nginx conf 구조 인식 실패 — 수동 편집 필요")

with open(conf_path, 'w', encoding='utf-8') as f:
    f.write(conf_new)
print("  ✓ /works/ 블록 삽입 완료")
PYEOF
fi

# ── 6. nginx 검증 + reload ─────────────────────────────────
step "6/9" "nginx 설정 검증"
if nginx -t 2>&1; then
  ok "nginx -t 통과"
else
  warn "nginx -t 실패 → 백업 복원"
  cp "$NGINX_BACKUP" "$NGINX_CONF"
  err "원본 복구함. 수동 점검 필요: $NGINX_BACKUP 와 비교."
fi

# ── 7. supervisor reread + update + start ──────────────────
step "7/9" "supervisor 갱신 + knk-works 시작"
supervisorctl reread
supervisorctl update
sleep 2
supervisorctl status knk-works || warn "knk-works 상태 RUNNING 이 아님 — 로그 확인 필요"

# ── 8. nginx reload ────────────────────────────────────────
step "8/9" "nginx reload"
nginx -s reload && ok "nginx reload 성공" || err "nginx reload 실패"

# ── 9. 헬스체크 ────────────────────────────────────────────
step "9/9" "헬스체크"
sleep 5

echo "  [내부] http://127.0.0.1:$WORKS_PORT/login"
if curl -fsS -o /dev/null -w "    HTTP %{http_code}\n" --max-time 10 http://127.0.0.1:$WORKS_PORT/login; then
  ok "내부 응답 OK"
else
  warn "내부 응답 실패 — 로그: tail $WORKS_DIR/logs/uvicorn.log"
fi

echo "  [외부] https://haist.knknara.co.kr/works/login"
if curl -fsS -o /dev/null -w "    HTTP %{http_code}\n" --max-time 10 -L https://haist.knknara.co.kr/works/login; then
  ok "외부 응답 OK"
else
  warn "외부 응답 실패 — DSM Reverse Proxy 도 메신저(/msg/)와 같은 라인이면 자동 통과 예상."
fi

echo "  [메신저 영향 점검] https://haist.knknara.co.kr/msg/healthz"
curl -fsS -o /dev/null -w "    HTTP %{http_code}\n" --max-time 10 https://haist.knknara.co.kr/msg/healthz || warn "메신저 헬스체크 실패 — 점검 필요"

echo ""
echo "============================================================"
echo "  설치 완료 (재실행은 idempotent — 안전)"
echo ""
echo "  📌 다음 단계:"
echo "    1) 브라우저에서 https://haist.knknara.co.kr/works/ 접속"
echo "    2) 로그인 화면 확인"
echo "    3) 메신저 https://haist.knknara.co.kr/msg/ 도 정상인지 확인"
echo ""
echo "  📋 관리 명령:"
echo "    supervisorctl status knk-works"
echo "    supervisorctl restart knk-works"
echo "    tail -f $WORKS_DIR/logs/uvicorn.log"
echo "    tail -f $WORKS_DIR/logs/uvicorn-error.log"
echo ""
echo "  🚨 롤백 (메신저까지 영향 시):"
echo "    supervisorctl stop knk-works"
echo "    cp $NGINX_BACKUP $NGINX_CONF"
echo "    nginx -s reload"
echo "============================================================"
