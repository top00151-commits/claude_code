# 🔥 HOTFIX 요청 — `/issues` 라우트 자재구매센터로 잘못 분류

**보고:** 실무팀1 (통합플랫폼)
**수신:** 빅터 (01 통합실무팀)
**일시:** 2026-05-10
**대표 보고:** 직접 — 사이드바 "이슈·AS" 클릭 시 자재구매센터로 이동

---

## 1. 증상 (대표 직접 확인)

- 사이드바 "🚨 이슈·AS" 클릭 → URL `/issues` 진입
- **결과:** 상단 탭 `자재구매센터` active + 사이드바 자재·구매 메뉴(M-02-XX) 표시
- **기대:** 상단 탭 `통합 플랫폼` active + 사이드바 통합플랫폼 메뉴(M-00-XX) + 이슈·AS 항목 active

## 2. 원인 (코드 정확 추적)

### 2-1. 백엔드는 정상
`main.py:9208`
```python
@app.get("/issues", response_class=HTMLResponse)
async def issues_page(...):
    ...
    return ctx(req, "issues_list.html", ..., active="issues")
```
→ `issues_list.html` (통합플랫폼) 정상 렌더링.

### 2-2. 프론트(chrome.html) 자동분류 버그
`_v5_partials/chrome.html:17`
```jinja
{% elif _path.startswith('/logistics') or _path.startswith('/po') or ... or _path.startswith('/issues') or ... %}
  {% set _at_auto = 'logi' %}
{% endif %}
```
→ `_path.startswith('/issues')`가 **logistics(자재구매센터)** 그룹에 잘못 묶여있음.

### 2-3. 정상 분류 vs 현재 코드
- `_paths_common` (라인 26): `'/issues'` 정확히 포함됨 ✓
- 자재구매센터의 출고 라우트는 `/stock/issue` (단수형) — 라인 17의 `_path.startswith('/stock')`로 이미 잡힘
- 즉, 라인 17의 `_path.startswith('/issues')`는 **불필요할 뿐 아니라 통합플랫폼 이슈·AS를 자재구매센터로 잘못 보냄**

### 2-4. 결과 chain
1. 사용자 `/issues` 진입
2. `chrome.html:17` `_at_auto = 'logi'`
3. 라인 63: 상단 탭 `자재구매센터` `.active`
4. 라인 146 (`{% elif _at == 'logi' %}`): 사이드바가 자재·구매 메뉴로 렌더링
5. 라인 178의 "이슈·AS" 항목 자체는 항상 노출되지만 상단/사이드바 컨텍스트가 자재구매센터로 보임

## 3. 수정 한 줄 패치

`_v5_partials/chrome.html:17` 에서 `or _path.startswith('/issues')` **제거**:

### Before:
```jinja
{% elif _path.startswith('/logistics') or _path.startswith('/po') or _path.startswith('/parts') or _path.startswith('/part/') or _path.startswith('/stock') or _path.startswith('/rates') or _path.startswith('/qms') or _path.startswith('/wo') or _path.startswith('/work') or _path.startswith('/suppliers') or _path.startswith('/supplier/') or _path.startswith('/qc') or _path.startswith('/receipts') or _path.startswith('/issues') or _path.startswith('/movements') or _path.startswith('/fx_rates') %}
```

### After:
```jinja
{% elif _path.startswith('/logistics') or _path.startswith('/po') or _path.startswith('/parts') or _path.startswith('/part/') or _path.startswith('/stock') or _path.startswith('/rates') or _path.startswith('/qms') or _path.startswith('/wo') or _path.startswith('/work') or _path.startswith('/suppliers') or _path.startswith('/supplier/') or _path.startswith('/qc') or _path.startswith('/receipts') or _path.startswith('/movements') or _path.startswith('/fx_rates') %}
```

→ `or _path.startswith('/issues')` 한 토큰만 제거.

## 4. 부수 영향 검증

- `/stock/issue` (자재구매센터 출고) → 라인 17의 `_path.startswith('/stock')` 이 먼저 잡으므로 logistics 분류 유지 ✓
- `/issues` (통합플랫폼 이슈·AS) → `_at_auto = 'home'` (default) ✓
- `/issues/new`, `/issues/{iid}` → 동일하게 home 분류 ✓
- `_paths_common`(라인 26)에 `/issues`가 있으므로 사이드바 active 표시 정상 ✓

## 5. 우리(실무팀1)가 직접 수정하지 않은 이유

- `_v5_partials/chrome.html`은 **공통 partial** — 발주서 7장 "공통 partial 미수정" 절대준수
- 룰 v4에서도 메인 BAT·`_v5_partials/`는 **빅터(01)만** 수정 권한
- 따라서 진단·패치 제안만 보고, **빅터 검토 후 핫패치 요청**

## 6. 권장 조치

1. **빅터 핫패치:** chrome.html:17에서 `or _path.startswith('/issues')` 제거 (1 토큰)
2. **회귀 테스트:**
   - `/issues` → 상단 탭 통합플랫폼 active 확인
   - `/issues/1` → 동일
   - `/stock/issue` → 자재구매센터 active 유지 확인
3. **추가 의심:** 비슷한 cross-hub 라우트가 있는지 점검
   - `/changes` (변경공지) — `_paths_common` 정상
   - `/tickets` (티켓) — 정상
   - `/notifications`, `/calendar`, `/search`, `/board/*` — 모두 _paths_common 정상

---

## 첨부: 스크린샷 증거

대표 직접 확인 (debug=1 모드):
- 상단 탭 자재구매센터 active 표시 (잘못)
- 사이드바 그룹 "자재·구매" 표시 + M-02-XX 메뉴 표시 (잘못)
- 페이지 본문은 issues_list.html (이슈·AS DATABASE) 정상 표시

→ chrome.html 자동분류만 어긋남. 백엔드 핸들러·페이지 본문은 정상.
