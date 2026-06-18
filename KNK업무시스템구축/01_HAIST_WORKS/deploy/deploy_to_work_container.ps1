# ============================================================
# HAIST WORKS - deploy to KNKHAIST.WORK container (PowerShell)
# v5H226z495 (2026-06-18) - 3-system container split cutover
# ============================================================
# 사용법 (PowerShell, 본인 PC):
#   1) 먼저 들여다보기(읽기전용):  ./deploy_to_work_container.ps1 -Inspect
#   2) 실제 배포:                  ./deploy_to_work_container.ps1
#   - SSH 비밀번호는 실행 중 직접 입력(스크립트에 저장 안 함).
#   - 포트/경로/프로그램 다르면:   -Port 32201 -AppDir /opt/knk_haist -Program knk-works
#
# 견고화(z495b): 원격 명령은 base64 로 실어 보냄 → PowerShell/ssh/bash 따옴표·한글 깨짐 원천차단.
#               원격 스크립트는 영문(ASCII)로 작성. 한글은 로컬 화면 출력에만.
# 사실확인: SSH 는 'KNKHAIST' 컨테이너 안으로 직접 들어감(whoami=root). docker exec 불필요.
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]$Port       = 32201,
    [string]$User    = "root",
    [string]$AppDir  = "/opt/knk_haist",
    [string]$Repo    = "https://github.com/top00151-commits/knk-haist-works.git",
    [string]$Program = "knk-works",
    [int]$HealthPort = 8081,
    [switch]$Inspect,
    [switch]$Start,         # supervisord 켜고 knk-works 만 기동(WORK 전용)
    [int]$SetPort = 0,      # >0 이면 knk-works uvicorn 을 --host 0.0.0.0 --port <SetPort> 로 변경(역프록시 일치용)
    [switch]$Look,          # 파일시스템/마운트 구조 읽기전용 조사(이동 전 경로 파악)
    [switch]$Stage,         # WORK(32201)서 /opt/knk_mail·knk_messenger 를 공유볼륨 /haist/_migrate 로 복사(원본보존)
    [switch]$PullMail,      # MAIL(32203)서 /haist/_migrate/knk_mail -> /opt/knk_mail (기존시 .bak)
    [switch]$PullMsg,       # MSG(32202)서 /haist/_migrate/knk_messenger -> /opt/knk_messenger (기존시 .bak)
    [switch]$MailInfo,      # MAIL 컨테이너의 KNK Mail 앱 실행정보(run.py·venv·python·포트) 읽기전용
    [switch]$StartMail,     # MAIL(32203)서 KNK Mail 을 0.0.0.0:5053 으로 detached 실행 + healthz
    [switch]$CleanMigrate   # 공유볼륨 staging(/haist/_migrate) 통째 삭제(35G 회수) — 메신저까지 검증 후 실행
)

$ErrorActionPreference = "Stop"
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")

