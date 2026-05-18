# 📋 서버 담당자 작업 지시서 — KNK 메신저 HTTPS 전환

**작성일**: 2026-05-12
**예상 소요시간**: 30~40분
**난이도**: 중급 (네트워크 + Synology DSM)
**작업 범위**: 라우터 포트 개방 + Synology DSM 인증서 발급 + Reverse Proxy 설정
**작업 후 효과**: 모든 직원이 `https://o.knknara.co.kr/` 로 안전하게 접속 가능. iPhone Chrome 호환성 문제 해결.

---

## 🎯 작업의 배경 (먼저 읽어주세요)

### 현재 상태
- KNK 메신저는 Synology NAS 위 **Docker 컨테이너 (Ubuntu 20.04, host network 모드)** 가동
- 컨테이너 안에서 `gunicorn` 이 `0.0.0.0:5050` 으로 실행
- **host network 모드라서 NAS 호스트(DSM) 입장에서 `localhost:5050` 으로 메신저 직접 도달 가능**
- 라우터에서 **외부 80, 443 → NAS 80, 443 매핑은 이미 완료** (2026-05-12 대표 확인)
- 도메인 `o.knknara.co.kr` 의 A 레코드는 회사 공인 IP 로 이미 등록됨 (DNS 정상)
- 기존 외부 `:3310` 매핑은 라우터 변경 시 제거됨 → 현재 베타 사용자 접속 영향 있을 수 있음 (별도 복구 필요 시 빅터에게 알림)

### 왜 HTTPS 가 필요한가
1. **iPhone Chrome 이 HTTP 사이트 차단**: 일부 iOS 환경에서 흰 화면만 나오고 연결 안 됨 (현재 발생 중)
2. **모바일 Push 알림 활성화**: HTTPS 가 아니면 Service Worker Push 권한 못 받음
3. **PWA 정식 설치**: 일부 브라우저는 HTTP 사이트의 "앱 설치" 자동 제안 차단
4. **베트남 법인 정식 합류 직전 필수**: 외부망 평문 전송은 보안 정책상 불가
5. **카카오톡 in-app 브라우저는 작동하지만 일반 브라우저(Safari/Chrome)에서 차단**

### 이 작업으로 무엇이 바뀌나
- 신규 외부 진입점: `https://o.knknara.co.kr/` (TLS 1.2/1.3, 자물쇠 아이콘)
- DSM 의 Let's Encrypt 무료 인증서가 90일마다 자동 갱신 (수동 관리 X)
- 기존 `http://o.knknara.co.kr:3310/` 도 당분간 같이 동작 (즉시 끊지 않음 — 롤백 안전망)

---

## 📐 작업 흐름도

```
[신규 HTTPS 경로 — 이번 작업으로 추가]
사용자 → 인터넷 :443  → 회사 공유기 → NAS 호스트 :443 (DSM nginx + TLS 종단)
                                          │
                                          ↓ (DSM Reverse Proxy)
                                          NAS 호스트 :5050 (= Docker 컨테이너의 gunicorn, host network 모드)

* 인증서 발급용: 인터넷 :80 → 회사 공유기 → NAS 호스트 :80 (DSM nginx, ACME 챌린지 응답)
```

---

## ✅ 사전 점검 체크리스트 (작업 시작 전)

서버 담당자가 미리 확인:

- [ ] **Synology NAS 모델·DSM 버전 확인**
  - DSM 좌상단 로고 클릭 → DSM 정보 → 버전 (예: DSM 7.2-64570)
  - **DSM 7.x 기준으로 이 가이드 작성됨**. DSM 6.x 라면 메뉴 위치가 약간 다름 (별도 문의)

- [ ] **DSM 관리자 계정 보유** (admin 권한 필수)

