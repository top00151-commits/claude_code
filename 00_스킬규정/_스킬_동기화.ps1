# 스킬 동기화 — 원본(00_스킬규정) → Claude 가 읽는 자리(.claude\skills)
# 대표 지시 2026-11-23 「앞으로 만들어지는 스킬은 모두 00_스킬규정 폴더에 저장」
# 쓰는 법:
#   powershell -ExecutionPolicy Bypass -File "C:\Users\top00\JR\Claude 코드\00_스킬규정\_스킬_동기화.ps1"
# 하는 일: 원본 폴더의 <스킬이름>\SKILL.md 를 .claude\skills\<스킬이름>\SKILL.md 로 덮어쓴다.
#   · 원본에 없는 스킬이 사본에만 있으면 지우지 않고 알려만 준다(실수 방지).
#   · 아무것도 묻지 않고, 원본 쪽은 건드리지 않는다.

$ErrorActionPreference = "Stop"
chcp 65001 > $null

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path          # ...\00_스킬규정
$Base = Split-Path -Parent $Root                                  # ...\Claude 코드
$Dest = Join-Path $Base ".claude\skills"

Write-Host ""
Write-Host "스킬 동기화" -ForegroundColor Cyan
Write-Host "  원본: $Root"
Write-Host "  사본: $Dest"
Write-Host ""

if (-not (Test-Path $Dest)) { New-Item -ItemType Directory -Path $Dest -Force | Out-Null }

$n = 0
$skipped = 0
foreach ($dir in (Get-ChildItem -Path $Root -Directory | Where-Object { $_.Name -notlike "_*" })) {
    $src = Join-Path $dir.FullName "SKILL.md"
    if (-not (Test-Path $src)) {
        Write-Host ("  [건너뜀] " + $dir.Name + " — SKILL.md 가 없습니다") -ForegroundColor Yellow
        $skipped++
        continue
    }
    $outDir = Join-Path $Dest $dir.Name
    if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
    $out = Join-Path $outDir "SKILL.md"

    $same = $false
    if (Test-Path $out) {
        $h1 = (Get-FileHash $src -Algorithm SHA256).Hash
        $h2 = (Get-FileHash $out -Algorithm SHA256).Hash
        $same = ($h1 -eq $h2)
    }
    Copy-Item $src $out -Force
    if ($same) { Write-Host ("  [그대로] " + $dir.Name) }
    else       { Write-Host ("  [새로 넣음] " + $dir.Name) -ForegroundColor Green }
    $n++
}

# 원본에 없는데 사본에만 있는 것 — 지우지 않고 알려만 준다
foreach ($dir in (Get-ChildItem -Path $Dest -Directory -ErrorAction SilentlyContinue)) {
    $origin = Join-Path $Root $dir.Name
    if (-not (Test-Path $origin)) {
        Write-Host ("  [확인 필요] " + $dir.Name + " — 사본에만 있습니다. 원본(00_스킬규정)으로 옮기거나 지우세요") -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host ("완료 — 스킬 " + $n + "개" + $(if ($skipped -gt 0) { " · 건너뜀 " + $skipped + "개" } else { "" })) -ForegroundColor Cyan
Write-Host "새 스킬은 다음에 세션을 열 때부터 목록에 뜹니다."
Write-Host ""
