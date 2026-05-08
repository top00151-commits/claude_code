# ============================================================
# KNK Messenger - 사내 서버 정보 확인 (배포 전 사전 체크)
# ============================================================
# 사내 서버에서 PowerShell로 1번 실행. 가비아 DNS·SSL·운영 전환에 필요한
# 정보를 한 번에 모아서 보여줌.
#
# 사용법:
#   서버에서 PowerShell 우클릭 -> "PowerShell로 실행" 또는
#   PowerShell 창에서: .\사내서버_정보확인.ps1
# ============================================================

$ErrorActionPreference = "SilentlyContinue"

function H($title) {
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host "  $title" -ForegroundColor Cyan
    Write-Host "===============================================" -ForegroundColor Cyan
}

# 1. 공인 IP (가비아 DNS A 레코드용)
H "1. 공인 IP - 가비아 DNS A 레코드에 입력할 값"
try {
    $publicIP = (Invoke-WebRequest 'https://api.ipify.org' -UseBasicParsing -TimeoutSec 10).Content
    Write-Host "  공인 IP:  $publicIP" -ForegroundColor Green
    Write-Host ""
    Write-Host "  -> 가비아 콘솔에서 다음 입력:" -ForegroundColor Yellow
    Write-Host "       Type:  A"
    Write-Host "       Host:  msg"
    Write-Host "       Value: $publicIP"
    Write-Host "       TTL:   600 (10분)"
} catch {
    Write-Host "  [실패] 인터넷 접속 안됨 또는 ipify 차단" -ForegroundColor Red
    Write-Host "  대안: https://www.whatismyip.com 브라우저 접속"
}

# 2. LAN IP (라우터 포트포워딩용)
H "2. LAN IP - 회사 라우터 포트포워딩 설정용"
$lans = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet|VMware' -and $_.IPAddress -notmatch '^169\.' }
foreach ($l in $lans) {
    Write-Host ("  {0,-15} ({1})" -f $l.IPAddress, $l.InterfaceAlias)
}
Write-Host ""
Write-Host "  -> 라우터 관리자 페이지에서 포트포워딩:" -ForegroundColor Yellow
Write-Host "       외부 80   -> [위 LAN IP]:80"
Write-Host "       외부 443  -> [위 LAN IP]:443"
Write-Host "       (KT/SKB 등 ISP가 80을 막으면 8080 -> 80 매핑 우회)"

# 3. 80·443 포트 사용 중 여부
H "3. 80/443 포트 점유 - 다른 서비스가 쓰고 있으면 nginx 충돌"
$tcp = Get-NetTCPConnection -LocalPort 80,443 -ErrorAction SilentlyContinue
if ($tcp) {
    foreach ($t in $tcp) {
        $proc = Get-Process -Id $t.OwningProcess -ErrorAction SilentlyContinue
        Write-Host ("  PORT {0,-4} {1,-12} <-- {2}" -f $t.LocalPort, $t.State, $proc.ProcessName) -ForegroundColor Yellow
    }
} else {
    Write-Host "  포트 80/443 비어있음 (정상)" -ForegroundColor Green
}

# 4. 5050 (메신저 현재 포트) 점유
H "4. 메신저 포트 5050 점유"
$tcp5050 = Get-NetTCPConnection -LocalPort 5050 -ErrorAction SilentlyContinue
if ($tcp5050) {
    Write-Host "  5050 사용 중 (정상 - 메신저 실행 중)" -ForegroundColor Green
} else {
    Write-Host "  5050 비어있음 (메신저 미실행)" -ForegroundColor Yellow
}

# 5. OS
H "5. OS 정보"
$os = Get-CimInstance Win32_OperatingSystem
Write-Host ("  OS:        {0}" -f $os.Caption)
Write-Host ("  버전:      {0}" -f $os.Version)
Write-Host ("  업타임:    {0:dd\.hh\:mm}" -f ((Get-Date) - $os.LastBootUpTime))

# 6. 인터넷 회선 - DNS 설정 보여주기 (정적 IP 힌트)
H "6. 게이트웨이 - 라우터 관리자 페이지 IP"
$route = Get-NetRoute -DestinationPrefix "0.0.0.0/0" | Sort-Object RouteMetric | Select-Object -First 1
if ($route) {
    Write-Host ("  게이트웨이: http://{0}" -f $route.NextHop) -ForegroundColor Green
    Write-Host "  (브라우저에서 위 주소 접속 -> 라우터 관리자)"
}

# 7. 방화벽 상태
H "7. Windows 방화벽 - 인바운드 80/443 허용 필요"
$fw = Get-NetFirewallProfile | Select-Object Name, Enabled
foreach ($f in $fw) {
    Write-Host ("  {0,-15} {1}" -f $f.Name, $f.Enabled)
}

# 8. 외부에서 80·443 접속 가능한지 (간이 체크 - canyouseeme.org API 없으니 안내만)
H "8. 외부 접속 테스트 (수동 확인)"
Write-Host "  공인 IP가 외부에서 80/443 으로 접근 가능한지:"
Write-Host "  1) 휴대폰을 LTE/5G로 바꾸기 (회사 와이파이 끊기)"
Write-Host "  2) 브라우저에서 http://[공인IP]  접속"
Write-Host "  3) 메신저 화면 보이면 OK, 안보이면 라우터 포트포워딩 미설정"

# 9. 결정 체크리스트
H "9. 가비아 + SSL 진행 전 확인 사항"
Write-Host @"
  [ ] 공인 IP 가 정적인지 확인
       -> ISP 콜센터 또는 인터넷 청구서. 정적이 아니면 1~3개월에 한 번 바뀔 수 있음
       -> 정적이 아니면: KT/SKB 정적IP 신청(월 ~1~3만원) 또는 DDNS 사용

  [ ] 회사 라우터 포트포워딩 가능 여부
       -> 외부 80 -> 사내서버 LAN:80
       -> 외부 443 -> 사내서버 LAN:443

  [ ] 회사 방화벽이 인바운드 80/443 허용
       -> 일부 기업 회선은 ISP가 80 포트 차단 (웹호스팅 방지)
       -> 막혔으면 8080/8443 우회

  [ ] 24/7 가동
       -> UPS 있는지, 야간 재부팅 정책 없는지
       -> 정전 시 자동 시작 BIOS 설정

  [ ] SSL 발급 방법 결정
       -> Win-acme(Windows용 Let's Encrypt) 또는
          가비아 SSL 구매(연 ~30,000~)
"@ -ForegroundColor White

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "  위 결과를 빅터에게 그대로 복사해서 붙여주세요." -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Read-Host "Enter 키를 누르면 종료됩니다"