- [ ] **회사 공유기 관리자 계정** (포트 포워딩 설정용)
  - 공유기 모델 알면 좋음 (iptime/asus/netgear 등)
  - 공유기 관리자 페이지 URL 확인 (보통 `192.168.x.1` 또는 `192.168.x.254`)

- [ ] **공인 IP 확인 + DNS 매핑**
  - 가비아 DNS 콘솔에서 `o.knknara.co.kr` A 레코드가 회사 공인 IP 가리키는지 확인
  - PowerShell 또는 cmd 에서 `nslookup o.knknara.co.kr` 실행 → 회사 공인 IP 나와야 함

- [ ] **NAS 내부 IP 확인**
  - DSM 제어판 → 정보 센터 → 네트워크 → IPv4 주소 (예: `192.168.12.5`)

- [ ] **현재 포트 사용 상황 확인**
  - 80 / 443 포트가 다른 서비스(웹 스테이션·Photo Station 등)에 점유 안 됐는지
  - DSM 제어판 → 정보 센터 → 서비스 → 네트워크 포트 (또는 "패키지" 의 Web Station 실행 여부)

- [ ] **이 가이드 1회 통독 후 시작**

---

# 🛠 1단계: 회사 공유기 포트 포워딩 (이미 완료됨 — 검증만)

**대표님이 2026-05-12 라우터에 80/443 포워딩을 이미 완료**했고, 빅터가 외부에서 도달 가능함을 검증했습니다 (HTTP 200, nginx 응답). 본 단계는 **검증만** 하시면 됩니다.

확인사항:
- 외부 80 → NAS 80 매핑 ✅
- 외부 443 → NAS 443 매핑 ✅
- 외부 IP `106.243.113.236` (회사 공인 IP) 의 80/443 OPEN ✅

## 1.5 검증 (외부에서 1회 확인)

다른 위치(예: 휴대폰 LTE/5G — Wi-Fi 끄고)에서:

```
브라우저로 http://o.knknara.co.kr/ 접속
```

- ❌ "사이트에 연결할 수 없음" → 포트 80 외부 노출 실패 → 1.3 다시 확인
- ✅ 페이지가 떠도 안 떠도 됨 (이 시점엔 503 또는 빈 페이지 정상). **연결 자체가 성공해야 함**

추가 검증 도구 (외부 서비스):
- https://www.yougetsignal.com/tools/open-ports/ → 포트 입력 80, 443 → 회사 공인 IP → "open" 표시되어야 함

---

# 🔐 2단계: Synology DSM Let's Encrypt 인증서 발급 (5분)

## 2.1 DSM 접속

1. 브라우저로 DSM 접속 (보통 `http://NAS_내부IP:5000` 또는 `https://NAS_내부IP:5001`)
2. admin 계정 로그인

## 2.2 인증서 메뉴 진입

**제어판** 아이콘 클릭 → 좌측 **보안** → **인증서** 탭

화면 구성:
- 상단 도구막대: **추가** / **편집** / **삭제** / **갱신** / **설정** 버튼
- 중앙: 기존 인증서 목록 (보통 `synology.com` 자체서명 1개 있음)

## 2.3 새 인증서 추가

**추가** 버튼 클릭

마법사 시작:

### 화면 1: 작업 선택
- ⦿ **새 인증서 추가** 선택
- **다음** 클릭

### 화면 2: 인증서 선택
- ⦿ **Let's Encrypt 에서 인증서 받기** 선택
- ☑ **기본값으로 설정** 체크 (DSM 자체 접속도 같은 인증서 사용)
- **다음** 클릭

### 화면 3: 도메인 정보 입력

| 항목 | 입력값 | 비고 |
|---|---|---|
| **도메인 이름** | `o.knknara.co.kr` | 정확히 입력. 대소문자 X. 공백 X |
| **이메일** | `admin@knknara.co.kr` | 인증서 만료 알림 받을 이메일. 실제 받는 주소로. |
| **주제 대체 이름 (SAN)** | (비워둠) | 다른 서브도메인도 같이 받을 때만 사용. 지금은 X |

