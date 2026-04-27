# 03 Research — deep_translator P11 영향 + 사내 i18n 확장 가능성

> **발신**: 03 Research worker (일회성)
> **수신**: 09 빅터 팀장
> **일시**: 2026-04-27
> **상위 지시**: 대표 14:19 — "P11 베트남 수출 실무자 영향 분석 후 판단, 실제로 많이 쓰는 단어를 빅터AI에 등록해서 해도 가능한지도 판단 필요"
> **제약**: 정찰만 (코드 0 / BAT 0 / 외부 자산 0 / 권한 팝업 0)
> **상위 정책**: `_TEAM_ORIENTATION.md` §3 (외부 자산 0건), §4 (자체 판단 4항 금지)

---

## A. 사용 위치 정확 (grep -n 직접 인용)

### A-1. 코드 본체 사용 위치 (3개소 단일 함수)

전부 `app/main.py` `api_translate()` 함수 1곳에 응집되어 있음 (line 1071~1112). 라우트는 `POST /api/translate`.

```
main.py:1071  @app.post("/api/translate")
main.py:1072  async def api_translate(req: Request):
main.py:1081      # 방법1: deep_translator
main.py:1083          from deep_translator import GoogleTranslator
main.py:1084          result = GoogleTranslator(source='auto', target=target).translate(text)
main.py:1089      # 방법2: MyMemoryTranslator (fallback)
main.py:1091          from deep_translator import MyMemoryTranslator
main.py:1095          result = MyMemoryTranslator(source=src, target=tgt_map.get(target,'en-GB')).translate(text)
main.py:1100      # 방법3: urllib로 직접 Google Translate 호출
main.py:1104          url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target}&dt=t&q={encoded}"
```

3 layer fallback (deep_translator → MyMemoryTranslator → translate.googleapis.com 직접 URL).

### A-2. UI 호출 위치 (단일 함수, 3 트리거)

`app/templates/base.html` 1개 화면(카드 모달) 안에서만 사용:

```
base.html:423  <select id="trLang">  ← 언어 선택 (ko/vi/en)
base.html:487  if (t.notes) ... <button class="tr-btn" onclick="translateFromDom(this)">${I.translate_btn}</button>
                ← 트리거 1: 카드 "오늘 한 일(notes)"
base.html:488  if (t.next_plan) ... <button class="tr-btn" ...>
                ← 트리거 2: 카드 "다음 계획(next_plan)"
base.html:524  ... <button class="tr-btn-sm" onclick="translateFromDom(this)">🌐</button>
                ← 트리거 3: 댓글(cm-item)
base.html:576  async function translateFromDom(btn) { ... fetch('/api/translate', ...) }
```

**호출 발생 화면**: 카드 상세 모달 1개 (홈/일일업무/피드/검색 등 어디서든 카드 클릭 → 모달 열림 → 번역 버튼 누를 때만 외부 호출).

**자동 호출 0건**: 페이지 로드 시 자동 번역 없음 — 사용자가 의식적으로 🌐 버튼을 눌러야만 발생. 부품명/거래처명/견적서/리스트 화면에서는 호출 0.

### A-3. 외부 자산 메타 등록

```
main.py:2874  "name": "deep_translator",
main.py:2926  allowed_assets = {"openpyxl", "pandas", "deep_translator"}
```

`/admin/external-assets` 페이지에 결재 카드 등록되어 있음 (사이클 64 spike). 결재값 ∈ {remove, keep, partial} 미통과 시 거부.

---

## B. P11 페르소나 영향 분석

P11 = 베트남 수출 실무자. 베트남 거래처 발주·견적·서류 작성. 기본 다국어 가능자(한국어/영어/베트남어 직접 입력 가능 추정).

### B-1. 매일 사용 패턴 추정

