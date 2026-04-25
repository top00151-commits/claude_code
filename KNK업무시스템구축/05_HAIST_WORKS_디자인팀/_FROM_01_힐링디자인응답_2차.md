# [01 → 05] 힐링 3차 패치 ①~④ 적용 완료 회신 (2차)

> **발신**: 01 메인 세션 빅터
> **수신**: 05 디자인팀
> **참조**: 04 운영테스트팀, 09 프로젝트 팀장
> **일자**: 2026-04-25 13:30
> **근거**: `_세션01_전달/_TO_01_힐링3차_QA반영_긴급패치.md` (05 발행 13:05)
>          `04_HAIST_WORKS_운영테스트팀/qa_healing_results.md` (04 1차 회신)

---

## 0. 한 줄

지시받은 4건 패치 모두 적용·검증 완료. 회귀 테스트 통과. 커밋 3건 (패치 ①·③ 동일 파일이라 1커밋, ②·④ 분리).

---

## 1. 회신 양식

- [x] **패치 ① (.dock-tab 제거)** 완료 — 커밋 `2db51e6`
- [x] **패치 ② (CEO 매출 fallback)** 완료 — 커밋 `7f5fb76`
- [x] **패치 ③ (언어 셀렉터 정합)** 완료 — 커밋 `2db51e6` (base.html 동시 수정)
- [x] **패치 ④ (인사말 검증 보강)** 완료 — 커밋 `756c47f`

---

## 2. 적용 상세

### 패치 ① — `.dock-tab` 제거 (QA-H2)
- `app/templates/base.html:1037` — 4줄 블록 → 한 줄 주석으로 대체
- `app/templates/base_logi.html:204` — 동일 처리
- `static/style.css:3616-3649` — `.dock-tab`, `.dock-tab:hover`, `.dock-tab .t-ico`, `.dock-tab kbd`, `body.dock-open .dock-tab` 5개 룰 모두 삭제
- `static/style.css:3891-3895` — 모바일 반응형 `.dock-tab` 룰도 제거
- 헤더 `.tb-icon-btn.victor` (앰버 버튼)이 유일한 트리거로 남음

### 패치 ② — CEO 매출 KPI graceful fallback (QA-H1)
- `app/templates/home.html:180` — 분기 `{% if is_executive and monthly_revenue is not none %}` → `{% if is_executive %}`
- 카드 내부에 `{% if monthly_revenue is not none and monthly_revenue > 0 %}` 분기 추가
- 데이터 부재 시 `— 집계 준비 중` + `이번 달 수주 데이터 누적 중이에요` 안내 출력
- `kpi-lock-badge`, `hm2-kpi-ico` 등 시각 요소는 그대로 유지 → 카드 위치 인지 가능
- 평직원·팀장은 `is_executive=False` 라 카드 자체 미렌더 (3중 방어 유지)

### 패치 ③ — `#trLang` LANGS 동적 (QA-H3·H4·H5)
- `app/templates/base.html:404` — `<select>` 옵션 5종 하드코딩 → `{% for code, label in LANGS.items() %}` 동적 렌더
- `app/templates/base.html:580` — JS `langNames` 객체 5종 → `{ko, vi, en}` 3종으로 축소
- `main.py:1047` `tgt_map` (외부 Google Translate API용)은 §4-3 권고대로 보류 — UI 옵션이 ko/vi/en 만 노출되면 ja·zh-CN 코드는 호출 경로에 진입 불가능

### 패치 ④ — `data-greeting-bucket` 속성 (QA-H6)
- `app/main.py:482-498` — 시간대 분기 시 `greeting_bucket` 변수 동시 설정 (`morning|lunch|afternoon|evening|night|default`)
- `app/main.py:512` — `ctx()` 호출에 `greeting_bucket=greeting_bucket` 추가
- `app/templates/home.html:38` — `<h1 class="hm2-title" data-greeting-bucket="{{ greeting_bucket|default('default') }}">` 속성 부여
- 04 검증 시 시각과 무관하게 속성 존재만 확인하면 인사말 동작 검증 가능

---

## 3. §7 회귀 검증 결과 (01 자체)

CEO `kjr / knk1234` 로그인 후 `/home` 응답 분석:

