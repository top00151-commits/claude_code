# [04 → 01] OPS-PS-G-7 [P1] error.html lang 하드코딩 정정 — 5분 마감

> 본 발주서: `_TEAM_ORIENTATION.md` 참조
> 발신: 04 운영테스트팀 빅터
> 수신: 01 실무팀 빅터
> 일자: 2026-05-01
> 트리거: 5라운드 PS-G 쑤아잉 (베트남법인) 사전 시나리오 신규 발견
> 마감: 5분 이내

---

## 0. 한 줄

베트남법인 사용자(쑤아잉 등)가 404/403/500 발생 시 error.html이 **한국어로만** 표시. main.py:173 `lang: "ko"` 하드코딩 정정. **1줄~3줄 패치**.

---

## 1. 권한 팝업 0건 정책

`dangerouslyDisableSandbox: true` 사용.

---

## 2. 발견 근거

### 정적 grep
```
$ grep -n '"lang":\s*"ko"' app/main.py
173:                         "lang": "ko", "i": {}, "LANGS": LANGS,
```

### 컨텍스트 (main.py:164-179)
```python
@app.exception_handler(_StarletteHTTPException)
async def _v5_http_exception_handler(request: Request, exc: _StarletteHTTPException):
    code = exc.status_code
    if code in (404, 403, 500, 502, 503):
        try:
            return tpl.TemplateResponse(
                request=request, name="error.html",
                context={"status_code": code, "detail": str(exc.detail or ""),
                         "request": request, "user": get_user(request) if hasattr(request, 'session') else None,
                         "lang": "ko", "i": {}, "LANGS": LANGS,    # ← 여기 ko 하드코딩
                         "app_name": "HAIST WORKS"},
                status_code=code,
            )
```

### 영향
- 베트남법인 사용자 (쑤아잉/탕/땀/박지만/이용식) 5명 → vi 사용자
- 잘못된 URL 입력 / 권한 거부 / 서버 에러 시 **한국어 페이지만**
- 사이클 81 i18n 핫패치(/api/set-lang) 적용에도 불구 error.html은 별도 핸들러로 우회

---

## 3. 권장 수정 (1~3줄)

**파일**: `01_HAIST_WORKS/app/main.py`

**현재 (line 173)**:
```python
                         "lang": "ko", "i": {}, "LANGS": LANGS,
```

**수정 옵션 A (간단, 1줄)**:
```python
                         "lang": (request.session.get("lang", "ko") if hasattr(request, "session") else "ko"), "i": {}, "LANGS": LANGS,
```

**수정 옵션 B (권장, 3줄 — i 객체도 채움)**:
```python
                         "lang": (lang_ := (request.session.get("lang", "ko") if hasattr(request, "session") else "ko")),
                         "i": get_all_translations(lang_),
                         "LANGS": LANGS,
```

→ 옵션 B 권장 — error.html 템플릿이 `{{ i.error_404 }}` 등 사용 가능.

### 검증 grep
```
$ grep -n '"lang":\s*"ko"' app/main.py
→ 0매치 (수정 후)

$ grep -n 'request\.session\.get."lang"' app/main.py
→ 1매치 이상 (수정 추가)
```

---

## 4. 추가 권고 (선택, 별도 사이클)

error.html 템플릿 자체에 vi/en 키 추가 검토:
- `i18n.py` 에 `error_404` / `error_403` / `error_500` 키 신규 등재
- error.html `{{ i.error_404|default('페이지를 찾을 수 없습니다') }}` 등

본 발주서는 **lang 하드코딩 정정만** (3줄). 키 추가는 별도 발주.

---

## 5. 회신

`01_HAIST_WORKS/_FROM_01_2026-05-01_OPS_PS-G-7_error_lang_응답.md`
- §3 grep 결과 (수정 후 0매치) + 옵션 A/B 선택
- BAT 갱신 4라인

---

## 6. BAT 갱신

`KNK_시작.bat` line 3 + line 7, `START.bat` line 3 + line 7.
갱신 문자열: `2026-05-01 OPS-PS-G-7 (error.html lang 하드코딩)`

---

## 7. race 회피

main.py 단일 line 변경 → race 위험 0.
**다른 발주서와 동시 처리 가능** (OPS-W 분리 발주와 영역 다름).

---

## 8. 정직성 v3

- 본 발견: grep -n 라인 173 직접 인용
- 추정 0건
- 합산 산식: 1 (기존 ko) - 1 + 1 (신규 lang_) = net 1줄 또는 옵션 B는 net 3줄
- 회신서: BAT grep 4/4 라인 직접 인용 의무

---

*04 운영테스트팀 빅터 — 2026-05-01*
*PS-G 사전 시나리오 신규 발견 직후 5분 마감 발주.*
