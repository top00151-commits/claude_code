# =============================================================
# KNK Messenger - OpenAI key registration on production NAS
# One-shot helper. Reads _temp_openai.txt, SSH to NAS, updates .env,
# installs openai, restarts service, verifies, then deletes temp file.
#
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File deploy\_setup_openai_nas.ps1
# Requires: $env:KNK_NAS_PASSWORD set
# =============================================================
$ErrorActionPreference = 'Stop'

$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
$KeyFile = Join-Path $ProjectDir '_temp_openai.txt'

if (-not (Test-Path $KeyFile)) {
    Write-Host "ERROR: $KeyFile not found" -ForegroundColor Red
    exit 1
}
if (-not $env:KNK_NAS_PASSWORD) {
    Write-Host "ERROR: KNK_NAS_PASSWORD env var not set" -ForegroundColor Red
    exit 1
}

$apiKey = (Get-Content $KeyFile -Raw).Trim()
if (-not $apiKey.StartsWith('sk-')) {
    Write-Host "ERROR: key does not start with sk-" -ForegroundColor Red
    exit 1
}
Write-Host "  Key read OK (length=$($apiKey.Length))" -ForegroundColor Green

# Setup SSH_ASKPASS for password-less SSH (same pattern as sync_to_synology.ps1)
$askpassDir = Join-Path $env:TEMP "knk_askpass_$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $askpassDir -Force | Out-Null
$askpassFile = Join-Path $askpassDir 'askpass.bat'
# Read password from env at run-time; do NOT log it.
$pwForAskpass = $env:KNK_NAS_PASSWORD
"@echo off`r`necho $pwForAskpass" | Set-Content -Path $askpassFile -Encoding ASCII

$env:DISPLAY = ':0'
$env:SSH_ASKPASS = $askpassFile
$env:SSH_ASKPASS_REQUIRE = 'force'

# Build remote command — single bash session (single-quote here-string, no PS interpolation)
$remoteCmd = @'
set -e
echo '=== [1] .env backup + key registration ==='
cp /opt/knk_messenger/.env /opt/knk_messenger/.env.bak.openai 2>/dev/null || true
sed -i '/^OPENAI_API_KEY=/d; /^KNK_MSG_TRANSLATE_PROVIDER=/d' /opt/knk_messenger/.env
echo 'OPENAI_API_KEY=__APIKEY__' >> /opt/knk_messenger/.env
echo 'KNK_MSG_TRANSLATE_PROVIDER=openai' >> /opt/knk_messenger/.env
chmod 600 /opt/knk_messenger/.env
N=$(grep -cE '^OPENAI_API_KEY=|^KNK_MSG_TRANSLATE_PROVIDER=' /opt/knk_messenger/.env)
echo "  .env target lines: $N"
echo
echo '=== [2] locate pip + install openai ==='
PIP=''
for p in /opt/knk_messenger/.venv/bin/pip /opt/knk_messenger/venv/bin/pip /usr/local/bin/pip /usr/bin/pip3 /usr/bin/pip; do
  if [ -x "$p" ]; then PIP="$p"; break; fi
done
echo "  PIP=$PIP"
if [ -z "$PIP" ]; then echo '!!! pip not found'; exit 1; fi
"$PIP" install 'openai>=1.40' 2>&1 | tail -5
echo
echo '=== [3] supervisorctl restart ==='
supervisorctl restart knk-messenger
sleep 5
echo
echo '=== [4] healthz ==='
curl -s --max-time 5 http://localhost:5050/healthz
echo
echo '=== [5] gunicorn startup log (AI translation lines) ==='
tail -80 /opt/knk_messenger/logs/gunicorn.log | grep -iE 'AI translation|server start' | tail -15
'@
# Replace placeholder with actual key (in memory only)
$remoteCmd = $remoteCmd.Replace('__APIKEY__', $apiKey)

# Write command to a stdin file (raw bytes, no BOM) and pipe via cmd.exe < redirect
$stdinFile = Join-Path $env:TEMP "knk_ssh_cmd_$([guid]::NewGuid().ToString('N')).sh"
[System.IO.File]::WriteAllText($stdinFile, $remoteCmd, (New-Object System.Text.UTF8Encoding $false))

$sshOpts = @('-o', 'BatchMode=no', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'ConnectTimeout=15', '-p', '31201')
$tmpOut = Join-Path $env:TEMP "knk_ssh_out_$([guid]::NewGuid().ToString('N')).log"
$tmpErr = Join-Path $env:TEMP "knk_ssh_err_$([guid]::NewGuid().ToString('N')).log"
$cmdLine = 'ssh.exe ' + ($sshOpts -join ' ') + ' root@o.knknara.co.kr "bash -s" < "' + $stdinFile + '" > "' + $tmpOut + '" 2> "' + $tmpErr + '"'

Write-Host "  SSH executing..." -ForegroundColor Cyan
$proc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $cmdLine -NoNewWindow -Wait -PassThru
Write-Host "  SSH exit code: $($proc.ExitCode)" -ForegroundColor Cyan

Write-Host "--- STDOUT ---" -ForegroundColor Cyan
if (Test-Path $tmpOut) {
    Get-Content $tmpOut -Raw
}
if (Test-Path $tmpErr) {
    $err = Get-Content $tmpErr -Raw
    if ($err -and $err.Trim()) {
        Write-Host "--- STDERR ---" -ForegroundColor Yellow
        Write-Host $err
    }
}

# Cleanup
Remove-Item $stdinFile, $tmpOut, $tmpErr, $askpassFile -ErrorAction SilentlyContinue
Remove-Item $askpassDir -Recurse -ErrorAction SilentlyContinue
$apiKey = $null
$pwForAskpass = $null
[System.GC]::Collect()

# Delete local temp key file
Remove-Item $KeyFile -Force
Write-Host "  Local _temp_openai.txt deleted." -ForegroundColor Green

if ($proc.ExitCode -eq 0) {
    Write-Host "  DONE." -ForegroundColor Green
} else {
    Write-Host "  WARNING: SSH exit code was $($proc.ExitCode) - review output above." -ForegroundColor Yellow
}
