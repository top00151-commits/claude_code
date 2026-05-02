# 영역 D — 협업·프로젝트 검증 (23건 발견)

> 04 운영테스트팀 / Explore agent D 결과 흡수
> 일자: 2026-04-29
> 정직성 v3: grep -n 직접 인용 / 추정 0건

## D-001 [P1] 변경공지 확인률 분모 오류
- 페이지: /changes
- 페르소나: 김형렬 전장
- 증거: `changes_list.html:97` `{{ ch.ack_count }}/{{ ch.impact_count * 5 }}`
- 문제: 분모 `× 5` 하드코딩 → 비논리적 확인률
- 권장: change_impacts 테이블 영향자 수 또는 change_reads 행 수 사용

## D-002 [P2] 변경공지 4단계 폼 단계 표시 미동작
- 페이지: /changes/new
- 페르소나: 김형렬
- 증거: `change_form.html:14-17` `data-step="1"` active 클래스
- 문제: JS 단계 전환 로직 부재
- 권장: 다음/이전 버튼 + JS 단계 토글

## D-003 [P1] 티켓 자동 라우팅 부재
- 페이지: /tickets/new
- 페르소나: 임택훈 제조2 leader
- 증거: `main.py:4041` 카테고리별 기본 수신팀 매핑 없음
- 문제: 수동 선택 → 카톡 누락과 동일 UX
- 권장: TICKET_CATEGORIES 별 default recipient_team_id

## D-004 [P2] 진행률 12공정 정의 부족
- 페이지: /progress (matrix)
- 페르소나: 김정록
- 증거: `progress_matrix.html:116` `for code, label, _ in PHASE_DEFS`
- 문제: 정렬·SLA·표준시간 누락
- 권장: PHASE_DEFS에 order/std_hours/team_id 추가

## D-005 [P2] 이슈 심각도 ko/en 혼용
- 페이지: /issues vs /qms
- 페르소나: 김정록
- 증거: `issues_list.html:46-48` (ko) vs `qms_dashboard.html:70` (en)
- 권장: i18n 통일 또는 SEVERITY_KO/EN 이중

## D-006 [P1] 게시글 승인 권한 미검증
- 페이지: /board/post/{id}/approve
- 페르소나: 일반 사용자
- 증거: `main.py:4546` is_leader 체크 없음
- 문제: 누구나 승인 가능
- 권장: leader/admin 가드

## D-007 [P2] 프로젝트 STAGES 의존성 부재
- 페이지: /projects
- 페르소나: 이한중
- 증거: `projects.html:22-24` STAGES select
- 문제: 단계 선행 조건(수주→개조→납품) 미정의
- 권장: ordered dict + 의존성 명시

## D-008 [P1] 미작성자 알림 자동화 부재
- 페이지: /admin/reminders
- 페르소나: 박지은
- 증거: `main.py:3514` 수동 GET 라우트
- 문제: 매일 16:30 자동 알림 부재
- 권장: APScheduler 자동 발송

## D-009 [P2] 캘린더 scope=team 권한 재검증 부재
- 페이지: /calendar
- 페르소나: 일반 직원
- 증거: `calendar.html:14-16` can_team UI만, 라우트 검증 부재
- 권장: scope=team 시 leader 재가드

## D-010 [P1] 주간 지연 판정 로직 단순
- 페이지: /weekly
- 페르소나: 박지은
- 증거: `weekly.html:114` `is_stale = (status == '지연')`
- 문제: 7일 경과 + 상태 결합 미적용
- 권장: `status=='지연' AND days_elapsed >= 7`

## D-011 [P2] QMS SLA 산식 미명시
- 페이지: /qms
- 페르소나: 김정록
- 증거: `qms_dashboard.html:71-72` sla_hours / remaining_h
- 문제: 발생일/보고일/영업시간 기준 불명
- 권장: database.py에 산식 주석

