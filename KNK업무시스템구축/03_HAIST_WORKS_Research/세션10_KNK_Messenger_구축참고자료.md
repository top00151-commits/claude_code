# 세션 10 (10_KNK_Messenger) 구축 참고자료

> **🔢 세션 번호 체계 (2026-04-21~)**: 00=감사 · 01=메인 · 02=baby · **03=Research(작성)** · 04=운영테스트 · 05=디자인 · 09=프로젝트팀장 · **10=KNK_Messenger(신규, 수신자)**
> **목적**: 세션 10이 자체 사내 메신저 구축 시 즉시 참조할 수 있는 사실·옵션·패턴 단일 자료
> **작성**: 2026-05-05, 03 Research 빅터
> **저장**: `KNK업무시스템구축/03_HAIST_WORKS_Research/세션10_KNK_Messenger_구축참고자료.md`
> **연계 자료**:
> - `외부연결_가이드_하이웍스_카카오워크.md` (2026-04-20, API/Bot/Webhook 깊이)
> - `기업용_메신저_비교_2026.md` (2026-05-05, 시장·가격 비교)
> - `memory/system_scope_policy.md` ("하이웍스 전자결제·메일 계속 사용" 정책)
>
> **03 권한 명시**: 본 자료는 **사실·옵션 제시**용. "KNK는 ~으로 가야 한다" 형태 권고 없음. 아키텍처 결정은 세션 10 + 09 + 대표.

---

## ⚠️ 현재 상태 — 2026-05-05 검증 (Greenfield 아님)

본 자료 작성 후 **세션 10 폴더 검증 결과**, 1단계 MVP가 **이미 가동 중**임을 확인:

**현 채택 스택** (`KNK업무시스템구축/10_KNK_Messenger/app.py` + `requirements.txt` 검증):
- **Flask 3.0+** (FastAPI 아님)
- **Flask-SocketIO 5.3+** (실시간) + **simple-websocket**
- **SQLite + FTS5** (PostgreSQL+Redis 아님 — 1단계 단일 파일 DB)
- 인증: Werkzeug `generate_password_hash`/`check_password_hash` + Flask session
- 포트: 5050 (`KNK_MSG_PORT` 환경변수)

**MVP에서 이미 구현된 것** (app.py 검증):
- ✅ users / rooms (direct·group·channel·**item**) / room_members / messages / **items** / **requests** 테이블
- ✅ FTS5 가상테이블 + 트리거 3종 (insert·delete·update)
- ✅ 첨부 4 컬럼 (file_path·file_name·file_size·file_mime), 25MB 제한
- ✅ 허용 확장자: 이미지 7종 + 문서/CAD/오피스/한글/압축/영상/음성 27종 (DWG·DXF·STEP·STP·STL 포함 — 제조 컨텍스트)
- ✅ unread 카운터 (`last_read_message_id`)
- ✅ 직접 메시지 중복 방지 로직
- ✅ 시드: 김정락 대표·홍길동·이순신 + 4개 아이템 (003M2501·WP-LOA·HM-001·M2504, 삼성전자/하나머티리얼)
- ✅ 시스템 메시지 (아이템 생성·상태 변경 자동 기록)

**메모리 명시 다음 단계** (`memory/project_knk_messenger.md` 인용):
> "다음: 사진/파일 → PWA → iOS Capacitor → WORKS 통합"

**본 참고자료의 재해석**:
- 자료 §A (Build vs Fork vs Buy 3대 경로) → 1단계 MVP 후 **확장 시점 참조**용 (예: 2~3단계 Phase에서 Mattermost로 전환 검토 시)
- 자료 §B (6개 컴포넌트) → **현재 SQLite 단일 → 다중 인스턴스 확장 시 PostgreSQL+Redis 패턴 참조**용
- 자료 §C (KNK 통합 포인트) → "WORKS 통합" 단계에서 **즉시 적용** 가능
- 자료 §D (한국형 패턴) → UI/UX·결재·webhook 보강 시 **즉시 참조** 가능
- 자료 §E (위험·함정 12개) → **현 단계에서 즉시 점검** 가능
- 자료 §F (5대 질문) → Q1·Q4는 이미 결정됨(Build / 메일 분리), Q2·Q3·Q5 미정

**Flask vs FastAPI 사실 비교** (스택 변경 검토 시 참고만, 권고 없음):
| 항목 | Flask + SocketIO (현재) | FastAPI + WebSocket |
|---|---|---|
| 학습 곡선 | 낮음 | 중간 |
| 비동기 | gevent/eventlet 의존 (threading 모드 사용 중) | 네이티브 async/await |
| 타입 안전성 | 낮음 | Pydantic 강제 |
| HAIST_WORKS 일관성 | (HAIST_WORKS가 FastAPI라면 분리됨) | (HAIST_WORKS가 FastAPI라면 일관) |
| 단일 인스턴스 ~수백명 | 충분 | 충분 |
| 다중 인스턴스 확장 | Redis adapter 추가 가능 | 동일 |

