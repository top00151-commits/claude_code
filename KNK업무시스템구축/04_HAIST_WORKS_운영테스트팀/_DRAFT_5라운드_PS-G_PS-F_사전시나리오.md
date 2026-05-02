# 5라운드 PS-G 쑤아잉 + PS-F kjr — 정적 사전 시나리오 매트릭스

> 04 운영테스트팀 / 빅터
> 일자: 2026-05-01
> 트리거: 09 결재서 5라운드 PS-A → PS-B → **PS-G 쑤아잉** → **PS-F kjr** 순서
> 비간섭 원칙: 사전 정적 매트릭스, 동적 회귀 09 신호 후

---

# Part I — PS-G 쑤아잉 (베트남법인 i18n 침투 검증 핵심)

## 0. 페르소나 정의

| 항목 | 값 | 근거 |
|---|---|---|
| 이름 | 쑤아잉 | `database.py:1575` |
| 팀 | 12 베트남법인 (team_id=12) | `database.py:1465, 1570` |
| 직급 | 차장 | `database.py:1575` |
| 역할 | member | `database.py:1575` |
| login_id | `쑤아잉` (한글 시드) | 사이클 81 마이그 후 |
| 비밀번호 | `knk1234` |
| 본업 | 베트남 현지 품질 이슈 대응 / 수출입 서류 / FTA 수입 (`database.py:982, 2196`) |
| 핵심 검증 | **i18n vi 언어 침투** (Level-10) — 한국어 잔존 시 사용 불가 |

## 1. 검증 동선 (8단계)

| Step | URL | L-10 vi 침투 검증 |
|---|---|---|
| S1 | /login?lang=vi | ✅ login.html v5_login.css PASS / ⚠ 사이클 81 lang param 핸들러 PASS 여부 |
| S2 | /home | ⚠ sb_* 키 472+ 정의됨 / 페이지 본문 한국어 잔존 검증 |
| S3 | /api/set-lang POST {lang:vi} | ✅ 사이클 81 PASS (서버) / 페이지 본문 한국어 grep |
| S4 | 사이드바 vi 라벨 | `i18n.py:22-37` `sb_my_work~sb_no_project` vi 정의 ✅ |
| S5 | /export → /fta 신규 발급 | ⚠ B-017 FTA_TYPES 중복 / origin_country=VN |
| S6 | /quotation/print?lang=vi | ⚠ B-014 reload 스크롤 손실 / B-015 통화 하드코딩 (KRW 고정 → VND/USD 미지원) |
| S7 | /search vi 검색어 입력 | sb_search 키 vi PASS |
| S8 | 빅터 도크 vi 인사말 | 사이클 88 W4·W5 PASS — vi 인사말 검증 필요 |

## 2. 5라운드 PS-G L-10 침투 매트릭스

| 영역 | 한국어 잔존 검증 grep | 결과 |
|---|---|---|
| 사이드바 메뉴 | `grep -n '내 업무\|업무현황\|일일업무' app/templates/base.html` | i18n 키 사용 OK 가정 |
| 헤더 버튼 | `grep -nE '검색\|알림\|로그아웃' app/templates/base.html` | i18n 키 사용 OK |
| 모달 제목 | partials `modals.html` 한국어 grep | 검증 필요 |
| 에러 메시지 | `error.html` ko/vi/en | error.html `lang: "ko"` 하드코딩 (L:173) ⚠ |
| 일일카드 카테고리 | `daily.html` select 옵션 | 검증 필요 |
| FTA C/O 페이지 | `fta_form.html`, `fta_print.html` | 검증 필요 |
| 환율 통화 코드 | `rates.html`, `rates_dashboard.html` | USD/VND/JPY/CNY/EUR 표기만 |
| 견적서 인쇄 통화 | `quotation_print.html:163` `i.qp_currency_krw` 고정 | ❌ FAIL (B-015) |

## 3. 발견 (117건 회귀 + i18n 신규)

