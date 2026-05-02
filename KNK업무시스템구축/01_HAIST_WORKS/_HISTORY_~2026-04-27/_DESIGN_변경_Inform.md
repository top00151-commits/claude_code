# 변경 Inform 시스템 설계 청사진

> **목적**: v2 종합설계분석 문서 받자마자 즉시 코드 작성 시작할 수 있도록 사전 설계
> **설문 매핑**: 1순위 ② / 6팀 공통 (전장·SW·제조2·가공·검사기·품질) + **제조2 실제 사고 사례**
> **흡수 패턴**: Microsoft ECN + Slack Workflow Conditional Branching + Variables + 하이웍스 메신저 알림
> **5대 원칙 적용**: ✅ 워크플로우 우선 / ✅ 매뉴얼 0 / ✅ 변수 흡수 / ✅ 자동 정리 / ✅ 기존 도구 공존
> **작성**: 2026-04-20 (메인 세션 빅터)

---

## 1. 사용자 시나리오 (직원 입장)

### 시나리오 A — 설계자 (전장설계팀 김형렬)
```
1. 기구 설계가 변경됨을 인지
2. HAIST_WORKS 사이드바 → "변경 알림" 클릭
3. 4단계 폼 따라 입력 (Step 1 종류 → 2 대상 → 3 전후 → 4 확인)
4. 영향 부서 자동 표시됨 (전장·SW·가공·제조1·2·구매)
5. [공지하기] 클릭
6. 즉시: 영향 부서 하이웍스 메신저 + 메일 + web 알림
```

### 시나리오 B — 받는 사람 (제조기술2팀 임택훈)
```
1. 하이웍스 메신저 알림 수신: "🔴 변경: 검사기 001T2604 기구 도면 변경"
2. 알림 클릭 → web 변경 상세 페이지
3. 변경 전/후 도면 비교 (큰 이미지 + 다운로드)
4. 영향 평가 입력 (선택) + [확인했습니다] 클릭
5. 작성자에게 자동 회신 (확인 완료 표시)
```

### 시나리오 C — 영업팀 (이해림)
```
1. 매일 아침 web 홈 화면에서 "어제 변경 N건" 카드 확인
2. 필터: 자기 관리 프로젝트만 → 변경 이력 한눈에
3. 고객사 응대 시 "최근 변경 N건" 정보 즉시 활용
```

---

## 2. 데이터 모델 (DB 스키마)

### 2.1 `changes` 테이블 (변경 사건 본체)

```sql
CREATE TABLE IF NOT EXISTS changes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    change_no       TEXT NOT NULL UNIQUE,        -- CHG-YYMMDD-NNN 자동 채번
    change_type     TEXT NOT NULL,                -- 기구설계/전장설계/SW/BOM/도면/Concept/사양
    target_kind     TEXT,                         -- project / part / document / supplier
    target_id       INTEGER,                      -- FK (polymorphic, 직접 join 안 함)
    target_label    TEXT,                         -- 사람이 읽는 라벨 (예: "001T2604 검사기")
    project_id      INTEGER REFERENCES projects(id),  -- 관리코드 연결 (선택, 진행률 대시보드 통합용)
    title           TEXT NOT NULL,
    description     TEXT,
    before_value    TEXT,                         -- 텍스트 or JSON
    after_value     TEXT,                         -- 텍스트 or JSON
    attached_files  TEXT,                         -- JSON 배열 (파일 경로)
    urgency         TEXT DEFAULT '일반',           -- 긴급/일반/예약
    author_id       INTEGER NOT NULL REFERENCES users(id),
    status          TEXT DEFAULT '공지중',         -- 작성중/공지중/확인완료/취소
    notified_at     TEXT,                         -- 하이웍스 메신저·메일 발송 시각
    completed_at    TEXT,                         -- 모든 영향자 확인 시각
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    updated_at      TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_chg_no ON changes(change_no);
CREATE INDEX IF NOT EXISTS idx_chg_project ON changes(project_id);
CREATE INDEX IF NOT EXISTS idx_chg_status ON changes(status);
CREATE INDEX IF NOT EXISTS idx_chg_author ON changes(author_id);
CREATE INDEX IF NOT EXISTS idx_chg_created ON changes(created_at DESC);
```

### 2.2 `change_impacts` 테이블 (영향 부서·사용자)