| 시나리오 | 현 시스템 동작 | P11 사용 빈도 | 비고 |
|----------|---------------|--------------|------|
| 베트남 거래처가 한국어 카드 댓글 다는 경우 | 🌐 버튼 클릭 → vi 번역 | **드묾** (베트남 거래처는 외부 사용자 = 시스템 사용자 아님) | 핵심 사용자는 사내 P11 본인 |
| 한국 직원이 P11 카드에 한글 댓글 | P11이 🌐 → vi 번역 | **간헐적** | P11이 한국어 가능 시 굳이 번역 X |
| P11이 카드에 베트남어/영문 입력 | 한국 직원이 🌐 → ko 번역 | **간헐적** | 한국 직원 측 사용 |
| 부품명/견적서 항목 | **번역 호출 안 함** (해당 화면에 🌐 없음) | 0 | 사이클 63 i18n.py qp_* 30키로 커버 |
| 거래처명/품명 자유 입력 | 호출 없음 | 0 | 한국어 그대로 보존 |

**결론**: `/api/translate`는 **카드 모달의 사용자 자유 입력 텍스트(notes/next_plan/댓글) 1회성 번역**에만 쓰임. 견적서·부품·거래처 등 정형 데이터는 이미 i18n.py 사내 사전으로 커버.

### B-2. 번역 기능이 사라지면 P11이 어떻게 대응?

1. **P11 본인 다국어 능력**: 베트남 수출 실무자 = 한/베/영 3종 직접 입력 가능 추정 → 자력 대응 가능성 높음
2. **사내 i18n.py 표준 단어 530키**: 견적서·메뉴·상태 라벨 등은 이미 ko/vi/en 3종 완전 커버 (qp_* 30키 + 기존 약 500키)
3. **자유 문장 번역 부재 시**:
   - 옵션 a: P11이 한국어/영문 직접 입력 (현 시스템에서도 가능)
   - 옵션 b: 외부 도구(번역 사이트) 별도 탭에서 사용 — **시스템 외부**에서 처리 (보안 영향 동일하나 KNK 시스템 책임 아님)
   - 옵션 c: 한국 직원이 P11에게 한국어 카드 댓글 작성 시 영문/베트남어 병기 (관행)

### B-3. 결격 발생 시나리오

번역 제거 시 **결격 가능 시나리오 = "사내 한국 직원이 P11의 베트남어/영문 댓글을 즉시 이해 못해 업무 지체"** 1건 추정.

- 빈도: 낮음 (P11이 시스템에 베트남어로 입력하는 경우는 드물 것 — 사내 공용어가 한국어/영어인 한)
- 대안: 한국 직원도 외부 번역기 별도 탭에서 처리 가능 (시스템 외부)

**핵심 발견**: `/api/translate`는 **편의 기능**이지 P11 업무 필수 기능이 아님. 견적서·부품·메뉴·상태 등 P11 핵심 업무는 i18n.py로 이미 커버됨.

---

## C. 사내 i18n.py 확장 가능성 (대표 메모 핵심)

### C-1. 현 상태 (grep -n 직접 인용)

```
i18n.py:13    # ===== 공통 / 상단바 =====
i18n.py:492   # ===== 사이클 63 — 견적서 인쇄 (P11 다국어) =====
i18n.py:496   "qp_title": {"ko":"견 적 서", "vi":"BÁO GIÁ", "en":"QUOTATION"},
... (qp_* 30키)
i18n.py:550   "qp_lang_en": {...}
i18n.py:551   }
i18n.py:553   def t(key, lang="ko"): ...
```

`grep -cE '^\s*"[a-z_0-9]+":' i18n.py` = **472 키** (= 약 530키 중 dict 키만 cnt). 견적서 30키 + 기존 약 442키 = 472.

`wc -l app/i18n.py` = **562 라인**.

### C-2. 확장 한계 추정

| 키 수 | 메모리 | 로드 시간 | 유지보수 | 권장 여부 |
|-------|--------|----------|---------|----------|
| 현재 472 | 무시할 수준 | 즉시 | 사람이 직접 읽음 | OK |
| ~1,000 | < 1MB | 즉시 | 가능 | OK |
| ~5,000 | ~5MB | < 100ms | 카테고리 분리 필요 | OK (DB 분리 권장) |
| 10,000+ | ~10MB | 수 초 | 사람 한계 | DB(words 테이블) 권장 |

