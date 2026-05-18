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
    [switch]$RegenerateVapid
)

$ErrorActionPreference = "Stop"

function Fail($m) { Write-Host "[FAIL] $m" -ForegroundColor Red; exit 1 }
function Info($m) { Write-Host "[*] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[OK] $m" -ForegroundColor Green }

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
    "backup.py"
)
$Existing = $Items | Where-Object { Test-Path $_ }

$TarArgs = @("-czf", $Tarball, "--exclude=__pycache__", "--exclude=*.pyc") + $Existing
& tar @TarArgs 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "tar 압축 실패" }

$TarSize = [math]::Round((Get-Item $Tarball).Length / 1KB, 1)
Ok "  archive: $TarSize KB"

# --- 2) NAS로 업로드 + 풀기 ---
Info "2/4 Uploading + extracting to NAS..."

# Synology 컨테이너의 sshd 가 로그인 시 stderr 메시지를 찍어 scp 깨짐 — base64 stream 우회
# .NET 직접 base64 encoding (UTF8 BOM 없음) — certutil 방식은 PowerShell 5.1 의 Set-Content 가 BOM 흘림
$b64File = "$Tarball.b64"
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
$diagCmd = "cd '$NasPath' && echo DIAG_START && echo healthz=`$(grep -c healthz app.py) && echo basepath_code=`$(grep -c KNK_MSG_BASE_PATH app.py) && echo size=`$(wc -c < app.py) && ls -la app.py wsgi.py static/js/app.js && echo '--- supervisor conf ---' && grep -rhE 'command=|environment=|dotenv|\.env' /etc/supervisor/conf.d/ 2>/dev/null && echo '--- status ---' && supervisorctl status && echo DIAG_END"
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
$code = Invoke-Ssh -Cmd "supervisorctl restart knk-messenger"
if ($code -ne 0) {
    Write-Host "stderr: $_LastSshErr" -ForegroundColor Yellow
    Fail "supervisorctl restart 실패. SSH 직접 디버깅 필요. code=$code"
}
Ok "  restarted"

Start-Sleep -Seconds 4

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
