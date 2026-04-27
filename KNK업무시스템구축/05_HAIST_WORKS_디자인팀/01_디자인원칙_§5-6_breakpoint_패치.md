# 01_디자인원칙 §5-6 break point 표준화 — 패치

> 발신: 05 디자인팀 빅터 · 일자: 2026-04-25
> 대상 문서: `05_HAIST_WORKS_디자인팀/01_디자인원칙.md` (v4) → §5-6 신설
> 발주 근거: `_FROM_09팀장_2026-04-25_보강발주_원칙서_폰트토큰.md` B3
> 04 인용: `_TO_09팀장_2026-04-25_T2_S4해상도정적.md` line 26~42 ("@media 25건 중 비표준 11건 (44%) — 819, 900(4건), 1000, 1100, 1280, 1599, 2200")

---

## §5-6. break point 표준화 (신설)

### §5-6-1. 표준 break point 5종 채택

| 토큰 | px | 디바이스 |
|---|---|---|
| `--bp-sm` | **320** | 모바일 (small) |
| `--bp-md` | **768** | 태블릿 |
| `--bp-lg` | **1024** | 노트북 |
| `--bp-xl` | **1366** | 데스크톱 |
| `--bp-2xl` | **1920** | 와이드·FHD+ |

- 위 5종 외 `@media` 쿼리 신규 작성 금지.
- `00_design_tokens.css`에 토큰 정의 후 `@media (min-width: 768px)` 등 직접 사용 (CSS 변수는 미디어쿼리에서 직접 못 쓰지만 토큰 문서화 목적).

### §5-6-2. 비표준 11건 정리 — 별도 P2 잡으로 발주 예정

04 실측 비표준 break point:

| 비표준 px | 횟수 | 대체안 |
|---|---|---|
| 819 | 2 | → 768 (md) |
| 900 | 4 | → 1024 (lg) |
| 1000 | 1 | → 1024 (lg) |
| 1100 | 1 | → 1024 (lg) |
| 1280 | 1 | → 1366 (xl) |
| 1599 | 1 | → 1366 또는 1920 (해당 영역 검토) |
| 2200 | 1 | → 1920 (2xl) 또는 제거 (초대형 별도 처리 불필요) |

- 본 §5-6 발주 범위 외. **01에 별도 P2 잡으로 발주 예정** (발주서 B3 §3 명시).
- 1023, 1365는 표준 근사값(≈1024, ≈1366)으로 1차 유지 후 점진 정리.

### §5-6-3. mobile-first @media 표준 패턴

```css
/* 권장: min-width 누적 (mobile-first) */
.kpi-grid { grid-template-columns: 1fr; }                /* SM 기본 */
@media (min-width: 768px)  { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }  /* MD */
@media (min-width: 1024px) { .kpi-grid { grid-template-columns: repeat(3, 1fr); } }  /* LG */
@media (min-width: 1366px) { .kpi-grid { grid-template-columns: repeat(4, 1fr); } }  /* XL */

/* 비권장: max-width 역방향 + 산발 px */
@media (max-width: 819px) { ... }     /* 금지 */
@media (max-width: 900px) { ... }     /* 금지 */
```

### §5-6-4. 자기 검증 grep 패턴

```
# G18-1: 비표준 break point 잔존 점검
grep -nE "@media[^{]*\(\s*(min|max)-width:\s*(819|900|1000|1100|1280|1599|2200)px" style.css
# 기대 (정리 후): 0건

# G18-2: 표준 5종 사용 분포
grep -cE "@media[^{]*\(\s*min-width:\s*(320|768|1024|1366|1920)px" style.css
# 기대: 5종 균형 사용 (정보값)

# G18-3: max-width 역방향 비율 점검
grep -cE "@media[^{]*\(\s*max-width:" style.css
# 기대: min-width 사용량보다 적음 (mobile-first 원칙)
```

검증 대상: `01_HAIST_WORKS/static/style.css` + 시안 03/*.

---

## 셀프오딧

- 추측 금지: 04 line 26~42 분포표 인용 명시. 비표준 11건 = 04 실측.
- 본 §5-6 자체는 권고 + grep 가이드만. 비표준 11건 정리는 별도 P2 발주 (범위 외).
- 외부 브랜드 인용 0건. 코드 수정 없음.

*05 빅터 · 2026-04-25 · B3 3/3*
