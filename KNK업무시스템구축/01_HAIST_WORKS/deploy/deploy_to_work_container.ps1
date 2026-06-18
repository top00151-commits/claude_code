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
    [int]$SetPort = 0       # >0 이면 knk-works uvicorn 을 --host 0.0.0.0 --port <SetPort> 로 변경(역프록시 일치용)
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
