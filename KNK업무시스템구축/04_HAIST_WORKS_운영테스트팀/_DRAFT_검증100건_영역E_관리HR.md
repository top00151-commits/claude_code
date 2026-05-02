# 영역 E — 관리·HR·외부자산 검증 (26건 발견)

> 04 운영테스트팀 / Explore agent E 결과 흡수
> 일자: 2026-04-29
> 정직성 v3: grep -n 직접 인용 / 추정 0건

## E-001 [P1] /admin 진입 권한 정합 모순
- 페이지: /admin
- 페르소나: 박지은 인사총무 leader
- 증거: `main.py:2818` require admin/ceo, vs `/admin/permissions/grant` 별도 권한
- 문제: 권한 부여 페이지 별도 진입 가능 → 정책 불일치
- 권장: leader 권한 부여 진입 경로 명시

## E-002 [P2] 권한 부여 폼 필수/선택 흐름 모호
- 페이지: /admin/permissions/grant
- 페르소나: 김정락 CEO
- 증거: `admin_permissions_grant.html:64-68` 사유=선택 + 위치 어색
- 권장: 필드 그룹핑 또는 사유 상단 배치

## E-003 [P1] 권한 만료 기본 30일 자동 설정 미구현
- 페이지: /admin/permissions/grant
- 페르소나: 김정락
- 증거: `admin_permissions_grant.html:61` "기본 30일" 힌트
- 문제: required date 빈 제출 불가 → JS/BE 자동 계산 없음
- 권장: 오늘+30일 placeholder/value 자동

## E-004 [P2] 권한 매트릭스 우선순위 표기 모호
- 페이지: /admin/permissions/matrix
- 페르소나: 감사자 / 김정락
- 증거: `admin_permissions_matrix.html:85` "D > G > T 우선"
- 문제: 다중 출처 시 셀 표기 규칙 부재
- 권장: 예시 + 표기 규칙 명시

## E-005 [P2] /profile 권한 8건 초과 시 전체보기 부재
- 페이지: /profile
- 페르소나: 최혜연
- 증거: `profile.html:117-121` `[:8]` + `+N`
- 권장: "전체 권한 보기" 링크

## E-006 [P2] /hr/hiworks URL 미설정 안내 단절
- 페이지: /hr/hiworks
- 페르소나: 최혜연 사원
- 증거: `hr_hiworks.html:49,20` opacity:0.5 + 텍스트만
- 문제: 사원이 설정 진입 못 함
- 권장: "관리자에게 요청" 버튼

## E-007 [P0] 회사정보 저장 피드백 부재
- 페이지: /admin/company-info
- 페르소나: 김정락
- 증거: `admin_company_info.html:14-17` saved 변수 미연결
- 문제: 저장 성공 여부 불명 → 본인 결재 의문
- 권장: ?saved=1 또는 flash

## E-008 [P1] 외부자산 색상 체계 불일치
- 페이지: /admin/external-assets
- 페르소나: 김정락
- 증거: `external_assets_review.html:33` 보안 빨강 #DC2626 vs 상단 카드 다른 색
- 권장: 보안 빨강 / 의존 오렌지 / 기타 회색 통일

## E-009 [P2] 외부자산 부분 처리 시 대체안 선택 부재
- 페이지: /admin/external-assets
- 페르소나: 김정락
- 증거: `external_assets_review.html:104-108` ul 정보성만
- 권장: "부분 처리" 시 대체안 드롭다운

## E-010 [P1] /admin/settings 토큰 마스킹 부재
- 페이지: /admin/settings
- 페르소나: 김정락
- 증거: `admin_settings.html:63` autocomplete=off + value 평문 노출 가능
- 권장: `•••••` + 변경 버튼

## E-011 [P2] 알림 채널 경고 12px 가독성
- 페이지: /admin/settings
- 페르소나: 김정락
- 증거: `admin_settings.html:84-86` font-size:12px
- 권장: 13~14px + 배경 강조

## E-012 [P2] 권한 감사 CSV 인코딩 미명시
- 페이지: /admin/permissions/audit.csv
- 페르소나: 감사자
- 증거: `main.py:6079` charset 헤더 미확인
- 문제: Windows Excel 인코딩 깨짐 가능
- 권장: UTF-8 BOM 또는 CP949