function Invoke-Remote([string]$bash) {
    # 원격 bash 스크립트를 base64 로 전송 → 따옴표/괄호/한글 깨짐 없음
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ("  target: {0}@{1}:{2}   appdir: {3}" -f $User,$SshHost,$Port,$AppDir) -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

if ($Inspect) {
    $look = @"
set +e
echo "=== WHOAMI / HOST ==="
whoami; hostname
echo "=== DOCKER (present => maybe NAS host) ==="
if command -v docker >/dev/null 2>&1; then docker ps --format "{{.Names}} {{.Ports}}"; else echo "no docker (inside container)"; fi
echo "=== /opt ==="
ls -la /opt 2>/dev/null
echo "=== git / supervisorctl present? ==="
command -v git || echo "no git"
command -v supervisorctl || echo "no supervisorctl"
echo "=== supervisor status ==="
supervisorctl status 2>/dev/null || echo "(none)"
echo "=== app repo at $AppDir ==="
if [ -d "$AppDir/.git" ]; then cd "$AppDir"; git log --oneline -1; git remote -v; else echo "$AppDir/.git NOT FOUND"; fi
echo "=== env (sso/mail keys present?) ==="
[ -f "$AppDir/.env" ] && grep -E "KNK_SSO_SERVICE_KEY|KNK_MESSENGER_SSO_BASE|KNK_SSO_ISSUER|KNK_RUN_MAIL_FETCH|KNK_MAIL_PUBLIC_BASE" "$AppDir/.env" | sed "s/=.*/=<set>/" || echo "(.env not found or keys unset)"
"@
    Invoke-Remote $look
    Write-Host "`n[들여다보기 완료] 위 출력을 빅터에게 붙여주세요 — 배포 명령을 정확히 맞춥니다." -ForegroundColor Green
    return
}

if ($Look) {
    # 읽기전용 — 마운트/볼륨·후보 경로·기존 앱파일 위치 조사(이동 전 파악, 아무것도 안 바꿈)
    $looksh = @"
set +e
echo "=== hostname ==="; hostname
echo "=== / (root dirs) ==="; ls -la /
echo "=== df -h (mounts/volumes) ==="; df -h
echo "=== mount (haist/knk/volume) ==="; mount 2>/dev/null | grep -iE "haist|knk|volume"
echo "=== candidate dest/source paths ==="
for d in /haistMail /haistMail/opt /haistMail/opt/knkmail /haistMail/opt/knk_mail /haistMsg /haistWork /opt /opt/knk_mail /opt/knkmail /opt/knk_messenger /opt/knk_haist /volume1; do
  echo "--- `$d ---"; ls -la "`$d" 2>/dev/null | head -25
done
echo "[done]"
"@
    Invoke-Remote $looksh
    Write-Host "`n[조사 완료] 위 출력을 붙여주세요 — /haistMail 마운트와 기존 파일 위치를 보고 안전한 이동(복사→검증) 명령을 만듭니다." -ForegroundColor Green
    return
}

if ($CleanMigrate) {
    # 공유볼륨 staging 삭제(/haist/_migrate). 어느 컨테이너서 실행해도 /haist 공유라 동일 반영.
    #   ⚠ 앱은 각 컨테이너 /opt 에서 돌고 WORK 원본도 그대로라 이 삭제는 운영 무영향(전송용 임시 복사본만 제거).
    $cm = @"
set +e
echo "[before] /haist/_migrate:"; du -sh /haist/_migrate 2>/dev/null; ls -la /haist/_migrate 2>/dev/null
echo "[delete] rm -rf /haist/_migrate"
rm -rf /haist/_migrate
echo "[after]"; ls -la /haist/_migrate 2>/dev/null || echo "  -> /haist/_migrate 삭제 완료(없음)"
echo "[free]"; df -h /haist 2>/dev/null
echo "[done]"
"@
    Invoke-Remote $cm
    Write-Host "`n[staging 삭제 완료] 운영 무영향(앱은 /opt 에서 가동·WORK 원본 보존). df 로 회수 확인." -ForegroundColor Green
    return
}

if ($StartMail) {
    # MAIL 컨테이너: KNK Mail(독립 uvicorn 앱)을 0.0.0.0:5053 으로 detached 실행(supervisor 없어 nohup/setsid)
    $sm = @"
set +e
cd /opt/knk_mail || { echo "ERROR: /opt/knk_mail 없음"; exit 1; }
mkdir -p logs
if curl -fsS -o /dev/null http://127.0.0.1:5053/healthz 2>/dev/null; then
  echo "[already] 5053 이미 응답 — 중복기동 생략"
else
  echo "[start] KNK Mail -> 0.0.0.0:5053 (detached)"
  KNK_MAIL_HOST=0.0.0.0 KNK_MAIL_PORT=5053 setsid nohup /opt/knk_mail/.venv/bin/python /opt/knk_mail/run.py > /opt/knk_mail/logs/run_5053.log 2>&1 < /dev/null &
  sleep 5
fi
echo "[healthz]"; curl -s -o /dev/null -w "  127.0.0.1:5053/healthz -> HTTP %{http_code}\n" http://127.0.0.1:5053/healthz
echo "[proc]"; ps aux 2>/dev/null | grep -E "run.py|5053" | grep -v grep | head
echo "[log tail]"; tail -25 /opt/knk_mail/logs/run_5053.log
echo "[done]"
"@
    Invoke-Remote $sm
    Write-Host "`n[KNK Mail 기동 시도] healthz 200/JSON 이면 OK. 출력 붙여주시면 kmail.knknara.co.kr 확인합니다." -ForegroundColor Green
    return
}

if ($MailInfo) {
    # MAIL 컨테이너의 KNK Mail 앱이 실행 가능한지(복사된 venv/python·실행포트) 읽기전용 점검
    $mi = @"
set +e
echo "=== run.py ==="; cat /opt/knk_mail/run.py 2>/dev/null
echo "=== README_RUN (앞부분) ==="; head -30 /opt/knk_mail/README_RUN.md 2>/dev/null
echo "=== requirements ==="; cat /opt/knk_mail/requirements.txt 2>/dev/null
echo "=== copied venv python ==="; /opt/knk_mail/.venv/bin/python --version 2>&1; ls -la /opt/knk_mail/.venv/bin/python* 2>/dev/null
echo "=== system python/supervisor/git ==="; which python3 python3.11 python3.12 supervisorctl git 2>/dev/null; python3 --version 2>&1
echo "=== port/uvicorn hints ==="; grep -rsnE "port|PORT|uvicorn|host|5050|5053" /opt/knk_mail/run.py /opt/knk_mail/app 2>/dev/null | grep -iE "port|uvicorn|host" | head -20
echo "=== supervisor confs (있나) ==="; ls -la /etc/supervisor/conf.d/ 2>/dev/null || echo "(no supervisor)"
echo "[done]"
"@
    Invoke-Remote $mi
    Write-Host "`n[KNK Mail 점검 완료] 출력을 붙여주세요 — 5053 기동 방법(venv 그대로/재설치)을 정합니다." -ForegroundColor Green
    return
}

if ($Stage) {
    # WORK 컨테이너(32201): /opt/knk_mail·knk_messenger 를 공유 NAS 볼륨 /haist/_migrate 로 복사(원본 /opt 보존)
    $stagesh = @"
set -e
mkdir -p /haist/_migrate
for d in knk_mail knk_messenger; do
  if [ -d "/opt/`$d" ]; then
    echo "[stage] /opt/`$d -> /haist/_migrate/`$d"
    rm -rf "/haist/_migrate/`$d"
    cp -a "/opt/`$d" "/haist/_migrate/`$d"
  else
    echo "[skip] /opt/`$d 없음"
  fi
done
echo "[sizes] staged vs source:"
du -sh /haist/_migrate/knk_mail /haist/_migrate/knk_messenger /opt/knk_mail /opt/knk_messenger 2>/dev/null
echo "[done] 원본(/opt)은 그대로. 공유볼륨에 staging 완료."
"@
    Invoke-Remote $stagesh
    Write-Host "`n[staging 완료] 크기 같은지 확인 후, MAIL=-PullMail / MSG=-PullMsg 로 받으세요." -ForegroundColor Green
    return
}

if ($PullMail) {
    $pm = @"
set -e
SRC=/haist/_migrate/knk_mail
[ -d "`$SRC" ] || { echo "ERROR: `$SRC 없음 - 먼저 WORK(32201)서 -Stage 실행"; exit 1; }
if [ -e /opt/knk_mail ] && [ -n "`$(ls -A /opt/knk_mail 2>/dev/null)" ]; then
  B=/opt/knk_mail.bak.`$(date +%s); echo "[backup] 기존 /opt/knk_mail -> `$B"; mv /opt/knk_mail "`$B"
fi
echo "[copy] `$SRC -> /opt/knk_mail"
cp -a "`$SRC" /opt/knk_mail
echo "[verify]"; ls -la /opt/knk_mail | head -20; du -sh /opt/knk_mail "`$SRC"
echo "[done]"
"@
    Invoke-Remote $pm
    Write-Host "`n[MAIL 복사 완료] 크기·목록 확인. (실행 런타임=python/supervisor 는 별도)" -ForegroundColor Green
    return
}

if ($PullMsg) {
    $pg = @"
set -e
SRC=/haist/_migrate/knk_messenger
[ -d "`$SRC" ] || { echo "ERROR: `$SRC 없음 - 먼저 WORK(32201)서 -Stage 실행"; exit 1; }
if [ -e /opt/knk_messenger ] && [ -n "`$(ls -A /opt/knk_messenger 2>/dev/null)" ]; then
  B=/opt/knk_messenger.bak.`$(date +%s); echo "[backup] 기존 /opt/knk_messenger -> `$B"; mv /opt/knk_messenger "`$B"
fi
echo "[copy] `$SRC -> /opt/knk_messenger"
cp -a "`$SRC" /opt/knk_messenger
echo "[verify]"; ls -la /opt/knk_messenger | head -20; du -sh /opt/knk_messenger "`$SRC"
echo "[done]"
"@
    Invoke-Remote $pg
    Write-Host "`n[MSG 복사 완료] 크기·목록 확인. (메신저 기동/설정은 전산/메신저)" -ForegroundColor Green
    return
}

if ($Start) {
    # WORK 컨테이너 기동: supervisord 켜고 knk-works 만(메신저·메일은 각자 컨테이너 몫 → 여기선 끔)
    $startsh = @"
set +e
SC=`$(ls /etc/supervisord.conf /etc/supervisor/supervisord.conf 2>/dev/null | head -1)
echo "supervisord.conf = `$SC"
if supervisorctl status >/dev/null 2>&1; then
  echo "supervisord already running"
else
  echo "starting supervisord ..."
  supervisord -c "`$SC"
  sleep 3
fi
echo "[WORK container: start knk-works only]"
supervisorctl start knk-works
echo "[stop messenger/mail here - they run in their own containers]"
supervisorctl stop knk-messenger knk-mail 2>/dev/null
sleep 2
supervisorctl status
echo "healthcheck:"
curl -fsS -o /dev/null -w "internal /login -> HTTP %{http_code}\n" http://127.0.0.1:$HealthPort/login || echo "  no response - tail -50 $AppDir/logs/uvicorn-error.log"
echo "[done]"
"@
    Invoke-Remote $startsh
    Write-Host "`n[기동 시도 완료] status 가 knk-works RUNNING 이면 OK. 출력을 붙여주세요." -ForegroundColor Green
    return
}

if ($SetPort -gt 0) {
    # knk-works uvicorn 을 --host 0.0.0.0 --port <SetPort> 로 (역프록시 localhost:<SetPort> 와 일치, 호스트에서 닿게)
    $setp = @"
set +e
W=/opt/knk_haist/.venv/bin/run_knk_works.sh
echo "=== wrapper before (no secrets - it just sources .env) ==="; cat "`$W"
cp "`$W" "`$W.bak.portchg.`$(date +%s)"
sed -i "s/--host 127.0.0.1/--host 0.0.0.0/" "`$W"
sed -i -E "s/--port[ =][0-9]+/--port $SetPort/" "`$W"
sed -i "s/--forwarded-allow-ips=127.0.0.1/--forwarded-allow-ips=*/" "`$W"
echo "=== wrapper after ==="; cat "`$W"
echo "=== restart ==="
supervisorctl restart knk-works
sleep 3; supervisorctl status knk-works
curl -fsS -o /dev/null -w "internal 127.0.0.1:$SetPort/login -> HTTP %{http_code}\n" http://127.0.0.1:$SetPort/login || echo "  no response on $SetPort"
echo "[done]"
"@
    Invoke-Remote $setp
    Write-Host "`n[포트 변경 완료] before/after 와 status 를 붙여주세요. 그 뒤 works.knknara.co.kr 를 빅터가 확인합니다." -ForegroundColor Green
    return
}

$deploy = @"
APP="$AppDir"
set -e
if [ -d "`$APP/.git" ]; then
  echo "[1] git pull (update code)"
  cd "`$APP" && git pull --ff-only
else
  echo "[1] git clone (first time)"
  git clone "$Repo" "`$APP"
  cd "`$APP"
fi
git -C "`$APP" log --oneline -1
set +e
echo "[2] app start/restart"
if supervisorctl status >/dev/null 2>&1; then
  supervisorctl restart "$Program" 2>/dev/null || supervisorctl restart all
  sleep 2; supervisorctl status
else
  echo "  !! supervisord NOT running in this container (app down)."
  echo "  --- supervisor configs present ---"
  ls -la /etc/supervisor/conf.d/ 2>/dev/null || echo "    (no /etc/supervisor/conf.d)"
  echo "  --- knk-works / uvicorn program def (how the app should start) ---"
  grep -Rsn "knk-works|uvicorn|run.py|8081|command=" /etc/supervisor* 2>/dev/null | head -30
  echo "  --- container entrypoint hint ---"
  ls -la /opt/knk_haist/deploy/*.sh 2>/dev/null | head
  echo "  (supervisord 미기동 — 위 출력을 빅터에게 주면 정확한 기동 명령을 드립니다)"
fi
echo "[3] healthcheck"
curl -fsS -o /dev/null -w "internal /login -> HTTP %{http_code}\n" http://127.0.0.1:$HealthPort/login || echo "  no internal response (app not running yet)"
echo "[done]"
"@
Invoke-Remote $deploy
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  완료 - 브라우저에서 https://works.knknara.co.kr 확인" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
