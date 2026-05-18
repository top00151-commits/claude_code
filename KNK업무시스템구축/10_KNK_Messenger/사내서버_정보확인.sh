#!/usr/bin/env bash
# ============================================================
# KNK Messenger - 사내 Linux 서버 정보 확인 (배포 전 사전 체크)
# ============================================================
# 사내 Linux 서버에서 1번 실행. 가비아 DNS·SSL·운영 전환에 필요한
# 정보를 한 번에 모아서 보여줌.
#
# 사용법:
#   bash 사내서버_정보확인.sh
# ============================================================

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
WHITE='\033[1;37m'
NC='\033[0m'

H() {
  echo
  echo -e "${CYAN}===============================================${NC}"
  echo -e "${CYAN}  $1${NC}"
  echo -e "${CYAN}===============================================${NC}"
}

# 1. 공인 IP
H "1. 공인 IP - 가비아 DNS A 레코드에 입력할 값"
PUBIP=$(curl -fsS --max-time 8 https://api.ipify.org 2>/dev/null \
        || curl -fsS --max-time 8 https://ifconfig.me 2>/dev/null \
        || curl -fsS --max-time 8 https://icanhazip.com 2>/dev/null)
if [ -n "$PUBIP" ]; then
  echo -e "  공인 IP:  ${GREEN}$PUBIP${NC}"
  echo
  echo -e "  ${YELLOW}-> 가비아 DNS 관리에 입력:${NC}"
  echo "       Type:  A"
  echo "       Host:  msg"
  echo "       Value: $PUBIP"
  echo "       TTL:   600 (10분)"
else
  echo -e "  ${RED}[실패] 인터넷 접근 불가 또는 차단${NC}"
fi

# 2. LAN IP
H "2. LAN IP - 라우터 포트포워딩 + sync 접속용"
ip -4 addr show 2>/dev/null | awk '/inet / && $2 !~ /^127\./ && $2 !~ /^169\.254\./ {
  split($2, a, "/"); print "  " a[1] "  (" $NF ")"
}'
echo
echo -e "  ${YELLOW}-> 라우터 관리자에서 포트포워딩:${NC}"
echo "       외부 80   -> [위 LAN IP]:80"
echo "       외부 443  -> [위 LAN IP]:443"
echo "       외부 22   -> [위 LAN IP]:22 (SSH 운영용 - 사무실 IP만 허용 권장)"

# 3. 80·443·5050 포트 점유
H "3. 포트 점유 (80/443/5050)"
if command -v ss >/dev/null 2>&1; then
  USED=$(ss -tlnp 2>/dev/null | grep -E ':(80|443|5050)\b' | head -20)
  if [ -n "$USED" ]; then
    echo "$USED" | sed 's/^/  /'
  else
    echo -e "  ${GREEN}80/443/5050 모두 비어있음${NC}"
  fi
elif command -v netstat >/dev/null 2>&1; then
  netstat -tlnp 2>/dev/null | grep -E ':(80|443|5050)\b' | sed 's/^/  /'
else
  echo "  (ss/netstat 미설치)"
fi

# 4. OS / Distribution
H "4. OS 정보 - 배포 키트 호환성 확인"
if [ -f /etc/os-release ]; then
  . /etc/os-release
  echo "  배포판:     $PRETTY_NAME"
  echo "  ID:         $ID"
  echo "  버전:       $VERSION_ID"
  case "$ID" in
    ubuntu|debian)
      echo -e "  ${GREEN}=> 배포 키트(deploy/) 그대로 사용 가능${NC}"
      ;;
    centos|rhel|rocky|almalinux|fedora)
      echo -e "  ${YELLOW}=> 배포 키트 일부 수정 필요 (apt -> dnf/yum)${NC}"
      echo "     빅터에게 OS 알려주면 RHEL용 setup_server_dev_rhel.sh 작성"
      ;;
    *)
      echo -e "  ${YELLOW}=> 처음 보는 배포판. 빅터에게 알려주기${NC}"
      ;;
  esac
fi
echo "  커널:       $(uname -r)"
echo "  업타임:     $(uptime -p 2>/dev/null || uptime)"

# 5. 게이트웨이
H "5. 게이트웨이 - 라우터 관리자 페이지"
GW=$(ip route 2>/dev/null | awk '/^default/ {print $3; exit}')
if [ -n "$GW" ]; then
  echo -e "  게이트웨이: ${GREEN}http://$GW${NC}"
  echo "  (브라우저에서 위 주소 -> 라우터 관리자 -> 포트포워딩 메뉴)"