**판단**: i18n.py 단일 파일은 **5,000키까지 실용적**. 그 이상은 DB(`words` 테이블) 분리.

### C-3. 빅터AI 단어 등록 기능 (구상)

빅터AI 도크에 명령:
- 사용자: "빅터, 등록: 비행기 = Máy bay (vi)"
- 빅터: i18n.py 또는 `words` 테이블에 키 추가 → 응답 "등록 완료, 키: term_001"

**기술적 가능성**: 가능. 단 다음 결정 필요:
1. 저장 위치: i18n.py 직접 수정 vs `words` 테이블 신설
2. 키 명명: 자동 생성(term_NNNN) vs 사용자 입력(part_aircraft)
3. 권한: P11/admin/sales만 vs 전 사용자
4. 검수: 즉시 반영 vs admin 승인 후 반영

**i18n.py 직접 수정의 위험**: 코드 파일이 사용자 데이터 의존 → 재시작 필요·배포와 데이터 분리 원칙 위반 → **권장 안 함**.

**권장**: `words` 테이블 신설(`key, ko, vi, en, registered_by, status`) + `app/i18n_dynamic.py`에서 정적 i18n.py + DB words 병합 후 dict 반환. P11이 도크에서 등록하면 즉시 DB INSERT, 다음 페이지부터 반영.

### C-4. parts 다국어 컬럼 (대표 결재 대기 중)

- `parts.part_name_en` / `parts.part_name_vi` 추가는 **DB 스키마 변경 → 대표 결재 의무**
- 현재 사이클 63은 i18n.py 표준 단어로만 처리, 자유 입력 부품명은 한국어 보존 (B 옵션3 채택, line 493~494 주석 인용)

---

## D. 빅터AI 단어 등록 인터페이스 — 작업 비용 / P11 가치

### D-1. 작업 비용 (정찰 추정)

| 작업 항목 | 추정 시간 | 사이클 |
|----------|----------|-------|
| `words` 테이블 마이그레이션 (key, ko, vi, en, by, status) | 0.5일 | 사이클 N |
| `app/i18n_dynamic.py` (정적 + DB 병합) | 0.5일 | 사이클 N |
| 빅터AI 도크 명령 파서 ("빅터, 등록: X = Y (lang)") | 1일 | 사이클 N+1 |
| `/admin/words` 관리 페이지 (목록·승인·삭제) | 1일 | 사이클 N+1 |
| 4 페르소나 시뮬레이션 검증 | 0.5일 | 사이클 N+2 |
| **합계** | **3.5일** | 3사이클 |

### D-2. P11 가치 (정성 평가)

- **High**: P11이 자주 쓰는 베트남 부품명·거래처 용어가 시간이 갈수록 사전화 → P11 입력 속도 ↑, 한국 직원 이해도 ↑, 신입 P11 후임자 온보딩 자동화
- **Medium**: 일회성 자유 문장 번역(/api/translate)은 못 대체 — 사용자가 매번 등록할 만큼 자주 안 쓰는 표현은 커버 안 됨
- **Network effect**: 1년 누적 시 1,000~3,000키 도달 가능 → P11 외 P1 영업·P4 구매도 활용

---

## E. 3안 비교 (A안 / B안 / C안)