```sql
CREATE TABLE IF NOT EXISTS change_impacts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id       INTEGER NOT NULL REFERENCES changes(id) ON DELETE CASCADE,
    impact_kind     TEXT NOT NULL,                -- team / user / role
    impact_team_id  INTEGER REFERENCES teams(id),
    impact_user_id  INTEGER REFERENCES users(id),
    auto_detected   INTEGER DEFAULT 1,             -- 1=자동 판별, 0=수동 추가
    impact_reason   TEXT                            -- 예: "기구 설계 변경 → 전장설계팀 자동"
);
CREATE INDEX IF NOT EXISTS idx_cimp_change ON change_impacts(change_id);
CREATE INDEX IF NOT EXISTS idx_cimp_team ON change_impacts(impact_team_id);
```

### 2.3 `change_reads` 테이블 (확인 추적)

```sql
CREATE TABLE IF NOT EXISTS change_reads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    change_id       INTEGER NOT NULL REFERENCES changes(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    read_at         TEXT,                           -- 페이지 열람
    ack_at          TEXT,                           -- "확인했습니다" 클릭
    ack_note        TEXT,                           -- 영향 평가 메모 (선택)
    UNIQUE(change_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_cread_change ON change_reads(change_id);
CREATE INDEX IF NOT EXISTS idx_cread_user ON change_reads(user_id);
```

---

## 3. 영향 부서 자동 판별 규칙

### 3.1 변경 종류 → 영향 부서 매트릭스

| 변경 종류 | 자동 영향 부서 (검사기) | 자동 영향 부서 (자동화) |
|---|---|---|
| **기구설계** | 전장설계, SW, 가공, 제조1, 구매 | 전장설계, SW, 가공, 제조2, 구매 |
| **전장설계** | SW, 제조1, 구매 | SW, 제조2, 구매 |
| **소프트웨어** | 검사기팀, 제조1 | 제조2 |
| **BOM** | 구매, 제조1, 가공 | 구매, 제조2, 가공 |
| **도면** | 가공, 제조1, 품질 | 가공, 제조2, 품질 |
| **Concept** | 전 부서 | 전 부서 |
| **사양** | 영업, 검사기, 설계, 품질 | 영업, 설계, 품질 |

### 3.2 추가 영향 자동 판별

- **target_kind = project** → 해당 관리코드의 PM·담당영업 자동 추가
- **target_kind = part** → 해당 부품을 사용하는 모든 활성 발주의 담당자 자동
- **urgency = 긴급** → CEO·Executive 자동 추가

### 3.3 코드 (database.py)

```python
IMPACT_RULES = {
    "기구설계": {
        "T": ["전장설계팀", "소프트웨어팀", "가공팀", "제조기술1팀", "구매팀"],
        "M": ["전장설계팀", "소프트웨어팀", "가공팀", "제조기술2팀", "구매팀"],
    },
    "전장설계": {
        "T": ["소프트웨어팀", "제조기술1팀", "구매팀"],
        "M": ["소프트웨어팀", "제조기술2팀", "구매팀"],
    },
    "소프트웨어": {
        "T": ["검사기팀", "제조기술1팀"],
        "M": ["제조기술2팀"],
    },
    "BOM": {
        "T": ["구매팀", "제조기술1팀", "가공팀"],
        "M": ["구매팀", "제조기술2팀", "가공팀"],
    },
    "도면": {
        "T": ["가공팀", "제조기술1팀", "품질팀"],
        "M": ["가공팀", "제조기술2팀", "품질팀"],
    },
    "Concept": {"T": "ALL", "M": "ALL"},
    "사양": {
        "T": ["기술영업팀", "검사기팀", "설계팀", "품질팀"],
        "M": ["기술영업팀", "설계팀", "품질팀"],
    },
}

def detect_impact_teams(change_type: str, biz_div: str) -> list[int]:
    """변경 종류 + 사업부로 영향 받는 팀 ID 리스트 반환"""
    rule = IMPACT_RULES.get(change_type, {}).get(biz_div, [])
    if rule == "ALL":
        with db_session() as c:
            return [r["id"] for r in c.execute("SELECT id FROM teams").fetchall()]
    with db_session() as c:
        rows = c.execute(
            f"SELECT id FROM teams WHERE name IN ({','.join(['?']*len(rule))})",
            tuple(rule),
        ).fetchall()
    return [r["id"] for r in rows]
```

---

## 4. 라우트 설계 (main.py 추가 예정)

