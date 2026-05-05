# KNK Messenger (10_KNK_Messenger)

KNK 사내 업무 전용 메신저. **카카오톡으로는 풀 수 없는 "대화 → 자동 정리된 아이템별 이력" 문제를 해결**하기 위한 시스템.

빅터(Claude) + 김정락 대표 협업 1차 빌드 — 2026-05-05.

---

## 왜 만들었는가

기존: 카카오톡으로 아이템(고객사×모델)별 방을 만들어 운영. 하지만:
- API 연결이 안 돼서 자동 정리 불가
- 대화 누적되면 요청이 묻혀서 그냥 넘어감
- 사진·파일이 흩어져 검색 불가
- 신규 담당자 인수받을 때 처음부터 끝까지 보기 어려움

해결: 메신저는 입력층, 그 위에 **아이템 자동 정리 레이어**를 올림.

---

## 차별 기능 (시중 메신저 7종에 없음)

| 기능 | 설명 | 효과 |
|---|---|---|
| **아이템 카드** | 방 = 아이템(고객사×모델). 메타데이터(상태/납기/담당)가 방 자체 속성 | 카톡 방 이름에만 의존하던 정보가 구조화됨 |
| **메시지 → 요청 승격** | 메시지 옆 📌 버튼 → 담당자·마감일 지정 → 추적 가능한 티켓 | "묻혀서 그냥 넘어가는 요청" 박멸 |
| **🌅 일간 다이제스트** | 로그인 시 자동 — 지연/오늘마감/이번주/내가 보낸 요청 한눈 | 매일 챙겨야 할 일을 누가 챙기지 않아도 떠오름 |
| **📊 아이템 대시보드** | `/dashboard` 페이지 — 전체 아이템 카드 그리드. 검색·필터·정렬 | 1초 안에 회사 전체 진행 상황 파악 |
| **아이템별 갤러리** | 사진·파일을 시간순 그리드 / 파일 목록으로 한 페이지 | 카톡에서 잃어버리던 자료가 자동 정리됨 |
| **타임라인 뷰** | 아이템의 모든 이벤트(메시지/사진/파일/요청)를 날짜별 그룹 | 신규 담당자 인수인계 30분 컷 |
| **전사 FTS5 검색** | 한글 토크나이저 + 전문(本文) 검색. 200ms 이하 응답 | 카톡의 "검색 됨/안됨 복불복" 해결 |
| **사이드바 📌 내 요청** | 담당자별 열린 요청. 지연 빨강·임박 주황·D-Day 노랑 | 본인 일이 시각적으로 바로 보임 |
| **@mention 자동완성** | 메시지에 @hong → 자동완성 + 본인 멘션이면 노랑 강조 | 그룹채팅에서 누구한테 묻는지 명확 |
| **드래그앤드롭·붙여넣기** | 파일 끌어놓기·클립보드 이미지 자동 업로드 | 카톡보다 빠른 자료 공유 |

## 기존 메신저와 비교

| 기능 | KNK | 카카오워크 | 잔디 | 두레이 | 하이웍스 |
|---|---|---|---|---|---|
| 아이템 카드 | **✅** | ❌ | ❌ | ❌ | ❌ |
| 메시지 → 요청 승격 (in-context) | **✅** | ❌ | ❌ | (별도 워크플로우) | ❌ |
| 자동 일간 다이제스트 | **✅** | ❌ | ❌ | ❌ | ❌ |
| 아이템별 갤러리/타임라인 | **✅** | ❌ | ❌ | ❌ | ❌ |
| 전사 한글 FTS | **✅** | ⚠️ 불안정 | ⚠️ | ✅ | ⚠️ |

→ **시장에 없는 차별점.** 03 리서치팀(2026-05-05) `기업용_메신저_비교_2026.md` 7종 모두 미보유.

---

## 기술 스택

- **Backend**: Python 3.13 + Flask 3.1 + Flask-SocketIO + SQLite (FTS5)
- **Frontend**: 바닐라 JS + 모바일 반응형 CSS (프레임워크 없음, 단일 페이지)
- **Realtime**: WebSocket (Socket.IO 4.7)
- **Storage**: SQLite + `data/uploads/<room_id>/` 파일 저장
- **PWA**: manifest + service worker (홈화면 설치 가능, 오프라인 캐시)
- **검색**: SQLite FTS5 가상 테이블 + unicode61 토크나이저 (한글 prefix 매칭)

