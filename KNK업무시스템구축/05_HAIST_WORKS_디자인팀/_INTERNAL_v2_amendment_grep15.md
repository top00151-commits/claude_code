# [INTERNAL] v2 amendment grep 15종 검증 패턴 (자기참조용)

- 작성: 05 디자인팀 빅터
- 일자: 2026-04-25
- 목적: 2026-04-24 LIVE 핫패치 사고(시안만 grep · LIVE 누락) 재발 방지
- 적용 대상: v2 시안(03_시안/) **AND** LIVE(01_HAIST_WORKS/) **양쪽 동시 grep**

---

## 0. 배경 (사고 요약)

| 항목 | 어제 1차 | 어제 핫패치 후 |
|---|---|---|
| 시안 grep 12종 | 12/12 PASS | 12/12 PASS |
| LIVE grep | **수행 안 함** | 추가 수행 → FAIL 2건 발견 |
| 결과 | 시안만 정합 · LIVE 결함 | LIVE 핫패치 c2 적용 |

→ 교훈: **시안 PASS = LIVE PASS 아님.** v2 정식 이식 시 양쪽 동일 패턴으로 grep.

---

## 1. grep 15종 (시안 12 + LIVE 전용 3 추가)

### A. 시안·LIVE 공통 12종 (기존 v2 amendment §4)

| # | 패턴 (regex) | 의도 | 기대값 |
|---|---|---|---|
| G01 | `--bg-primary:` | 토큰 정의 존재 | ≥1 |
| G02 | `--bg-secondary:` | 토큰 정의 존재 | ≥1 |
| G03 | `--text-primary:` | 토큰 정의 존재 | ≥1 |
| G04 | `--accent-primary:` | 토큰 정의 존재 | ≥1 |
| G05 | `--radius-md:` | 라운드 토큰 | ≥1 |
| G06 | `--shadow-soft:` | 그림자 토큰 | ≥1 |
| G07 | `--font-display:` | 타이포 토큰 | ≥1 |
| G08 | `--space-3:` | 간격 토큰 | ≥1 |
| G09 | `WORKSPACES` | 사이드바 별칭 alias 노출 | ≥1 |
| G10 | `data-theme="healing"` | 테마 속성 | ≥1 |
| G11 | `cache:c2` 또는 `?v=c2` | 캐시 버전 토큰 | ≥1 |
| G12 | `(?<!--)\s*/\*[^*]` (주석 리터럴 누수) | 주석 흔적 0건 | **0** |

### B. LIVE 전용 추가 3종 (신규)

| # | 패턴 | 의도 | 기대값 |
|---|---|---|---|
| **G13** | `<dock` 또는 `id="victor-dock"` | 빅터도크 DOM 존재 | ≥1 (LIVE base.html) |
| **G14** | `data-i18n=` 와 `t('` 병행 사용 | i18n 키 일관성 | 동일 키셋 |
| **G15** | `KPI.*매출` 또는 `kpi-revenue` | 매출 KPI 카드 마운트 | CEO 뷰 ≥1 |

→ G13/G14/G15 는 어제 04 힐링QA 1차 FAIL 항목과 1:1 대응.

---

## 2. 실행 절차 (체크리스트)

```
[ ] STEP 1. 시안 grep (03_시안/ 전체) — G01~G12 전부 PASS 확인
[ ] STEP 2. LIVE grep (01_HAIST_WORKS/ 전체) — G01~G15 전부 PASS 확인
[ ] STEP 3. 둘 중 하나라도 FAIL → 09 팀장 보고 후 핫패치 분기
[ ] STEP 4. 양쪽 PASS → v2 amendment 본문에 "LIVE 정합 OK" 명기
[ ] STEP 5. 04 힐링QA 재의뢰
```

---

## 3. 회피 (Anti-pattern)

- 시안만 PASS → 정합 완료 선언 **금지**
- grep 결과를 텍스트로만 보고하고 라인넘버 미첨부 **금지**
- LIVE 핫패치 라인은 v2 정식 이식 시 반드시 보존 (→ D3 가이드 참조)

---

(끝)
