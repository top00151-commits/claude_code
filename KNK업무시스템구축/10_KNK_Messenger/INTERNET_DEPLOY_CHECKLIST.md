# KNK Messenger 인터넷 운영 전환 체크리스트

대표가 위에서부터 차례로 진행. 각 단계 끝에 **빅터에게 보고할 출력**을 적어놨음. 막히면 그 출력을 그대로 빅터에게 붙여넣으면 됨.

진행 상태: **[ ] 대기 / [x] 완료 / [!] 막힘**

---

## A단계 — 결재·계약 (대표만 가능, 약 30분)

### A-1. 도메인 결정 [ ]
- 권장: `msg.knk.co.kr` (knk.co.kr 서브도메인)
- knk.co.kr 등록업체(가비아/카페24 등)에서 **DNS A 레코드** 추가만 하면 됨 (별도 비용 없음)
- 대안: `knkmsg.com` 같은 신규 도메인 (연 ~₩15,000)
- **결정 사항**: ___________________

### A-2. AWS 계정 [ ]
- 이미 KNK 명의 AWS 계정이 있으면 그 계정 사용
- 없으면 https://aws.amazon.com 에서 신규 가입 (개인 신용카드 등록 필요 — 빅터는 입력 못함)
- 가입 후 결제 통화 KRW 가능

### A-3. 백업 저장소 결정 [ ]
- (a) **S3 Tokyo** 월 ~$1, 자동 동기화. AWS 안에서 끝남.
- (b) 사내 NAS 동기화 — 별도 스크립트 필요
- 권장: (a)
- **결정 사항**: ___________________

### A-4. 시스템 메일 발신 [ ] (선택, 후순위)
- 비번 리셋·중요 알림용
- (a) Gmail SMTP (App Password) — 무료
- (b) AWS SES — 월 $0.10/1,000건
- 권장: (a) 베타 단계는 충분
- **결정 사항**: ___________________

---

## B단계 — Lightsail 인스턴스 (대표 약 15분, 빅터 도움 가능)

### B-1. 인스턴스 생성 [ ]
1. https://lightsail.aws.amazon.com 접속
2. **Region**: `Asia Pacific (Tokyo) ap-northeast-1` 선택
3. **Plan**: `OS Only / Ubuntu 22.04 LTS / $10 (2GB RAM)` 선택
4. **Instance name**: `knk-messenger-prod`
5. Create instance

### B-2. 정적 IP 부여 [ ]
1. Lightsail → Networking → Create static IP
2. Region 동일, Instance에 attach
3. 발급된 IP 메모: `___.___.___.___`
4. **빅터 보고**: 이 IP

### B-3. 방화벽 [ ]
1. 인스턴스 → Networking 탭
2. IPv4 Firewall:
   - SSH (22) — 가능하면 사무실 IP만 (Restrict)
   - HTTP (80) — Allow
   - HTTPS (443) — Allow
   - 그 외 모두 삭제

### B-4. SSH 키 다운로드 [ ]
1. Lightsail → Account → SSH keys
2. Default key 다운로드 (`LightsailDefaultKey-ap-northeast-1.pem`)
3. 저장 위치: `C:\Users\top00\.ssh\` (또는 본인이 기억할 곳)
4. 권한: 우클릭 → 속성 → 보안 → 본인 외 모두 제거 (Windows)

---

## C단계 — DNS 연결 (대표 약 5분)

### C-1. DNS A 레코드 추가 [ ]
도메인 등록업체(예: 가비아) 관리 콘솔에서:
- 호스트(서브도메인): `msg`
- 레코드 타입: `A`
- 값: B-2의 정적 IP
- TTL: 600

### C-2. 전파 확인 [ ]
PowerShell에서:
```powershell
nslookup msg.knk.co.kr 8.8.8.8
```
→ 정적 IP가 보이면 OK. 보통 5분~1시간 소요.

---

## D단계 — 코드 업로드 (빅터 또는 대표, 약 10분)

### D-1. SSH 접속 [ ]
```powershell
ssh -i "C:\Users\top00\.ssh\LightsailDefaultKey-ap-northeast-1.pem" ubuntu@<정적IP>
```
→ 처음 접속 시 yes 입력. 프롬프트 `ubuntu@ip-...:$` 나오면 OK.

### D-2. 코드 업로드 [ ]

**옵션 1 — scp (가장 간단)**: 새 PowerShell 창에서
```powershell
cd "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축"
scp -i "C:\Users\top00\.ssh\LightsailDefaultKey-ap-northeast-1.pem" `
    -r 10_KNK_Messenger ubuntu@<정적IP>:/tmp/messenger
```
업로드 끝나면 SSH 창에서:
```bash
sudo mkdir -p /opt/knk_messenger
sudo cp -r /tmp/messenger/. /opt/knk_messenger/
sudo chown -R ubuntu:ubuntu /opt/knk_messenger
```

**옵션 2 — git private 저장소**: GitHub에 private repo 만들고 deploy key 등록 후
```bash
sudo git clone git@github.com:knk/messenger.git /opt/knk_messenger
sudo chown -R ubuntu:ubuntu /opt/knk_messenger
```

