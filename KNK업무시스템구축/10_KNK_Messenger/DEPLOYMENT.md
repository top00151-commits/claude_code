# KNK Messenger 운영 배포 가이드

대표 결재 (2026-05-05): 클라우드 안정형, 베트남법인 동시 사용.

## 추천 호스팅 비교 (KR + VN 동시 사용 기준)

| 옵션 | 월 비용 | KR latency | VN latency | 데이터 거주 | 신뢰성 | 추천도 |
|---|---|---|---|---|---|---|
| **AWS Lightsail Tokyo** ($10/월) | ₩14,000 | ~30ms | ~70ms | 일본 | SLA 99.95% | ★★★ 단순·저렴 |
| **NCP Compact** | ₩30,000~ | ~5ms | ~80ms | **한국** | SLA 99.9% | ★★★ KR 우선 |
| AWS EC2 Seoul (t3.small) | $15~ | ~5ms | ~80ms | 한국 | SLA 99.99% | ★★ 비싸짐 |
| Oracle Always Free (Tokyo) | ₩0 | ~30ms | ~70ms | 일본 | 베스트에포트 | ★ 신청 어려움 |
| 사무실 PC | ₩0 | LAN | VPN 필요 | 사무실 | 정전·재부팅 위험 | ✗ |

**최종 추천: AWS Lightsail Tokyo ($10/월)** — 한국 빠르고, 베트남도 빠르고, 일본은 한국 기업 데이터 거주 정책상 자주 허용됨. 단순한 콘솔 + 자동 백업($1/월 추가).

> KR 데이터 거주가 법무·고객 요구로 강제되는 경우만 NCP. 그 경우 비용 약 2배.

## 사전 준비

1. **도메인** — 카페24/가비아 등에서 `knk.kr` 또는 `messenger.knk.co.kr` (서브도메인 권장)
2. **AWS 계정** — Lightsail 인스턴스 1개
3. **SSL** — Let's Encrypt 무료 (certbot)
4. **VPN** (선택) — 직원 외부 접속 차단 시 OpenVPN 또는 WireGuard

## Lightsail 인스턴스 1회 셋업

```bash
# 1. Lightsail Tokyo region에 Ubuntu 22.04 LTS / $10 plan 인스턴스 생성
# 2. 정적 IP 부여
# 3. 방화벽: 80, 443 만 공개. 5050 차단

# 인스턴스 SSH 접속 후:
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv git nginx certbot python3-certbot-nginx ufw

# Python 환경
mkdir -p /opt/knk_messenger && cd /opt/knk_messenger
git clone <your private repo> .   # 또는 scp 로 코드 업로드
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt gunicorn

# systemd 서비스
sudo tee /etc/systemd/system/knk-messenger.service > /dev/null <<'EOF'
[Unit]
Description=KNK Messenger
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/knk_messenger
Environment="KNK_MSG_SECRET=PRODUCTION_RANDOM_SECRET_HERE_32_CHARS"
Environment="KNK_MSG_RETENTION_MONTHS=12"
ExecStart=/opt/knk_messenger/.venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:5050 app:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now knk-messenger
```

## Nginx 리버스 프록시 + SSL

```nginx
# /etc/nginx/sites-available/knk-messenger
server {
    listen 80;
    server_name messenger.knk.co.kr;
    client_max_body_size 30M;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5050;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/knk-messenger /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d messenger.knk.co.kr   # SSL 자동 설정 + auto-renewal
```

## 자동 백업

```bash
# /opt/knk_messenger/backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M)
DEST=/opt/knk_messenger/backups
mkdir -p $DEST
sqlite3 /opt/knk_messenger/data/messenger.db ".backup $DEST/messenger_$DATE.db"
# 7일 이상 백업 삭제
find $DEST -name "messenger_*.db" -mtime +7 -delete
# S3 업로드 (선택)
# aws s3 sync $DEST s3://knk-messenger-backup/
```

```cron
# crontab -e
0 3 * * * /opt/knk_messenger/backup.sh
0 4 1 * * curl -X POST -b "session=..." https://messenger.knk.co.kr/api/admin/cleanup   # 매월 1일 보존정책 실행
```

## 보안 체크리스트

- [ ] `KNK_MSG_SECRET` 환경변수에 32자 랜덤 문자열 (운영 절대 노출 X)
- [ ] `app.py`의 `cors_allowed_origins="*"` → 실제 도메인으로 제한
- [ ] 방화벽 22(SSH)는 사무실 IP만 허용, 80/443은 공개
- [ ] fail2ban 설치 (SSH brute force 방어)
- [ ] HTTPS 외 HTTP 자동 redirect (Nginx 자동 설정)
- [ ] 정적 IP 부여 (Lightsail 무료 1개)
- [ ] 매주 `apt upgrade`로 패치
- [ ] DB 백업 별도 위치 (S3 / Google Drive 동기화)
- [ ] 직원별 강력 비밀번호 강제 + 첫 로그인 시 변경 (TODO)

## 베트남법인 접속

- 동일 URL (`https://messenger.knk.co.kr`) — 인터넷 통해서 접속
- 베트남 통신 환경상 ~70-100ms 응답, 채팅에 무리 없음
- VPN 필요 없음 (HTTPS면 충분)
- 화상회의 추가 시 별도 검토 (WebRTC TURN 서버 필요)

## 비용 요약 (KNK 약 140명 운영 가정)

| 항목 | 월 비용 |
|---|---|
| Lightsail $10 인스턴스 | ₩14,000 |
| 자동 백업 ($1) | ₩1,400 |
| 도메인 (.co.kr 연 ₩22,000) | ~₩1,800 |
| TestFlight Internal($99/년) | ~₩11,500 |
| **합계** | **약 ₩28,700/월** |

→ 카카오워크 Mini 140명 ₩406,000/월 vs **₩28,700/월 = 약 14배 절감**.

## 운영 모니터링

- 헬스체크: `curl https://messenger.knk.co.kr/login` → 200 확인
- 디스크 사용량 모니터링: `df -h` (60GB SSD 기준 매월 점검)
- 로그: `journalctl -u knk-messenger -f`
- 사용자 수 증가 시 → Lightsail $20 plan(4GB RAM) 업그레이드 고려
