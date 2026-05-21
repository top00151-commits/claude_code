# KNK Messenger Load Test wrapper (2026-05-20)
# Compatible with Windows PowerShell 5.1 and PowerShell 7+

$base = "https://haist.knknara.co.kr/msg"

# SSL certificate bypass (PowerShell 5.1 compatible)
try {
    Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCerts : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint sp, X509Certificate cert, WebRequest req, int problem) { return true; }
}
"@
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCerts
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
} catch { }

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  KNK Messenger Load Test Phase 3"
Write-Host "  Base URL: $base"
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# 1. admin auth
$adminUser = Read-Host "admin username (e.g. dhkimman@knknara.co.kr)"
$pwSecure = Read-Host -Prompt "admin password" -AsSecureString
$pwBSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pwSecure)
$pw = [Runtime.InteropServices.Marshal]::PtrToStringAuto($pwBSTR)

# 2. Pre-test backup via API
Write-Host ""
Write-Host "[*] Pre-test backup (deploy/backup.sh via API)..." -ForegroundColor Yellow

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$session.UserAgent = "loadtest-wrapper/1.0"

$backupOk = $false
try {
    $loginBody = @{username=$adminUser; password=$pw}
    # Login - allow redirect chain (302 to /chat then to login chain)
    $loginResp = Invoke-WebRequest -Uri "$base/login" -Method Post -Body $loginBody -WebSession $session -UseBasicParsing -MaximumRedirection 5 -ErrorAction SilentlyContinue
    $cookies = $session.Cookies.GetCookies("$base/")
    $hasSession = $false
    foreach ($c in $cookies) { if ($c.Name -eq "session") { $hasSession = $true; break } }
    if (-not $hasSession) {
        Write-Host "  Login failed - no session cookie. Check username/password." -ForegroundColor Red
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pwBSTR)
        exit 1
    }
    Write-Host "  Login OK (session cookie acquired)" -ForegroundColor Green

    $backupResp = Invoke-RestMethod -Uri "$base/api/admin/backup_now" -Method Post -ContentType "application/json" -Body '{}' -WebSession $session -TimeoutSec 600 -UseBasicParsing
    Write-Host "  Backup exit_code: $($backupResp.exit_code)" -ForegroundColor Green
    if ($backupResp.stdout) {
        $tail = $backupResp.stdout
        if ($tail.Length -gt 500) { $tail = $tail.Substring($tail.Length - 500) }
        Write-Host "  stdout tail:"
        Write-Host $tail
    }
    $backupOk = $true
} catch {
    Write-Host "  Backup call failed: $_" -ForegroundColor Red
}

if (-not $backupOk) {
    $cont = Read-Host "Continue without backup? (y/N)"
    if ($cont -ne "y" -and $cont -ne "Y") {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pwBSTR)
        exit 1
    }
}

# 3. Python requests check
Write-Host ""
Write-Host "[*] Checking Python requests package..." -ForegroundColor Yellow
$pyTest = python -c "import requests" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  requests not installed - auto installing..."
    python -m pip install requests urllib3 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Install failed. Run manually: python -m pip install requests" -ForegroundColor Red
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pwBSTR)
        exit 1
    }
}
Write-Host "  Python ready" -ForegroundColor Green

# 4. Run load test
Write-Host ""
Write-Host "[*] Starting load test..." -ForegroundColor Yellow
Write-Host "    Scenarios: 5MB*1 -> 5MB*5 -> 5MB*20 -> 5MB*75 -> 30MB*75 -> 100MB*75"
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$scriptDir\load_test_client.py" `
    --base $base `
    --admin-username $adminUser `
    --admin-password $pw `
    --count 75 `
    --scenarios "5:1,5:5,5:20,5:75,30:75,100:75"

# 5. Clear password from memory
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pwBSTR)
Remove-Variable pw -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  Done. Check loadtest_result_*.csv file."
Write-Host "=====================================================" -ForegroundColor Cyan