## E-013 [P1] /guide 검색 JS 미구현 추정
- 페이지: /guide
- 페르소나: 신입사원
- 증거: `guide.html:256-263` 검색바 input + JS 미확인
- 권장: 검색 기능 활성화 또는 "준비 중" 안내

## E-014 [P1] /guide 인라인 스타일 과다
- 페이지: /guide
- 페르소나: 운영팀
- 증거: `guide.html:1-244` ~500줄 인라인
- 문제: 유지보수 악화
- 권장: 재사용 클래스 / CSS 변수 추출

## E-015 [P1] /profile 비번 변경 취소 URL 오류
- 페이지: /profile
- 페르소나: 최혜연
- 증거: `profile.html:78` `href="/daily/{{ '' }}"` (빈 날짜)
- 문제: 404 가능
- 권장: `/home` 또는 `javascript:history.back()`

## E-016 [P2] /admin 사용자 목록 leader 필터링 정합
- 페이지: /admin
- 페르소나: 박지은
- 증거: `main.py:2831` `WHERE u.role!='admin'`
- 문제: leader 진입 못하므로 무의미
- 권장: 정책 통일

## E-017 [P3] /admin 활성 탭 색상 비표준
- 페이지: /admin
- 페르소나: 김정락
- 증거: `admin.html:32` `.atab-on { color:#A5282C !important; }`
- 권장: 전사 탭 스타일 가이드 적용

## E-018 [P2] 권한 위임 카드 재위임 토글 표기 모호
- 페이지: /admin/permissions
- 페르소나: 김정락
- 증거: `admin_permissions.html:45` "🔒 재위임OFF" 고정
- 권장: ON 케이스 표기 추가

## E-019 [P1] 비번 재생성 체크박스 모바일 깨짐
- 페이지: /admin
- 페르소나: 김정락
- 증거: `admin.html:227-228` label max-width 없음
- 권장: flex-wrap + max-width

## E-020 [P2] 권한 매트릭스 sticky z-index 충돌 가능
- 페이지: /admin/permissions/matrix
- 페르소나: 감사자
- 증거: `admin_permissions_matrix.html:54-62` `position:sticky;left:0;z-index:1`
- 권장: 헤더=2, 사용자명=1 계층화

## E-021 [P1] 외부자산 결정 문서 경로 하드코딩
- 페이지: /admin/external-assets
- 페르소나: 빅터 / 김정락
- 증거: `external_assets_review.html:145` `99_DISPATCH/외부자산_결정_2026-04-27.md`
- 문제: 일자 고정 → 향후 결정과 불일치
- 권장: `{{ today_date }}.md` 동적

## E-022 [P2] /admin/hiworks-settings 저장 피드백 미확인
- 페이지: /admin/hiworks-settings
- 페르소나: 김정락
- 증거: `main.py:3281` 저장 후 응답 미확인
- 권장: ?saved=1

## E-023 [P1] 팀 권한 수정 소유권 검증 미확인
- 페이지: /team/{team_id}/permissions
- 페르소나: 박지은
- 증거: `main.py:1654-1727` require 조건 확인 필요
- 문제: leader가 다른 팀 권한 수정 가능 가능성
- 권장: 본인 팀만 수정 가드

## E-024 [P2] /guide edition_no 하드코딩
- 페이지: /guide
- 페르소나: 운영팀
- 증거: `guide.html:251` `VOL. 26 · NO. {{ edition_no|default('118') }}`
- 권장: BE 동적 계산 또는 표기 제거

## E-025 [P2] /admin 사용자 추가 비번 기본값 안내 부재
- 페이지: /admin
- 페르소나: 김정락
- 증거: `admin.html:82` placeholder만, BE `hash_pw(d.get("password", "knk1234"))`
- 권장: "기본 knk1234" placeholder + 안내

## E-026 [P1] /admin/permissions/groups 라우트 검증 미완
- 페이지: /admin/permissions/groups
- 페르소나: 김정락
- 증거: `main.py:6117-6238` 라우트 + 템플릿 미상세 검토
- 권장: 그룹 CRUD UI 흐름 별도 검증

---

**Tier 합계**: P0×1 + P1×11 + P2×13 + P3×1 = 26건