| OPS | Tier | 117건 코드 / 신규 |
|---|---|---|
| OPS-PS-G-1 | P1 | B-012 customer_detail i18n 미전달 (S5 동선) |
| OPS-PS-G-2 | P1 | B-014 quotation 다국어 reload (S6 마찰) |
| OPS-PS-G-3 | P1 | B-015 quotation 통화 하드코딩 (S6 본업 차단) |
| OPS-PS-G-4 | P1 | B-016 export_home empty state (S5) |
| OPS-PS-G-5 | P1 | B-017 FTA_TYPES 중복 (S5) |
| OPS-PS-G-6 | P2 | C-017 환율 통화 코드 일관성 (S5/S7) |
| OPS-PS-G-7 | **P1 신규** | error.html `lang: "ko"` 하드코딩 → vi 사용자 에러 페이지 한국어만 |
| OPS-PS-G-8 | **P2 신규** | partials/modals.html 한국어 잔존 검증 미수행 — 정적 grep 필요 |
| OPS-PS-G-9 | **P2 신규** | i18n 키 472+ vs 실제 템플릿 사용 키 매칭 미검증 (사이클 81 추적) |

→ 9건 (P1×6 + P2×3). 본 라운드는 i18n 침투 신규 3건 발견.

## 4. error.html lang 하드코딩 정정 권고 (즉시 발주 가능)

**파일**: `app/main.py:173`
**현재**:
```python
"lang": "ko", "i": {}, "LANGS": LANGS,
```
**수정**:
```python
"lang": (request.session.get("lang", "ko") if hasattr(request, "session") else "ko"),
"i": get_all_translations(request.session.get("lang", "ko") if hasattr(request, "session") else "ko"),
"LANGS": LANGS,
```
- 검증 grep: `grep -n '"lang":\s*"ko"' app/main.py` → 1매치 (수정 후 0)
- 마감: 5분
- race: 단일 main.py 단일 line 수정 — 안전

---

# Part II — PS-F kjr (실제 김정락 대표 + OPS-V15·OPS-012 회귀)

## 0. 페르소나 정의

| 항목 | 값 | 근거 |
|---|---|---|
| 이름 | 김정락 | `database.py:1475` |
| 팀 | None (이사회 직속) | `database.py:1474-1475` |
| 직급 | 대표이사 | `database.py:1475` |
| 역할 | **ceo** | `database.py:1475` |
| login_id | `kjr` (명시 부여) | `database.py:1991` |
| 비밀번호 | `knk1234` |
| 본업 | 전사 대시보드 / 외부자산 / 회사 정보 / 결재 / 매출 KPI |
| 보조 시드 (사이클 85) | `kjr2` 가짜 CEO 시드 — OPS-012 안내 배너 검증용 |

## 1. 검증 동선 (10단계)

| Step | URL | 검증 |
|---|---|---|
| S1 | /login → kjr / knk1234 | role=ceo |
| S2 | /home → role_home → /dashboard 자동 | `main.py:550` `role in ("ceo","admin","executive")` → /dashboard |
| S3 | /dashboard | ✅ 9 KPI grid (Phase 2-1 W9) / OPS-A-018 모바일 grid 검증 |
| S4 | /admin 진입 | role=ceo PASS / `main.py:2818` require admin/ceo |
| S5 | /admin/external-assets | E-008 색상 / E-009 대체안 선택 / E-021 결정 문서 경로 |
| S6 | /admin/company-info | OPS-P0-4 (E-007) ?saved=1 적용 PASS 회귀 |
| S7 | /admin/permissions/matrix | E-004 우선순위 표기 / W10 토글 |
| S8 | /admin → 사용자 비번 리셋 (OPS-V15) | 사이클 85 핫패치 — admin 옆 [비번 리셋] 버튼 |
| S9 | /weekly | I-2 빅터 인사이트 / OPS-W-3 print 룰 회귀 |
| S10 | 외부자산 결정 → 99_DISPATCH 작성 | (대표 수동 처리) |

## 2. 보조 검증 — kjr2 (가짜 CEO 시드, 사이클 85 OPS-012)

| Step | URL | 검증 |
|---|---|---|
| 보조 1 | /login → kjr2 / knk1234 | 시드된 가짜 leader (역할=leader 가정) |
| 보조 2 | /dashboard | OPS-P1-G1 (A-008) → ?no_perm=dashboard 폴백 |
| 보조 3 | /home (폴백) | "🔒 전사 대시보드는 경영진..." 노란 배너 (OPS-012 PASS) |

