# 사이클 69 — deep_translator 제거 + 사이클 68 잔여 정리

> **발신**: 일회성 01 메인 worker
> **수신**: 09 빅터 팀장
> **일시**: 2026-04-27
> **상위 지시**: 대표 14:19 — "deep_translator → 부분 처리(Partial)" + 03 정찰(15:30) C안 단계 분할 권고
> **상위 정책**: `_TEAM_ORIENTATION.md` §3.1 (외부 자산 0건), §4 (자체 판단 4항 금지)
> **권한 팝업**: 0건

---

## A. deep_translator 라이브러리 제거 (운영 자유 문장 번역 → 사내 사전)

### A-1. main.py:1071~1112 → 1071~1116 교체

**전 (정찰 인용)**:
```
main.py:1071  @app.post("/api/translate")
main.py:1083      from deep_translator import GoogleTranslator
main.py:1091      from deep_translator import MyMemoryTranslator
main.py:1104      url = f"https://translate.googleapis.com/translate_a/single?..."
```

**후 (변경 후 grep -n 직접 인용)**:
```
main.py:1071  @app.post("/api/translate")
main.py:1072  async def api_translate(req: Request):
main.py:1073      """
main.py:1074      사내 사전 번역 (외부 API 0건).
main.py:1075      사이클 69 (2026-04-27): deep_translator + Google Translate URL 직접 호출 제거.
main.py:1076      오리엔테이션 §3.1 외부 자산 0건 정책 이행. 대표 14:19 "부분 처리" 결정.
main.py:1077      동작: app/i18n.py T 사전(약 472키 / ko·vi·en)에서 입력 텍스트와 매칭되는 항목을 찾아 응답.
main.py:1078      매칭 실패 시 "사내 사전 미등록" 안내 + 빅터AI 등록 기능(사이클 70+) 예고.
main.py:1093          from .i18n import T as _T
main.py:1100      for _key, entry in _T.items():
main.py:1107                  return JSONResponse({"ok": True,
main.py:1108                                       "translated": tgt_text,
main.py:1109                                       "target": target,
main.py:1110                                       "source": "사내 사전"})
main.py:1112      return JSONResponse({
main.py:1113          "ok": False,
main.py:1114          "error": "사내 사전 미등록 — 빅터AI 단어 등록 기능(예정)으로 추가 가능합니다.",
main.py:1115          "source": "사내 사전",
main.py:1116      }, 200)
```

**변경 라인 산식**:
- 신규(추가): 36 라인 (i18n lookup 로직 + 안내)
- 삭제: 32 라인 (deep_translator 3-layer fallback)
- net: +4 라인 (1112→1116)

옵션 B 채택 — 함수·라우트 자체는 유지하되 i18n 사전 lookup으로 대체. 사이클 70 빅터AI 등록 기능 신설 시 자연 연결. 라우트 호출자(base.html JS) 무수정 (status 200 응답 + ok 플래그 호환 그대로).

### A-2. requirements.txt 정정

**전 (전체)**:
```
1:fastapi
2:uvicorn[standard]
3:jinja2
4:python-multipart
5:itsdangerous
6:deep-translator
```

**후 (전체)**:
```
1:fastapi
2:uvicorn[standard]
3:jinja2
4:python-multipart
5:itsdangerous
```

**변경**: 1라인 삭제 (`deep-translator`).

---

## B. base.html 🌐 버튼 라벨 변경

### B-1. base.html:440 i18n 라벨 (translate_btn)

**전**: `translate_btn: "{{ i.translate_btn|default('🌐 번역') }}",`
**후**: `translate_btn: "{{ i.translate_btn|default('🌐 사내 사전') }}",`

라벨이 "사내 사전"으로 명확히 표시되어 사용자가 외부 번역 기대를 갖지 않도록.

### B-2. base.html:599~601 결과 라벨 (출처 표기)

**전**:
```
599  const langNames = {ko:'🇰🇷 한국어', vi:'🇻🇳 Tiếng Việt', en:'🇺🇸 English'};
600  resultDiv.innerHTML = `<div class="tr-label">${langNames[target]||target} 번역</div>...
```

**후**:
```
599  const langNames = {ko:'🇰🇷 한국어', vi:'🇻🇳 Tiếng Việt', en:'🇺🇸 English'};
600  const srcLabel = j.source ? ` · ${escHtml(j.source)}` : '';
601  resultDiv.innerHTML = `<div class="tr-label">${langNames[target]||target} 번역${srcLabel}</div>...
```

매칭 시 라벨에 "· 사내 사전" 부착. 매칭 실패는 기존 j.error 분기 그대로 — `사내 사전 미등록 — 빅터AI 단어 등록 기능(예정)으로 추가 가능합니다.` 메시지 표시.

