# ============================================================
# KNK Eum MAIL - local -> NAS (KNKHAIST container) deploy
# Same pattern as WORKS(knk-works): /opt/knk_mail + venv + supervisor(knk-mail, 8201)
# Messenger/WORKS untouched - fully isolated. Rollback: rm -rf /opt/knk_mail + remove supervisor conf.
# (ASCII-only on purpose: PowerShell 5.1 mangles non-BOM UTF-8 Korean.)
# ------------------------------------------------------------
# Usage: from 15_KNK_Mail  .\deploy\sync_to_nas.ps1
#   -CodeOnly   : upload + venv + import check only (no service register)
#   -NoRestart  : register supervisor but do not start
# Conn: env KNK_NAS_HOST/PORT/USER/PASSWORD (same as messenger deploy)
# ============================================================
[CmdletBinding()]
param(
    [string]$NasHost = $env:KNK_NAS_HOST,
    [int]$NasPort    = $(if ($env:KNK_NAS_PORT) { [int]$env:KNK_NAS_PORT } else { 22 }),
    [string]$NasUser = $(if ($env:KNK_NAS_USER) { $env:KNK_NAS_USER } else { "root" }),
    [string]$NasPass = $env:KNK_NAS_PASSWORD,
    [string]$AppDir  = "/opt/knk_mail",
    [int]$Port       = 8201,
    [switch]$CodeOnly,
    [switch]$NoRestart
)
$ErrorActionPreference = "Stop"
function Info($m){ Write-Host "[*] $m" -ForegroundColor Cyan }
function Ok($m){ Write-Host "[OK] $m" -ForegroundColor Green }
function Die($m){ Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }
if(-not $NasHost){ Die "KNK_NAS_HOST missing" }
if(-not $NasPass){ Die "KNK_NAS_PASSWORD missing" }

$ProjRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjRoot

$ap = Join-Path $env:TEMP ("knk_ap_"+[guid]::NewGuid().ToString('N')+".cmd")
"@echo off`r`necho $NasPass" | Set-Content -Encoding ASCII $ap
$env:DISPLAY=":0"; $env:SSH_ASKPASS=$ap; $env:SSH_ASKPASS_REQUIRE="force"
$sshOpts = @("-o","StrictHostKeyChecking=accept-new","-o","ConnectTimeout=15","-p","$NasPort")

