# KNK Messenger - Retest 30MB x 75 only (after gunicorn timeout boost)
# Same as run_loadtest.ps1 but only the 30MB scenario, with --no-cleanup so data persists for inspection.

$base = "https://haist.knknara.co.kr/msg"

try {
    Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCerts3 : ICertificatePolicy {
    public bool CheckValidationResult(ServicePoint sp, X509Certificate cert, WebRequest req, int problem) { return true; }
}
"@
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCerts3
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
} catch { }

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  KNK Messenger Retest - 30MB x 75 only"
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

$adminUser = Read-Host "admin username"
$pwSecure = Read-Host -Prompt "admin password" -AsSecureString
$pwBSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($pwSecure)
$pw = [Runtime.InteropServices.Marshal]::PtrToStringAuto($pwBSTR)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$scriptDir\load_test_client.py" `
    --base $base `
    --admin-username $adminUser `
    --admin-password $pw `
    --count 75 `
    --scenarios "30:75"

[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pwBSTR)
Remove-Variable pw -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Done. Result CSV in this folder."
Read-Host "Press Enter to close"
