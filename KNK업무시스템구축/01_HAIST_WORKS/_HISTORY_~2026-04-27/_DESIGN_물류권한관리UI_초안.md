# 물류 권한 관리 UI — 설계 초안

> **근거**: 2026-04-22 대표 결재 (D01-NEW-PERM)
> **요청**: "구매팀장이 다른 직원들에게 물류 접근 권한을 줄 수 있게 하라"
> **상태**: 설계 초안 (구현 착수 전 — 팀장 확인 후 구현)
> **작성**: 2026-04-22 빅터 (01 메인 세션)

---

## 1. 라우트 설계

| 라우트 | 메서드 | 설명 | 접근 조건 |
|---|---|---|---|
| `/logistics/perm` | GET | 직원 목록 + 권한 토글 화면 | role=leader AND team_id=10 (구매팀장만) |
| `/logistics/perm/update` | POST | can_use_logistics 플래그 DB 업데이트 | 동일 |

### 접근 조건 상세
```python
def can_manage_logistics_perm(user) -> bool:
    """물류 권한 관리 화면 접근 — 구매팀장만"""
    if not user:
        return False
    role = user.get("role")
    team_id = user.get("team_id")
    # admin/ceo도 접근 허용 (관리 목적)
    if role in ("admin", "ceo"):
        return True
    return role == "leader" and team_id == 10
```

---

## 2. 화면 구조 (`/logistics/perm`)

```
┌─────────────────────────────────────────────────────────┐
│  물류 접근 권한 관리                  [구매팀장 전용]    │
├─────────────────────────────────────────────────────────┤
│  검색: [직원 이름 또는 팀명 검색              ]          │
├─────────────────────────────────────────────────────────┤
│  직원 목록                                              │
│                                                         │
│  팀명       이름    직급    물류 접근                    │
│  ─────────────────────────────────────                  │
│  구매팀     정성진  팀장    자동허용 (팀장)              │
│  구매팀     김민수  사원    [ON  ●────]                  │
│  제조기술1  노충일  팀장    자동허용 (제조팀)            │
│  제조기술2  임택훈  팀장    자동허용 (제조팀)            │
│  영업팀     이해림  과장    [OFF ────●]                  │
│  소프트웨어 한이중  주임    [OFF ────●]                  │
│  ...                                                    │
│                                                         │
│  * admin/ceo/executive/제조팀 직원은 자동허용 표시      │
│    (토글 불필요 — 코드로 보장)                          │
└─────────────────────────────────────────────────────────┘
```

### 표시 규칙
- `role in (admin, ceo, executive)` → "자동허용 (역할)" 텍스트, 토글 비활성
- `team_id == 7` (제조팀) → "자동허용 (제조팀)" 텍스트, 토글 비활성 (D01-02 결과)
- 그 외 → ON/OFF 토글 활성, 클릭 시 즉시 AJAX POST

---

## 3. POST 처리 (`/logistics/perm/update`)

```python
# 요청 파라미터
user_id: int   # 대상 직원 ID
flag: str      # "1" (허용) 또는 "0" (거부)

# DB 처리
UPDATE users SET can_use_logistics = ? WHERE id = ?

# 응답 (JSON)
{"ok": True, "user_id": user_id, "can_use_logistics": flag}
```

- 기존 `/api/admin/set_logistics` 엔드포인트와 동일한 DB 쿼리 재사용 가능
  (현재 admin.html에서 admin 전용으로 사용 중 — 구매팀장 권한 추가 필요)

---

## 4. DB 변경 사항

추가 마이그레이션 없음. 기존 `users.can_use_logistics` 컬럼 그대로 사용.

---

## 5. 구현 난이도 및 공수

| 항목 | 내용 |
|---|---|
| 난이도 | M (Medium) |
| 예상 공수 | 2~3시간 |
| 구성 | 라우트 2개 + 템플릿 1개 + 권한 함수 1개 + DB 쿼리 1개 |
| 재사용 | admin.html 토글 UI 패턴 + `/api/admin/set_logistics` DB 쿼리 재사용 |

---

## 6. 구현 전 확인 필요 사항

1. `/api/admin/set_logistics` 에서 구매팀장도 호출 가능하도록 권한 체크 수정 여부
   - 현재: admin 전용
   - 변경안: `can_manage_logistics_perm(user)` 통과 시 허용
2. 권한 없는 직원이 `/logistics/perm` 접근 시 → `/home?no_perm=logistics_perm` 리다이렉트 (D01-NEW-BANNER 연동)
3. 구매팀장 본인의 `can_use_logistics` 는 role=leader+team_id=10 이므로 자동허용 표시

---

## 7. 구현 착수 조건

팀장(09) 초안 확인 및 구현 착수 지시 수신 후 진행.

---

**문서 위치**: `KNK업무시스템구축/01_HAIST_WORKS/_DESIGN_물류권한관리UI_초안.md`
**다음 단계**: 09팀장 확인 → 구현 착수 지시 → main.py + 템플릿 구현
