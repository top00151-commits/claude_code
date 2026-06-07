$ErrorActionPreference = 'Stop'
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

$askpassDir = Join-Path $env:TEMP "knk_askpass_diag_$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Path $askpassDir -Force | Out-Null
$askpassFile = Join-Path $askpassDir 'askpass.bat'
"@echo off`r`necho $($env:KNK_NAS_PASSWORD)" | Set-Content -Path $askpassFile -Encoding ASCII
$env:DISPLAY = ':0'
$env:SSH_ASKPASS = $askpassFile
$env:SSH_ASKPASS_REQUIRE = 'force'

$cmd = @'
echo '=== [1] NAS outbound HTTPS to OpenAI API ==='
curl -s -o /dev/null -w 'HTTP %{http_code}, time %{time_total}s\n' --max-time 10 https://api.openai.com/v1/models || echo 'curl FAILED'
echo
echo '=== [2] .env source + actual _ai_translate call ==='
cd /opt/knk_messenger
set -a
. /opt/knk_messenger/.env
set +a
echo "  loaded TRANSLATE_PROVIDER=$KNK_MSG_TRANSLATE_PROVIDER OPENAI len=${#OPENAI_API_KEY}"
/opt/knk_messenger/.venv/bin/python -c "
import sys
sys.path.insert(0, '/opt/knk_messenger')
import app as a
print('TRANSLATE_PROVIDER:', a.TRANSLATE_PROVIDER)
print('OPENAI_API_KEY len:', len(a.OPENAI_API_KEY))
print('TRANSLATE_MOCK:', a.TRANSLATE_MOCK)
print('_ai_provider_has_key:', a._ai_provider_has_key())
print()
print('--- Actual translation call ---')
result, err = a._ai_translate('hello', 'ko')
if err:
    print('ERROR:', err)
else:
    print('OK translation:', repr(result[0]))
    print('TOKENS in/out:', result[2], result[3])
    print('COST USD:', result[4])
"
'@
$stdinFile = Join-Path $env:TEMP "knk_ssh_diag2_$([guid]::NewGuid().ToString('N')).sh"
[System.IO.File]::WriteAllText($stdinFile, $cmd, (New-Object System.Text.UTF8Encoding $false))
$tmpOut = Join-Path $env:TEMP "knk_ssh_out_$([guid]::NewGuid().ToString('N')).log"
$tmpErr = Join-Path $env:TEMP "knk_ssh_err_$([guid]::NewGuid().ToString('N')).log"
$cmdLine = 'ssh.exe -o BatchMode=no -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 -p 31201 root@o.knknara.co.kr "bash -s" < "' + $stdinFile + '" > "' + $tmpOut + '" 2> "' + $tmpErr + '"'
$proc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $cmdLine -NoNewWindow -Wait -PassThru
Write-Host "exit=$($proc.ExitCode)"
if (Test-Path $tmpOut) { Get-Content $tmpOut -Raw }
if (Test-Path $tmpErr) { $e = Get-Content $tmpErr -Raw; if ($e.Trim()) { Write-Host '--- STDERR ---'; Write-Host $e } }
Remove-Item $stdinFile, $tmpOut, $tmpErr, $askpassFile -ErrorAction SilentlyContinue
Remove-Item $askpassDir -Recurse -ErrorAction SilentlyContinue