```python
# ============ 변경 Inform 시스템 ============

@app.get("/changes", response_class=HTMLResponse)
async def changes_list(req, q="", change_type="", urgency="", status=""):
    """목록 (필터: 키워드·종류·긴급도·상태)"""

@app.get("/changes/new", response_class=HTMLResponse)
async def changes_new_form(req):
    """4단계 등록 폼"""

@app.post("/changes/new")
async def changes_new_submit(req, change_type, target_kind, target_id,
                              title, description, before_value, after_value,
                              urgency, project_id, attached_files):
    """등록 처리:
    1. CHG-YYMMDD-NNN 자동 채번
    2. detect_impact_teams() → change_impacts 자동 생성
    3. change_reads 행 미리 생성 (영향 부서원 전원)
    4. 알림 발송:
       - web: notifications 테이블에 등록
       - 하이웍스 메신저: notify_channel 설정으로 발송
       - 메일: 하이웍스 SMTP (요약)
       - 게시판: 자동 글 등록 (해당 부서 게시판)
    """

@app.get("/changes/{cid}", response_class=HTMLResponse)
async def changes_detail(req, cid):
    """상세: 전후 비교 + 영향 부서 + 확인 현황"""

@app.post("/changes/{cid}/ack")
async def changes_ack(req, cid, note=""):
    """'확인했습니다' 클릭 → change_reads.ack_at 갱신"""

@app.post("/changes/{cid}/edit")
async def changes_edit(req, cid, ...):
    """수정 (작성자만, 알림 안 보냄 — 확인된 거 무효화 방지)"""

@app.post("/changes/{cid}/delete")
async def changes_delete(req, cid):
    """삭제 (작성자/admin)"""

@app.get("/api/changes/unread")
async def api_unread_changes(req):
    """내가 받은 미확인 변경 카운트 (사이드바 빨간 뱃지용)"""

@app.get("/api/changes/recent")
async def api_recent_changes(req, scope="me", days=7):
    """홈 KPI용 — 최근 N일 변경 (내 관련/팀/전사)"""
```

---

## 5. UI / 화면 — 워크플로우 우선 4단계

### 5.1 등록 폼 (`changes/new`)

```
┌─────────────────────────────────────────────────────┐
│  변경 등록  [1] [2] [3] [4]    (진행 표시 바)      │
├─────────────────────────────────────────────────────┤
│ Step 1. 무엇이 바뀌었나요?                          │
│                                                     │
│  [기구설계]  [전장설계]  [소프트웨어]                │
│  [BOM]      [도면]      [Concept]    [사양]          │
│                                                     │
│  ↓ 클릭 시 자동으로 Step 2 등장 (페이지 이동 X)      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Step 2. 어떤 대상?                                   │
│                                                     │
│  관리코드: [001T2604 - 검사기 ICT     ▼ 자동완성]    │
│           또는                                       │
│  부품번호: [PRT-2026-0001 검색       ]               │
│           또는                                       │
│  도면번호: [DWG-T-001-Rev3 검색      ]               │
│                                                     │
│  → 영향 부서 미리보기 (자동 표시)                    │
│  ✓ 전장설계팀  ✓ 소프트웨어팀  ✓ 가공팀              │
│  ✓ 제조기술1팀  ✓ 구매팀                            │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Step 3. 변경 전 / 변경 후                            │
│                                                     │
│  제목 *: [한 줄 요약                              ]   │
│  설명: [상세 내용 (선택)                          ]   │
│                                                     │
│  ┌─변경 전──────┐    ┌─변경 후──────┐               │
│  │ [파일 첨부] │    │ [파일 첨부] │                  │
│  │ 또는 텍스트  │ → │ 또는 텍스트  │                  │
│  │             │    │             │                  │
│  └─────────────┘    └─────────────┘                  │
│                                                     │
│  긴급도: ○ 일반  ○ 긴급 (즉시 하이웍스 메신저 푸시)             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Step 4. 확인 (영향 부서 자동)                        │
│                                                     │
│  자동 판별된 영향 부서:                              │
│  ✅ 전장설계팀 (3명) — 김형렬 외                     │
│  ✅ 소프트웨어팀 (5명) — 이한중 외                   │
│  ✅ 가공팀 (4명) — 윤영조 외                         │
│  ✅ 제조기술1팀 (6명) — 노충일 외                    │
│  ✅ 구매팀 (3명) — 정성진 외                         │
│                                                     │
│  + 추가 부서/사람 [수동 추가]                        │
│  − 제외 [체크 해제]                                  │
│                                                     │
│  알림 채널:                                          │
│  ☑ HAIST WORKS web 알림                             │
│  ☑ 하이웍스 메신저 푸시                             │
│  ☑ 하이웍스 메일 (요약)                             │
│  ☐ 추가 알림 채널 (긴급만 — Phase 2)                         │
│                                                     │
│  [공지하기] (큰 빨간 버튼)                           │
└─────────────────────────────────────────────────────┘
```

