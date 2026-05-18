# [발주] 사이클 85 핫패치 — OPS-012 flash 인프라 + OPS-V15 admin 개별 비번 리셋 UI

> 본 발주서: `KNK업무시스템구축/_TEAM_ORIENTATION.md` 참조 의무
> 발주: 09 팀장 (빅터) → 01 메인
> 발주 시각: 2026-04-28
> 우선순위: 🚨 P0 (4차 누적 미해소 + admin 운영 마비 위험)
> 메모리 #5 main.py 순차: 사이클 81 + 사이클 84 main.py 작업 완료 후 시작

---

## 1. 배경 (04 보고)

**참조**:
- `04_HAIST_WORKS_운영테스트팀/_TO_09팀장_2026-04-28_10명시각시연결과.md`
- `04_HAIST_WORKS_운영테스트팀/_TO_01세션_2026-04-28_OPS012_안내배너.md`
- `04_HAIST_WORKS_운영테스트팀/_TO_09팀장_2026-04-28_시드비번광역깨짐.md`

---

## 2. 작업 A — OPS-012 flash 인프라 (4차 누적)

### Step A-1. main.py /dashboard 핸들러

```python
@app.get("/dashboard")
async def dashboard_page(req: Request):
    u = get_user(req)
    if not u:
        return RedirectResponse("/login", 303)
    if u["role"] not in ("admin", "ceo", "executive"):
        # ★ 추가
        req.session["flash"] = (
            "warning",
            "전사 대시보드는 경영진(executive 이상)만 볼 수 있습니다. 팀 현황으로 이동합니다."
        )
        return RedirectResponse("/team", 303)
    # ... 기존 로직
```

### Step A-2. base.html 공통 flash 배너

```html
{% if request.session.get('flash') %}
  {% set lvl, msg = request.session.pop('flash') %}
  <div class="flash-banner flash-{{ lvl }}">
    <span class="flash-icon">{% if lvl == 'warning' %}🔒{% elif lvl == 'success' %}✅{% else %}ℹ️{% endif %}</span>
    <span class="flash-msg">{{ msg }}</span>
    <button class="flash-close" onclick="this.parentElement.remove()">×</button>
  </div>
{% endif %}
```

### Step A-3. CSS (style.css 또는 신규)

- 05 디자인팀 UX-12 시안 활용 또는 신규 토큰 (sage 팔레트 일관)
- `.flash-banner`, `.flash-warning` (#FEF3C7), `.flash-success` (#D1FAE5), `.flash-info` (#DBEAFE)

### Step A-4. 동일 패턴 적용 (한 번에 처리)

- `/admin` 비권한 접근 시 flash
- `/logistics` `/parts` 비권한 시 flash (사이클 84 OPS-001 보완)
- 기타 silent 리다이렉트 모두 flash 안내로 변경

### 통과 기준

`kjr2 / knk1234` 로그인 → `/dashboard` 직접 접근 → /team 도착 + 상단 노란 배너 "🔒 전사 대시보드는 경영진..." 표시.

---

## 3. 작업 B — OPS-V15 admin 개별 비번 리셋 UI

### Step B-1. admin.html 보안 탭에 사용자별 [비번 리셋] 버튼 추가

- 사용자 행 옆 [🔑 비번 리셋] 버튼
- 클릭 → POST `/admin/users/{user_id}/reset-password`
- 새 임시 비번 자동 발급 (knk1234 또는 랜덤) → 모달로 표시

### Step B-2. main.py 새 엔드포인트

```python
@app.post("/admin/users/{user_id}/reset-password")
async def admin_reset_user_password(user_id: int, req: Request):
    u = get_user(req)
    if not u or u["role"] != "admin":
        return RedirectResponse("/login", 303)
    new_pw = "knk1234"  # 또는 secrets.token_urlsafe(8)
    new_hash = hash_password(new_pw)
    # DB UPDATE users SET password_hash=? WHERE id=?
    return JSONResponse({"new_password": new_pw, "user_id": user_id})
```

### Step B-3. admin.html JavaScript 모달

- fetch POST → 응답 수령 → 새 비번 모달 표시 + 클립보드 복사
- 일괄 재생성 버튼은 **2단계 확인** 추가 (비번 폭파 방지)

### 통과 기준

`admin / admin1234` (사이클 81에서 비번 복구된 후) → `/admin` → 보안 탭 → 사용자 옆 [비번 리셋] → 새 비번 모달 → 04가 새 비번으로 로그인 검증.

---

## 4. 작업 C — `/admin/download-passwords` 404 수정

- 04 보고: "기존 파일 다시 받기" → 404
- 시드 리셋 직후 생성된 CSV 보존 + 다운로드 가능하게 수정
- main.py 핸들러 점검 + 파일 경로 검증

---

## 5. 지시 사항

- **권한 팝업 0건** (메모리 #1)
- **BAT 갱신 순차** (메모리 #4): 사이클 84 회신 도착 후 BAT 갱신 (race 방지)
- **외부 자산 0** (메모리 #6)
- **정직성 v3**: grep -n 직접 인용 / wc -l 라인 수
- **사이드바 본질** (메모리 #7): admin 비번 리셋은 admin 페이지 안에서만 (사이드바 노출 금지)

---

## 6. 회신 형식

- **회신 파일**: `01_HAIST_WORKS/_TO_09팀장_2026-04-28_사이클85_회신.md`
- 통합 grep 인용:
  - `grep -n "/dashboard\|flash\|reset-password\|download-passwords" app/main.py`
  - `grep -n "flash-banner\|reset-password" app/templates/base.html app/templates/admin.html`
  - 사이클 86 (04) 회귀 의뢰
