# KNK Messenger 운영 배포 가이드

대표 결재 (2026-05-05): 클라우드 안정형, 베트남법인 동시 사용.

> **🚀 빠른 진행**: 이 문서 읽지 말고 [INTERNET_DEPLOY_CHECKLIST.md](INTERNET_DEPLOY_CHECKLIST.md) 한 페이지만 따라하세요. 모든 셋업이 `deploy/setup_server.sh` **명령어 한 줄**로 끝납니다.

---

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

1. **도메인** — 확정: `msg.knknara.co.kr` (knknara.co.kr 서브도메인, DNS A 레코드만 추가)
2. **AWS 계정** — Lightsail 인스턴스 1개
3. **SSL** — Let's Encrypt 무료 (certbot)
4. **VPN** (선택) — 직원 외부 접속 차단 시 OpenVPN 또는 WireGuard

## Lightsail 인스턴스 1줄 셋업 (2026-05-07 자동화 완료)

### 사전 준비 — 대표만 가능
1. Lightsail Tokyo region / Ubuntu 22.04 LTS / $10 plan 인스턴스 생성
2. 정적 IP 부여 (인스턴스에 attach)
3. 방화벽: 22(SSH 사무실IP만), 80, 443
4. 도메인 DNS A 레코드: `msg.knknara.co.kr → 정적IP`
5. SSH key 다운로드 + scp/git으로 코드를 `/opt/knk_messenger` 에 올리기

### 1줄 자동 셋업 — 빅터/관리자
```bash
ssh ubuntu@<정적IP>
cd /opt/knk_messenger
# 인터넷에서 개발하면서 검증 → 안정 후 운영 전환 (권장)
sudo bash deploy/setup_server_dev.sh msg.knknara.co.kr admin@knknara.co.kr

# 또는 처음부터 운영 모드
sudo bash deploy/setup_server.sh msg.knknara.co.kr admin@knknara.co.kr
```

이 한 줄이 처리하는 것:
- Python 3 + nginx + certbot + ufw + fail2ban + sqlite3 설치
- `/opt/knk_messenger/.venv` 생성 + requirements 설치
- `.env.production` 자동 생성 + SECRET 랜덤 채움
- systemd 서비스 (`/etc/systemd/system/knk-messenger.service`) 등록 + 시작
- nginx 사이트 (`__DOMAIN__` 자동 치환) 설정
- Let's Encrypt SSL 자동 발급 + HTTP→HTTPS 리다이렉트 + 90일 자동갱신
- UFW 방화벽 + fail2ban 활성
- 매일 03:00 백업 cron + 매월 1일 보존정책 cron

### 운영 명령어
```bash
sudo systemctl status knk-messenger      # 상태 확인
sudo systemctl restart knk-messenger     # 재시작
sudo journalctl -u knk-messenger -f      # 실시간 로그
bash /opt/knk_messenger/deploy/update.sh # 코드 업데이트 (자동 백업 + 재시작 + 헬스체크)
bash /opt/knk_messenger/deploy/backup.sh # 즉시 백업
```

## 배포 키트 파일 구조 (2026-05-07)

```
10_KNK_Messenger/
├── wsgi.py                            # gunicorn 진입점
├── requirements.txt                   # eventlet/gunicorn/pywebpush 포함
├── INTERNET_DEPLOY_CHECKLIST.md       # ⭐ 대표가 따라할 한 페이지 가이드
└── deploy/
    ├── setup_server.sh                # Ubuntu 1회 셋업 (전체 자동)
    ├── nginx.conf                     # __DOMAIN__ 치환 템플릿
    ├── knk-messenger.service          # systemd 유닛 (eventlet 워커)
    ├── backup.sh                      # 일일 백업 (DB 30일·uploads 7일)
    ├── update.sh                      # 코드 업데이트 (백업+pip+재시작+헬스)
    └── .env.production.example        # 환경변수 템플릿
```

각 파일의 역할은 `INTERNET_DEPLOY_CHECKLIST.md` 참고.

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

- 동일 URL (`https://msg.knknara.co.kr`) — 인터넷 통해서 접속
- 베트남 통신 환경상 ~70-100ms 응답, 채팅에 무리 없음
- VPN 필요 없음 (HTTPS면 충분)
- 화상회의 추가 시 별도 검토 (WebRTC TURN 서버 필요)

## 비용 요약 (KNK 약 140명 운영 가정)

| 항목 | 월 비용 |
|---|---|
| Lightsail $10 인스턴스 | ₩14,000 |
| 자동 백업 ($1) | ₩1,400 |
| 도메인 서브도메인 (knknara.co.kr 보유 시) | ₩0 |
| TestFlight Internal($99/년) | ~₩11,500 |
| **합계** | **약 ₩28,700/월** |

→ 카카오워크 Mini 140명 ₩406,000/월 vs **₩28,700/월 = 약 14배 절감**.

## 운영 모니터링

- 헬스체크: `curl https://msg.knknara.co.kr/login` → 200 확인
- 디스크 사용량 모니터링: `df -h` (60GB SSD 기준 매월 점검)
- 로그: `journalctl -u knk-messenger -f`
- 사용자 수 증가 시 → Lightsail $20 plan(4GB RAM) 업그레이드 고려