---

## DB 스키마 (요약)

```
users          — 직원 계정
rooms          — 방 (type: direct | group | channel | item)
room_members   — 방 참여자 + 마지막 읽음 위치
messages       — 메시지 (kind: text | image | file | system) + 첨부 컬럼
items          — rooms.type='item' 인 방의 아이템 메타 (1:1)
requests       — 요청/티켓 (assignee + due + status)
messages_fts   — FTS5 가상 테이블 (자동 동기화 트리거 3개)
```

---

## API (요약)

```
인증
  GET  /login, POST /login
  GET  /logout
  GET  /api/me

방 / 메시지
  GET  /api/rooms
  POST /api/rooms              (1:1·그룹·채널)
  GET  /api/rooms/<id>/messages
  POST /api/rooms/<id>/read
  GET  /api/rooms/<id>/summary  (카운트)
  GET  /api/rooms/<id>/timeline (이벤트 통합)

아이템
  POST /api/items
  GET  /api/items/<room_id>
  PATCH /api/items/<room_id>
  GET  /api/items/dashboard

업로드 / 갤러리
  POST /api/upload (multipart, 25MB 한도)
  GET  /uploads/<room_id>/<file>
  GET  /api/rooms/<id>/attachments?kind=image|file

요청 (티켓)
  GET  /api/rooms/<id>/requests?status=open
  POST /api/requests
  PATCH /api/requests/<id>
  GET  /api/my/requests

검색 / 다이제스트
  GET  /api/search?q=
  GET  /api/digest

PWA
  GET  /manifest.json
  GET  /sw.js
```

---

## 실행

```cmd
cd 10_KNK_Messenger
START.bat
```

또는

```bash
py app.py
```

- 접속: <http://localhost:5050>
- 휴대폰 (같은 와이파이): <http://[PC IP]:5050>
- 시드 계정: `kjr` / `hong` / `lee` (모두 비밀번호 `knk1234`)

## 휴대폰 설치 (PWA)

**안드로이드**: 크롬으로 접속 → 주소창 옆 "앱 설치" 또는 메뉴 > "홈 화면에 추가"

**iOS**: 사파리로 접속 → 공유 → "홈 화면에 추가". 그 아이콘으로 실행해야만 푸시 알림 받음 (iOS 16.4+).

---

## 현황 (2026-05-05 1차 완료)

- ✅ 1단계 (메시지·아이템·읽음·검색·요청·갤러리·타임라인·다이제스트·PWA) 완료
- ⏳ 2단계 (Web Push 서버측 구현 + iOS Capacitor 래핑) 대기
- ⏳ 3단계 (HAIST WORKS SSO + 사용자 API + 결재·SO·PO 이벤트 봇) 대기

## 결재 보류 사항

1. **iOS 배포 방식**: 앱스토어 vs Apple Developer Enterprise(연 $299, 사내 한정)
2. **메시지 보존 정책**: 영구 vs N개월 후 자동삭제
3. **서버 호스팅**: 사무실 PC vs 클라우드(월 ~$5) vs 회사 NAS
4. **베타 시범 부서**: 영업 / 전장 / 제조2 등 1팀 선정

## 데이터 이전 정책 (확정)

**신규부터** — 카톡은 읽기전용 1~2개월 병행, 신규 아이템은 KNK 메신저에서 시작. 외부(고객·협력사)는 카톡 유지하고 담당자가 자료만 우리쪽에 1초 업로드로 자동 정리.

---

## 빅터(Claude) 메모

**세션 정체성**: 10_KNK_Messenger (2026-05-05 신설). 00~09 팀 옆 10번째 팀.
**권한 범위**: `KNK업무시스템구축\` 안쪽만.
**작업 방식**: 09 팀장 라인 거치지 않고 이 세션에서 직접 코드. 대표 직권 예외.
**다음 세션 진입 시**: 이 README + `memory/project_knk_messenger.md` 먼저 읽기.
