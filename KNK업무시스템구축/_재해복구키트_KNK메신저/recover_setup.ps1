# ============================================================
# KNK Messenger - 재해 복구 부트스트랩 (recover_setup.ps1)
# ------------------------------------------------------------
# 새 PC / 새 클로드 환경에서 이 프로젝트를 "다시 배포 가능" 상태로
# 만들기 위한 점검·안내 스크립트.
#
#  * 비밀값(KNK_NAS_KEY / KNK_NAS_PASSWORD 등)은 절대 화면에 출력하지 않음.
#    오직 "설정됨 / 미설정" 여부만 표시한다. (안전 규칙)
#  * 이 스크립트는 아무것도 삭제·배포하지 않는다. 점검 + 안내만.
#
# 사용:
#   git clone 후 그 폴더에서
#     & "deploy\recover_setup.ps1"
#   모든 항목이 OK 로 뜨면, 마지막에 -RunDiag 로 실제 서버 연결까지 확인:
#     & "deploy\recover_setup.ps1" -RunDiag
#
# 콘솔 출력은 한글 깨짐 방지를 위해 영어로 고정 (Windows PowerShell 5.1 호환).
# ============================================================
param([switch]$RunDiag)

$ErrorActionPreference = "Stop"
function L($m){ Write-Host $m }
function OKx($m){ Write-Host "  [OK]   $m" -ForegroundColor Green }
function NGx($m){ Write-Host "  [MISS] $m" -ForegroundColor Red }
function WNx($m){ Write-Host "  [warn] $m" -ForegroundColor Yellow }

$ok = $true

L ""
L "=================================================="
L "  KNK Messenger - Disaster Recovery Check"
L "=================================================="
L ""

# --- 1. Git 설치 확인 -------------------------------------------------
L "[1] Git installed?"
try { $gv = (git --version) 2>$null; OKx "git found: $gv" }
catch { NGx "git NOT found  ->  install Git for Windows: https://git-scm.com/download/win"; $ok = $false }

# --- 2. 저장소 안에 있는지 + 원격 확인 --------------------------------
L "[2] Inside the knk-messenger git repo?"
$repoRoot = $null
try { $repoRoot = (git rev-parse --show-toplevel) 2>$null } catch {}
if ($repoRoot) {
    OKx "repo root: $repoRoot"
    $remote = (git remote get-url origin) 2>$null
    if ($remote -match "knk-messenger") { OKx "remote origin: $remote" }
    else { WNx "remote origin looks unexpected: $remote" }
} else {
    NGx "Not a git repo. Run:  git clone git@github.com:top00151-commits/knk-messenger.git"
    $ok = $false
}

# --- 3. 배포에 필요한 환경변수 (값은 표시하지 않음, 존재만) ------------
L "[3] Deploy environment variables (values are NEVER shown):"
function ChkEnv($name, $required) {
    $val = [Environment]::GetEnvironmentVariable($name, "User")
    if (-not $val) { $val = [Environment]::GetEnvironmentVariable($name, "Process") }
    if ($val) { OKx "$name is SET" ; return $true }
    else {
        if ($required) { NGx "$name is MISSING (required)" }
        else { WNx "$name is not set (optional)" }
        return $false
    }
}
$envOk = $true
if (-not (ChkEnv "KNK_NAS_HOST" $true))  { $envOk = $false }   # o.knknara.co.kr
if (-not (ChkEnv "KNK_NAS_PORT" $true))  { $envOk = $false }   # 31201
if (-not (ChkEnv "KNK_NAS_USER" $true))  { $envOk = $false }   # root
if (-not (ChkEnv "KNK_NAS_PATH" $true))  { $envOk = $false }   # /opt/knk_messenger
# 접속 비밀값: KEY(SSH 키파일) 또는 PASSWORD 둘 중 하나면 충분
$hasKey = ChkEnv "KNK_NAS_KEY" $false
$hasPw  = ChkEnv "KNK_NAS_PASSWORD" $false
if (-not ($hasKey -or $hasPw)) {
    NGx "Need ONE of: KNK_NAS_KEY (ssh key file) OR KNK_NAS_PASSWORD"
    $envOk = $false
}
# KEY 가 설정돼 있으면 그 파일이 실제로 존재하는지 (값 출력 없이 경로 존재만)
if ($hasKey) {
    $kf = [Environment]::GetEnvironmentVariable("KNK_NAS_KEY","User")
    if (-not $kf) { $kf = $env:KNK_NAS_KEY }
    if ($kf -and (Test-Path $kf)) { OKx "KNK_NAS_KEY file exists on disk" }
    else { NGx "KNK_NAS_KEY is set but the key file is missing -> restore the ssh key file"; $envOk = $false }
}
if (-not $envOk) { $ok = $false }

# --- 4. GitHub push 가능 여부(키) 안내 --------------------------------
L "[4] GitHub access (for pulling code / pushing changes):"
$sshKey = Join-Path $HOME ".ssh\id_ed25519"
if (Test-Path $sshKey) { OKx "ssh key present: ~/.ssh/id_ed25519" }
else { WNx "no ~/.ssh/id_ed25519 . For push, add an SSH key to the GitHub account, or use HTTPS + token." }

# --- 결과 요약 + 다음 단계 -------------------------------------------
L ""
L "=================================================="
if ($ok) {
    Write-Host "  RESULT: READY to deploy." -ForegroundColor Green
    L "  Next: verify live server connection (read-only):"
    L "        & `"deploy\sync_to_synology.ps1`" -Diag"
} else {
    Write-Host "  RESULT: NOT ready - fix [MISS] items above." -ForegroundColor Red
    L ""
    L "  How to set the NAS env vars (fill the blanks yourself,"
    L "  take the secret values from your off-PC recovery kit):"
    L '    [Environment]::SetEnvironmentVariable("KNK_NAS_HOST","o.knknara.co.kr","User")'
    L '    [Environment]::SetEnvironmentVariable("KNK_NAS_PORT","31201","User")'
    L '    [Environment]::SetEnvironmentVariable("KNK_NAS_USER","root","User")'
    L '    [Environment]::SetEnvironmentVariable("KNK_NAS_PATH","/opt/knk_messenger","User")'
    L '    [Environment]::SetEnvironmentVariable("KNK_NAS_KEY","<path-to-your-ssh-key-file>","User")'
    L "  (open a NEW PowerShell window after setting, then re-run this script)"
}
L "=================================================="
L ""

# --- 5. (옵션) 실제 서버 연결 진단 실행 -------------------------------
if ($RunDiag) {
    if ($ok) {
        L "[5] Running read-only server diagnostic (-Diag) ..."
        $diag = Join-Path $PSScriptRoot "sync_to_synology.ps1"
        & $diag -Diag
    } else {
        WNx "Skipping -Diag because required items are missing."
    }
}
