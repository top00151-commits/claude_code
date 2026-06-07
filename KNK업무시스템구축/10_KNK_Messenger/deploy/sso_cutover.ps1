# ============================================================
#  사번 SSO cutover — 운영 DB 마이그레이션 + 키 생성 (단계별)
#  발주: _TO_메신저세션/2026-05-29_사번SSO.md  ·  2026-05-31
#  SSH 인증/전송은 sync_to_synology.ps1 패턴 재사용 (비밀번호 SSH_ASKPASS)
#  ★ 비밀번호는 절대 출력하지 않음. 백업 최우선. dry-run 후 apply.
#
#  사용:  powershell deploy\sso_cutover.ps1 -Mode <probe|excel|dryrun|backup|keys|apply|verify|cleanup>
# ============================================================
param([Parameter(Mandatory=$true)][string]$Mode)
$ErrorActionPreference = "Stop"

$NasHost = $env:KNK_NAS_HOST
$NasPort = if ($env:KNK_NAS_PORT) { $env:KNK_NAS_PORT } else { "22" }
$NasUser = if ($env:KNK_NAS_USER) { $env:KNK_NAS_USER } else { "root" }
$NasPath = if ($env:KNK_NAS_PATH) { $env:KNK_NAS_PATH } else { "/opt/knk_messenger" }
$Password = $env:KNK_NAS_PASSWORD
if (-not $NasHost) { throw "KNK_NAS_HOST 없음" }
if (-not $Password) { throw "KNK_NAS_PASSWORD 없음" }

$sshOpts = @("-p", $NasPort, "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR")

$askpassFile = Join-Path $env:TEMP "knk_sso_askpass_$([guid]::NewGuid().ToString('N')).cmd"
@"
@echo off
echo $Password
"@ | Set-Content -Encoding ASCII $askpassFile

function Invoke-Ssh {
    param([string]$Cmd, [string]$StdinFile = $null)
    if (-not $StdinFile) {
        $opts = $sshOpts + @("-n")
        $remoteArg = '"' + ($Cmd -replace '"', '\"') + '"'
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "ssh.exe"
        $psi.Arguments = ($opts -join " ") + " ${NasUser}@${NasHost} $remoteArg"
        $psi.UseShellExecute = $false; $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true
        $psi.EnvironmentVariables["DISPLAY"] = ":0"
        $psi.EnvironmentVariables["SSH_ASKPASS"] = $askpassFile
        $psi.EnvironmentVariables["SSH_ASKPASS_REQUIRE"] = "force"
        $proc = [System.Diagnostics.Process]::Start($psi)
        $script:_Out = $proc.StandardOutput.ReadToEnd()
        $script:_Err = $proc.StandardError.ReadToEnd()
        $proc.WaitForExit()
        return $proc.ExitCode
    }
    $env:DISPLAY = ":0"; $env:SSH_ASKPASS = $askpassFile; $env:SSH_ASKPASS_REQUIRE = "force"
    $remoteArg = '"' + ($Cmd -replace '"', '\"') + '"'
    $sshLine = "ssh.exe " + ($sshOpts -join " ") + " ${NasUser}@${NasHost} $remoteArg"
    $tmpOut = "$env:TEMP\knk_sso_out_$([guid]::NewGuid().ToString('N')).log"
    $tmpErr = "$env:TEMP\knk_sso_err_$([guid]::NewGuid().ToString('N')).log"
    $fullCmd = "$sshLine < `"$StdinFile`" > `"$tmpOut`" 2> `"$tmpErr`""
    $proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $fullCmd -NoNewWindow -Wait -PassThru
    $script:_Out = if (Test-Path $tmpOut) { Get-Content $tmpOut -Raw } else { "" }
    $script:_Err = if (Test-Path $tmpErr) { Get-Content $tmpErr -Raw } else { "" }
    Remove-Item $tmpOut, $tmpErr -ErrorAction SilentlyContinue
    return $proc.ExitCode
}

function Send-File {
    param([string]$Local, [string]$Remote)
    $bytes = [System.IO.File]::ReadAllBytes($Local)
    $b64 = [Convert]::ToBase64String($bytes)
    $b64File = Join-Path $env:TEMP "knk_sso_sf_$([guid]::NewGuid().ToString('N')).b64"
    [System.IO.File]::WriteAllText($b64File, $b64, [System.Text.UTF8Encoding]::new($false))
    $rc = Invoke-Ssh -Cmd "base64 -d > '$Remote'" -StdinFile $b64File
    Remove-Item $b64File -ErrorAction SilentlyContinue
    return $rc
}

function Run-Show { param([string]$Cmd)
    $rc = Invoke-Ssh -Cmd $Cmd
    if ($script:_Out) { Write-Host $script:_Out }
    if ($script:_Err -and $script:_Err.Trim()) { Write-Host "[stderr] $($script:_Err)" -ForegroundColor DarkYellow }
    Write-Host "[exit=$rc]" -ForegroundColor Cyan
    return $rc
}

