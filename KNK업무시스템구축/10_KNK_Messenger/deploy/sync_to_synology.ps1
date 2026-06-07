# ============================================================
# KNK Messenger - 로컬(Windows) -> Synology NAS Docker 동기화
# ============================================================
# 사용 시나리오:
#   1) 빅터/대표가 로컬에서 코드 수정
#   2) 이 스크립트 1번 실행
#   3) 변경된 파일 NAS로 업로드 + 컨테이너 재시작 + 헬스체크
#   4) https://msg.knknara.co.kr 에서 즉시 확인
#
# 첫 사용 전 환경변수 1회 설정 (PowerShell):
#   [Environment]::SetEnvironmentVariable("KNK_NAS_HOST", "o.knknara.co.kr", "User")
#   [Environment]::SetEnvironmentVariable("KNK_NAS_PORT", "31201", "User")
#   [Environment]::SetEnvironmentVariable("KNK_NAS_USER", "root", "User")
#   [Environment]::SetEnvironmentVariable("KNK_NAS_PATH", "/opt/knk_messenger", "User")
#   (PowerShell 새 창)
#
# 2026-05-11 실배포 환경:
#   SSH: o.knknara.co.kr:31201 root
#   설치 경로: /opt/knk_messenger
#   서비스 관리: supervisorctl (systemd 없음)
#   적용: docker compose 대신 supervisorctl restart knk-messenger
#
# (선택) SSH 키 등록 — 비밀번호 없이 접속:
#   ssh-keygen -t ed25519 -f $HOME\.ssh\knk_synology
#   type $HOME\.ssh\knk_synology.pub | ssh admin@<NAS> "cat >> ~/.ssh/authorized_keys"
#   [Environment]::SetEnvironmentVariable("KNK_NAS_KEY", "$HOME\.ssh\knk_synology", "User")
#
# 실행:
#   cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\10_KNK_Messenger"
#   .\deploy\sync_to_synology.ps1
#
# 옵션:
#   -Rebuild         requirements 변경 시 (이미지 재빌드)
#   -SkipRestart     파일만 동기화하고 컨테이너 재시작 안 함
# ============================================================

[CmdletBinding()]
param(
    [string]$NasHost = $env:KNK_NAS_HOST,
    [int]$NasPort    = $(if ($env:KNK_NAS_PORT) { [int]$env:KNK_NAS_PORT } else { 22 }),
    [string]$NasUser = $(if ($env:KNK_NAS_USER) { $env:KNK_NAS_USER } else { "root" }),
    [string]$NasPath = $(if ($env:KNK_NAS_PATH) { $env:KNK_NAS_PATH } else { "/opt/knk_messenger" }),
    [string]$KeyFile = $env:KNK_NAS_KEY,
    [string]$Password = $env:KNK_NAS_PASSWORD,  # 평문 자제 — SSH 키 권장
    [switch]$Restart,
    [switch]$SkipRestart,
    # 하위 경로 배포: 예) -SetBasePath /msg  →  서버 .env 의 KNK_MSG_BASE_PATH 설정
    #                  -SetBasePath ""(빈값)  →  KNK_MSG_BASE_PATH 제거(루트 / 복귀)
    [string]$SetBasePath = $null,
    # 테스트용 '빅터' 사용자 + 전체 방 가입 (멱등). deploy/add_victor.py 실행.
    [switch]$AddVictor,
    # 빅터로 테스트 메시지 전송. 형식:
    #   -VictorSend "all" "메시지"      → 빅터 속한 모든 방에 일괄
    #   -VictorSend "4" "메시지"        → 방 ID 4번에
    #   -VictorSend "all"               → 모든 방에 기본 메시지
    [string]$VictorSend = $null,
    [string]$VictorMessage = $null,
    # VAPID 키 재생성 + 옛 push 구독 모두 삭제 — 키 손상 시 사용.
    # 사용자는 다음 번 PWA 열 때 새 키로 자동 재구독.
    [switch]$RegenerateVapid,
    # 읽기 전용 진단 — 업로드·재시작 없이 서버 상태(메모리·OOM·디스크·supervisord/gunicorn 로그·설정)만 수집. (대표 지시 2026-05-25 장애 원인조사)
    [switch]$Diag,
    # 내부 보강 — supervisor 설정에서 nginx autostart=false→true. 실행 중 서비스 무중단(파일만 수정, reread/update 안 함). (대표 지시 2026-05-25)
    [switch]$HardenNginx,
    # 읽기 전용 — 특정 사용자(이름 일부)의 접속 세션·푸시 등록 현황 조회 (상태표시 진단용, 변경 없음). (대표 지시 2026-05-25)
    [string]$DbUser = $null
)

