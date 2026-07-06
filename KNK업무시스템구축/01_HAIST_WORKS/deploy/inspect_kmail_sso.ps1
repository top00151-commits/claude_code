# ============================================================
# kmail SSO 설정 진단 (읽기전용·비밀값 가림) — cutover 진입점 문제 원인 파악
# ------------------------------------------------------------
# kmail 로그인이 works 로 새는 원인 = PUBLIC_BASE / 메신저 SSO 주소 확인.
# 사용: ./inspect_kmail_sso.ps1   (-Port 32203 = kmail)
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [int]$Port       = 32203,
    [string]$User    = "root"
)
$ErrorActionPreference = "Stop"
$sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new")
function Invoke-Remote([string]$bash) {
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    ssh @sshOpts "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  kmail SSO 설정 진단 (읽기전용·비밀 가림)" -ForegroundColor Cyan
Write-Host "  (SSH 비밀번호를 물으면 직접 입력하세요)" -ForegroundColor Yellow
Write-Host "=================================================="

$probe = @'
set +e
echo "[1] 실제 적용 env (run.py 프로세스 · 주소/플래그만)"
P=$(pgrep -f "/opt/knk_mail/run.py" | head -1)
echo "  run.py pid: $P"
if [ -n "$P" ]; then
  tr '\0' '\n' < /proc/$P/environ 2>/dev/null | grep -E "^KNK_MAIL_PUBLIC_BASE=|^KNK_MESSENGER_SSO_BASE=|^KNK_MESSENGER_SSO_INTERNAL_BASE=|^KNK_SSO_ISSUER=|^KNK_MAIL_SSO_AUDIENCE=|^KNK_MAIL_HTTPS_ONLY=" | sort | sed -E 's/(SECRET|_KEY|PASSWORD|TOKEN)=.*/\1=<hidden>/'
fi
echo "[2] .env 파일 SSO 관련 (비밀 마스킹)"
if [ -f /opt/knk_mail/.env ]; then
  grep -E "PUBLIC_BASE|MESSENGER_SSO|SSO_ISSUER|SSO_AUDIENCE|HTTPS_ONLY" /opt/knk_mail/.env 2>/dev/null | sed -E 's/(SECRET|_KEY|PASSWORD|TOKEN)=.*/\1=<hidden>/'
else
  echo "  (.env 없음 → 기본값 사용: PUBLIC_BASE=http://127.0.0.1:8201)"
fi
echo "[3] 빌드되는 redirect_uri 미리보기"
if [ -n "$P" ]; then
  PB=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null | grep "^KNK_MAIL_PUBLIC_BASE=" | cut -d= -f2-)
  echo "  PUBLIC_BASE=${PB:-(미설정→127.0.0.1:8201)}"
  echo "  => redirect_uri = ${PB:-http://127.0.0.1:8201}/sso/land"
fi
echo "[done]"
'@
Invoke-Remote $probe
Write-Host "`n[완료] 위 출력을 빅터에게 붙여주세요 — PUBLIC_BASE 가 kmail 인지/works 인지로 원인이 갈립니다." -ForegroundColor Green