### 5.2 상세 화면 (`changes/{id}`)

```
┌─────────────────────────────────────────────────────┐
│ CHG-260420-001  [긴급]  기구 설계 변경              │
│ 작성: 김상무 (설계팀) · 2026-04-20 14:32             │
│ 대상: 001T2604 검사기 ICT                            │
│ 진행률: 영향자 18명 중 12명 확인 ▓▓▓▓░░░ 67%        │
├─────────────────────────────────────────────────────┤
│  변경 전                  변경 후                    │
│  ┌─────────┐              ┌─────────┐                │
│  │ [도면1] │      →       │ [도면2] │                │
│  └─────────┘              └─────────┘                │
│  설명: ...                                           │
├─────────────────────────────────────────────────────┤
│ 영향 부서 확인 현황:                                 │
│ ✅ 전장설계팀 — 3/3 확인 (김형렬 14:35, ...)        │
│ ⏳ 소프트웨어팀 — 2/5 (이한중 14:40, 미확인 3명)    │
│ ⏳ 가공팀 — 1/4 (미확인 3명)                         │
│ ✅ 제조기술1팀 — 6/6                                 │
│ ⏳ 구매팀 — 0/3 미확인                              │
├─────────────────────────────────────────────────────┤
│ [내가 영향자라면]                                    │
│ [✓ 확인했습니다] (큰 초록 버튼)                      │
│ 영향 평가 (선택): [메모                          ]   │
└─────────────────────────────────────────────────────┘
```

### 5.3 사이드바 메뉴 추가 (base.html)

게시판 다음에 새 섹션:

```html
{% if user %}
<div class="sb-section">
  <div class="sb-head">변경 알림</div>
  <a href="/changes" class="sb-item">
    <svg ...></svg>
    변경 목록
    {% if unread_changes > 0 %}
      <span class="sb-badge sb-badge-red">{{ unread_changes }}</span>
    {% endif %}
  </a>
  <a href="/changes/new" class="sb-item">
    <svg ...></svg>
    변경 등록
  </a>
</div>
{% endif %}
```

홈 페이지 KPI에도 "어제 변경 N건" 카드 추가.

---

## 6. 알림 발송 로직 (database.py + main.py)

```python
def notify_change_impacts(change_id: int):
    """변경 등록 후 영향자 모두에게 알림 발송"""
    change = get_change(change_id)
    impacts = get_change_impacts(change_id)

    for imp in impacts:
        for user in get_team_members(imp["impact_team_id"]):
            # 1. web 알림 (notifications 테이블)
            create_notification(
                user_id=user["id"],
                kind="change",
                title=f"{change['change_type']} 변경: {change['target_label']}",
                body=change["title"],
                link=f"/changes/{change_id}",
            )
            # 2. 하이웍스 메신저 알림 (2026-04-22 대표 결재: 카카오워크 완전 폐기)
            hiworks_notify(
                channel_id=f"team_{imp['impact_team_id']}",
                text=f"🔴 [{change['change_type']}] {change['title']}\n{HOST}/changes/{change_id}",
            )

    # 4. 게시판 자동 글 (이력 보존)
    board_post_create(
        board_id=board_get_or_create_company(),
        author_id=change["author_id"],
        title=f"[변경공지] {change['title']}",
        body=f"종류: {change['change_type']}\n대상: {change['target_label']}\n\n{change['description']}",
        category="공지",
    )

    # 5. 메일 발송 (요약, 하이웍스 SMTP)
    # (선택, Phase 2에서 추가)

    # 6. notified_at 갱신
    with db_session() as c:
        c.execute("UPDATE changes SET notified_at=? WHERE id=?",
                  (now_str(), change_id))
```

---

## 7. 권한 모델

