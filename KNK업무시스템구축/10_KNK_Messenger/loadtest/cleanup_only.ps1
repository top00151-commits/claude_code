# KNK Messenger Load Test - Cleanup Only
# Run this if test data remains after main test (loadtest_* accounts or [LOADTEST] room)

$base = "https://haist.knknara.co.kr/msg"

try {
    Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCerts2 : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint sp, X509Certificate cert, WebRequest req, int problem) { return true; }
}
"@
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCerts2
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
} catch { }

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  KNK Messenger Load Test - Cleanup Only"
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

$adminUser = Read-Host "admin username"
$pwSecure = Read-Host -Prompt "admin password" -AsSecureString
$pwBSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pwSecure)
$pw = [Runtime.InteropServices.Marshal]::PtrToStringAuto($pwBSTR)

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$session.UserAgent = "loadtest-cleanup/1.0"

try {
    $loginBody = @{username=$adminUser; password=$pw}
    Invoke-WebRequest -Uri "$base/login" -Method Post -Body $loginBody -WebSession $session -UseBasicParsing -MaximumRedirection 5 -ErrorAction SilentlyContinue | Out-Null

    Write-Host ""
    Write-Host "[*] Checking current test data status..." -ForegroundColor Yellow
    $status = Invoke-RestMethod -Uri "$base/api/admin/load_test/status" -Method Get -WebSession $session -UseBasicParsing -TimeoutSec 60
    Write-Host "  test users:    $($status.test_users_count)"
    Write-Host "  test rooms:    $($status.test_rooms.Count)"
    Write-Host "  test messages: $($status.test_messages_count)"

    if ($status.test_users_count -eq 0 -and $status.test_rooms.Count -eq 0) {
        Write-Host ""
        Write-Host "  Nothing to clean. Test data already gone." -ForegroundColor Green
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pwBSTR)
        Read-Host "Press Enter to close"
        exit 0
    }

    Write-Host ""
    Write-Host "[*] Running cleanup..." -ForegroundColor Yellow
    $body = '{"confirm_token":"I_UNDERSTAND_LOAD_TEST"}'
    $result = Invoke-RestMethod -Uri "$base/api/admin/load_test/cleanup" -Method Post -ContentType "application/json" -Body $body -WebSession $session -UseBasicParsing -TimeoutSec 300
    Write-Host "  deleted users:    $($result.deleted_users)" -ForegroundColor Green
    Write-Host "  deleted rooms:    $($result.deleted_rooms)" -ForegroundColor Green
    Write-Host "  deleted messages: $($result.deleted_messages)" -ForegroundColor Green
    Write-Host "  deleted files:    $($result.deleted_files)" -ForegroundColor Green
} catch {
    Write-Host "  Error: $_" -ForegroundColor Red
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pwBSTR)
    Remove-Variable pw -ErrorAction SilentlyContinue
}

Write-Host ""
Read-Host "Press Enter to close"