**호출자 영향**: 카드 모달 🌐 버튼 3 트리거 (base.html:487/488/524) JS 무수정. 매칭 시 정상 표시·실패 시 안내 메시지.

---

## C. 사이클 68 잔여 정리

### C-1. database.py:2291 alias 제거

**전**:
```
database.py:2290  # Backward-compat alias (사이클 68 호환 — main.py 전면 교체 후 제거 가능)
database.py:2291  build_password_xlsx = build_password_csv
```

**후**:
```
database.py:2290  # 사이클 69 (2026-04-27): 호환 alias `build_password_xlsx = build_password_csv` 제거.
database.py:2291  # 호출자 0건 (grep 검증) — main.py:15·2794는 이미 build_password_csv 직접 호출.
```

**검증 grep**:
```
$ grep -rn "build_password_xlsx" app/ | grep -v __pycache__
app/database.py:2290:# 사이클 69 (2026-04-27): 호환 alias `build_password_xlsx = build_password_csv` 제거.
```
실행 코드 참조 0건. 주석 1건만 잔존(이력 보존용).

### C-2. EXTERNAL_ASSETS_REVIEW 상태 갱신 (main.py:2828~2906)

세 자산에 `status` 필드 신설:
- **openpyxl** → `status: "removed_2026-04-27_cycle68"` + main.py·database.py 항목에 `deprecated: True` 표기 + lines를 "(제거됨)"로 갱신
- **pandas** → `status: "pending_decision"` + lines `"2090"` → `"2108"` 사실 정정 (사이클 68 이후 이동)
- **deep_translator** → `status: "removed_2026-04-27_cycle69"` + main.py·requirements.txt 항목 `deprecated: True` + 대안에 "사내 i18n 사전 lookup" + "빅터AI 단어 등록 기능(사이클 70+)" 명시

**main.py:2935 `allowed_assets` 변경 없음** (white-list — 이력 자산도 유지하여 결재 페이지 호환).

`external_assets_review.html` 템플릿은 `a.status` / `u.deprecated` 추가 키를 무시 (Jinja `{{ u.file }}/{{ u.lines }}/{{ u.purpose }}`만 사용 — line 87~89 grep 확인). 기존 결재 동작·렌더링 무영향.

### C-3. spike 보고서 정정

`_TO_09팀장_2026-04-27_외부자산점검페이지_spike.md` line 60~66 표 갱신:
- "현 상태" 컬럼 신설 (사이클 69 후)
- openpyxl → `removed_2026-04-27_cycle68` (운영 라우트 0건, scripts/ 잔존만)
- pandas → `pending_decision` (대표 결재 대기, line 2090→2108 정정)
- deep_translator → `removed_2026-04-27_cycle69` (운영·requirements 모두 0건)

---

## D. 검증 (변경 후 grep, 직접 인용)

### D-1. deep_translator import / Google API URL 0건

```
$ grep -rnE "^import deep_translator|^from deep_translator|googleapis.com" 01_HAIST_WORKS/app/ | grep -v __pycache__
(0 results)
```

### D-2. requirements.txt 0건

```
$ grep -nE "deep_translator|deep-translator" 01_HAIST_WORKS/requirements.txt
(0 results)
```

### D-3. 합산 grep (주석/메타까지 포함, 정직성)

```
$ grep -rnE "deep_translator|deep-translator" 01_HAIST_WORKS/app/ 01_HAIST_WORKS/requirements.txt | grep -v __pycache__ | grep -v "removed_2026-04-27"
app/main.py:1075:    사이클 69 (2026-04-27): deep_translator + Google Translate URL 직접 호출 제거.
app/main.py:2882:        "name": "deep_translator",
app/main.py:2890:             "purpose": "사이클 69: deep-translator 의존성 제거",
app/main.py:2935:    allowed_assets = {"openpyxl", "pandas", "deep_translator"}
```

4건 모두 **메타·이력·결재 화이트리스트** (실행 import / 외부 호출 0).

### D-4. build_password_xlsx 실행 참조 0건

```
$ grep -rn "build_password_xlsx" 01_HAIST_WORKS/app/ | grep -v __pycache__
app/database.py:2290:# 사이클 69 (2026-04-27): 호환 alias `build_password_xlsx = build_password_csv` 제거.
```

주석 1건만 (이력 보존). 실행 참조 0건 PASS.

---

## BAT 6/6 grep 직접 인용