$ErrorActionPreference = "Stop"

function Fail($m) { Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }
function Info($m) { Write-Host "[*] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }

# Git bash(MSYS2)가 /opt/... 를 "C:/Program Files/Git/opt/..." 로 자동변환하는 현상 보정
# NasHost, NasPath 에서 Windows 드라이브 경로가 검출되면 원래 Unix 경로로 복원한다.
if ($NasPath -match '^[A-Za-z]:[/\\]') {
    # "C:/Program Files/Git/opt/knk_messenger" → "/opt/knk_messenger"
    $NasPath = '/' + ($NasPath -replace '^[A-Za-z]:[/\\].*?[Gg]it[/\\]', '' -replace '\\', '/')
    Write-Host "[info] NasPath git-bash 경로 변환 보정: $NasPath" -ForegroundColor DarkYellow
}

if (-not $NasHost) { Fail "KNK_NAS_HOST 환경변수 또는 -NasHost 인자 필요" }
if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    Fail "ssh 명령어 없음. Windows 10+ 'OpenSSH 클라이언트' 기능 설치 필요"
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# SSH 옵션 (포트 포함)
$sshOpts = @("-o", "StrictHostKeyChecking=accept-new", "-p", "$NasPort")
$scpOpts = @("-o", "StrictHostKeyChecking=accept-new", "-P", "$NasPort")
if ($KeyFile -and (Test-Path $KeyFile)) {
    $sshOpts += @("-i", $KeyFile)
    $scpOpts += @("-i", $KeyFile)
}

# 비밀번호 인증 모드 — SSH_ASKPASS 우회 (자동화)
$askpassEnv = @{}
if ($Password) {
    $askpassFile = Join-Path $env:TEMP "knk_askpass_$([guid]::NewGuid().ToString('N')).cmd"
    @"
@echo off
echo $Password
"@ | Set-Content -Encoding ASCII $askpassFile
    $askpassEnv["DISPLAY"] = ":0"
    $askpassEnv["SSH_ASKPASS"] = $askpassFile
    $askpassEnv["SSH_ASKPASS_REQUIRE"] = "force"
}

Write-Host ""
Write-Host "===============================================" -ForegroundColor Yellow
Write-Host "  KNK Messenger -> Synology Container Sync" -ForegroundColor Yellow
Write-Host "  NAS:    ${NasUser}@${NasHost}:${NasPort}  ->  ${NasPath}"
Write-Host "  Local:  $ProjectRoot"
Write-Host "  Mode:   $(if ($SkipRestart) {'SYNC ONLY'} else {'SYNC + RESTART (supervisorctl)'})"
Write-Host "===============================================" -ForegroundColor Yellow
Write-Host ""

# --- 1) tar로 압축 ---
Info "1/4 Packing files..."
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Tarball = Join-Path $env:TEMP "knk_synology_$Stamp.tar.gz"

# 컨테이너에 보낼 파일 — data/ backups/ .venv/ 제외
$Items = @(
    "requirements.txt",
    "app.py",
    "wsgi.py",
    "templates",
    "static",
    "deploy",
    "generate_icons.py",
    "generate_vapid.py",
    "seed_from_xlsx.py",
    "backup.py",
    "consent_doc.py"
)
$Existing = $Items | Where-Object { Test-Path $_ }

# Git for Windows tar.exe 는 Windows 드라이브 경로를 네트워크 주소로 오인 → Python tarfile 사용
# Python은 Windows/bash 양쪽에서 경로를 올바르게 처리함
$PyItems = ($Existing | ForEach-Object { "'$($_ -replace "'","\'")'" }) -join ","
$PyScript = @"
import tarfile, os, sys, fnmatch
out = sys.argv[1]
items = [x for x in sys.argv[2:]]
def excl(ti):
    if '__pycache__' in ti.name: return None
    if ti.name.endswith('.pyc'): return None
    return ti
with tarfile.open(out, 'w:gz') as tf:
    for item in items:
        if os.path.exists(item):
            tf.add(item, filter=excl)
print('OK', out)
"@
$PyResult = & python -c $PyScript $Tarball @Existing 2>&1
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Tarball)) {
    Write-Host "Python output: $PyResult" -ForegroundColor Yellow
    Fail "tarball 생성 실패 (python tarfile)"
}

$TarSize = [math]::Round((Get-Item $Tarball).Length / 1KB, 1)
Ok "  archive: $TarSize KB"

# --- 2) NAS로 업로드 + 풀기 ---
Info "2/4 Uploading + extracting to NAS..."

# Synology 컨테이너의 sshd 가 로그인 시 stderr 메시지를 찍어 scp 깨짐 — base64 stream 우회
# .NET 직접 base64 encoding (UTF8 BOM 없음) — certutil 방식은 PowerShell 5.1 의 Set-Content 가 BOM 흘림
$b64File = Join-Path $env:TEMP "knk_synology_$Stamp.tar.gz.b64"
$rawBytes = [System.IO.File]::ReadAllBytes($Tarball)
$b64Str = [Convert]::ToBase64String($rawBytes)
[System.IO.File]::WriteAllText($b64File, $b64Str, [System.Text.UTF8Encoding]::new($false))

# ============================================================
# SSH 호출 헬퍼 — bash 의존 제거, Start-Process 로 stdin/stdout 리다이렉트
#   - 패스워드 인증 시 SSH_ASKPASS 환경변수 전달 (자동 입력)
#   - stdin/stdout 리다이렉트로 OpenSSH 가 tty 없다고 판단 → askpass 사용
# ============================================================
function Invoke-Ssh {
    param(
        [string]$Cmd,
        [string]$StdinFile = $null,
        [string]$OutFile = $null
    )
    # stdin 없는 명령: ssh -n 플래그로 stdin 을 /dev/null 로 강제 (PowerShell 의 BOM 주입 차단)
    # stdin 있는 명령: cmd.exe < 리다이렉트로 파일 직접 입력 (PowerShell stdin 우회)
    if (-not $StdinFile) {
        # ssh -n: stdin을 nul로 강제. PowerShell 이 stdin 으로 BOM 주는 거 무력화.
        $opts = $sshOpts + @("-n")
        $remoteArg = '"' + ($Cmd -replace '"', '\"') + '"'
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "ssh.exe"
        $psi.Arguments = ($opts -join " ") + " ${NasUser}@${NasHost} $remoteArg"
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        if ($Password) {
            $psi.EnvironmentVariables["DISPLAY"] = ":0"
            $psi.EnvironmentVariables["SSH_ASKPASS"] = $askpassEnv["SSH_ASKPASS"]
            $psi.EnvironmentVariables["SSH_ASKPASS_REQUIRE"] = "force"
        }
        $proc = [System.Diagnostics.Process]::Start($psi)
        $stdout = $proc.StandardOutput.ReadToEnd()
        $stderr = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()
        if ($OutFile) { Set-Content -Path $OutFile -Value $stdout -NoNewline }
        $script:_LastSshOut = $stdout
        $script:_LastSshErr = $stderr
        return $proc.ExitCode
    }
    # StdinFile 있는 경우: cmd.exe 의 < 리다이렉트 사용 (PowerShell stdin 완전 우회)
    # SSH_ASKPASS 환경변수는 현재 PowerShell process 에서 cmd 가 상속
    $env:DISPLAY = ":0"
    $env:SSH_ASKPASS = $askpassEnv["SSH_ASKPASS"]
    $env:SSH_ASKPASS_REQUIRE = "force"
    $remoteArg = '"' + ($Cmd -replace '"', '\"') + '"'
    $sshLine = "ssh.exe " + ($sshOpts -join " ") + " ${NasUser}@${NasHost} $remoteArg"
    # cmd.exe 의 < 로 파일을 stdin 으로 — 순수 raw bytes, BOM 없음
    $cmdLine = "$sshLine < `"$StdinFile`""
    $tmpOut = "$env:TEMP\knk_ssh_out_$([guid]::NewGuid().ToString('N')).log"
    $tmpErr = "$env:TEMP\knk_ssh_err_$([guid]::NewGuid().ToString('N')).log"
    # cmd /c "ssh ... < file > out 2> err"
    $fullCmd = "$sshLine < `"$StdinFile`" > `"$tmpOut`" 2> `"$tmpErr`""
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $fullCmd -NoNewWindow -Wait -PassThru
    $script:_LastSshOut = if (Test-Path $tmpOut) { Get-Content $tmpOut -Raw } else { "" }
    $script:_LastSshErr = if (Test-Path $tmpErr) { Get-Content $tmpErr -Raw } else { "" }
    Remove-Item $tmpOut, $tmpErr -ErrorAction SilentlyContinue
    return $proc.ExitCode
}

# ============================================================
# 읽기 전용 진단 모드 (-Diag) — 서버 변경 없이 장애 원인 단서만 수집 후 종료
#   (대표 지시 2026-05-25: supervisord 다운 장애 원인 철저 규명)
# ============================================================
if ($Diag) {
    Info "DIAG (read-only) — 서버 상태 수집 중..."
    $diagCmd = @'
echo ===UPTIME===; uptime 2>&1; awk '{print "proc_uptime_sec="$1}' /proc/uptime 2>&1
echo ===PID1===; cat /proc/1/comm 2>&1; tr "\0" " " < /proc/1/cmdline 2>&1; echo
echo ===MEM_MB===; free -m 2>&1
echo ===CGROUP_MEM===; for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.events /sys/fs/cgroup/memory/memory.limit_in_bytes /sys/fs/cgroup/memory/memory.usage_in_bytes /sys/fs/cgroup/memory/memory.failcnt; do [ -e "$f" ] && echo "$f:" && cat "$f" 2>&1; done
echo ===OOM_DMESG===; dmesg 2>/dev/null | grep -iE 'oom|killed process|out of memory' | tail -20 || echo '(dmesg 권한없음/없음)'
echo ===DISK===; df -h 2>&1
echo ===PROCS===; ps aux 2>&1 | grep -E 'supervisor|gunicorn|nginx|python' | grep -v grep
echo ===SUPERVISORD_TAIL===; tail -80 /var/log/supervisor/supervisord.log 2>&1 || echo '(no supervisord.log)'
echo ===SUPERVISOR_CONF===; cat /etc/supervisor/supervisord.conf 2>&1
echo ===SUPERVISOR_CONFD===; cat /etc/supervisor/conf.d/*.conf 2>&1
echo ===GUNICORN_ERR_TAIL===; tail -80 /opt/knk_messenger/logs/gunicorn.err.log 2>&1 || echo '(no err log)'
echo ===GUNICORN_OUT_TAIL===; tail -40 /opt/knk_messenger/logs/gunicorn.log 2>&1 || echo '(no out log)'
echo ===RUN_GUNICORN_SH===; cat /opt/knk_messenger/run_gunicorn.sh 2>&1
echo ===DIAG_DONE===
'@
    Invoke-Ssh -Cmd $diagCmd | Out-Null
    Write-Host $_LastSshOut
    if ($_LastSshErr) { Write-Host "--- stderr ---" -ForegroundColor DarkYellow; Write-Host $_LastSshErr -ForegroundColor DarkGray }
    if ($askpassFile -and (Test-Path $askpassFile)) { Remove-Item $askpassFile -ErrorAction SilentlyContinue }
    Ok "DIAG 완료"
    exit 0
}

# ============================================================
# 내부 보강 모드 (-HardenNginx) — nginx autostart=false→true (무중단: 파일만 수정)
#   실행 중인 nginx 는 건드리지 않고, 다음 supervisord 기동부터 nginx 가 자동 시작되게 한다.
#   → supervisord 가 죽었다 살아날 때 nginx 까지 자동 복구 (수동 start 불필요). (대표 지시 2026-05-25)
# ============================================================
if ($HardenNginx) {
    Info "HARDEN — nginx autostart=true (무중단: 설정 파일만 수정, reread/update 안 함)"
    $hc = @'
CONF=/etc/supervisor/conf.d/knk-messenger.conf
echo ===BEFORE===; grep -n autostart $CONF
cp $CONF ${CONF}.bak.$(date +%s) && echo BACKUP_OK
sed -i 's/^autostart=false/autostart=true/' $CONF
echo ===AFTER===; grep -n autostart $CONF
echo ===HEALTHZ===; curl -fsS --max-time 8 http://127.0.0.1:5050/healthz && echo HEALTHZ_OK || echo HEALTHZ_FAIL
echo ===STATUS===; supervisorctl status 2>&1
echo HARDEN_DONE
'@
    Invoke-Ssh -Cmd $hc | Out-Null
    Write-Host $_LastSshOut
    if ($_LastSshErr) { Write-Host "--- stderr ---" -ForegroundColor DarkYellow; Write-Host $_LastSshErr -ForegroundColor DarkGray }
    if ($askpassFile -and (Test-Path $askpassFile)) { Remove-Item $askpassFile -ErrorAction SilentlyContinue }
    Ok "HARDEN 완료"
    exit 0
}

# ============================================================
# 읽기 전용 — 사용자 접속/푸시 진단 (-DbUser "<이름일부>")
#   서버 DB(messenger.db)를 read-only(mode=ro)로 열어 active_sessions·push_subscriptions 조회.
#   민감정보(토큰·암호키·푸시 endpoint)는 SELECT 하지 않음. (대표 지시 2026-05-25)
# ============================================================
if ($DbUser) {
    Info "DBUSER (read-only) — '$DbUser' 접속/푸시 현황 조회 중..."
    $pyTmp = Join-Path $env:TEMP "knk_dbuser_$([guid]::NewGuid().ToString('N')).py"
    $nameLit = $DbUser.Replace('\','\\').Replace('"','\"')
    $pyContent = @"
import sqlite3
NAME = "$nameLit"
db = sqlite3.connect("file:/opt/knk_messenger/data/messenger.db?mode=ro", uri=True)
db.row_factory = sqlite3.Row
us = db.execute("SELECT id,username,display_name,role,COALESCE(is_guest,0) g FROM users WHERE display_name LIKE ?", ('%'+NAME+'%',)).fetchall()
print("=== matched users:", len(us), "===")
for u in us:
    print("  id=%s username=%s name=%s role=%s guest=%s" % (u['id'], u['username'], u['display_name'], u['role'], u['g']))
for u in us:
    print("\n=== %s (id=%s) ===" % (u['display_name'], u['id']))
    sess = db.execute("SELECT device_type,ip,substr(user_agent,1,45) ua,created_at FROM active_sessions WHERE user_id=?", (u['id'],)).fetchall()
    print("  active_sessions:", len(sess))
    for s in sess:
        print("    [%s] ip=%s created=%s ua=%s" % (s['device_type'], s['ip'], s['created_at'], s['ua']))
    push = db.execute("SELECT substr(user_agent,1,55) ua,created_at,last_used FROM push_subscriptions WHERE user_id=?", (u['id'],)).fetchall()
    print("  push_subscriptions:", len(push))
    for p in push:
        print("    created=%s last_used=%s ua=%s" % (p['created_at'], p['last_used'], p['ua']))
print("\n=== DBUSER_DONE ===")
"@
    [IO.File]::WriteAllText($pyTmp, $pyContent, (New-Object System.Text.UTF8Encoding $false))
    Invoke-Ssh -Cmd "python3 -" -StdinFile $pyTmp | Out-Null
    Write-Host $_LastSshOut
    if ($_LastSshErr) { Write-Host "--- stderr ---" -ForegroundColor DarkYellow; Write-Host $_LastSshErr -ForegroundColor DarkGray }
    Remove-Item $pyTmp -ErrorAction SilentlyContinue
    if ($askpassFile -and (Test-Path $askpassFile)) { Remove-Item $askpassFile -ErrorAction SilentlyContinue }
    Ok "DBUSER 완료"
    exit 0
}

# 업로드 — base64 stream 을 stdin 으로 전달
$b64Len = (Get-Item $b64File).Length
Info "  b64 size (local): $b64Len bytes"
$code = Invoke-Ssh -Cmd "cat > /tmp/knk_sync.tar.gz.b64" -StdinFile $b64File
Remove-Item $b64File -ErrorAction SilentlyContinue
if ($code -ne 0) {
    Write-Host "stderr: $_LastSshErr" -ForegroundColor Yellow
    Fail "업로드 실패 (host/port/user/pw 또는 키 점검). code=$code"
}

# 업로드 무결성 검증 — 원격 b64 크기가 로컬과 일치하는지 (sshd 배너 오염 대비 마커 사용)
$code = Invoke-Ssh -Cmd "echo SZ_START; wc -c < /tmp/knk_sync.tar.gz.b64; echo SZ_END"
$remoteB64Len = -1
if ($_LastSshOut -match "SZ_START\s*(\d+)\s*SZ_END") { $remoteB64Len = [int]$matches[1] }
Info "  b64 size (remote): $remoteB64Len bytes"
if ($remoteB64Len -ne $b64Len) {
    Fail "업로드 손상 — 로컬 $b64Len bytes != 원격 $remoteB64Len bytes. stdin 파이프 truncation."
}
Ok "  upload integrity OK ($b64Len bytes)"

# 원격에서 디코드 + 풀기 — 각 단계 상태를 마커로 명시 보고 (; echo DONE 무음실패 제거)
$ExtractCmd = "cd /tmp && base64 -d knk_sync.tar.gz.b64 > knk_sync.tar.gz && rm knk_sync.tar.gz.b64 && (gzip -t knk_sync.tar.gz && echo GZIP_OK || echo GZIP_BAD) && echo NFILES=`$(tar -tzf knk_sync.tar.gz | wc -l) && mkdir -p '$NasPath' && cd '$NasPath' && (tar -xzf /tmp/knk_sync.tar.gz && echo TAR_OK || echo TAR_FAIL) && rm /tmp/knk_sync.tar.gz && chmod +x deploy/*.sh 2>/dev/null; echo EXTRACT_END"
$code = Invoke-Ssh -Cmd $ExtractCmd
Write-Host $_LastSshOut -ForegroundColor Gray
if ($_LastSshOut -notmatch "GZIP_OK") {
    Write-Host "stderr: $_LastSshErr" -ForegroundColor Yellow
    Fail "원격 gzip 무결성 실패 — 업로드된 tar.gz 손상."
}
if ($_LastSshOut -notmatch "TAR_OK") {
    Write-Host "stderr: $_LastSshErr" -ForegroundColor Yellow
    Fail "원격 tar 추출 실패."
}
Ok "  extracted to $NasPath"

# --- 2.1) 배포 검증 — app.py 가 실제로 갱신됐는지 + 환경 진단 ---
# (과거 대용량 파일 무음 sync 실패 사례 → 마커 grep 으로 확인)
Info "2.1/4 Verifying deployed app.py + diagnostics..."
$diagCmd = "cd '$NasPath' && echo DIAG_START && echo healthz=`$(grep -c healthz app.py) && echo basepath_code=`$(grep -c KNK_MSG_BASE_PATH app.py) && echo size=`$(wc -c < app.py) && ls -la app.py wsgi.py static/js/app.js && echo loginhtml_size=`$(wc -c < templates/login.html) && echo logincss_policy=`$(grep -c login-policy static/css/style.css) && echo env_openai_linelen=`$(grep -E '^[[:space:]]*OPENAI_API_KEY[[:space:]]*=' .env 2>/dev/null | head -1 | wc -c) && echo '--- supervisor conf ---' && grep -rhE 'command=|environment=|dotenv|\.env' /etc/supervisor/conf.d/ 2>/dev/null | sed -E 's/([A-Za-z0-9_]*(KEY|SECRET|TOKEN|PASSWORD|PASSWD))=[^,]*/\1=***MASKED***/g' && echo '--- status ---' && supervisorctl status && echo DIAG_END"
Invoke-Ssh -Cmd $diagCmd | Out-Null
Write-Host $_LastSshOut -ForegroundColor Gray
$healthzCount = 0
if ($_LastSshOut -match "healthz=(\d+)") { $healthzCount = [int]$matches[1] }
if ($healthzCount -lt 1) {
    Fail "app.py 가 서버에 갱신되지 않음 (healthz 마커 0개) — 업로드 무음 실패. tar/base64 파이프 점검 필요."
}
Ok "  app.py 갱신 확인 (healthz 마커 ${healthzCount}개)"

Remove-Item $Tarball -ErrorAction SilentlyContinue

# --- 2.5) (선택) 서버 .env 의 KNK_MSG_BASE_PATH 설정 ---
$applyBasePath = $PSBoundParameters.ContainsKey('SetBasePath')
if ($applyBasePath) {
    Info "2.5/4 Setting KNK_MSG_BASE_PATH on server (.env)..."
    $envFile = "$NasPath/.env"
    $bakFile = "$envFile.before_basepath.$Stamp"
    $envCmd = "cp '$envFile' '$bakFile'; grep -v '^KNK_MSG_BASE_PATH=' '$envFile' > '$envFile.tmp' && mv '$envFile.tmp' '$envFile'"
    if ($SetBasePath) { $envCmd += "; echo 'KNK_MSG_BASE_PATH=$SetBasePath' >> '$envFile'" }
    $envCmd += "; echo '---ENV---'; grep -E '^KNK_MSG_(BASE_PATH|ENV|CORS)=' '$envFile' || echo '(KNK_MSG_BASE_PATH none - root mode)'"
    $code = Invoke-Ssh -Cmd $envCmd
    if ($code -ne 0) {
        Write-Host "stderr: $_LastSshErr" -ForegroundColor Yellow
        Fail ".env 수정 실패. code=$code"
    }
    Write-Host $_LastSshOut
    Ok "  .env updated (backup: $bakFile)"
}

if ($SkipRestart) {
    Ok "DONE (재시작 생략)"
    if ($askpassFile -and (Test-Path $askpassFile)) { Remove-Item $askpassFile -ErrorAction SilentlyContinue }
    exit 0
}

# --- 3) supervisord 로 재시작 ---
Info "3/4 Restarting knk-messenger (supervisorctl)..."
# supervisord 데몬 자체가 중단됐을 경우 먼저 시작 후 재시도
# PID 기록 → restart 후 PID 변경 여부로 성공 판단
$pidBefore = -1
$pidCmd = "supervisorctl status knk-messenger 2>&1"
Invoke-Ssh -Cmd $pidCmd | Out-Null
if ($_LastSshOut -match "pid\s+(\d+)") { $pidBefore = [int]$matches[1] }
Write-Host "  before restart PID: $pidBefore" -ForegroundColor DarkCyan

# 1차: supervisorctl stop → start (별개 명령, 더 안정적)
$restartCmd = "supervisorctl stop knk-messenger 2>&1; sleep 2; supervisorctl start knk-messenger 2>&1"
$code = Invoke-Ssh -Cmd $restartCmd
Write-Host $_LastSshOut -ForegroundColor Gray

# 2차 확인: PID 바뀌었는지 체크
Start-Sleep -Seconds 4
Invoke-Ssh -Cmd $pidCmd | Out-Null
$pidAfter = -1
if ($_LastSshOut -match "pid\s+(\d+)") { $pidAfter = [int]$matches[1] }
Write-Host "  after restart PID: $pidAfter" -ForegroundColor DarkCyan

if ($pidAfter -eq $pidBefore -and $pidBefore -gt 0) {
    Write-Host "[warn] PID unchanged ($pidBefore) — supervisorctl stop/start 미작동. kill -9 강제 재시작..." -ForegroundColor Yellow
    $forceKill = "kill -9 $pidBefore 2>&1; sleep 4; supervisorctl start knk-messenger 2>&1 || supervisord -c /etc/supervisor/supervisord.conf 2>/dev/null; sleep 2; supervisorctl start knk-messenger 2>&1 || true"
    Invoke-Ssh -Cmd $forceKill | Out-Null
    Write-Host $_LastSshOut -ForegroundColor Gray
    Start-Sleep -Seconds 5
    Invoke-Ssh -Cmd $pidCmd | Out-Null
    Write-Host "  after kill-9 PID: $_LastSshOut" -ForegroundColor DarkCyan
}

# supervisord 데몬 자체가 내려간 경우 (supervisorctl status 가 'refused connection' → PID 파싱 실패로 -1)
#   → supervisord 가 죽으면 자식(gunicorn)을 재시작해주지 못해 앱이 영구 다운(502)됨.
#   supervisord 를 새로 기동하면 autostart 로 knk-messenger 가 다시 뜬다. (데몬을 kill 하지 않아 컨테이너 안전)
#   (대표 지시 2026-05-25 긴급 복구: supervisor.sock refused 장애 대응)
if ($pidBefore -le 0) {
    Write-Host "[warn] supervisorctl 응답 없음(supervisord 데몬 다운 추정) — supervisord 재기동 복구 시도..." -ForegroundColor Yellow
    $recoverCmd = "supervisord -c /etc/supervisor/supervisord.conf 2>&1; sleep 6; supervisorctl start knk-messenger 2>&1; supervisorctl start knk-nginx 2>&1; sleep 2; supervisorctl status 2>&1"
    Invoke-Ssh -Cmd $recoverCmd | Out-Null
    Write-Host $_LastSshOut -ForegroundColor Gray
}

Ok "  restart 시도 완료"

# --- 4) 헬스체크 ---
# 컨테이너 sshd 로그인 배너가 stdout 을 오염시키므로 마커로 감싸 정확히 추출
Info "4/4 Health check..."
$HealthCmd = "echo HC_START; curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5050/healthz; echo; echo HC_END"
$code = Invoke-Ssh -Cmd $HealthCmd
$Status = "000"
if ($_LastSshOut -match "HC_START\s*(\d{3})\s*HC_END") { $Status = $matches[1] }

if ($Status -match "200|302") {
    Ok "  /healthz HTTP $Status - server healthy"

    # --- 4.5) -AddVictor: 테스트용 빅터 사용자 + 전체 방 가입 ---
    if ($AddVictor) {
        Info "Adding test user 'victor' and joining all rooms..."
        $vcmd = "cd /opt/knk_messenger && .venv/bin/python3 deploy/add_victor.py 2>&1"
        Invoke-Ssh -Cmd $vcmd | Out-Null
        Write-Host $_LastSshOut -ForegroundColor Gray
        Ok "  victor 설정 완료"
    }

    # --- 4.5.5) -RegenerateVapid: VAPID 키 재생성 + 옛 push 구독 삭제 ---
    if ($RegenerateVapid) {
        Info "VAPID 키 재생성 (옛 키 백업 + 새 키 생성 + push_subscriptions 비우기 + 서버 재시작)..."
        $vapidCmd = @"
cd /opt/knk_messenger
ts=`$(date +%Y%m%d_%H%M%S)
if [ -f data/vapid_private.pem ]; then
  mv data/vapid_private.pem data/vapid_private.pem.bak_`$ts
  echo "backup: data/vapid_private.pem.bak_`$ts"
fi
.venv/bin/python3 generate_vapid.py
echo '--- file check ---'
ls -la data/vapid_private.pem
echo '--- file head ---'
head -3 data/vapid_private.pem
echo '--- cryptography load test ---'
.venv/bin/python3 -c "from cryptography.hazmat.primitives import serialization; pem=open('data/vapid_private.pem','rb').read(); k=serialization.load_pem_private_key(pem, password=None); print('LOAD OK', type(k).__name__)"
echo '--- pywebpush self-test ---'
.venv/bin/python3 -c "from pywebpush import webpush; print('pywebpush import OK')"
echo '--- DB cleanup ---'
.venv/bin/python3 -c "import sqlite3; db=sqlite3.connect('data/messenger.db'); n=db.execute('SELECT COUNT(*) FROM push_subscriptions').fetchone()[0]; db.execute('DELETE FROM push_subscriptions'); db.commit(); print('deleted', n, 'subscriptions')"
echo '--- restart ---'
supervisorctl restart knk-messenger
"@
        Invoke-Ssh -Cmd $vapidCmd | Out-Null
        Write-Host $_LastSshOut -ForegroundColor Gray
        Ok "  VAPID 재생성 + 진단 완료. 출력 확인 후 사용자는 휴대폰 PWA 다시 열어 자동 재구독."
    }

    # --- 4.55) -VictorSend: 빅터로 테스트 메시지 전송 ---
    if ($VictorSend) {
        $msg = if ($VictorMessage) { $VictorMessage } else { "" }
        # 메시지에 따옴표 있을 수 있으니 escape — bash 측은 single-quote 로 감쌈
        $msgEsc = ($msg -replace "'", "'\\''")
        if ($VictorSend -eq "all") {
            $sendCmd = "cd /opt/knk_messenger && .venv/bin/python3 deploy/victor_send.py --all '$msgEsc' 2>&1"
            Info "Victor → ALL rooms : '$msg'"
        } else {
            $sendCmd = "cd /opt/knk_messenger && .venv/bin/python3 deploy/victor_send.py $VictorSend '$msgEsc' 2>&1"
            Info "Victor → room $VictorSend : '$msg'"
        }
        Invoke-Ssh -Cmd $sendCmd | Out-Null
        Write-Host $_LastSshOut -ForegroundColor Gray
    }

    # --- 4.6) BASE_PATH 적용 시 추가 검증 ---
    if ($applyBasePath -and $SetBasePath) {
        Info "Verifying base path '$SetBasePath' (and root 404)..."
        $vcmd = "echo VS; curl -s -o /dev/null -w '%{http_code}' 'http://127.0.0.1:5050$SetBasePath/login'; echo; curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5050/; echo; echo VE"
        Invoke-Ssh -Cmd $vcmd | Out-Null
        $msgStatus = "?"; $rootStatus = "?"
        if ($_LastSshOut -match "VS\s*(\d{3})\s*(\d{3})\s*VE") { $msgStatus = $matches[1]; $rootStatus = $matches[2] }
        if ($msgStatus -match "200|302") { Ok "  $SetBasePath/login HTTP $msgStatus - OK" }
        else { Write-Host "  [WARN] $SetBasePath/login HTTP $msgStatus" -ForegroundColor Yellow }
        Ok "  root / HTTP $rootStatus (404 = 정상: 메신저는 $SetBasePath 하위 전용)"
    }

    if ($askpassFile -and (Test-Path $askpassFile)) { Remove-Item $askpassFile -ErrorAction SilentlyContinue }
    $publicUrl = if ($applyBasePath) { "https://haist.knknara.co.kr$SetBasePath/" } else { "https://haist.knknara.co.kr/" }
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "  SYNC COMPLETE" -ForegroundColor Green
    Write-Host "  -> $publicUrl  (refresh Ctrl+Shift+R)" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
} else {
    if ($askpassFile -and (Test-Path $askpassFile)) { Remove-Item $askpassFile -ErrorAction SilentlyContinue }
    Write-Host "[FAIL] /healthz HTTP $Status" -ForegroundColor Red
    Write-Host ""
    Write-Host "Last 30 log lines:" -ForegroundColor Yellow
    Invoke-Ssh -Cmd "tail -30 /opt/knk_messenger/logs/gunicorn.err.log /opt/knk_messenger/logs/gunicorn.log 2>&1" | Out-Null
    Write-Host $_LastSshOut
    exit 2
}