fi

# 6. 방화벽 상태
H "6. 방화벽 - 인바운드 80/443 허용 필요"
if command -v ufw >/dev/null 2>&1; then
  echo "  --- ufw ---"
  sudo -n ufw status 2>/dev/null | sed 's/^/  /' || echo "  (ufw 상태 확인은 sudo 필요)"
fi
if command -v firewall-cmd >/dev/null 2>&1; then
  echo "  --- firewalld ---"
  sudo -n firewall-cmd --list-all 2>/dev/null | sed 's/^/  /' || echo "  (firewalld 상태 확인은 sudo 필요)"
fi
if ! command -v ufw >/dev/null && ! command -v firewall-cmd >/dev/null; then
  echo "  iptables/nftables (수동 확인 필요)"
fi

# 7. 시스템 자원
H "7. 시스템 자원"
echo "  CPU:        $(grep -c processor /proc/cpuinfo) cores"
echo "  메모리:     $(free -h | awk '/^Mem:/ {print $2 " (사용 " $3 ", 가용 " $7 ")"}')"
echo "  디스크 /:   $(df -h / | awk 'NR==2 {print $4 " 가용 / " $2 " 전체"}')"

# 8. SSH 설정 확인 (sync_to_cloud.ps1에 필요)
H "8. SSH 접속 가능 여부 (Windows에서 sync 하려면 필수)"
if systemctl is-active --quiet ssh 2>/dev/null || systemctl is-active --quiet sshd 2>/dev/null; then
  echo -e "  SSH 데몬:   ${GREEN}동작 중${NC}"
  PORT=$(grep -E '^\s*Port\s' /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' | head -1)
  echo "  SSH 포트:   ${PORT:-22}"
  echo
  echo -e "  ${YELLOW}-> 대표 PC에서 SSH 키 등록 후 다음 동작:${NC}"
  echo "       ssh-copy-id -i <pubkey> ubuntu@$(hostname -I | awk '{print $1}')"
  echo "       (Windows OpenSSH는 ssh-copy-id 없음 - 대신 PowerShell 1줄)"
else
  echo -e "  ${RED}SSH 데몬 미동작${NC}"
  echo "  설치: sudo apt install openssh-server && sudo systemctl enable --now ssh"
fi

# 9. 외부 접속 테스트 안내
H "9. 외부 접속 테스트 (수동)"
cat <<EOF
  공인 IP가 외부에서 80/443 으로 도달 가능한지:
  1) 휴대폰을 LTE/5G 로 (회사 와이파이 끊기)
  2) 브라우저에서 http://${PUBIP:-[공인IP]}  접속
  3) 80 막혔으면 5050 으로: http://${PUBIP:-[공인IP]}:5050
  4) 둘 다 안되면 라우터 포트포워딩 미설정 또는 ISP 차단
EOF

# 10. 결정 체크리스트
H "10. 가비아 + SSL 진행 전 확인 사항"
cat <<EOF
  [ ] 공인 IP 정적인지 확인
       -> ISP 콜센터, 인터넷 청구서. 동적이면 1~3개월에 변경 가능
       -> 정적 신청(월 ~1~3만원) 또는 DDNS

  [ ] 회사 라우터 포트포워딩
       -> 외부 80   -> 사내서버 LAN:80
       -> 외부 443  -> 사내서버 LAN:443
       -> 외부 22   -> 사내서버 LAN:22 (SSH, 사무실 IP만 허용 권장)

  [ ] ISP 가 80/443 인바운드 허용하는지
       -> 일부 가정·기업 회선은 80 차단. 막히면 8443 우회

  [ ] 24/7 가동 + UPS
       -> 정전 시 자동 시작 BIOS 설정
       -> 야간 자동 재부팅 정책 없는지

  [ ] SSL 발급 (deploy/setup_server_dev.sh 가 자동 처리)
       -> Let's Encrypt + certbot (무료, 90일 자동갱신)
       -> 가비아 SSL 구매(연 ~3만~)는 필요 없음

  [ ] sudo 권한 확인
       -> setup_server_dev.sh 실행에 sudo 필요
EOF

echo
echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}  결과 전체를 빅터에게 복사해서 붙여주세요.${NC}"
echo -e "${GREEN}===============================================${NC}"
echo