| 역할 | 등록 | 영향자 확인 | 수정 | 삭제 | 전체 모니터링 |
|---|---|---|---|---|---|
| member | 자기 부서 관련 | ✓ | (작성자 본인) | (작성자 본인) | — |
| leader | 자기 부서 + 하위 | ✓ | 본인+팀원 | 본인+팀원 | 자기 팀 |
| executive | 사업부 전체 | ✓ | ✓ | ✓ | 사업부 전체 |
| ceo / admin | 전사 | ✓ | ✓ | ✓ | 전사 |

---

## 8. 5대 원칙 자가 점검

| 원칙 | 적용 여부 | 어떻게 |
|---|---|---|
| 1. 워크플로우 우선 | ✅ | 4단계 자연 흐름, 다음 단계 자동 등장 |
| 2. 매뉴얼 0 | ✅ | Step별 안내, 영향 부서 자동 미리보기, 빈 입력 시 예시 표시 |
| 3. 변수 흡수 | ✅ | 긴급 토글, 영향 부서 수동 +/-, 모든 입력 후수정 가능 |
| 4. 자동 정리 | ✅ | 채번 자동, 영향 부서 자동, 알림 채널 자동 분기, 게시판 자동 글 |
| 5. 기존 도구 공존 | ✅ | 하이웍스 메신저 + 하이웍스 메일 + 게시판 동시 |

---

## 9. 구현 순서 (v2 받자마자 즉시)

| 순서 | 작업 | 시간 |
|---|---|---|
| 1 | database.py — 3개 테이블 + IMPACT_RULES + CRUD 함수 | 30분 |
| 2 | main.py — 9개 라우트 | 30분 |
| 3 | 템플릿 — `changes_list.html`, `change_form.html` (4-step), `change_detail.html` | 60분 |
| 4 | 사이드바 메뉴 + 홈 KPI 추가 | 15분 |
| 5 | 알림 발송 로직 (web + 게시판 자동 글) | 30분 |
| 6 | 하이웍스 메신저 토큰 설정 (admin 설정에서 hiworks_messenger_token 입력) | 10분 |
| 7 | 검증 + 테스트 데이터 + 커밋 | 30분 |

**총 예상**: 약 3시간 (하이웍스 메신저 토큰은 admin 설정에서 입력)

---

## 10. v2 문서 도착 후 검증할 것

Research 세션이 v2 작성 완료하면 이 청사진을 v2와 대조

| 검증 항목 | 일치/수정 |
|---|---|
| 5대 원칙 정의가 v2와 일치하는가 | (확인) |
| ECN 패턴 흡수 방식이 v2 권고와 일치하는가 | (확인) |
| 하이웍스 메신저 알림 패턴이 v2 권고와 일치하는가 | (확인) |
| 영향 부서 자동 판별 규칙이 12부서 매핑과 정확한가 | (확인) |
| 우선순위 (1주차)가 v2 로드맵과 일치하는가 | (확인) |

→ 일치하면 즉시 코드 작성, 불일치하면 청사진 수정 후 코드.

---

## 11. 다음 작업 (메인 세션이 지금부터 할 것)

이 청사진을 보고 **사전에 만들어 둘 것** (실제 라우트 등록은 안 하고, 함수만 준비):

### 11.1 IMPACT_RULES 데이터 (database.py 상단에 추가 가능)
- 위 § 3.3 코드 그대로 — DB에 저장하지 않고 코드 상수로 (관리 쉬움)

### 11.2 영향 부서 자동 판별 함수 (database.py에 추가)
- `detect_impact_teams(change_type, biz_div)` → 단순 dict lookup

### 11.3 하이웍스 메신저 알림 함수 (database.py)
- 토큰은 admin 설정에서 hiworks_messenger_token 입력
- `hiworks_notify(channel_id, text)` → notify_channel 설정에 따라 자동 분기

### 11.4 변경 알림 통합 함수 (notify_change_impacts)
- 위 § 6 코드 — 미리 작성해두고 Research 세션 v2 받으면 즉시 호출

→ 이렇게 하면 v2 도착 시 **DB 스키마 + 라우트 + 템플릿만 추가**하면 즉시 동작.

---

**문서 위치**: `KNK업무시스템구축/01_HAIST_WORKS/_DESIGN_변경_Inform.md`
**작성**: 2026-04-20 (메인 세션 빅터, B안 진행)
**다음 검증**: Research 세션 v2 도착 후 대조
