# =============================================================
# KNK Messenger - OpenAI (ChatGPT) API key setup
# LAST UPDATE: 2026-05-27 - PowerShell version (UTF-8 BOM)
# 한글 인코딩 안정성을 위해 BAT 에서 분리
# =============================================================

# 콘솔을 UTF-8 로 (출력 깨짐 방지)
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    chcp 65001 > $null
} catch {}

$Host.UI.RawUI.WindowTitle = "KNK Messenger - OpenAI key setup"

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "  KNK 메신저 - AI 번역 활성화 (OpenAI / ChatGPT)" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ChatGPT API 번역을 사용하려면 OpenAI API 키가 필요합니다."
Write-Host ""
Write-Host "  1) 키 발급:  " -NoNewline
Write-Host "https://platform.openai.com/api-keys" -ForegroundColor Yellow
Write-Host "                Create new secret key -> 키 복사"
Write-Host "                (sk-proj-... 또는 sk-... 로 시작)"
Write-Host ""
Write-Host "  2) 아래에 키를 붙여넣고 Enter"
Write-Host "     (붙여넣기: 마우스 우클릭 또는 Ctrl+V)"
Write-Host ""

$apikey = Read-Host "    OPENAI_API_KEY"
$apikey = $apikey.Trim()

if ([string]::IsNullOrEmpty($apikey)) {
    Write-Host ""
    Write-Host "  [취소] 키가 입력되지 않았습니다." -ForegroundColor Red
    Write-Host ""
    Read-Host "  계속하려면 Enter"
    exit 1
}

# sk- 접두 가벼운 검증
if ($apikey -notlike "sk-*") {
    Write-Host ""
    Write-Host "  [경고] 키가 'sk-' 로 시작하지 않습니다. 정말 맞으십니까?" -ForegroundColor Yellow
    $yn = Read-Host "    그래도 저장할까요? (Y/N)"
    if ($yn -notmatch "^[Yy]") {
        Write-Host "  [취소] 사용자가 저장을 취소했습니다." -ForegroundColor Red
        Read-Host "  계속하려면 Enter"
        exit 1
    }
}

# .env 파일에 저장 — 기존 OPENAI_API_KEY / KNK_MSG_TRANSLATE_PROVIDER 라인 제거 후 새로 추가
$envPath = Join-Path $PSScriptRoot ".env"
$lines = @()
if (Test-Path $envPath) {
    $lines = Get-Content $envPath | Where-Object {
        ($_ -notmatch "^OPENAI_API_KEY=") -and ($_ -notmatch "^KNK_MSG_TRANSLATE_PROVIDER=")
    }
}
$lines += "OPENAI_API_KEY=$apikey"
$lines += "KNK_MSG_TRANSLATE_PROVIDER=openai"

# UTF-8 (no BOM) 으로 저장
[System.IO.File]::WriteAllLines($envPath, $lines, (New-Object System.Text.UTF8Encoding $false))

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "  저장 완료: .env 파일에 키 등록됨" -ForegroundColor Green
Write-Host "  공급자: OpenAI (ChatGPT) / 모델: gpt-4o-mini" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  다음 단계:"
Write-Host "   1) 메신저START.bat 가 켜져 있으면 Ctrl+C 로 종료"
Write-Host "   2) 메신저START.bat 다시 더블클릭"
Write-Host "   3) 채팅방에서 번역 토글 ON -> 메시지 입력 -> 전송"
Write-Host ""
Write-Host "  공급자 전환 (향후):"
Write-Host "   .env 의 KNK_MSG_TRANSLATE_PROVIDER 값을 변경"
Write-Host "     openai     = ChatGPT (기본)"
Write-Host "     anthropic  = Claude (Anthropic 결제 활성 후)"
Write-Host ""
Write-Host "  모델 변경 (선택):"
Write-Host "   .env 에 KNK_MSG_OPENAI_MODEL=gpt-4o-mini 를 추가"
Write-Host "     gpt-4o-mini  = 저렴/빠름 (기본, 권장)"
Write-Host "     gpt-4o       = 고품질/고가"
Write-Host ""
Write-Host "  Tip: .env 파일은 텍스트 편집기로 직접 열어 수정 가능."
Write-Host "       파일 권한: 본인만 읽도록 보관 (절대 외부 공유 금지)." -ForegroundColor Yellow
Write-Host ""
Read-Host "  계속하려면 Enter"
exit 0