| 평가 항목 | A안 즉시 제거 + i18n 확장 | B안 유지 + 화이트리스트 | C안 즉시 제거 + 빅터AI 등록 신설 |
|----------|--------------------------|------------------------|-------------------------------|
| **P11 가치 (즉시)** | 중 (자유 문장 번역 사라짐) | 상 (현 기능 유지) | 중 (자유 문장 번역 사라짐) |
| **P11 가치 (1년 후)** | 중 (사전 누적 의존) | 상 (그대로) | **상** (사전 자동 누적) |
| **보안 (KNK 데이터 외부 송출)** | **0** (외부 호출 0) | 중 (whitelist 검증 필요·우회 위험) | **0** (외부 호출 0) |
| **외부 자산 0건 정책 부합** | **OK** | NG (deep_translator 잔존) | **OK** |
| **작업량** | 1사이클 (제거만) | 1.5사이클 (검증 로직) | 3사이클 (DB+UI+검증) |
| **재발 방지** | 상 (코드 제거) | 하 (라이브러리 잔존) | 상 |
| **P11 자율성** | 하 (관리자 의존) | 중 | **상** (도크에서 직접 등록) |
| **결재 의무** | 빅터 자체 결정 가능 | 빅터 자체 결정 가능 | 빅터 자체 결정 가능 (DB 신규는 신중) |

**가중치 평가**:
- 보안·정책 부합 우선 → A 또는 C 우위
- P11 장기 가치 우선 → C 우위
- 즉시 가용성 우선 → B 우위 (단 정책 위반)

---

## F. 09 팀장 결정 권고

### F-1. 빅터 자체 결정 가능 안 (대표 명시 위임 범위 안 — 코드 1파일 수정 + 신규 모듈)

**권고: C안 — 사이클 N에서 deep_translator 즉시 제거 + 빅터AI 단어 등록 기능 신설**

근거:
1. **외부 자산 0건 정책** (TEAM_ORIENTATION §3.1) 즉시 부합
2. **P11 핵심 업무는 이미 i18n.py 530키로 커버** (B-1 표) — 자유 문장 번역은 편의 기능
3. **장기 P11 가치 최대화** — 사용 누적으로 사전 자가 성장
4. **재발 방지** — 라이브러리 자체 제거 → 우회 호출 불가능

### F-2. 대표 결재 필요 안 (DB 스키마 / 페르소나 영향 큼)

다음 항목은 빅터 자체 결정 보류, **대표 결재 의무**:
1. `words` 테이블 신설 (DB 스키마 변경)
2. `parts.part_name_en` / `parts.part_name_vi` 추가 (이미 결재 대기 중)
3. `customers.default_language` 추가 (기존 spike 제안)
4. 빅터AI 도크에 등록 권한 부여 범위 (전 사용자 vs admin/P11 한정)

### F-3. 단계 제안 (대표 결재 분할)

- **사이클 N (즉시 가능, 빅터 자체 결정 OK)**: deep_translator 3개소 제거 + `/api/translate`를 i18n.py 기반 단어 매칭 fallback으로 대체 + 04 시뮬레이션 P11
- **사이클 N+1 (대표 결재 후)**: `words` 테이블 + i18n_dynamic.py + 빅터AI 등록 명령 파서
- **사이클 N+2 (대표 결재 후)**: parts 다국어 컬럼·customers.default_language

### F-4. 즉시 보고 사안 (99 디스패치 권고)

- **DEC**: deep_translator 제거 즉시 가능 여부 (대표 14:19 메모 "부분 처리" 해석 확인)
- **결재요청**: words 테이블 신설 (DB 스키마)

---

## 산출

- 본 문서: `03_HAIST_WORKS_Research/_TO_09팀장_2026-04-27_정찰_deep_translator부분처리.md`
- 코드 변경: **0**
- BAT 변경: **0**
- 외부 호출: **0**
- 권한 팝업: **0**

---

## 정직성 v3 직접 인용 체크

- `app/main.py` line 1071, 1083, 1091, 1104, 2874, 2926: grep -n 인용 (A-1, A-3)
- `app/templates/base.html` line 423, 487, 488, 524, 576, 593: grep -n 인용 (A-2)
- `app/i18n.py` line 13, 492, 496, 550, 551: grep -n 인용 (C-1)
- `wc -l app/i18n.py` = 562 (C-1)
- `grep -c '^\s*"[a-z_0-9]+":' i18n.py` = 472 (C-1)
- 추정·기억 인용 0건. 측정값과 정찰값 분리 명시.