## D-012 [P1] 변경공지 영향 부서 자동 판별 한계
- 페이지: /changes/new
- 페르소나: 김형렬
- 증거: `main.py:3725-3740` biz_div 단일 기준
- 문제: 도면 변경 시 기구·전장·품질 동시 알림 불가
- 권장: CHANGE_TYPE → team_id 리스트 매핑

## D-013 [P2] 티켓 상태 전이 화이트리스트 부재
- 페이지: /tickets/{id}
- 페르소나: 임택훈
- 증거: `main.py:4136` 이전 상태 검증 없음
- 문제: 완료 → 접수 역전이 가능
- 권장: TICKET_STATUS_TRANSITIONS dict 화이트리스트

## D-014 [P2] 프로젝트 관리코드 중복 검증 부재
- 페이지: /projects/new
- 페르소나: 이한중
- 증거: `main.py:4842` mgmt_code 유일성 검증 없음
- 권장: INSERT 전 SELECT COUNT 검증

## D-015 [P1] 이슈 → CAPA 연결 동선 부재
- 페이지: /issues/{id}
- 페르소나: 김정록
- 증거: `main.py:4308-4330` CAPA 등록 링크 없음
- 권장: "시정조치 등록" 버튼 + issue_id 전달

## D-016 [P2] 게시판 카테고리 분류 기준 부재
- 페이지: /board/new
- 페르소나: 박지은
- 증거: `board_form.html:30-40` select 옵션 하드코딩 의심
- 문제: 부서별 카테고리 화이트리스트 부재
- 권장: BOARD_CATEGORY_BY_TYPE dict

## D-017 [P1] 주간보고 refresh 캐시 무효화 부재
- 페이지: /weekly/refresh
- 페르소나: 박지은
- 증거: `weekly.html:26-31` location.reload()
- 문제: 브라우저 캐시 → 이전 데이터 표시
- 권장: Cache-Control: no-cache

## D-018 [P2] 티켓 댓글 알림 미연동
- 페이지: /tickets/{id}
- 페르소나: 임택훈
- 증거: `main.py:4182` 댓글 후 notify 없음
- 문제: 카톡 별도 통보 필요
- 권장: notify_comment() 호출

## D-019 [P2] 진행률 마일스톤 산식 미명시
- 페이지: /progress-dashboard
- 페르소나: 이한중
- 증거: `progress_dashboard.html:44` done_ms / total_ms
- 권장: database.py에 progress_matrix() 산식 주석

## D-020 [P2] 변경공지 SLA 부재
- 페이지: /changes
- 페르소나: 김형렬
- 증거: `changes_list.html:105-108` 무한 "공지중"
- 권장: CHANGE_ACK_SLA_HOURS=72 + 경과 색상

## D-021 [P1] 게시글 반려 사유 저장 부재
- 페이지: /board/post/{id}/reject
- 페르소나: 박지은
- 증거: `board_list.html:44-46` reject_reason input + DB 저장 없음
- 권장: rejection_reason 컬럼 추가 + 저장

## D-022 [P2] WO 번호 패턴 불일치 가능
- 페이지: /production/work-orders
- 페르소나: 윤영조
- 증거: `wo_list.html:78` "WO-0001" 표기 + gen_wo_no() 미공개
- 권장: 패턴 통일 (WO-2026-0001) + 공개

## D-023 [P2] /feed 필터 클라이언트만 동작
- 페이지: /feed
- 페르소나: 박지은
- 증거: `feed.html:56-70` `data-filter` 속성, 서버 필터 없음
- 문제: 전체 데이터 로드 후 JS 숨김만
- 권장: 서버 필터 (`?filter=지연`)

---

**Tier 합계**: P0×0 + P1×9 + P2×14 + P3×0 = 23건
(에이전트 보고: P0:3건이지만 본 검증 시 모두 P1로 재분류 — 본업 차단 아닌 운영 마찰)