| 검증 항목 | 명령 결과 | 기대 | 판정 |
|---|---|---|---|
| `dock-tab` 마크업 | 0건 | 0 | ✅ PASS |
| `zh-CN` 노출 | 0건 | 0 | ✅ PASS |
| `중국어` 노출 | 0건 | 0 | ✅ PASS |
| `일본어` 노출 | 0건 | 0 | ✅ PASS |
| `이번 달 수주` (CEO) | 2건 (라벨 + lock-badge) | ≥1 | ✅ PASS |
| `집계 준비 중` (데이터 없음) | 1건 | ≥1 | ✅ PASS (fallback 동작) |
| `data-greeting-bucket` | `lunch` (검증 시각 13:30) | 매트릭스 일치 | ✅ PASS |
| `경영진` 뱃지 | 2건 | ≥1 | ✅ PASS |
| 응답 길이 | 176 KB | — | 정상 |

평직원/팀장 매출 미노출은 04 1차 검증에서 이미 PASS (`monthly_revenue=0, ₩=0, 억=0`). 본 패치 ②는 평직원 분기를 변경하지 않았으므로 회귀 위험 없음.

---

## 4. 미처리/보류 사항

### 4-1. `projects` 테이블 부재 (05 §3-3 “시드 보강(선택)”)
- 본 패치 범위 외 — 09 팀장 의사결정 대기
- 현재 fallback 으로 UX는 매끄럽게 동작
- baby PMS 스키마 확정 후 `projects`/`shipments` 테이블이 정착되면 자연 해소 예상

### 4-2. `tgt_map` (main.py:1047)
- 05 §4-3 권고 그대로 보류 — ja·zh-CN 매핑 코드는 남겼지만 UI 진입 경로 차단으로 호출되지 않음
- 향후 외부 번역 위젯 정책 변경 시 일괄 정리 권장

### 4-3. 힐링 전환 잔여 작업 (1차 응답 기준)
| 시안 | 상태 |
|---|---|
| #6 로그인 sage 스킨 | 미착수 (원래 1차 응답에서 보고) |
| #8 /progress 매트릭스 | 미착수 |
| #9 /dashboard SVG 차트 | 미착수 |
| #4 페이지 헤더 partial | 미착수 |
→ 09 팀장 / 대표 우선순위 지시 대기

---

## 5. 회귀 명령 (재현 가능)

```bash
cd 01_HAIST_WORKS
PYTHONIOENCODING=utf-8 python run.py &  # 8081
python -c "
import requests, re
s = requests.Session()
s.post('http://127.0.0.1:8081/login', data={'login_id':'kjr','password':'knk1234'})
h = s.get('http://127.0.0.1:8081/home').text
print('dock-tab:', h.count('dock-tab'))         # 0
print('zh-CN:', h.count('zh-CN'))               # 0
print('일본어/중국어:', '일본어' in h, '중국어' in h)  # False False
print('이번 달 수주:', h.count('이번 달 수주'))  # >=1
print('집계 준비 중:', h.count('집계 준비 중'))  # 1 (시드 없을 때)
print('bucket:', re.findall(r'data-greeting-bucket=\"([^\"]+)\"', h))  # ['<bucket>']
"
```

---

## 6. 04 운영테스트팀 재검증 요청

- **회귀 범위**: QA-H1·H2·H3·H4·H5·H6 6건 전체
- **CEO 인증**: `kjr / knk1234`
- **시간대별 인사말 매트릭스** (05 §5-2 그대로 인용):
  ```
  06~11: 좋은 아침입니다 ☀️           (bucket=morning)
  11~14: 점심은 드셨나요              (bucket=lunch)
  14~18: 오후도 힘내세요 🌿            (bucket=afternoon)
  18~22: 오늘도 수고하셨어요          (bucket=evening)
  22~06: 늦은 시간까지 애쓰시네요      (bucket=night)
  ```
  → 텍스트 매칭 대신 `data-greeting-bucket` 속성 존재만 확인하면 시각 무관 PASS

---

## 7. 커밋 ID 일람

| 커밋 | 메시지 | 패치 |
|---|---|---|
| `2db51e6` | fix(dock): remove .dock-tab residual (QA-H2) | ① + ③ (base.html 동시) |
| `7f5fb76` | feat(home): graceful fallback for revenue KPI (QA-H1) | ② |
| `756c47f` | chore(home): add greeting_bucket context (QA-H6) | ④ |

총 3커밋 / 5파일 / +31 -62 라인.

---

**발행**: 2026-04-25 13:35 · 01 메인 세션 빅터
**상태**: 🟢 패치 ①~④ 전부 완료 · 04 재검증 요청 대기
