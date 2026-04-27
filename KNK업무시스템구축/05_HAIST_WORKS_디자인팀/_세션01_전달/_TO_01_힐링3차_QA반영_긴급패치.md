# [05 → 01] 🔴 힐링 3차 패치 지시 · 04 QA 결과 반영

> **발신**: 05 디자인팀 세션 빅터
> **수신**: 01 메인 세션
> **일자**: 2026-04-25 13:00
> **근거**: `_FROM_04_힐링QA결과_01.md` (04 운영테스트팀 1차 회신)

---

## 0. 한 줄

04 페르소나 검증에서 발견된 **S1 3건 + S2 3건**을 4건의 패치로 통합 처리해 주세요. 각 라인 번호·코드 블록 명시.

**우선순위**: 패치 ① → ② → ③ → ④ 순. 모두 **2시간 내** 가능 추정.

---

## 1. 04 검증 결과 요약 (참조)

| QA-ID | 심각도 | 04 발견 | 본 지시 처리 |
|---|---|---|---|
| QA-H1 | 🔴 S1 | CEO 화면에 매출 금액 0회 노출 | **패치 ②** (시드 + 표시 안전화) |
| QA-H2 | 🔴 S1 | `.dock-tab` 마크업 1건 잔존 | **패치 ①** (2차 지시 재독려) |
| QA-H3 | 🔴 S1 | `zh-CN` 중국어 옵션 노출 | **패치 ③** |
| QA-H4 | 🟠 S2 | `ja` 일본어 옵션 노출 | **패치 ③** (동시 처리) |
| QA-H5 | 🟠 S2 | ko/vi/en 옵션 마크업 중복 | **패치 ③** (자연 해결) |
| QA-H6 | 🟠 S2 | 시간대별 인사말 0회 발견 | **패치 ④** (검증 재요청) |

**04 PASS 항목 (유지)**:
- 평직원·팀장 매출 미노출 (`monthly_revenue` JSON 키 0건, "₩"·"억" 텍스트 0건)
- /dashboard 평직원 직접 접근 차단 (303 리다이렉트)
- ko/vi/en 번역 자체 정상 동작

---

## 2. 패치 ① — 빅터 도크 `.dock-tab` 제거 (재독려)

### 2-1. 04 발견 마크업 (24종 dock 클래스 중 .dock-tab 1건 존재)

```
04 검증: "class='...dock-tab...' 발견 → 1건"
```

**의미**: 19:35 발행한 `_TO_01_힐링2차_빅터도크긴급수정_우선순위.md` 의 **§2-5-① HTML 변경**이 미반영.

### 2-2. 점검 명령

```bash
cd 01_HAIST_WORKS
grep -rn "dock-tab" app/templates/ static/style.css
# 결과 0이어야 함. 1건 이상이면 모두 제거.
```

### 2-3. 제거 대상 (예시 — 실제 위치는 grep 결과 따름)

`app/templates/base.html` 중에서:
```html
<!-- ❌ 이 블록 통째로 삭제 -->
<div class="dock-tab" onclick="toggleDock()" ...>
  <span>🤖 빅터</span>
  <span>⌘K</span>
</div>
```

`static/style.css`:
```css
/* ❌ 관련 CSS 모두 삭제 */
.dock-tab { ... }
.dock-tab::before { ... }
.dock-tab:hover { ... }
```

**조건**: 헤더 `.tb-icon-btn.victor` (앰버 버튼)이 유일한 트리거여야 함. 시각적으로 우측 세로 탭 잔존 시 메인 영역 "신규 작성" 버튼과 충돌 가능 (대표 직접 지적사항).

---

## 3. 패치 ② — CEO 매출 KPI 표시 안전화 (QA-H1)

### 3-1. 원인 분석 (05가 직접 조사)

```bash
$ sqlite3 01_HAIST_WORKS/haist.db "SELECT count(*) FROM projects WHERE order_amount>0"
ERR: no such table: projects
```

→ **`projects` 테이블 자체 부재**. 따라서:
- `main.py:464~478` SELECT 실행 → 예외 → `except: print` 만 하고 `monthly_revenue` 가 **`None` 으로 남음**
- `home.html:180`: `{% if is_executive and monthly_revenue is not none %}` → **카드 미렌더**

→ **결과**: CEO 에게도 매출 KPI 자체가 표시되지 않음.

### 3-2. 처리 옵션

**(A) 시드 데이터 보강** — 가장 정공법. 시드 마이그레이션 별도 작업.

**(B) 매출 카드 "준비 중" fallback** — 즉시 적용 가능 ✓ **권장**