- **적용** 클릭

## 2.4 발급 대기

- 30초~2분 정도 대기. DSM 이 자동으로:
  1. ACME (Let's Encrypt) 서버에 도메인 인증 요청
  2. Let's Encrypt 가 `http://o.knknara.co.kr/.well-known/acme-challenge/<random>` 으로 도전 파일 요청
  3. DSM 내부 nginx 가 port 80 으로 도전 응답
  4. 검증 성공 시 인증서 발급

## 2.5 결과 확인

- ✅ **성공**: 인증서 목록에 `o.knknara.co.kr` 추가됨. 발급자: `Let's Encrypt Authority X3` (또는 `R3`). 유효기간 3개월
- ❌ **실패** — 주요 원인:
  - "도메인 검증 실패" → 외부에서 port 80 도달 안 됨. 1단계 라우터 포트 80 다시 점검.
  - "DNS 조회 실패" → 가비아 DNS A 레코드 미설정 또는 미반영. `nslookup o.knknara.co.kr` 로 확인.
  - "Rate limit" → 같은 도메인으로 1주일에 5회 이상 시도 시 발생. 24시간 대기.

---

# 🔁 3단계: DSM Reverse Proxy 설정 (5분)

이제 외부 HTTPS 요청을 Docker 컨테이너 안의 메신저로 전달하는 다리를 설정합니다.

## 3.1 메뉴 진입

DSM 7.x 기준:
**제어판** → **로그인 포털** → 상단의 **고급** 탭 → **역방향 프록시** 버튼

DSM 6.x 라면:
**제어판** → **응용 프로그램 포털** → **역방향 프록시** 탭

## 3.2 신규 규칙 생성

**생성** 버튼 클릭 → 다이얼로그 오픈

## 3.3 [일반] 탭

### 역방향 프록시 이름
```
KNK 메신저 (o.knknara.co.kr)
```

### 소스 (Source) — 외부에서 들어오는 요청

| 항목 | 값 |
|---|---|
| 프로토콜 | **HTTPS** |
| 호스트 이름 | `o.knknara.co.kr` |
| 포트 | `443` |
| ☑ **HSTS 활성화** | 체크 (브라우저가 HTTPS 강제하게) |
| HTTP/2 활성화 | 체크 권장 |
| 액세스 제어 프로필 | (비워둠) |

### 목적지 (Destination) — 안쪽 메신저로 전달

| 항목 | 값 |
|---|---|
| 프로토콜 | **HTTP** |
| 호스트 이름 | `localhost` |
| 포트 | **`5050`** |

⚠️ **핵심**: KNK 메신저 컨테이너는 **host network 모드**로 동작 중. 즉 컨테이너의 `:5050` 이 NAS 호스트의 `:5050` 과 동일. DSM 입장에서 `localhost:5050` 으로 직접 접근 가능.

#### 사전 검증 (선택, DSM SSH 또는 컨테이너 안에서)
```bash
curl -fsI http://localhost:5050/login | head -3
# HTTP/1.1 302 FOUND  또는 HTTP/1.1 200 OK 가 나오면 OK
```

## 3.4 [사용자 정의 헤더] 탭 — WebSocket 활성화 (필수!)

KNK 메신저는 실시간 메시지를 위해 Socket.IO (WebSocket) 사용. 이 헤더 없으면 메시지 실시간 수신 불가.

1. **만들기** 버튼 클릭 → 드롭다운에서 **WebSocket** 선택
2. 자동으로 헤더 2개 추가됨:

| 헤더 이름 | 값 |
|---|---|
| `Upgrade` | `$http_upgrade` |
| `Connection` | `$connection_upgrade` |

만약 WebSocket 자동 추가 옵션이 없으면 **만들기** 로 위 2개 헤더를 수동 추가.

추가로 다음 헤더도 권장 (수동 추가):

| 헤더 이름 | 값 | 용도 |
|---|---|---|
| `X-Forwarded-For` | `$proxy_add_x_forwarded_for` | 메신저가 진짜 클라이언트 IP 알게 (로그·rate limit) |
| `X-Forwarded-Proto` | `$scheme` | 메신저가 HTTPS 인지 알게 (쿠키 SECURE 처리) |
| `X-Real-IP` | `$remote_addr` | 위와 동일 |
| `Host` | `$host` | Host 헤더 유지 |

## 3.5 [고급 설정] 탭

| 항목 | 값 | 이유 |
|---|---|---|
| **최대 업로드 크기** | `600M` (또는 `600` MB) | 도면·사진 파일 업로드 위해. 기본은 너무 작음 |
| Proxy 연결 시간 초과 | `600` 초 | 대용량 업로드 중 타임아웃 방지 |
| Proxy 읽기 시간 초과 | `600` 초 | 위와 동일 |
| Proxy 전송 시간 초과 | `600` 초 | 위와 동일 |

## 3.6 [인증서] 탭

이 화면에서 `o.knknara.co.kr` 의 인증서가 자동으로 매핑됐는지 확인.
만약 비어있거나 다른 인증서면:
- DSM 좌측 메뉴 → **인증서** 탭 (역방향 프록시 화면 안의 상단 탭) → **설정** 버튼
- `o.knknara.co.kr` → 인증서 드롭다운에서 방금 2단계에서 발급한 인증서 선택 → 확인

## 3.7 저장

**저장** 클릭 → 역방향 프록시 목록에 추가된 것 확인

## 3.8 즉시 검증

회사 외부망(LTE) 휴대폰 또는 외부 서버에서:

```
https://o.knknara.co.kr/
```

- ✅ KNK 메신저 로그인 페이지가 뜨면서 자물쇠 아이콘 → **성공**
- ❌ "ERR_CONNECTION_REFUSED" → 포트 443 미개방. 1단계 다시.
- ❌ "ERR_CERT_AUTHORITY_INVALID" → 인증서 매핑 실패. 3.6 다시.
- ❌ "502 Bad Gateway" → Reverse Proxy 는 동작하나 컨테이너 5050 이 응답 X. 빅터에게 알림.
- ❌ "504 Gateway Timeout" → 컨테이너가 살아있으나 응답 느림. 빅터에게 알림.

---

# 🔄 4단계: 메신저 production 모드 전환

**이 단계는 빅터(Claude)가 자동 수행**합니다. 1~3단계가 정상 완료되면 서버 담당자가 빅터에게 알려주세요. 빅터가:

1. 메신저의 `.env` 파일을 `KNK_MSG_ENV=production` 으로 변경
2. CORS 화이트리스트를 `https://o.knknara.co.kr` 로 제한
3. 세션 쿠키에 SECURE 플래그 활성 (HTTPS 강제)
4. HSTS·X-Frame-Options·CSP 등 보안 헤더 활성
5. 메신저 재시작 (supervisorctl restart)
6. 자동 검증

서버에 이미 업로드된 스크립트로 한 줄 실행 가능:
```bash
ssh root@o.knknara.co.kr -p 31201 bash /opt/knk_messenger/deploy/flip_to_production.sh
```

---

# ✔ 5단계: 최종 검증 체크리스트

빅터가 4단계 끝낸 후 서버 담당자가 다음 모두 확인 — 1개라도 ❌ 면 빅터에게 알림.

## 5.1 외부망 (LTE/5G — Wi-Fi 끄고) 또는 회사 외부

- [ ] `https://o.knknara.co.kr/` 접속 시 자물쇠 아이콘 표시
- [ ] 로그인 페이지 정상 로드
- [ ] 로그인 (`top0015 / 35401552`) 후 대화방 목록 표시
- [ ] 메시지 입력·전송 정상
- [ ] 사진 1장 업로드 정상

## 5.2 iPhone Chrome (기존 문제 검증)

- [ ] iPhone Chrome 에서 `https://o.knknara.co.kr/` 접속 → **정상** (기존 흰 화면 문제 해결됨을 확인)
- [ ] iPhone Safari 에서도 동일하게 정상

## 5.3 PWA 재설치

기존 `http://o.knknara.co.kr:3310` 으로 설치한 PWA 는 삭제 후 새 HTTPS 주소로 재설치 권장.
- [ ] PWA 설치 (Edge: 주소창 오른쪽 컴퓨터+화살표 아이콘 / Chrome: 메뉴 → 앱 설치)
- [ ] 바탕화면 아이콘으로 실행 → 자체 창으로 정상 표시

## 5.4 Socket.IO 실시간

- [ ] PC + 휴대폰 동시 로그인 → 한쪽에서 메시지 보내면 다른 쪽에 1초 이내 표시
- [ ] (이게 실패하면 3.4 WebSocket 헤더 누락. DSM Reverse Proxy 헤더 다시 확인)

## 5.5 인증서

브라우저에서 자물쇠 클릭 → 인증서 정보:
- [ ] 발급자: Let's Encrypt
- [ ] 유효 기간: 약 3개월 미만
- [ ] 도메인: `o.knknara.co.kr`

## 5.6 기존 HTTP 도 살아있는지 (롤백 안전망)

- [ ] `http://o.knknara.co.kr:3310/` 도 여전히 접속 가능 (기존 PWA 유지용)

---

# 🚨 트러블슈팅 (자주 발생하는 문제)

## A. "Let's Encrypt 인증서 발급 실패"

| 에러 메시지 | 원인 | 해결 |
|---|---|---|
| `Domain validation failed` | 외부 → port 80 → NAS 도달 실패 | 1.5 검증 다시. 라우터 + 방화벽 |
| `DNS_PROBLEM` | DNS A 레코드 미반영 | 가비아 DNS 콘솔 확인. `nslookup o.knknara.co.kr` |
| `Connection refused` | NAS 자체에서 port 80 사용 안 함 | DSM nginx 가 80 듣고 있는지: `sudo netstat -tlnp \| grep :80` |
| `Rate limit exceeded` | 1주 5회 초과 시도 | 24시간 대기 |
| `Some challenges failed` | DSM 자체 web station 이 80 점유 | Web Station 임시 정지 후 재시도 |

## B. "Reverse Proxy 설정했는데 502/504"

- 컨테이너 안의 gunicorn 동작 여부 (컨테이너 SSH):
  ```bash
  ssh root@o.knknara.co.kr -p 31201 "supervisorctl status knk-messenger"
  # RUNNING 안 보이면 빅터에게 알림 (재시작 필요)
  ```
- NAS 호스트(DSM)에서 메신저에 도달 가능한지 (DSM SSH):
  ```bash
  curl -fsI http://localhost:5050/login
  # HTTP/1.1 302 FOUND 안 나오면 → 컨테이너 죽었거나 host network 설정 변경됨. 빅터에게 알림.
  ```

## C. "메시지 보내도 실시간 수신 안 됨 (5초 후에 보임)"

- WebSocket 헤더 누락. 3.4 다시 확인
- 브라우저 개발자 도구 → Network → WS 탭 → Socket.IO 연결 상태 확인 (101 Switching Protocols 떠야 정상)

## D. "iPhone 에서만 안 됨"

- iPhone 의 Private Relay 켜져있는지 확인 (설정 → Apple ID → iCloud → Private Relay → 끄기)
- iPhone 캐시 삭제: 설정 → Safari → 방문 기록 및 웹 사이트 데이터 지우기

## E. "라우터에서 포트 포워딩 했는데 외부에서 안 됨"

- 일부 인터넷 회선은 회사 공인 IP 가 NAT 뒤에 있음 (이중 NAT). ISP 에 "공인 IP 직접 할당" 요청 필요.
- 회사 방화벽 (UTM 장비) 이 따로 있으면 거기서도 80, 443 허용 필요.
- 회사 IP 가 동적이면 → DDNS 설정 필요 (별도 작업)

## F. "DSM 메뉴가 가이드와 다름"

- DSM 6.x 라면 메뉴 이름 약간 다름 — 빅터에게 DSM 버전 알려주면 6.x 용 가이드 작성 가능

---

# 📞 빅터에게 문의 시 알려줄 정보

문제 발생해서 빅터에게 알릴 때 다음 정보 같이 주시면 빠른 진단 가능:

1. **현재 단계**: 1단계 / 2단계 / 3단계 / 검증 중 어디서 막혔는지
2. **에러 메시지** (정확한 텍스트 또는 스크린샷)
3. **시도한 것** (포트 다시 확인했다 / Reverse Proxy 다시 만들었다 등)
4. **DSM 버전** (DSM 정보에서 확인한 정확한 버전 번호)
5. **공유기 모델** (iptime/asus/...)
6. **현재 외부에서 도달 가능한 포트**:
   - `nmap -p 80,443,3310 o.knknara.co.kr` 외부에서 실행한 결과 (있다면)
   - 또는 https://www.yougetsignal.com/tools/open-ports/ 결과

---

# 📂 관련 파일 위치

서버 (`/opt/knk_messenger/`):
- `deploy/flip_to_production.sh` — production 자동 전환 (빅터 실행)
- `deploy/rollback_https.sh` — 롤백 (만약 문제 발생 시)
- `deploy/HTTPS_전환_가이드.md` — 빅터용 간이 가이드
- `deploy/서버담당자_HTTPS_작업서.md` — 이 문서
- `.env` — 환경변수 (KNK_MSG_ENV 등)

---

# ⏱ 작업 시간 가이드

| 작업 | 시간 | 누가 |
|---|---|---|
| 1. 라우터 포트 포워딩 | 5~10분 | 서버 담당자 |
| 1.5 검증 (외부망) | 2분 | 서버 담당자 |
| 2. DSM 인증서 발급 | 3~5분 | 서버 담당자 |
| 3. DSM Reverse Proxy | 5분 | 서버 담당자 |
| 3.8 검증 | 2분 | 서버 담당자 |
| 4. production 전환 | 즉시 | 빅터 |
| 5. 최종 검증 | 10분 | 서버 담당자 + 빅터 |
| **합계** | **약 30~40분** | |

---

# 🎬 작업 순서 요약 (한 페이지 요약)

```
[1] 라우터 포트 포워딩 — 80/443 ✅ 이미 완료 (대표 2026-05-12)
    └ 외부망에서 http://o.knknara.co.kr/ 접속해서 nginx 응답 받으면 OK

[2] DSM → 제어판 → 보안 → 인증서 → 추가
    └ Let's Encrypt 선택
    └ 도메인 o.knknara.co.kr / 이메일 입력 → 적용
    └ 발급 완료 확인

[3] DSM → 제어판 → 로그인 포털 → 고급 → 역방향 프록시 → 생성
    └ 소스: HTTPS / o.knknara.co.kr / 443
    └ 목적지: HTTP / localhost / 5050   ← (host network 모드 — 그대로)
    └ 사용자 정의 헤더 → WebSocket 추가
    └ 고급 → 최대 업로드 600M
    └ 저장
    └ 외부망에서 https://o.knknara.co.kr/ 접속 확인

[4] 빅터에게 "DSM 작업 완료" 알림
    └ 빅터가 메신저 production 전환 + 재시작 + 검증

[5] 최종 5중 검증 통과 → 종료
```

---

**작성**: 빅터 (Claude — KNK 메신저 개발팀)
**문의**: 빅터 또는 김정락 대표이사
