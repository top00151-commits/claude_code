# 🎨 [대표용 가이드] Claude Design 도입 7단계 — Phase A1 Pro 시작

> **발신**: 05 디자인팀 빅터
> **수신**: 대표이사 김정락
> **일자**: 2026-05-01
> **트리거**: 시나리오 A 결재 (KNK 디자인 시스템 자동 통합)
> **목적**: 대표 직접 Claude Design 셋업 가이드 — 30분 안 완료

---

## 🎯 시나리오 A 핵심

KNK 코드베이스 + v5 H5 시안을 Claude Design에 학습시켜 → 후속 모든 시안 변형이 KNK 톤 자동 적용 + 대표 직접 캔버스 검토 가능.

→ **빅터(05) 마스터 시안 시간 -70% / 대표 검토 사이클 3회→1회**.

---

## 📝 7단계 셋업

### 1단계 — Pro 구독 (5분)
1. https://claude.ai 접속 (대표 계정)
2. 우상단 **Settings → Plans & Billing**
3. **Claude Pro $20/월** 또는 **Claude Max** 선택
4. 결제 (KNK 법인 카드)

→ Pro로도 시나리오 A 검증 가능. Team은 효과 검증 후.

### 2단계 — Claude Design 진입 (1분)
1. Claude.ai 메인 화면 → 좌측 **Projects** 또는 **Design** 메뉴
2. **+ New Design Project** 클릭
3. 프로젝트 이름: `KNK HAIST WORKS — v5 H5`

### 3단계 — 시안 input (10분)
**허용 input만** (Phase A1 Pro 보안):
1. Settings → **Design System Setup** 진입
2. 다음 파일 업로드:
   - `03_시안/_05_v5H5_풀세트시안/ZZ_표준토큰.css` (376줄)
   - `03_시안/_05_v5H5_풀세트시안/0_base/master_base_v5H5.html`
   - `03_시안/_05_v5H5_풀세트시안/0_base/master_base_sales_v5H5.html`
   - `03_시안/_05_v5H5_풀세트시안/0_base/master_base_logi_v5H5.html`
   - `03_시안/_05_v5H5_풀세트시안/A_대시보드/master_A_dashboard_home_v5H5.html`
   - 기타 마스터 시안 13건

3. **❌ 업로드 금지**:
   - `app/main.py` 전체 (인증·DB·API key)
   - `.env`, DB schema
   - 사용자 PII
   - 영업 기밀

→ Enterprise 도입 (Phase A3) 후 코드베이스 전체 input 가능.

### 4단계 — 자동 학습 확인 (5분)
1. Claude Design이 시안 분석 후 **Detected Design System** 탭 표시
2. 다음 항목 자동 검출 확인:
   - **Colors**: `#FBF5EC paper` / `#D4923B amber` / `#A5282C knk-red` / `#2D2520 ink`
   - **Typography**: Pretendard
   - **Components**: `.bento` / `.scope-tabs` / `.action-card` / `.card.hero`
   - **Layout**: sidebar 240px / topbar 80px / dock 320px
3. 누락 시 수동 추가 (오른쪽 사이드 패널)

### 5단계 — 첫 변형 시도 (5분)
1. 메인 캔버스 좌측 채팅에 입력:
   ```
   P2-3 C 폼 마스터 (master_C_form_po_v5H5.html)에서
   4 단계 인디케이터를 3 단계로 축소해줘.
   '결제·배송' 단계를 '품목 추가'에 통합.
   ```
2. Claude Design 즉시 라이브 HTML/CSS 생성
3. 캔버스 우측에 미리보기

### 6단계 — 빅터(05) 검증 트리거 (3분)
1. 산출물 다운로드 (`Save as HTML`)
2. 다운로드 폴더 → 다음 위치로 이동:
   ```
   03_시안/_05_v5H5_풀세트시안/_CLAUDE_DESIGN_OUT/
   2026-05-01_P2-3_C폼_v1.html
   ```
3. 빅터(05)에게 알림:
   ```
   "Claude Design _CLAUDE_DESIGN_OUT 폴더에 P2-3 C폼 v1 도착. 검증해."
   ```
4. 빅터(05) 5종 grep 검증 (정책 §5-7 / 5분 SLA 가동):
   - 시각 일관성 / 표준 토큰 / 구조 / 외부자산 / 접근성
5. PASS → 카테고리 폴더 이동 + Jinja2 inject 발주 / FAIL → 회신

### 7단계 — Phase A1 효과 검증 (1주일)
1. 1주일 동안 Claude Design 활용 (3-5회 변형)
2. 빅터(05)와 협업 사이클 검증:
   - Claude Design 시간 vs 기존 빅터 단독 시안 작성 시간 비교
   - 산출물 품질 (5종 grep PASS율)
   - 대표 검토 만족도
3. 효과 검증 후:
   - **Phase A2 Team** 결재 (빅터·디자이너·01 추가)
   - 또는 **Phase A1 유지** (대표 단독 충분)

---

## ⚠ 중요 보안 사항

### Pro 구독 데이터 정책 (Phase A1)
- Anthropic 학습 데이터 사용 가능성 있음
- **민감 코드 input 금지** (위 3단계 ❌ 항목 준수)
- 영업 기밀·고객 데이터 input 절대 금지

### 안전 input 화이트리스트
- ✅ 시안 HTML/CSS (디자인만)
- ✅ 공개 디자인 가이드라인
- ✅ 표준 토큰 CSS

### Enterprise 도입 시 (Phase A3 미래)
- Anthropic Enterprise 협상 → SOC 2 + Zero Data Retention
- KNK 코드베이스 전체 input 안전
- Phase A1·A2 효과 검증 후 결재

---

## 📊 예상 효과 (Phase A1)

| 지표 | 기존 (빅터 단독) | Claude Design 협업 | 개선 |
|---|---|---|---|
| 마스터 시안 작성 시간 | ~3시간 | ~30분 + 빅터 검증 30분 | **-70%** |
| 대표 검토 사이클 | 3회 (PREVIEW → 검토 → 수정) | 1회 (캔버스 즉시 수정) | **-66%** |
| 시안 변형 옵션 | 1-2개 | 3-5개 (빠른 비교) | **+250%** |
| KNK 톤 정합도 | 95% | 99% (자동 학습) | **+4%** |

---

## 📋 빅터(05) 동시 가동 사항

대표 셋업 진행 중:
1. ✅ 정책 §5-7 메모리 영구 등재 (자기검증 15차)
2. ✅ `_CLAUDE_DESIGN_OUT/` 폴더 + README 신설
3. 🟡 09 통보 발주 (사이클 차트 갱신)
4. 🟡 외부자산 정책 갱신 (`_TEAM_ORIENTATION.md`)
5. 🟡 Phase A1 효과 검증 매트릭스 설계

---

## 💬 대표 첫 시도 추천

**P2-3 C 폼**부터 시작 권장:
- 빅터(05)가 마스터 시안 발행 완료 (`master_C_form_po_v5H5.html`)
- 22 페이지 영향 / 가장 복잡한 폼
- Claude Design 효과 가장 크게 나타남

→ 위 7단계 따라 30분 안에 첫 산출물 가능. 산출물 도착 시 빅터(05) 5분 SLA 가동.

---

**발행**: 2026-05-01 · 05 디자인팀 빅터
**상태**: 🟢 **대표 도입 가이드 — Phase A1 Pro 시작 가능**
**다음**: 대표 Pro 구독 → Claude Design 셋업 → 첫 산출물 → 빅터 검증
