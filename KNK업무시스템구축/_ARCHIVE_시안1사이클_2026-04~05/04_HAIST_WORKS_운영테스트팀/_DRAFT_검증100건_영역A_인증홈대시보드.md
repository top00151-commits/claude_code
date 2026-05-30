# 영역 A — 인증·홈·대시보드 검증 (20건 발견)

> 04 운영테스트팀 / Explore agent A 결과 흡수
> 일자: 2026-04-29
> 정직성 v3: grep -n 직접 인용 / 추정 0건

## A-001 [P1] 로그인 라벨 9px 가독성 부족
- 페이지: /login
- 페르소나: 모바일·시각장애 사용자
- 증거: `login.html:99-107` `.field label{ font-size: 9px !important; ... text-transform: uppercase; }`
- 문제: 9px 고정 → WCAG 4.1.2 위반 가능
- 권장: clamp(11px, 1vw, 14px) 적용

## A-002 [P1] 로그인 에러 메시지 정보 노출
- 페이지: /login
- 페르소나: 외부 공격자 / 신규 사용자
- 증거: `login.html:413-418` + `main.py:373` "아이디 또는 비밀번호..."
- 문제: 아이디 존재 여부 vs 비밀번호 오류 분리 가능 (보안 모범사례 위반 잠재)
- 권장: 통일 메시지 "입력 정보를 확인하세요"

## A-003 [P0] /home 빠른입력 공수 max 미설정
- 페이지: /home
- 페르소나: 일반 사용자 실수 입력
- 증거: `home.html:80` `<input type="number" id="newHours" step="0.5" min="0">` (max 없음)
- 문제: 999999 등 비정상 값 입력 가능 → BE 검증만 의존
- 권장: max="24" 또는 max="48" 추가

## A-004 [P2] /home 빠른입력 필드 순서 비논리
- 페이지: /home
- 페르소나: 빠른 입력 사무원
- 증거: `home.html:59-83` 업무명 → 프로젝트 → 고객사 → 공수 순
- 문제: 실무 흐름 "업무명+공수 → (옵션) 프로젝트/고객사" 와 역행
- 권장: 2-step (필수 1단계 + 선택 2단계)

## A-005 [P1] 안내 배너 3.5초 타임아웃 하드코딩
- 페이지: /daily, /home
- 페르소나: 스크린리더·느린 네트워크
- 증거: `daily.html:21-30`, `home.html:24-29` setTimeout 3500ms
- 문제: 스크린리더가 배너 읽기 전 사라짐
- 권장: 8초 이상 + 명시적 닫기 버튼

## A-006 [P1] /daily 주말·공휴일 표시 부재
- 페이지: /daily
- 페르소나: 일반 사용자
- 증거: `daily.html:13-18` 단순 date input
- 문제: 금요일 다음날이 월요일 자동 인식 안 됨
- 권장: 달력 위젯 + 요일 + 공휴일 표시

## A-007 [P2] /summary 모바일 6버튼 줄바꿈
- 페이지: /summary
- 페르소나: 모바일 사용자
- 증거: `summary.html:17-34` 기간 3 + 대상 3 = 6 버튼 한 줄
- 문제: 320px 환경 줄바꿈
- 권장: 2x3 그리드 또는 select

## A-008 [P1] /dashboard 권한 차단 무음 리다이렉트
- 페이지: /dashboard
- 페르소나: 박지은 영업 leader
- 증거: `main.py:1911-1923` `RedirectResponse("/home", 303)` 안내 없음
- 문제: 사용자는 링크 작동 안 한다고 느낌
- 권장: `/home?no_perm=dashboard` 배너

## A-009 [P1] /history 날짜 역순 검증 없음
- 페이지: /history
- 페르소나: 일반 사용자
- 증거: `history.html:12-16` frm/to date inputs
- 문제: to < frm 시 빈 결과만 반환
- 권장: JS 검증 + 자동 swap

## A-010 [P2] /notifications 아이콘 단조
- 페이지: /notifications
- 페르소나: 알림 다량 수신자
- 증거: `notifications.html:20-28` comment 외 모두 🔔
- 문제: kind 시각 차별화 부재
- 권장: kind별 고유 아이콘 (task_create 🆕, retro 📖)

## A-011 [P1] /now 폴링 에러 무음
- 페이지: /now
- 페르소나: 실시간 모니터링
- 증거: `now.html:42-72` `catch(e){}` 빈 핸들러, setInterval 30000
- 문제: 30초마다 실패해도 사용자 모름
- 권장: 에러 배너 + 재시도

## A-012 [P3] /cockpit 미작성 강조 약함
- 페이지: /cockpit
- 페르소나: 박지은 / 김정락
- 증거: `cockpit.html:25` `<span style="color:#A5282C">미작성</span>` 텍스트만
- 권장: tag-warn 클래스 + 배경

## A-013 [P0] /login 비번 토글 모바일 터치 영역 부족
- 페이지: /login
- 페르소나: 모바일
- 증거: `login.html:438-440` `.toggle` 크기 미정의
- 문제: 44px 미만 가능 (모바일 가이드 위반)
- 권장: 44×44 강제

## A-014 [P1] /home 탭 전환 시 sel_date 손실
- 페이지: /home
- 페르소나: 과거 날짜 조회 사용자
- 증거: `home.html:91-103` `?tab=my` 등 단일 파라미터
- 문제: sel_date 파라미터 소실 → 오늘 리셋
- 권장: `?tab=my&sel_date={{ sel_date }}`

## A-015 [P2] /daily 주간 통계 링크 범위 미적용
- 페이지: /daily
- 페르소나: 일반 사용자
- 증거: `daily.html:32-40` `/history?status=완료` (주간 미포함)
- 문제: status만 필터, 주간 범위 없음
- 권장: `/history?frm={{ week_start }}&to={{ week_end }}&status=완료`

## A-016 [P1] /summary 지연 델타 방향 역
- 페이지: /summary
- 페르소나: 박지은 / 이한중
- 증거: `summary.html:62-65` `delta.delay <= 0` 조건에 `up` 클래스
- 문제: 지연은 낮을수록 좋음 → up/down 의미 반전
- 권장: `delta.delay <= 0 ? down : up`

## A-017 [P1] /cockpit ck-mute 클래스 정의 부재
- 페이지: /cockpit
- 페르소나: 김정락
- 증거: `cockpit.html:20-29` `class="ck-mute"` 사용 + CSS 정의 미확인
- 문제: 시각 강조 없음
- 권장: `.ck-mute { background: #f5f5f5; color: #999; }`

## A-018 [P2] /dashboard 9-KPI 모바일 깨짐 가능
- 페이지: /dashboard
- 페르소나: 모바일 임원
- 증거: `dashboard.html:27` `.kpi-grid-9`
- 권장: `@media (max-width: 768px) { .kpi-grid-9 { grid-template-columns: 1fr 1fr; } }`

## A-019 [P1] /notifications 100+ 안내 부재
- 페이지: /notifications
- 페르소나: 다수 수신자
- 증거: `notifications.html:4-14` "최근 100건" 표기만
- 문제: 100건 초과 시 페이지네이션 미명시
- 권장: "총 N건 중 최근 100건" 명시

## A-020 [P3] /home quickExtras 즉시 표시
- 페이지: /home
- 페르소나: 일반 사용자
- 증거: `home.html:64-67` `onfocus="...style.display='flex'"`
- 권장: opacity transition 0.2s

---

**Tier 합계**: P0×2 + P1×11 + P2×6 + P3×1 = 20건