→ 사이클 85 핫패치 회귀. **kjr2 시드 존재 여부 동적 검증 필요** (옵션 C 시드 재실행 후).

## 3. 5라운드 PS-F 발견 (117건 회귀 + 관리자 영역)

| OPS | Tier | 코드 | kjr 동선 |
|---|---|---|---|
| OPS-PS-F-1 | P0 | E-007 회사정보 저장 피드백 (수정 PASS 회귀) | S6 |
| OPS-PS-F-2 | P1 | E-001 admin 진입 정책 (CEO=admin/ceo OK) | S4 — kjr는 PASS, 박지은(leader)만 차단 |
| OPS-PS-F-3 | P1 | E-008 외부자산 색상 체계 | S5 |
| OPS-PS-F-4 | P1 | E-010 토큰 마스킹 부재 | (보안) |
| OPS-PS-F-5 | P1 | E-021 외부자산 결정 문서 경로 하드코딩 | S5 |
| OPS-PS-F-6 | P1 | E-023 팀 권한 수정 소유권 (CEO 무관) | — |
| OPS-PS-F-7 | P2 | E-004 권한 매트릭스 우선순위 | S7 |
| OPS-PS-F-8 | P2 | A-018 9-KPI 모바일 grid | S3 |
| OPS-PS-F-9 | P2 | OPS-W-3 weekly print | S9 (수정 PASS 회귀) |
| OPS-PS-F-10 | P2 | E-018 재위임 토글 표기 | S7 |
| OPS-PS-F-11 | P3 | E-017 admin 활성 탭 색상 | S4 |
| OPS-PS-F-12 | P3 | E-024 guide edition_no 하드코딩 | (사용가이드) |

→ 12건 회귀 (P0×1 + P1×5 + P2×4 + P3×2).

## 4. 회신 양식 (PS-G + PS-F 통합)

```
## P-G 쑤아잉 (베트남법인 차장 / member)
### Level-10 i18n vi 침투 매트릭스 (8단계)
- 사이드바 vi 라벨: ✅ i18n.py 사용 OK / 동적 grep 필요
- error.html vi: ❌ FAIL (lang 하드코딩)
- quotation_print vi: ❌ FAIL (통화 KRW 고정)
- ...
### 발견 9건 (117 회귀 6 + 신규 3)
### 즉시 발주: error.html lang 하드코딩 정정 (5분)

## P-F kjr (김정락 대표 / ceo)
### 10단계 + kjr2 보조 3단계
- /dashboard 진입 PASS (role=ceo)
- E-007 회사정보 저장 (수정 PASS) — 회귀
- OPS-V15 비번 리셋 UI — 동적 검증
- OPS-012 kjr2 → /home 노란 배너 — 동적 검증
### 발견 12건 회귀
```

---

# Part III — 통합 권고

## 5라운드 4 페르소나 사전 매트릭스 완료
- ✅ PS-A 안지연 (영업 11단계, 13 OPS)
- ✅ PS-B 허동준 (구매 12단계, 25 OPS + 6 V 보강)
- ✅ PS-G 쑤아잉 (베트남법인 i18n 8단계, 9 OPS + 3 신규)
- ✅ PS-F kjr (대표 10단계 + kjr2 3단계, 12 OPS)

→ **합계 41단계 / 59 OPS / 6 V 보강 / 신규 3건**

## 즉시 가능 추가 발주
1. **OPS-PS-G-7 [P1] error.html lang 하드코딩 정정** — main.py:173 1줄 패치 / 5분 / race 0
   - 09 결재 후 _TO_01 발주 발행 권고
   - 사이클 81 i18n 트랙 흡수 가능

## 동적 회귀 가동 시점 (재확인)
- 옵션 A 즉시 / 옵션 B 117건 회신 + 시드 재실행 후
- **04 권고: 옵션 B** — 패치 미반영 상태 동적 = 같은 결함 재발견

---

*04 운영테스트팀 빅터 — 2026-05-01*
*5라운드 4 페르소나 사전 매트릭스 완료 + i18n 신규 3건 발견 (OPS-PS-G-7 즉시 발주 가능).*