function Ssh-Cmd([string]$Bash){
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Bash))
    $remote = "echo $b64 | base64 -d | bash"
    $o = & ssh -n @sshOpts "$NasUser@$NasHost" $remote
    return ($o -join "`n")
}
function Ssh-Upload([string]$LocalFile,[string]$RemotePath){
    $line = "ssh " + ($sshOpts -join " ") + " $NasUser@$NasHost `"cat > $RemotePath`" < `"$LocalFile`""
    $tmpO = "$env:TEMP\u_$([guid]::NewGuid().ToString('N')).log"
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "$line > `"$tmpO`" 2>&1" -NoNewWindow -Wait | Out-Null
    Remove-Item $tmpO -ErrorAction SilentlyContinue
}

try {
    Info "1/6 packing (app, run.py, requirements.txt, deploy)..."
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $tar = Join-Path $env:TEMP "knkmail_$stamp.tar.gz"
    $pyPack = @"
import tarfile, os
out = r'''$tar'''
os.chdir(r'''$ProjRoot''')
items = ['app','run.py','requirements.txt','deploy']
def excl(ti):
    n = ti.name
    if '__pycache__' in n or n.endswith('.pyc'): return None
    if n.endswith('/.env') or n == 'deploy/.env': return None
    return ti
with tarfile.open(out,'w:gz') as tf:
    for it in items:
        if os.path.exists(it): tf.add(it, filter=excl)
print('PACK_OK')
"@
    $r = & python -c $pyPack
    if($r -notmatch "PACK_OK" -or -not (Test-Path $tar)){ Die "pack failed: $r" }
    $b64 = "$tar.b64"
    [IO.File]::WriteAllText($b64, [Convert]::ToBase64String([IO.File]::ReadAllBytes($tar)), [Text.UTF8Encoding]::new($false))
    Ok ("  archive {0} KB" -f [math]::Round((Get-Item $tar).Length/1KB,1))

    Info "2/6 upload + extract -> $AppDir ..."
    Ssh-Upload $b64 "/tmp/knkmail.tar.gz.b64"
    $ext = Ssh-Cmd "set -e; cd /tmp; base64 -d knkmail.tar.gz.b64 > knkmail.tar.gz; rm -f knkmail.tar.gz.b64; gzip -t knkmail.tar.gz && echo GZIP_OK; mkdir -p $AppDir; tar -xzf knkmail.tar.gz -C $AppDir; rm -f knkmail.tar.gz; mkdir -p $AppDir/data $AppDir/logs; echo NFILES=`$(find $AppDir -type f | wc -l); echo EXTRACT_DONE"
    Write-Host $ext -ForegroundColor Gray
    if($ext -notmatch "GZIP_OK" -or $ext -notmatch "EXTRACT_DONE"){ Die "extract failed" }
    Remove-Item $tar,$b64 -ErrorAction SilentlyContinue
    Ok "  uploaded"

    Info "3/6 venv + pip install (may take minutes)..."
    $venv = Ssh-Cmd "set -e; cd $AppDir; if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi; .venv/bin/pip install -q --upgrade pip; .venv/bin/pip install -q -r requirements.txt && echo PIP_OK; .venv/bin/python --version"
    Write-Host $venv -ForegroundColor Gray
    if($venv -notmatch "PIP_OK"){ Die "pip install failed - see log above" }
    Ok "  deps installed"

    Info "4/6 import check (Python 3.8 compat)..."
    $impCmd = @"
cd $AppDir
KNK_MAIL_DATA=$AppDir/data KNK_MAIL_DB=$AppDir/data/mail.db .venv/bin/python - <<'PYEOF' 2>&1
import app.main
print('IMPORT_OK routes=', len(app.main.app.routes))
PYEOF
"@
    $imp = Ssh-Cmd $impCmd
    Write-Host $imp -ForegroundColor Gray
    if($imp -notmatch "IMPORT_OK"){ Die "import failed (3.8 compat?) - see traceback above" }
    Ok "  app imports OK on 3.8"

    if($CodeOnly){ Ok "CODE-ONLY done (service not registered)"; return }

    Info "5/6 .env (shared keys from WORKS .env) + supervisor(knk-mail)..."
    $envSetup = @"
set -e
cd $AppDir
SRC=/opt/knk_haist/.env
get(){ grep -E "^`$1=" "`$SRC" 2>/dev/null | head -1 | cut -d= -f2-; }
SVC=`$(get KNK_SSO_SERVICE_KEY)
AIK=`$(get ANTHROPIC_API_KEY)
OAI=`$(get OPENAI_API_KEY)
# 세션키는 1회 생성 후 보존(재배포마다 바뀌면 로그인 풀림) — 기존 .env 값 재사용
SESS=`$(grep -E "^KNK_MAIL_SESSION_SECRET=" $AppDir/data/.env 2>/dev/null | head -1 | cut -d= -f2-)
[ -z "`$SESS" ] && SESS=`$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
cat > $AppDir/data/.env <<EOF
KNK_MAIL_DATA=$AppDir/data
KNK_MAIL_DB=$AppDir/data/mail.db
KNK_MAIL_PUBLIC_BASE=https://mail.knknara.co.kr
KNK_MAIL_HTTPS_ONLY=1
KNK_MAIL_PORT=$Port
KNK_MAIL_SESSION_SECRET=`$SESS
KNK_MAIL_SSO_AUDIENCE=knk-mail
KNK_MESSENGER_SSO_BASE=https://haist.knknara.co.kr/msg
KNK_SSO_SERVICE_KEY=`$SVC
ANTHROPIC_API_KEY=`$AIK
OPENAI_API_KEY=`$OAI
KNK_MAIL_DEV_LOGIN=0
EOF
chmod 600 $AppDir/data/.env
echo ENV_DONE service_key_set=`$( [ -n "`$SVC" ] && echo yes || echo no )
"@
    $envR = Ssh-Cmd $envSetup
    Write-Host $envR -ForegroundColor Gray

    # IMPORTANT: source data/.env so KNK_MAIL_* (SESSION_SECRET/PUBLIC_BASE/HTTPS_ONLY/keys) reach the process.
    # supervisord does NOT auto-source .env and the app has no load_dotenv -> wrap with sh that sources it, then exec uvicorn.
    $supConf = @"
[program:knk-mail]
command=/bin/sh -c 'set -a; . $AppDir/data/.env; exec $AppDir/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $Port --workers 2 --proxy-headers --forwarded-allow-ips=127.0.0.1'
directory=$AppDir
user=root
autostart=true
autorestart=true
startsecs=8
stopasgroup=true
killasgroup=true
environment=PATH="$AppDir/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",PYTHONUNBUFFERED="1",PYTHONUTF8="1",TZ="Asia/Seoul",LANG="C.UTF-8",LC_ALL="C.UTF-8"
stdout_logfile=$AppDir/logs/uvicorn.log
stderr_logfile=$AppDir/logs/uvicorn-error.log
stdout_logfile_maxbytes=20MB
stderr_logfile_maxbytes=20MB
"@
    $b64sup = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($supConf))
    $reg = Ssh-Cmd "set -e; mkdir -p $AppDir/logs; echo $b64sup | base64 -d > /etc/supervisor/conf.d/knk-mail.conf; supervisorctl reread; supervisorctl update; echo REG_DONE"
    Write-Host $reg -ForegroundColor Gray

    if($NoRestart){ Ok "registered (start skipped)"; return }

    Info "6/6 start + healthcheck..."
    $start = Ssh-Cmd "supervisorctl start knk-mail 2>&1; sleep 4; supervisorctl status knk-mail; echo HC=`$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$Port/healthz); curl -s http://127.0.0.1:$Port/healthz; echo"
    Write-Host $start -ForegroundColor Gray
    if($start -match "HC=200"){ Ok "mail app LIVE internally (127.0.0.1:$Port) - external needs DSM reverse proxy" }
    else { Write-Host "[warn] healthcheck not 200 - check log: tail $AppDir/logs/uvicorn-error.log" -ForegroundColor Yellow }
}
finally {
    Set-Content -Path $ap -Value "x" -Encoding ASCII
    $env:SSH_ASKPASS=""; $env:SSH_ASKPASS_REQUIRE=""
}