### D-3. data/ 비우기 [ ] (테스트 데이터 운영 유입 방지)
```bash
rm -rf /opt/knk_messenger/data/messenger.db
rm -rf /opt/knk_messenger/data/uploads/*
rm -rf /opt/knk_messenger/backups/*
```
→ 첫 실행 시 빈 DB로 새로 init 됨. 시드 사용자(kjr/hong/lee)만 자동 생성.

---

## E단계 — 1줄 셋업 (빅터, 약 5분)

### E-1. 셋업 스크립트 실행 [ ]
SSH 창에서:
```bash
cd /opt/knk_messenger
sudo bash deploy/setup_server.sh msg.knk.co.kr admin@knk.kr
```
(도메인·이메일은 본인 것으로)

이 명령 하나가 다음을 모두 처리:
- python3 + nginx + certbot + ufw + fail2ban 설치
- venv + requirements 설치
- `.env.production` 자동 생성 (SECRET 자동 채움)
- systemd 서비스 등록 + 시작
- nginx 사이트 설정 + reload
- Let's Encrypt SSL 발급 + 자동갱신
- UFW 방화벽 활성화
- cron 백업 등록

마지막에 `셋업 완료!` 출력 + `https://msg.knk.co.kr` 줄이 보이면 성공.

### E-2. 브라우저 접속 [ ]
- `https://msg.knk.co.kr` → 자물쇠 아이콘 ✓ + 로그인 화면
- 시드 계정: `kjr` / `knk1234`
- **막히면 빅터에게 보고**: `sudo journalctl -u knk-messenger -n 50` 출력 그대로

---

## F단계 — 운영 안전망 (빅터, 약 10분)

### F-1. UptimeRobot 등록 [ ]
- https://uptimerobot.com 무료 가입
- New monitor → HTTP(s) → URL: `https://msg.knk.co.kr/healthz`
- 5분 간격 → 다운 시 이메일 발송

### F-2. 백업 동작 확인 [ ]
SSH에서 즉시 1회 실행:
```bash
bash /opt/knk_messenger/deploy/backup.sh
ls -lh /opt/knk_messenger/backups/
```
→ `messenger_20260507_*.db` 파일 보이면 OK.

### F-3. (선택) S3 백업 연결 [ ]
A-3에서 (a) 선택했으면:
1. AWS S3 → 버킷 생성 `knk-messenger-backup` (Tokyo)
2. IAM → 사용자 생성 → S3 PutObject 권한만
3. 액세스 키 발급 → 서버에 `aws configure`
4. `.env.production` 에 `KNK_BACKUP_S3=s3://knk-messenger-backup/` 추가
5. `sudo systemctl restart knk-messenger`

---

## G단계 — 사용자 전환 (대표, 1주)

### G-1. 본인 단독 사용 (1~2일) [ ]
- PC + 휴대폰에서 `https://msg.knk.co.kr` 접속
- PWA 설치 (Android: 메뉴 → 홈화면 추가, iOS: 공유 → 홈화면 추가)
- 어색한 점 발견 → 빅터에게 즉시 보고

### G-2. 기술영업팀 합류 (3~5일) [ ]
- 6명에게 URL + ID/임시비번 안내 (시드: lhr, lh, okh, bsj, ajy, lsr / 모두 `knk1234`)
- 카톡 그룹과 병행, 자료는 우리 메신저에 업로드
- 만족도·문제점 수집

### G-3. 베트남법인 합류 (6일~) [ ]
- 동일 URL — VPN 불필요
- 한/베 이중 안내 메일 (빅터가 초안 작성)
- 응답속도 (~70-100ms) 체감 확인

### G-4. 카톡 → 메신저 전환 공지 (만족 시) [ ]
- 카톡 전사 공지: "신규 자료는 메신저로, 카톡은 1개월 읽기전용 병행"
- 1개월 후 카톡 그룹 정리

---

## 비용 정산 (월)

| 항목 | 비용 |
|---|---|
| Lightsail Tokyo $10 | ₩14,000 |
| 정적 IP (인스턴스에 attach 시 무료) | ₩0 |
| 도메인 (.co.kr 서브도메인) | ₩0 |
| S3 백업 (~5GB) | ~₩1,400 |
| Let's Encrypt SSL | ₩0 |
| UptimeRobot | ₩0 |
| **합계** | **약 ₩15,400/월** |

카카오워크 Mini 140명 ₩406,000/월 대비 **26배 절감**.

---

## 비상시

| 증상 | 명령 |
|---|---|
| 사이트 안 열림 | `sudo systemctl status knk-messenger` |
| 502 Bad Gateway | `sudo journalctl -u knk-messenger -n 50` |
| nginx 설정 오류 | `sudo nginx -t` |
| SSL 갱신 실패 | `sudo certbot renew --dry-run` |
| DB 손상 의심 | `bash /opt/knk_messenger/deploy/backup.sh` 후 빅터 호출 |
| 디스크 가득 | `df -h` 확인 → 백업 보관 기간 줄이기 |

---

## 빅터 전권 가능 항목

빅터가 SSH 접근권 받으면 다음은 알아서 가능:
- 코드 갱신 (`update.sh`)
- 패키지 업데이트
- nginx 설정 변경
- 백업 검증
- 로그 분석
- 사용자 비번 리셋

대표 결재 필요: 도메인 변경, 인스턴스 사양 업그레이드, 신규 사용자 일괄 등록, 데이터 거주지 이전.