```
$ grep -nE "사이클69|사이클70|2026-04-27" KNK_시작.bat START.bat
KNK_시작.bat:3:REM   LAST UPDATE: 2026-04-27 사이클69+70 deep_translator제거+EXTERNAL_ASSETS상태갱신+빅터AI호출버튼Hub추가
KNK_시작.bat:7:title KNK HAIST WORKS - HAIST Innovation [Updated 2026-04-27 사이클69+70 deep_translator제거+EXTERNAL_ASSETS상태갱신+빅터AI호출버튼Hub추가]
KNK_시작.bat:14:echo    [Last Update: 2026-04-27 사이클69+70 deep_translator제거+EXTERNAL_ASSETS상태갱신+빅터AI호출버튼Hub추가]
START.bat:3:REM   LAST UPDATE: 2026-04-27 사이클69+70 deep_translator제거+EXTERNAL_ASSETS상태갱신+빅터AI호출버튼Hub추가
START.bat:7:title KNK HAIST WORKS - HAIST Innovation [Updated 2026-04-27 사이클69+70 deep_translator제거+EXTERNAL_ASSETS상태갱신+빅터AI호출버튼Hub추가]
START.bat:13:echo    [Last Update: 2026-04-27 사이클69+70 deep_translator제거+EXTERNAL_ASSETS상태갱신+빅터AI호출버튼Hub추가]
```

**6/6 PASS** (KNK_시작.bat line 3·7·14 + START.bat line 3·7·13).

**주의**: 본 worker 시작 시 BAT는 이미 동시 가동 사이클 70 라벨로 갱신되어 있었음 ("사이클70-빅터AI호출버튼Hub추가_긴급"). 사이클 69+70 결합 라벨로 통합하여 양쪽 사이클 변경을 모두 명시.

---

## 핫패치 130 / v2 본체 미접촉

```
$ grep -cE "\\.sb-toggle|\\.dock \\{|\\.main-wrap" static/style.css
130
```

**G1~G5 130 매칭 PASS**. style.css 라인 수 5610 무변경. v2 본체 4287~4574 영역 미접촉.

---

## 변경 라인 (산식)

| 파일 | 작업 | 신규 | 삭제 | net |
|------|------|------|------|-----|
| app/main.py | api_translate() 교체 (A-1) | +36 | -32 | +4 |
| app/main.py | EXTERNAL_ASSETS_REVIEW status 추가 (C-2) | +12 | -2 | +10 |
| app/database.py | alias 제거 (C-1) | +1 | -1 | 0 |
| app/templates/base.html | translate_btn 라벨 (B-1) | 0 | 0 | 0 (1글자) |
| app/templates/base.html | source 라벨 부착 (B-2) | +1 | 0 | +1 |
| requirements.txt | deep-translator 제거 (A-2) | 0 | -1 | -1 |
| _TO_09팀장_2026-04-27_외부자산점검페이지_spike.md | 4. 표 갱신 (C-3) | +6 | -3 | +3 |
| KNK_시작.bat | LAST UPDATE 갱신 | 0 | 0 | 0 (라벨만) |
| START.bat | LAST UPDATE 갱신 | 0 | 0 | 0 (라벨만) |
| **합계 (코드+요소)** | | **+56** | **-39** | **+17** |

---

## 외부 자산 0 / 새 외부 패키지 0 / 권한 팝업 0

- 새 import: `from .i18n import T as _T` — 사내 모듈만 (이미 사용 중인 i18n.py)
- 새 PyPI: 0
- 새 외부 URL: 0
- 권한 팝업: 0건 (보고만)

---

## 산출

- 본 보고서: `01_HAIST_WORKS/_TO_09팀장_2026-04-27_사이클69_deep_translator제거.md`
- 변경: app/main.py · app/database.py · app/templates/base.html · requirements.txt · _TO_09팀장_2026-04-27_외부자산점검페이지_spike.md · KNK_시작.bat · START.bat
- 사이클 70+ 권고: 빅터AI 단어 등록 기능 신설 (대표 결재 대기 — `words` 테이블 + i18n_dynamic.py + 도크 명령 파서 / 03 정찰 D-1 작업 비용 3.5일 추정)

---

## 정직성 v3 자체 적용 (5/5)

1. **변경 위치 grep -n 직접 (전후)**: A-1·A-2·B-1·B-2·C-1·C-2·C-3 모두 grep 결과 직접 인용
2. **requirements.txt 변경 직접 인용**: A-2 전·후 전체 인용
3. **EXTERNAL_ASSETS_REVIEW 데이터 변경 read 인용**: C-2 status·deprecated·alternatives 명시
4. **BAT 6/6 (line 14/13 포함) 직접 인용**: 6/6 grep 인용
5. **합산 산식 정확**: 변경 라인 산식 표 전체

추정·기억 인용 0건. 측정값과 정찰값 분리 명시.