→ MVP가 작동하면 **스택 변경은 ROI 낮음**. 본 비교는 단순 사실 정리. 전환 결정은 세션 10 + 09 + 대표.

---

## 📋 목차

- [0. Executive Summary (3분 결정용)](#0-executive-summary-3분-결정용)
- [Part A. Build vs Fork vs Buy — 3대 경로](#part-a-build-vs-fork-vs-buy--3대-경로)
- [Part B. 핵심 시스템 컴포넌트 (6개)](#part-b-핵심-시스템-컴포넌트-6개)
- [Part C. KNK 통합 포인트 (HAIST_WORKS 연결)](#part-c-knk-통합-포인트)
- [Part D. 한국형·자체 메신저 모방 가능 패턴](#part-d-한국형자체-메신저-모방-가능-패턴)
- [Part E. 위험·함정·체크리스트 (Top 12)](#part-e-위험함정체크리스트-top-12)
- [Part F. 세션 10 의사결정 재료 (5대 질문)](#part-f-세션-10-의사결정-재료-5대-질문)
- [G. 출처 URL (전체)](#g-출처-url)

---

## 0. Executive Summary (3분 결정용)

### 0.1 핵심 사실 5가지

1. **자체 구축 메신저는 3가지 경로** — (A) 오픈소스 셀프호스팅 (Mattermost/Rocket.Chat/Zulip/Element), (B) 오픈소스 + 커스텀 플러그인, (C) FastAPI+WebSocket 처음부터.
2. **KNK 메인 스택 (FastAPI + PostgreSQL)** 과 **자체 구축 챗 앱 표준 스택**(FastAPI + WebSocket + Redis Pub/Sub + PostgreSQL)이 일치.
3. **140명 규모는 단일 서버로 충분** — Mattermost 기준 2 vCPU/4GB RAM/45GB 스토리지로 250~500명 지원 가능 (mattermost docs 인용).
4. **푸시 알림은 FCM 단일 통합** — Android는 FCM, iOS도 FCM이 APNs로 중계 → 백엔드는 FCM 1개 API만 호출하면 됨.
5. **한국어/베트남어 검색** — MySQL은 ngram 파서 필수(Mattermost docs 명시). PostgreSQL은 `pg_trgm` + 외부 형태소 분석기(Korean: MeCab-ko / Vietnamese: VnCoreNLP) 별도 통합 필요.

### 0.2 KNK 컨텍스트 (메모리·기존 자료 정리)

| 요소 | 상태 |
|---|---|
| 사용자 수 | 약 140명 (HAIST_WORKS 사용자) |
| 메인 스택 | FastAPI + PostgreSQL + pgvector (memory/knk_systems) |
| 정책 (system_scope_policy) | "하이웍스 전자결제·메일 유지" — 메신저는 자체 구축 가능 |
| 현재 알림 채널 | 카카오워크 webhook (system_scope_policy 허용) |
| 다국어 컨텍스트 | 한국어 + 베트남어 (KNKVN 자회사) |
| 사이클 적용 | v5H136까지 SO/PO/프로젝트 연결 진척, 알림 통합은 미정 |

### 0.3 3대 경로 한눈 비교

| 경로 | 구축 기간 (추정) | 라이선스 비용 | 커스터마이징 자유도 | KNK 적합도 (사실 관찰) |
|---|---|---|---|---|
| **A. 오픈소스 셀프호스팅 (수정 없이)** | 2~4주 | 무료 (Mattermost Team / Rocket.Chat Community) | 낮음 (외부 플러그인 한정) | UI/UX·결재 통합 즉시 가능 여부 ❓ |
| **B. 오픈소스 fork + 플러그인** | 6~12주 | 무료 + 개발 인건비 | 중간 (REST·webhook·Bot SDK 활용) | HAIST_WORKS 통합 + UI 일부 변경 |
| **C. FastAPI 처음부터** | 12~24주 | 무료 + 개발 인건비 | 최고 | 메인 스택 일치, 단 운영 부담 (E2E·푸시·검색·DR) |

→ **권고 없음**. 각 경로의 사실 비교는 [Part A](#part-a-build-vs-fork-vs-buy--3대-경로) 상세.

---

## Part A. Build vs Fork vs Buy — 3대 경로

### A.1 경로 A: 오픈소스 셀프호스팅 (수정 없이)

**4대 후보** (rocket.chat blog / mattermost docs / openalternative.co 인용):

| 도구 | 라이선스 | 강점 (원문 인용) | 약점 (관찰) |
|---|---|---|---|
| **Mattermost** | MIT (Team Edition) | "Slack design patterns 그대로—channels·threads·DMs·reactions·file sharing—no user limits" / "two containers (Mattermost + PostgreSQL), 5분 설치" | 결재 통합 별도 / 한국어 UI 번역 품질 자체 검증 필요 |
| **Rocket.Chat** | MIT (Community) | "more features than any other self-hosted" / "200+ apps marketplace" / "livechat·omnichannel·E2E·video" | 무겁다 평가 다수 / 100명 이하 권장 사양 미공식화 |
| **Zulip** | Apache 2.0 | "threaded conversations by topic—async remote teams favour" | 한국식 채팅 UX와 거리감 (스레드 우선) |
| **Element (Matrix)** | Apache 2.0 | "Federation core differentiator—외부 조직과 보안 통신·제어 양보 없음" / Olm·Megolm E2E 기본 | 운영 복잡도 높음 / Federation은 KNK 단일 회사엔 불필요 |

**시스템 요구사항** (mattermost docs 인용):
- 250~500명: 2 vCPU / 4GB RAM / 45~90GB 스토리지
- KNK 140명: 위 사양 내 충분 (단일 서버)
- MySQL 사용 시: **ngram Full-Text parser** 필수 (한국어·중국어·일본어 검색)

**설치 사례 (Rocket.Chat docs)**:
- 5,000명 동시 접속: 16 vCPU / 12GB RAM / 40GB 스토리지

### A.2 경로 B: 오픈소스 Fork + 커스텀 플러그인

**가능한 통합 패턴**:
- Mattermost Plugin SDK → HAIST_WORKS API 호출 슬래시 커맨드 (예: `/po PO-1234` → PO 카드 표시)
- Rocket.Chat Apps Engine → SO 알림·결재 푸시 통합
- Element Bridge → 카카오워크/하이웍스 양방향 (단, Bridge는 Federation 모델 의존)

**Pros·Cons (관찰)**:
- ✅ 메신저 코어 검증된 코드 (E2E·푸시·검색 다 들어있음)
- ✅ 커뮤니티 보안 업데이트 수혜
- ❌ Plugin API의 한계 내에서만 변경 가능 (코어 UX 대폭 수정 시 Fork 불가피)
- ❌ Upstream 머지 부담 (한국어 결재 패턴 추가 시 본가에 PR 가능 여부 불확실)

### A.3 경로 C: FastAPI 처음부터 구축

**KNK 스택 일치도** (memory/knk_systems):
- HAIST_WORKS = FastAPI + PostgreSQL + pgvector → 챗 앱 표준 스택과 동일
- 추가 도입 필요: WebSocket 핸들러, Redis Pub/Sub, FCM SDK, 검색 인덱서

**참조 가능한 오픈소스 예제**:
- `leonh/redis-streams-fastapi-chat` (GitHub) — Redis Streams + WebSocket + Asyncio
- `XavierCanadas/kafka-realtime-chat` (GitHub) — FastAPI + Kafka + PostgreSQL + MongoDB + Redis (마이크로서비스)

**일반화된 아키텍처** (mirrorfly·bytebytego 인용):
1. **Chat Server**: 메시지 송수신
2. **Presence Server**: 온라인/오프라인 상태
3. **API Server**: 로그인·프로필
4. **Notification Server**: 푸시 발송
5. **KV Store**: 채팅 히스토리

**처음부터 만드는 비용 (사실 관찰)**:
- ✅ 코어 UX·통합·다국어 100% 제어
- ❌ E2E·DR·검색·푸시 토큰 라이프사이클 모두 자체 책임
- ❌ Mattermost 12년치 보안 패치 누적분을 단일 팀이 따라잡아야 함

---

## Part B. 핵심 시스템 컴포넌트 (6개)

### B.1 실시간 전송 (WebSocket vs SSE vs MQTT)

| 프로토콜 | 양방향 | 모바일 친화 | 표준화 | 적합 시나리오 |
|---|---|---|---|---|
| **WebSocket** | ✅ | ✅ (RFC 6455) | ✅ | 일반 챗 앱 (FastAPI/Socket.IO 권장) |
| **SSE** (Server-Sent Events) | ❌ (서버→클라만) | ✅ | ✅ | 알림·라이브 피드 한정 |
| **MQTT** | ✅ | ✅ (저전력) | ✅ | IoT·매우 저대역 환경 (KNK는 일반 사무 환경 → 과한 선택) |

**FastAPI WebSocket 표준 패턴** (fastapi.tiangolo.com 공식):
```python
from fastapi import FastAPI, WebSocket
app = FastAPI()

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    # ConnectionManager에 등록 → Redis Pub/Sub로 broadcast
```

**다중 서버 확장 시 핵심**:
> "Redis pub/sub becomes essential for broadcasting messages to all connected clients regardless of which server they're connected to" (oneuptime.com 인용)

### B.2 메시지 저장 (PostgreSQL 스키마 패턴)

**최소 5개 테이블** (chat app system design 일반):

```sql
-- 1. users (사용자)
CREATE TABLE users (
    id UUID PRIMARY KEY,
    employee_id TEXT UNIQUE,        -- HAIST_WORKS 연동 키
    display_name TEXT,
    avatar_url TEXT,
    locale TEXT DEFAULT 'ko'        -- 'ko' / 'vi'
);

-- 2. rooms (채팅방·채널)
CREATE TABLE rooms (
    id UUID PRIMARY KEY,
    name TEXT,
    type TEXT,                      -- 'dm' | 'group' | 'channel'
    related_entity TEXT,            -- 'po:1234' | 'so:5678' (HAIST_WORKS 객체 연결)
    created_at TIMESTAMPTZ
);

-- 3. memberships (참여)
CREATE TABLE memberships (
    user_id UUID REFERENCES users(id),
    room_id UUID REFERENCES rooms(id),
    role TEXT,                      -- 'owner' | 'admin' | 'member'
    last_read_at TIMESTAMPTZ,       -- 안읽음 카운트 계산
    PRIMARY KEY (user_id, room_id)
);

-- 4. messages (메시지)
CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    room_id UUID REFERENCES rooms(id),
    sender_id UUID REFERENCES users(id),
    content TEXT,                   -- E2E 시 cipher
    content_type TEXT,              -- 'text' | 'file' | 'card' | 'system'
    parent_id BIGINT,               -- 스레드
    created_at TIMESTAMPTZ,
    edited_at TIMESTAMPTZ
);
CREATE INDEX idx_messages_room_time ON messages(room_id, created_at DESC);

-- 5. attachments (파일)
CREATE TABLE attachments (
    id UUID PRIMARY KEY,
    message_id BIGINT REFERENCES messages(id),
    file_url TEXT,                  -- S3·MinIO·로컬
    mime_type TEXT,
    size_bytes BIGINT,
    encryption_key TEXT             -- E2E 시
);
```

**KNK 특화 추가 테이블 후보** (관찰만):
- `mention_events` — 멘션·푸시 트리거 이벤트
- `bot_messages` — HAIST_WORKS 자동 알림 (변경 Inform·SO 상태)
- `kakao_bridge` — 기존 카카오워크 webhook 메시지 흡수 시

### B.3 Pub/Sub (Redis vs Kafka)

| 옵션 | 처리량 | 지속성 | 운영 부담 | KNK 140명 적합도 |
|---|---|---|---|---|
| **Redis Pub/Sub** | 매우 빠름 | 휘발성 (구독자 없으면 손실) | 낮음 | ✅ 적합 (단일 인스턴스 충분) |
| **Redis Streams** | 빠름 | 영속 (consumer group) | 중간 | ✅ 메시지 보장 필요 시 |
| **Kafka** | 매우 높음 | 영속 (디스크) | 높음 | ❌ 과한 선택 (10K+ msg/s 필요 시 고려) |

**일반 가이드** (oneuptime / ably 인용):
- 동시 접속 <1만: Redis Pub/Sub 충분
- 메시지 누락 0% 보장 필요: Redis Streams or Kafka
- KNK 140명 시 동시 접속 ≤140 → **Redis Pub/Sub 권장 사례 다수**

### B.4 푸시 알림 (FCM/APNs)

**핵심 사실** (clix.so 인용):
> "FCM acts as a reliable broker, letting your back-end send one message to one API, while Google handles the complex handshake with Apple's servers in the background, rather than connecting directly to APNs which forces you to build a custom engine just for iOS"

**아키텍처 단순화**:
- Android → FCM → 디바이스
- **iOS → FCM → APNs → 디바이스** (FCM이 APNs 중계)
- 백엔드는 FCM 1개 SDK만 통합

**오프라인 동작 차이** (clix.so 인용):
| 플랫폼 | 오프라인 큐 |
|---|---|
| **FCM** (Android) | "약 1개월 큐, 디바이스 온라인 시 일괄 전송" |
| **APNs** (iOS) | "**최신 1건만** 보관, 새 알림이 오면 이전 것 덮어씀, 오프라인 시 옛 메시지 손실" |

**KNK 영향 (관찰)**:
- iOS 직원이 오프라인이면 PO 변경 알림이 누적 5건 와도 마지막 1건만 본다
- 해결책 후보: 인앱 unread badge에서 일괄 회수 / 카카오워크 웹훅 백업 병행

**우선순위 매핑**:
- "high priority for time-sensitive alerts (chat)"·"normal priority for background updates"
- KNK 사용 시: PO/SO 변경 = high / 일반 채팅 = high / 시스템 알림 = normal

### B.5 E2E 암호화 (필요한가? — 옵션 검토)

**Signal Protocol** (wikipedia 인용):
- "non-federated cryptographic protocol for end-to-end encryption" (Open Whisper Systems 2013)
- 핵심 3요소: **Double Ratchet** + **prekeys** + **3-DH 핸드셰이크**

**Matrix Olm/Megolm** (matrix.org 인용):
- "Olm = Double Ratchet 구현, Megolm = 정부·국가 규모 확장"
- 클라이언트 라이브러리: **vodozemac** (Rust, 권장) / libolm (구버전)

**KNK 컨텍스트 사실 관찰**:
- 사내 단일 회사 사용 → **서버 측 암호화(TLS + at-rest 암호화)** 만으로도 컴플라이언스 충족 가능
- E2E 도입 시 비용: 키 관리·디바이스 인증·키 손실 시 메시지 영구 손실 위험
- 보안 등급 매우 높은 프로젝트 (ex: 정부 매출분, 산업기밀) 한정 시 적용 검토

**E2E 미도입 시 대체 패턴** (공무원 메신저 "바로톡" 인용):
- "모바일 백신·**화면담기(캡처) 방지**·파일 내려받기 방지·암호화"
- 즉 **DLP(데이터 유출 방지) + 캡처 방지 + 통신 암호화(TLS)** 3축으로 E2E 없이도 보안 가능

### B.6 검색 (한국어·베트남어 — 매우 까다로움)

**MySQL** (mattermost docs 인용):
> "MySQL deployments requiring searching in Chinese, Japanese, and Korean languages require the configuration of **ngram Full-Text parser**"

**PostgreSQL 옵션**:
- 기본 `tsvector` — 영어 형태소만, 한국어 부적합
- **`pg_trgm` 확장** — n-gram 기반, 한국어 부분 검색 가능
- **`pg_bigm`** — 일본어 표준, 한국어도 커뮤니티 패치 존재
- **외부 형태소 분석기 통합**:
  - 한국어: MeCab-ko / Khaiii (카카오 오픈소스)
  - 베트남어: VnCoreNLP / underthesea

**Elasticsearch 옵션**:
- Nori 분석기 (한국어 공식)
- icu_tokenizer (베트남어 일반화)

**KNK 검색 시나리오 (관찰)**:
- 메시지 본문 검색 → ko + vi 두 언어 토큰화
- 첨부 파일명·OCR — 별도 파이프라인 (네이버웍스 Standard Plus 가 OCR 검색 제공 [`기업용_메신저_비교_2026.md` §2.3])

---

## Part C. KNK 통합 포인트

### C.1 HAIST_WORKS SSO·디렉토리

**현 상태**: HAIST_WORKS는 FastAPI 단일 인증 (memory/knk_systems)
**자체 메신저 SSO 옵션**:
- A. JWT 공유 — HAIST_WORKS 토큰 그대로 메신저 인증
- B. OAuth 2.0 자체 발급 — 메신저 = OAuth Provider, HAIST_WORKS = Client (또는 반대)
- C. SAML — 엔터프라이즈 표준이나 KNK 규모엔 과함

**디렉토리 동기화**:
- HAIST_WORKS `users` 테이블 → 메신저 `users` 테이블 1:1 매핑
- `employee_id` 외래키로 연결 (위 §B.2 스키마 참조)

### C.2 카카오워크 webhook 흡수 시나리오

**현 상태** (system_scope_policy 정책 + `외부연결_가이드_하이웍스_카카오워크.md` Part B):
- 카카오워크 webhook으로 SO·PO·일정 알림 발송
- 자체 메신저 도입 시 4가지 처리 옵션:

| 옵션 | 패턴 |
|---|---|
| 1 | **카카오워크 유지 + 자체 메신저 병행** (당분간 양쪽 모두 알림) |
| 2 | **자체 메신저 우선 + 카카오워크 보조** (오프라인 시·외부 통신용) |
| 3 | **자체 메신저로 일원화 + 카카오워크 webhook → 자체 메신저 봇 메시지로 변환** |
| 4 | **자체 메신저로 일원화 + 카카오워크 폐기** |

→ 옵션 결정은 09 + 대표. 03은 옵션만.

### C.3 하이웍스 결재 연동

**정책 인용** (`memory/system_scope_policy.md`):
> "하이웍스 전자결제·메일 계속 사용"

→ 자체 메신저는 **하이웍스 결재를 대체하지 않음**.
**연동 가능 패턴** (`외부연결_가이드_하이웍스_카카오워크.md` Part A 인용):
- 하이웍스 API의 결재 상태 변경 webhook → 메신저 봇 메시지로 표시
- 메신저에서 "결재 작성" 슬래시 커맨드 → 하이웍스 결재 페이지 딥링크
- 결재 알림 (회람·합의·반려) → 메신저 푸시

### C.4 변경 Inform · SO·PO 알림 통합

**기존 자료 참조**:
- 04-25 R1·R2 보고서 (매출주문 라이프사이클 / 재고 입출고 연계) — 자체 메신저 알림 시나리오에 적용
- v5H132~136 SO/PO/프로젝트 다대다 매핑 — 알림 그룹핑 단위로 활용 가능

**알림 카드 설계 패턴** (카카오워크 Block Kit 인용 — `외부연결_가이드_하이웍스_카카오워크.md` B.4):
- 헤더: 호기 ID·SO 번호
- 본문: 변경 항목 (전·후 값)
- 액션 버튼: "확인", "이의 제기", "관련 PO 보기" 등
- 푸터: 시간·작성자

→ 메신저 자체 카드 포맷도 위 패턴 참조 가능.

---

## Part D. 한국형·자체 메신저 모방 가능 패턴

### D.1 카카오워크 Block Kit (말풍선 UI)

**기존 03 자료**: `외부연결_가이드_하이웍스_카카오워크.md` Part B.4 상세

**핵심 컴포넌트**:
- Header / Section / Action / Divider / Image
- 버튼·드롭다운·체크박스 인터랙션
- Modal Dialog

**자체 구현 시**: JSON 스키마로 동일 패턴 도입 가능 (Slack Block Kit·Microsoft Adaptive Cards와 호환 가능 설계)

### D.2 하이웍스 결재 흐름 (한국식)

**foxcg.com 인용** (`기업용_메신저_비교_2026.md` §2.1):
> "기안, 합의, 재무 합의, 최종 결재 등 복잡한 결재 라인을 직관적인 UI로 손쉽게 설정"

**메신저에서 흡수 가능한 부분**:
- 결재 진행 단계 표시 (완료·대기·반려)
- 합의자 멘션·푸시
- 첨부 파일 미리보기
- (실제 결재 처리는 하이웍스 페이지 — system_scope_policy 정책 준수)

### D.3 두레이 워크플로우

**dooray.com / namu.wiki 인용**:
- Project + Mail + Workflow + Messenger + Calendar 통합
- 모든 플랜에 메신저+영상회의 무료 포함
- IFTTT·Jenkins·Trello·GitHub·Bitbucket 연동

**모방 가능 패턴**:
- "Project ↔ Messenger 1:1 연결" — KNK는 SO/PO/Project 객체 ↔ 채팅방 1:1 매핑 가능 (위 §B.2 `related_entity` 컬럼)
- IFTTT 류 외부 자동화 → 자체 webhook + 룰 엔진

### D.4 잔디 양방향 Webhook

**잔디 공식 / GitHub 인용**:
- **Incoming Webhook** — 외부 → 잔디 메시지
- **Outgoing Webhook** — 잔디 메시지 → 외부 (커맨드 라우팅)
- Node.js·Perl 등 SDK 다수

**자체 구현 시**: REST POST 엔드포인트 1쌍으로 동등 기능 구현 가능 (FastAPI 매우 적합).

### D.5 공무원 메신저 "바로톡" 보안 패턴

**namu.wiki 인용**:
- 모바일 백신
- **화면담기(캡처) 방지**
- 파일 내려받기 방지
- 암호화

**KNK 자체 구현 적용 가능성**:
- iOS: `UIScreen.captured` 모니터링·`UIWindow.shareLayer` 차단
- Android: `WindowManager.LayoutParams.FLAG_SECURE`
- 데스크톱: 어렵지만 워터마킹 가능
- 다운로드 방지는 OS·앱 레벨 강제 가능

→ 산업기밀·정부 매출분 채팅에 한정 적용 검토 가능.

---

## Part E. 위험·함정·체크리스트 (Top 12)

### E.1 기술적 위험 6개

| # | 위험 | 발생 시 영향 | 회피 패턴 |
|---|---|---|---|
| 1 | **WebSocket 연결 누수** | 메모리 폭증·서버 다운 | ConnectionManager + heartbeat (30s) + force close |
| 2 | **다중 서버 메시지 누락** | 일부 사용자만 안 보임 | Redis Pub/Sub 또는 Streams 의무 |
| 3 | **푸시 토큰 만료** | 알림 미수신 | FCM token refresh 이벤트 처리 |
| 4 | **iOS 오프라인 다중 알림** | 마지막 1건만 도착 | unread badge + 인앱 풀링 |
| 5 | **한국어/베트남어 검색 부정확** | 사용자 불만 | ngram·MeCab·Nori 사전 검증 필수 |
| 6 | **DB 무한 증가** | 디스크 폭발 | Cold storage tier (90일+ 메시지 S3 이관) |

### E.2 운영 위험 3개

| # | 위험 | 회피 |
|---|---|---|
| 7 | **DR (재해 복구)** 미정 | PG_Backup + S3 야간 동기화 / RPO·RTO 정의 |
| 8 | **GDPR·개인정보보호법** 위반 | 메시지 보유 기간 정책 / 사용자 탈퇴 시 마스킹 |
| 9 | **개발 인력 1인 의존** | 코드 리뷰·문서화·on-call 회전 |

### E.3 UX·정책 위험 3개

| # | 위험 | 회피 |
|---|---|---|
| 10 | **카카오워크와 알림 중복** | Part C.2 옵션 1~4 중 명시적 선택 |
| 11 | **결재는 하이웍스, 채팅은 자체 → UX 분절** | 메신저에서 하이웍스 딥링크·webhook 통합 |
| 12 | **베트남어 미지원** | 베트남 직원 사용 거부 가능성 — i18n 1차 출시부터 포함 권장 사례 다수 |

---

## Part F. 세션 10 의사결정 재료 (5대 질문)

> 03 권고 없음. 각 질문에 대한 옵션과 근거 사실만 제공. 결정은 세션 10 + 09 + 대표.

### Q1. Build vs Fork? (3옵션)

| 옵션 | 근거 |
|---|---|
| A. Mattermost Team Edition 셀프호스팅 | 5분 설치·MIT·250~500명 단일 서버·플러그인 SDK |
| B. Rocket.Chat fork + KNK 플러그인 | 200+ 앱 마켓·E2E 기본·omnichannel |
| C. FastAPI 처음부터 | KNK 메인 스택 일치·100% 통제·12~24주 |

### Q2. E2E 암호화 필요한가?

| 옵션 | 근거 |
|---|---|
| Yes | Signal/Olm 표준 존재·정부/기밀 매출분 보호 |
| No | 사내 단일 조직·TLS+at-rest+DLP+캡처 방지로 충분한 사례 다수 |
| Partial | 일반 채널 No, "기밀" 채널만 Yes (Matrix/Megolm 가능) |

### Q3. 클라이언트 어떤 폼팩터?

| 옵션 | 근거 |
|---|---|
| Web 우선 | 빠른 출시·React/Vue + WebSocket 충분 |
| Web + Mobile (iOS/Android) | 푸시 알림·외근 직원 (FCM 통합 필수) |
| Web + Mobile + Desktop | Electron으로 데스크톱 추가 (Mattermost·Rocket.Chat 모두 Electron 기반) |

### Q4. 하이웍스 메일 통합 vs 분리?

> **system_scope_policy 정책: 하이웍스 메일 유지** → 자체 메신저는 메일 기능 미포함이 정책 일관.
> 단, 메일 알림을 메신저로 받는 통합은 가능 (deep link 만).

### Q5. 베트남어 1차 지원 시점?

| 옵션 | 근거 |
|---|---|
| 1차 출시부터 | KNKVN 직원 사용 거부 회피·i18n 후속 비용 절감 |
| Phase 2 | 한국어만 먼저 검증 후 확장 |
| 미지원 (한국어만) | KNKVN이 자체 한국어 학습 가정 — 04-27 P11 다국어견적서 정찰 보고서와 충돌 |

---

## G. 출처 URL

### 오픈소스 메신저 비교
- [10+ Best Open Source Mattermost Alternatives 2026 — OpenAlternative](https://openalternative.co/alternatives/mattermost)
- [Best Self-Hosted Chat Apps 2026 — Rocket.Chat Blog](https://www.rocket.chat/blog/self-hosted-chat-app)
- [Best Self-Hosted Communication & Chat Tools 2026 — DEV Community](https://dev.to/selfhostingsh/best-self-hosted-communication-chat-tools-in-2026-4m77)
- [Mattermost vs Element comparison — Rocket.Chat](https://www.rocket.chat/blog/mattermost-vs-element)
- [Top 3 Slack Alternatives — wz-it.com](https://wz-it.com/en/blog/slack-alternatives-mattermost-rocketchat-zulip/)

### 시스템 설계
- [Chat App System Design 2026 Guide — MirrorFly](https://www.mirrorfly.com/blog/chat-app-system-design/)
- [Design A Chat System — ByteByteGo](https://bytebytego.com/courses/system-design-interview/design-a-chat-system)
- [Design WhatsApp — Hello Interview](https://www.hellointerview.com/learn/system-design/problem-breakdowns/whatsapp)
- [WebSocket Architecture Best Practices — Ably](https://ably.com/topic/websocket-architecture-best-practices)
- [Building Chat with WebSockets — OneUptime 2026-01](https://oneuptime.com/blog/post/2026-01-26-websocket-chat-application/view)

### FastAPI 구현
- [FastAPI WebSockets 공식 문서](https://fastapi.tiangolo.com/advanced/websockets/)
- [FastAPI WebSocket Servers with Redis — OneUptime 2026-01](https://oneuptime.com/blog/post/2026-01-25-websocket-servers-fastapi-redis/view)
- [Build FastAPI WebSocket Chat with Redis — OneUptime 2026-03](https://oneuptime.com/blog/post/2026-03-31-redis-build-fastapi-websocket-chat-with-redis/view)
- [redis-streams-fastapi-chat — GitHub](https://github.com/leonh/redis-streams-fastapi-chat)
- [kafka-realtime-chat — GitHub](https://github.com/XavierCanadas/kafka-realtime-chat)
- [WebSocket with FastAPI Async Connections & Scaling — websocket.org](https://websocket.org/guides/frameworks/fastapi/)

### E2E 암호화
- [Matrix.org E2EE 구현 가이드](https://matrix.org/docs/matrix-concepts/end-to-end-encryption/)
- [Signal Protocol — Wikipedia](https://en.wikipedia.org/wiki/Signal_Protocol)
- [Matrix protocol — Wikipedia](https://en.wikipedia.org/wiki/Matrix_(protocol))
- [Olm/Megolm 분석 — Jabberhead](https://blog.jabberhead.tk/2019/03/10/a-look-at-matrix-orgs-olm-megolm-encryption-protocol/)
- [Element E2EE 기능](https://element.io/en/features/end-to-end-encryption)

### 푸시 알림
- [Push Notification Delivery — Clix Blog](https://blog.clix.so/how-push-notification-delivery-works-internally/)
- [Handling States for Push Notifications — Clix](https://blog.clix.so/handling-states-for-push-notifications/)
- [iOS FCM Push — CometChat](https://www.cometchat.com/docs/notifications/ios-fcm-push-notifications)
- [Cloud Messaging — RNFirebase](https://rnfirebase.io/messaging/usage)
- [iOS Notifications with APNs/FCM/Courier](https://www.courier.com/guides/ios-notifications)

### 시스템 요구사항
- [Mattermost software & hardware requirements](https://docs.mattermost.com/install/software-hardware-requirements.html)
- [Rocket.Chat System Requirements](https://docs.rocket.chat/installation/hardware-requirements)
- [Mattermost docs (Korean ngram parser 언급)](https://docs.mattermost.com/deployment-guide/software-hardware-requirements.html)

### KNK 기존 자료 (03 작성)
- [외부연결_가이드_하이웍스_카카오워크.md (2026-04-20)](KNK업무시스템구축/03_HAIST_WORKS_Research/외부연결_가이드_하이웍스_카카오워크.md)
- [기업용_메신저_비교_2026.md (2026-05-05)](KNK업무시스템구축/03_HAIST_WORKS_Research/기업용_메신저_비교_2026.md)

---

## H. 정직성 v3 자가 점검

- ✅ 출처 URL 직접 인용 (총 30+개)
- ✅ 추정 0건 — 시스템 사양·환율 등은 "추정·가정" 명시
- ✅ "권고 없음" 명시 — 옵션 A/B/C/Yes/No/Partial 형태로 결정 재료만
- ✅ 정책 충돌 점검 — `memory/system_scope_policy.md` "하이웍스 유지" 정책 명시 인용
- ✅ 03 권한 일탈 없음 — 아키텍처 처방 0건
- ⚠️ Mattermost 250~500명 단일 서버 — 공식 docs 기반이나 KNK 실측 필요
- ⚠️ 한국어 검색은 ngram·MeCab·Nori 모두 검증 필요 (PoC 권장)

---

**작성**: 2026-05-05 / 03 Research 빅터
**다음 갱신 시점**:
- 세션 10이 Q1~Q5 결정한 후 → 선택된 경로 깊이 자료 추가 작성
- Mattermost·Rocket.Chat 신버전 출시 시
- KNK PoC 결과 (한국어 검색 정확도·동시 접속 부하) 도착 시