# 한글 경로는 PS 5.1 .ps1 인코딩 이슈 → ASCII 사본 사용 (sso_work/_kor_src.xlsx 등)
$KOR_LOCAL = Join-Path $PSScriptRoot "..\sso_work\_kor_src.xlsx"
$VN_LOCAL  = Join-Path $PSScriptRoot "..\sso_work\_vn_src.xlsx"
$KOR_NAS = "$NasPath/sso_work/_kor.xlsx"
$VN_NAS  = "$NasPath/sso_work/_vn.xlsx"
$DB  = "$NasPath/data/messenger.db"
$MIG = "$NasPath/sso_work/migrate_employee_no.py"
$PROBEPY = "$NasPath/sso_work/_cutover_probe.py"
$VERIFYPY = "$NasPath/sso_work/_cutover_verify.py"
$PY = "/opt/knk_messenger/.venv/bin/python"
$LOCAL_PROBE = Join-Path $PSScriptRoot "..\sso_work\_cutover_probe.py"
$LOCAL_VERIFY = Join-Path $PSScriptRoot "..\sso_work\_cutover_verify.py"
$LOCAL_MIG = Join-Path $PSScriptRoot "..\sso_work\migrate_employee_no.py"

try {
  switch ($Mode) {
    "probe" {
      Write-Host "== SSH 연결 + 환경 탐지 (읽기 전용) ==" -ForegroundColor Green
      Invoke-Ssh -Cmd "mkdir -p $NasPath/sso_work" | Out-Null
      Send-File $LOCAL_PROBE $PROBEPY | Out-Null
      Run-Show "echo CONNECT_OK; whoami; ls -la '$DB'; echo RG:; cat $NasPath/run_gunicorn.sh; echo VENV:; ls -la $NasPath/.venv/bin/python; echo PROBE:; $PY $PROBEPY '$DB'"
    }
    "excel" {
      Write-Host "== 엑셀 2개 NAS 전송 ==" -ForegroundColor Green
      Invoke-Ssh -Cmd "mkdir -p $NasPath/sso_work" | Out-Null
      $r1 = Send-File $KOR_LOCAL $KOR_NAS
      $r2 = Send-File $VN_LOCAL $VN_NAS
      Run-Show "ls -la $KOR_NAS $VN_NAS"
      Write-Host "send rc: kor=$r1 vn=$r2" -ForegroundColor Cyan
    }
    "dryrun" {
      Write-Host "== 마이그레이션 DRY-RUN (운영DB 읽기, 롤백) ==" -ForegroundColor Green
      Send-File $LOCAL_MIG $MIG | Out-Null
      Run-Show "$PY $MIG --db '$DB' --kor '$KOR_NAS' --vn '$VN_NAS'"
    }
    "backup" {
      Write-Host "== 운영 DB 백업 ==" -ForegroundColor Green
      $ts = Get-Date -Format "yyyyMMdd_HHmmss"
      $BK = "$NasPath/data/backup_pre_employee_no_$ts.db"
      Run-Show "cp -v '$DB' '$BK'; ls -la $NasPath/data/backup_pre_employee_no_*.db"
    }
    "keys" {
      Write-Host "== PyJWT 설치 + RS256 키 생성 ==" -ForegroundColor Green
      Run-Show "$PY -m pip install --quiet 'PyJWT[crypto]>=2.8.0'; $PY -c 'import jwt; print(jwt.__version__)'"
      Run-Show "sh $NasPath/deploy/gen_sso_keys.sh"
    }
    "apply" {
      Write-Host "== 마이그레이션 APPLY (정지 -> 적용 -> 재시작) ==" -ForegroundColor Green
      Send-File $LOCAL_MIG $MIG | Out-Null
      Run-Show "supervisorctl stop knk-messenger; sleep 1; $PY $MIG --db '$DB' --kor '$KOR_NAS' --vn '$VN_NAS' --apply; supervisorctl start knk-messenger; sleep 2; supervisorctl status knk-messenger"
    }
    "verify" {
      Write-Host "== 검증 ==" -ForegroundColor Green
      Send-File $LOCAL_VERIFY $VERIFYPY | Out-Null
      Run-Show "$PY $VERIFYPY '$DB'"
      Write-Host "-- healthz / SSO public-key --"
      try { $h = Invoke-WebRequest "https://haist.knknara.co.kr/healthz" -UseBasicParsing -TimeoutSec 15; Write-Host "healthz HTTP $($h.StatusCode)" } catch { Write-Host "healthz ERR" }
      try { $k = Invoke-WebRequest "https://haist.knknara.co.kr/msg/api/sso/public-key" -UseBasicParsing -TimeoutSec 15; Write-Host "public-key HTTP $($k.StatusCode) (200 = 키 활성)" } catch { Write-Host "public-key HTTP $($_.Exception.Response.StatusCode.value__)" }
    }
    "cleanup" {
      Write-Host "== NAS 임시 엑셀(PII) + 헬퍼 삭제 ==" -ForegroundColor Green
      Run-Show "rm -fv $KOR_NAS $VN_NAS $PROBEPY $VERIFYPY; ls -la $NasPath/sso_work/"
    }
    default { Write-Host "Unknown mode: $Mode" -ForegroundColor Red }
  }
}
finally {
  Remove-Item $askpassFile -ErrorAction SilentlyContinue
}