`app/templates/home.html:180` 분기 변경:
```jinja2
{# AS-IS #}
{% if is_executive and monthly_revenue is not none %}
  ...매출 카드...
{% endif %}

{# TO-BE — 경영진은 항상 카드 표시. 데이터 없으면 안내 문구 #}
{% if is_executive %}
<div class="hm2-kpi-grid" style="margin-top:14px;">
  <a href="/dashboard" class="hm2-kpi" style="...">
    <div class="kpi-lock-badge" style="...">🔒 경영진</div>
    <div class="hm2-kpi-top">
      <span class="hm2-kpi-lab">이번 달 수주</span>
      <div class="hm2-kpi-ico" style="...">...</div>
    </div>
    {% if monthly_revenue is not none and monthly_revenue > 0 %}
      <div class="hm2-kpi-val" style="font-size:var(--fs-fluid-2xl);color:#2B3E2E;">
        {% if monthly_revenue >= 100000000 %}{{ '%.1f'|format(monthly_revenue/100000000) }}<span class="hm2-kpi-unit">억</span>
        {% elif monthly_revenue >= 10000000 %}{{ '%.1f'|format(monthly_revenue/10000000) }}<span class="hm2-kpi-unit">천만</span>
        {% else %}{{ '{:,.0f}'.format(monthly_revenue) }}{% endif %}
      </div>
      <div class="hm2-kpi-delta {% if yoy_delta and yoy_delta >= 0 %}up{% else %}down{% endif %}">
        {% if yoy_delta is not none %}
          {% if yoy_delta >= 0 %}▲ 전년 대비 +{{ yoy_delta }}%{% else %}▼ 전년 대비 {{ yoy_delta }}%{% endif %}
        {% else %}전년 비교 집계 준비 중{% endif %}
      </div>
    {% else %}
      <div class="hm2-kpi-val" style="font-size:var(--fs-fluid-lg);color:#8FA594;font-weight:600;">
        — <span style="font-size:60%;font-weight:500">집계 준비 중</span>
      </div>
      <div class="hm2-kpi-delta" style="color:#8FA594">이번 달 수주 데이터 누적 중이에요</div>
    {% endif %}
  </a>
  ...
</div>
{% endif %}
```

**효과**: 경영진은 항상 매출 카드 위치 인지. 데이터 부재 시에도 "준비 중" 안내로 자연스러운 UX. 권한 분기는 그대로 유지 (평직원에겐 카드 자체 안 뜸).

### 3-3. 시드 보강 (선택 · 별도 진행 가능)

`01_HAIST_WORKS/app/database.py` 또는 `seed.py` 에서 `projects` 테이블 생성 + 4월 매출 시드 3~5건 삽입. **본 패치와 분리 가능**. 09 팀장 별도 의사결정.

---

## 4. 패치 ③ — 언어 셀렉터 `zh-CN`·`ja` 제거 (QA-H3·H4·H5)

### 4-1. 04 발견

```
홈 페이지 셀렉터 마크업:
[('ko','🇰🇷 한국어'), ('vi','🇻🇳 Tiếng Việt'), ('en','🇺🇸 English'),
 ('vi','🇻🇳 베트남어'), ('en','🇺🇸 영어'), ('ko','🇰🇷 한국어'),
 ('ja','🇯🇵 일본어'),     ← 의뢰서 외
 ('zh-CN','🇨🇳 중국어')]   ← 의뢰서 §S3 위반
```

### 4-2. 원인 (05가 직접 조사)

| 위치 | 셀렉터 | 옵션 | 상태 |
|---|---|---|---|
| `base.html:35~39` | `#langSel` (UI 언어) | `LANGS.items()` 순회 = ko/vi/en | ✅ 정상 |
| `base.html:404~410` | `#trLang` (번역 위젯) | **5종 하드코딩** (vi, en, ko, ja, zh-CN) | ❌ 이상 |
| `base.html:582` | `langNames` JS 객체 | **5종 하드코딩** | ❌ 이상 |
| `main.py:1047` | 외부 번역 API tgt_map | 5종 매핑 | ⚠ 조정 검토 |

**핵심**: `#trLang` 은 카드 모달 내부의 "본문 자동 번역" 위젯. UI 언어와는 다른 개념이지만, 내부 직원 구성(한국·베트남)에 일본·중국 추가는 정합성 부족.

### 4-3. 패치 (`app/templates/base.html`)

**① line 404~410 교체**:
```html
<!-- AS-IS -->
<select id="trLang">
  <option value="vi">🇻🇳 베트남어</option>
  <option value="en">🇺🇸 영어</option>
  <option value="ko">🇰🇷 한국어</option>
  <option value="ja">🇯🇵 일본어</option>
  <option value="zh-CN">🇨🇳 중국어</option>
</select>

<!-- TO-BE — LANGS 기반 동적 렌더 (UI 셀렉터와 일치) -->
<select id="trLang">
  {% for code, label in LANGS.items() %}
    <option value="{{ code }}">{{ label }}</option>
  {% endfor %}
</select>
```

**② line 582 교체**:
```js
// AS-IS
const langNames = {vi:'🇻🇳 베트남어',en:'🇺🇸 영어',ko:'🇰🇷 한국어',ja:'🇯🇵 일본어','zh-CN':'🇨🇳 중국어'};

// TO-BE — i18n.py 의 LANGS 와 일치 (한국어 표기 통일)
const langNames = {ko:'🇰🇷 한국어', vi:'🇻🇳 Tiếng Việt', en:'🇺🇸 English'};
```

**③ line 1047 (`main.py`) — 검토만, 변경 보류**:
```python
tgt_map = {'vi':'vi-VN','en':'en-GB','ko':'ko-KR','ja':'ja-JP','zh-CN':'zh-CN'}
```
외부 번역 API (Google Translate) 호출용. ja·zh-CN 매핑 자체는 무해(API 호출 시에만 사용). UI 옵션이 ko/vi/en 만 노출되면 ja·zh-CN 코드는 호출되지 않음. **본 패치에서는 그대로 둠** (i18n.py 와 분리된 외부 매핑).

**효과**:
- QA-H3 (zh-CN) ✓ 해결
- QA-H4 (ja) ✓ 해결
- QA-H5 (ko/vi/en 중복) ✓ 자연 해결 (LANGS 1회 순회로 통일)
- 04 운영테스트팀 §S3 모두 통과

---

## 5. 패치 ④ — 인사말 검증 명확화 (QA-H6)

### 5-1. 04 발견 vs 코드 상태 불일치

- **04 검증 결과**: "시간대별 힐링 인사말(`오늘도 평안`, `좋은 아침` 등) 0회"
- **실제 코드**: `main.py:484~492` 시간대별 분기 정상 구현, `home.html:38` `{{ greeting|default(...) }}` 사용 중

**가능성**: 04 검증 시각이 오후 14~18시 사이였다면 `"오후도 힘내세요"` 가 노출됨 — 04 검색 키워드("오늘도 평안", "좋은 아침")와 불일치.

### 5-2. 처리

**01 → 04 검증 가이드 회신** (별도 파일):
- 검증 시각별 기대 텍스트 매트릭스 제공
  ```
  06~11시: "좋은 아침입니다, {name}님 ☀️"
  11~14시: "점심은 드셨나요"
  14~18시: "오후도 힘내세요"
  18~22시: "오늘도 수고하셨어요"
  22~06시: "늦은 시간까지 애쓰시네요"
  ```
- 04 가 2차 검증 시 이 매트릭스 기반으로 키워드 매칭
- 본 패치는 **코드 변경 없음**. 검증 방법론 정정만.

**또는 보강 (선택)**: `home.html:38` 에 `data-greeting-bucket="{{ greeting_bucket }}"` 속성 추가 → 04 검증 시 시각 무관하게 인사말 존재 확인 가능. 단순 코드라 30초 작업.

```python
# main.py home_page 컨텍스트 추가
greeting_bucket = "morning" if 6<=_h<11 else "lunch" if 11<=_h<14 else "afternoon" if 14<=_h<18 else "evening" if 18<=_h<22 else "night"
```
```jinja2
<h1 class="hm2-title" data-greeting-bucket="{{ greeting_bucket }}">{{ greeting|default(...) }}</h1>
```

→ 04 검증: `data-greeting-bucket` 속성 존재 = 인사말 동작 확인.

---

## 6. 권장 커밋 분리

1. `fix(dock): remove .dock-tab residual (QA-H2 · 2차 지시 보강)`
2. `feat(home): graceful fallback for revenue KPI when no data (QA-H1)`
3. `fix(i18n): trLang to LANGS-driven options · drop zh-CN/ja (QA-H3·H4·H5)`
4. `chore(home): add data-greeting-bucket for QA verification (QA-H6 · optional)`

---

## 7. QA 회귀 (01 자체 검증)

패치 적용 후 다음 명령으로 04 페르소나 재현:

```bash
# 평직원 매출 미노출 회귀
curl -s "http://localhost:8000/home" -b "session=PLAIN_USER_TOKEN" | grep -c "이번 달 수주\|monthly_revenue\|₩"
# 기대: 0

# CEO 매출 카드 노출
curl -s "http://localhost:8000/home" -b "session=CEO_TOKEN" | grep -c "이번 달 수주"
# 기대: 1 이상 (데이터 있으면 금액, 없으면 "준비 중")

# 언어 셀렉터 정합성
curl -s "http://localhost:8000/home" -b "session=CEO_TOKEN" | grep -c "zh-CN\|중국어\|일본어"
# 기대: 0

# 도크 탭 제거
curl -s "http://localhost:8000/home" | grep -c "dock-tab"
# 기대: 0
```

---

## 8. 회신 양식

- [ ] 패치 ① (.dock-tab 제거) 완료 — 커밋: _________
- [ ] 패치 ② (CEO 매출 fallback) 완료 — 커밋: _________
- [ ] 패치 ③ (언어 셀렉터 정합) 완료 — 커밋: _________
- [ ] 패치 ④ (인사말 검증 보강 · 선택) 완료 — 커밋: _________
- [ ] §7 회귀 검증 결과: _________

**회신 위치**: `05_.../_FROM_01_힐링디자인응답_2차.md` 또는 `_3차.md`

---

**발행**: 2026-04-25 13:05 · 05 디자인팀 세션 빅터
**우선순위**: 🔴🔴 패치 ①~③ 모두 24시간 내 완료 권장 (대표 지적 사안 + 04 검증)
**예상 시간**: ① 15분 + ② 30분 + ③ 15분 + ④ 5분 = **약 1시간 5분**
