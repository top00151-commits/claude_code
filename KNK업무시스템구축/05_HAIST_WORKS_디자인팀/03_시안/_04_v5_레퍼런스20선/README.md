# 🎨 v5 디자인 레퍼런스 20선 — 외부 트렌드 폭넓은 탐색

> **트리거**: 대표 *"디자인팀… 웹에서 디자인 참고할만한 한것들로 20가지 찾아놔… 아직도 디자인이 마음에 들지않아."* (2026-04-29)
> **편집**: 05 디자인팀 빅터
> **목적**: v1(sage)·v2(매트릭스)·v3(헤더 재설계)·v4(CX23c 매거진70) 5라운드 21옵션 탐색이 모두 빅터 좁은 시야 안에 머물렀음을 인정 → **외부 실제 시장 트렌드 4대 축에서 20건 큐레이션** → 대표 1차 선정 → v5 시안 3종 제작

---

## 📊 한눈에 — 20선 분류 매트릭스

| # | 작품·브랜드 | 카테고리 | 핵심 무드 | KNK 적합도 | 비고 |
|---|---|---|---|---|---|
| 01 | **Linear** | A. 미니멀 SaaS 정수 | 흑·고요·정밀 | ★★★★★ | 사이드바·이슈 리스트 표준 |
| 02 | **Vercel Dashboard** | A. 미니멀 SaaS 정수 | 흑백·데이터 우선 | ★★★★★ | 배포 카드·sparkline |
| 03 | **Stripe Dashboard** | A. 미니멀 SaaS 정수 | 보라·세련·신뢰 | ★★★★☆ | 4-카드 KPI 패턴 |
| 04 | **Notion Sidebar** | A. 미니멀 SaaS 정수 | 종이·글자·여백 | ★★★★☆ | 접이식 그룹 네비 |
| 05 | **Apple iPhone 15 Pro** | F. 벤토 그리드 | 다크·하이엔드·모듈 | ★★★★★ | 벤토 원조 |
| 06 | **Awwwards Renaissance Edition** | B. 에디토리얼 진화 | 회화·고품·예술 | ★★★☆☆ | Site of the Month 2026.02 |
| 07 | **Datadog Dashboard** | F. 벤토 그리드 | 데이터·실시간·보라 | ★★★★☆ | 운영 대시보드 정수 |
| 08 | **Mixpanel Dashboard** | F. 벤토 그리드 | 흰·차트·해상 | ★★★★☆ | 분석 모듈 카드 |
| 09 | **Amplitude Dashboard** | F. 벤토 그리드 | 보라·청록·인사이트 | ★★★☆☆ | 사용자 흐름 시각화 |
| 10 | **HubSpot Role-based UI** | A. 미니멀 SaaS 정수 | 주황·역할별·맥락 | ★★★★☆ | 권한별 다른 첫 화면 |
| 11 | **Glassmorphism Fintech** | C. 글래스·라이트닝 | 반투명·블러·3D | ★★★☆☆ | 2026 부활 트렌드 |
| 12 | **Neobrutalism Dashboard** | D. 네오브루탈리즘 | 굵은 테두리·고대비·재미 | ★★☆☆☆ | 차별화 카드, B2B엔 모험 |
| 13 | **Muji Online Store** | E. 일본 미니멀 | 흰·여백·간결 | ★★★★★ | MA(間) — 사이의 미학 |
| 14 | **Sony Pro Site** | E. 일본 미니멀 | 흑·정밀·고급 | ★★★★☆ | 정보 응축 + 침묵 |
| 15 | **Toss Workplace** | G. 한국 엔터프라이즈 | 청·둥근·친근 | ★★★★★ | 한국형 핀테크 표준 |
| 16 | **Naver Works** | G. 한국 엔터프라이즈 | 녹·기관·신뢰 | ★★★★☆ | 정부 3부처 채택 |
| 17 | **Naver Cloud Console** | G. 한국 엔터프라이즈 | 녹·기술·정돈 | ★★★☆☆ | 한국 클라우드 1위 UI |
| 18 | **Wellness Earthy Palette** | H. 힐링 고급화 | 클레이·세이지·테라코타 | ★★★★☆ | 흙빛+세이지 조합 |
| 19 | **Deep Teal + Dusty Rose** | H. 힐링 고급화 | 청록·먼지장미 | ★★★★☆ | 녹색 탈피 힐링 |
| 20 | **Liquid / Apple Liquid Glass** | C. 글래스·라이트닝 | 액체·반사·광택 | ★★★☆☆ | 2026 액체 디자인 부활 |

---

## A. 미니멀 SaaS 정수 — Linear·Vercel·Stripe·Notion·HubSpot

### 01. Linear (https://linear.app)
- **무드**: 검은 잉크·흰 종이·정밀 격자, 그림자 거의 없음
- **핵심**: 이슈 뷰에서 status·priority·assignee **3개 외 모든 것 제거**. 명령 팔레트 (`Cmd+K`) 가 모든 네비를 대체
- **KNK 적용 포인트**: 매출 매트릭스 5종 (대시·일별·월별·연간·고객별) 을 동일 패턴으로 — sticky 헤더 + 행별 status 칩 + 빠른 키보드 네비
- **참고**: 5라운드 CX17 (단일 액센트), CX21 (서체 위계) 의 진화형
- **위험**: 너무 차가워 보일 수 있음 → 따뜻한 액센트 1색 필요

### 02. Vercel Dashboard (https://vercel.com)
- **무드**: 모노 (흑·회·흰) + 가끔 보라 또는 핫핑크 액센트
- **핵심**: 배포 카드 = 상태점 + 커밋 메시지 + 시간 + sparkline. **노이즈 제로**
- **KNK 적용 포인트**: 매출 영업·자재 구매 카드를 "배포 상태" 처럼 — 아주 간결한 4줄 정보, 하나의 액센트 색
- **위험**: 흑백 일변도면 매거진톤 v4 와 차별화 모호 → 액센트 색 선택이 결정적

### 03. Stripe Dashboard (https://dashboard.stripe.com)
- **무드**: 보라 (#635BFF) + 차분한 흰 + 그라데이션
- **핵심**: 4-카드 KPI 패턴 = 숫자 + 추세 화살표 + sparkline (그게 다)
- **KNK 적용 포인트**: 메인 대시보드 상단을 **"이번 달 매출·전월비·주문건수·진행 중 견적"** 4-카드로 정리
- **위험**: 보라색 그대로면 핀테크 같음 → KNK는 KNK 레드(#A5282C) + 보라 톤다운으로 응용

### 04. Notion Sidebar (https://notion.so)
- **무드**: 종이 흰 + 검은 글자 + 미세한 회색 호버
- **핵심**: 접이식 그룹 네비 (워크스페이스 → 페이지 → 하위 페이지). 아이콘은 이모지·심볼 자유
- **KNK 적용 포인트**: 좌측 사이드바를 **"센터 → 매트릭스 → 페이지"** 3단 접이식으로 — 현재 구조와 호환성 우수
- **위험**: 서체 가독성 의존도 높음 → Pretendard 같은 한글 최적화 폰트 필수

### 10. HubSpot Role-based UI (https://hubspot.com)
- **무드**: 주황 + 흰 + 차분한 회색
- **핵심**: 같은 플랫폼이지만 **역할별 첫 화면 다름** — 영업은 파이프라인, 마케터는 캠페인, 관리자는 청구
- **KNK 적용 포인트**: 김 부장(영업), 이 차장(자재), 박 대리(물류) 가 로그인하면 **첫 화면이 다른** 권한별 분기. P2 분기 정책과 정합
- **위험**: 구현 복잡도 +30% → P2 단계로 미루는 옵션도

---

## B. 에디토리얼 진화형

### 06. Awwwards Renaissance Edition (Shopify Editorial)
- **무드**: 르네상스 회화 + 모던 이커머스 = "갤러리로 위장한 제품 쇼케이스"
- **핵심**: 150개 플랫폼 업데이트를 그림처럼 큐레이팅. **2026.02 Site of the Month**
- **KNK 적용 포인트**: 사용가이드·온보딩을 "월간 잡지" 형식으로 — v4 매거진톤 가이드의 진화형
- **위험**: 업무 시스템 메인 화면엔 과함 → 가이드·블로그·공지 영역 한정 권장

---

## C. 글래스·라이트닝 (2026 부활 트렌드)

### 11. Glassmorphism Fintech Dashboard
- **무드**: 반투명 + 블러 + 컬러풀 배경 + 흰 카드
- **핵심**: 핀테크 대시보드 골드 스탠다드. 데이터 풍부한 환경에서 **레이어 명확성** 제공
- **KNK 적용 포인트**: 빅터 AI 채팅창을 글래스 패널로 — 메인 화면 위에 떠있는 느낌
- **위험**: 너무 화려해 보일 수 있음 → 액센트 영역 한정 (전체 적용 X)

### 20. Apple Liquid Glass / Liquid Design (iOS 26)
- **무드**: 액체 같은 반사·광택·동적 흐름
- **핵심**: 2026 트렌드 #2 = Glassmorphism + Liquid의 부활 (Mohan Kumar S, Bootcamp)
- **KNK 적용 포인트**: 호버·클릭 인터랙션의 미세한 액체 애니메이션
- **위험**: 성능 부하 — 구형 PC 사용자 (KNK 영업소) 고려 필수

---

## D. 네오브루탈리즘 (대담한 차별화)

### 12. Neobrutalism Dashboard
- **무드**: 굵은 검은 테두리 + 파스텔 채도 + 그리드 + 약한 그림자
- **핵심**: AI가 만든 "슬릭한" 인터페이스의 의도적 반대. **"이건 진짜 사람이 만들었다"** 는 메시지
- **KNK 적용 포인트**: 사내 공지·이벤트·교육 페이지 한정 — 메인 시스템엔 모험
- **위험**: B2B 업무 시스템에 과한 캐릭터 → 부분 적용 권장

---

## E. 일본 미니멀 (Muji·Sony)

### 13. Muji Online Store (https://www.muji.com)
- **무드**: 순백 배경 + 단순 제품 사진 + 최소한의 텍스트
- **핵심**: **MA (間) — 사물 사이의 공간** 그 자체를 디자인. 바우하우스 + 젠
- **KNK 적용 포인트**: 빈 화면·빈 상태 (Empty State) 디자인의 정수 — "오늘 처리할 일이 없습니다" 를 미니멀하게
- **위험**: 그래픽 약하면 단조로움 → 한 줄의 강한 헤드라인 필요

### 14. Sony Pro Site (https://pro.sony)
- **무드**: 검은 배경 + 흰 글자 + 정밀 그리드
- **핵심**: 프로페셔널 = 침묵 + 정보 응축
- **KNK 적용 포인트**: 빅터 AI 화면을 Sony Pro 톤으로 — "AI는 조용히 일한다" 메시지
- **위험**: 너무 차가워 보임 → 따뜻한 액센트 필수

---

## F. 벤토 그리드 (Apple 발 — 2026 표준)

### 05. Apple iPhone 15 Pro Page (https://apple.com/iphone-15-pro)
- **무드**: 다크·고품·모듈식 직사각형
- **핵심**: 큰 타일(히어로) + 작은 타일(보조) 의 비대칭 그리드. **6개월 만에 모든 SaaS 대시보드가 모방**
- **KNK 적용 포인트**: 메인 대시보드를 벤토로 — 큰 타일에 "이번 달 매출", 작은 타일에 미수금·재고·일정
- **카드 수**: 12~15개 이내가 황금률 (그 이상은 인지 부하)

### 07. Datadog (https://datadoghq.com)
- **무드**: 보라 + 검은 + 데이터 시각화
- **핵심**: 실시간 운영 대시보드의 정수
- **KNK 적용 포인트**: 자재 입출고·재고 알림·물류 추적 영역

### 08. Mixpanel (https://mixpanel.com)
- **무드**: 흰 + 다채로운 차트
- **핵심**: 분석 모듈 카드. F-패턴 시선 활용
- **KNK 적용 포인트**: 매출 분석·트렌드·비교 영역

### 09. Amplitude (https://amplitude.com)
- **무드**: 보라·청록 + 인사이트 카드
- **핵심**: 사용자 흐름 시각화
- **KNK 적용 포인트**: 영업 파이프라인·견적→주문→발주 흐름

---

## G. 한국 엔터프라이즈

### 15. Toss Workplace (https://workplace.toss.im)
- **무드**: 청 (#3182F6) + 둥근 모서리 (16px+) + 친근한 일러스트
- **핵심**: 한국형 핀테크/B2B 표준. **bitjaru/styleseed 디자인 시스템에 Toss 브랜드 스킨 포함** (GitHub 화제)
- **KNK 적용 포인트**: 한국 직원 친숙도 ★★★★★ — 김 부장도 한 번에 이해
- **위험**: 너무 친근해서 "B2B 무게감" 부족 우려 → 헤더만이라도 무게감 추가

### 16. Naver Works (https://naver.worksmobile.com)
- **무드**: 녹 (#03C75A) + 흰 + 정돈된 그리드
- **핵심**: **2026.03 행안부·과기부·식약처 3개 부처 공식 협업 플랫폼 채택**. CSAP 인증
- **KNK 적용 포인트**: 정부·공공 신뢰감 — KNK가 향후 공공 진출 시 정합
- **위험**: 녹색 = 라인 메신저·네이버 인상 → 차별화 어려움

### 17. Naver Cloud Console
- **무드**: 어두운 녹 + 흰 + 기술적 정돈
- **핵심**: 한국 클라우드 1위, 카카오·네이버 같은 대형 서비스의 백엔드 UI
- **KNK 적용 포인트**: 관리자 페이지 (시스템 설정·권한·로그) 톤
- **위험**: 일반 사용자에겐 무거움

---

## H. 힐링 고급화 (녹색 탈피)

### 18. Earthy Wellness Palette
- **팔레트**: 클레이 + 세이지 + 테라코타 + 따뜻한 토프
- **핵심**: 자연 럭셔리. **유기적 럭셔리** 감각 (Haute Stock, The Brand Alchemists)
- **KNK 적용 포인트**: v1 sage 의 진화형 — 세이지 + 클레이 + 테라코타 3색으로 **"자연이지만 비싼"** 톤
- **위험**: 명도 대비 부족 → CTA·중요 정보의 가독성 보강 필수

### 19. Deep Teal + Dusty Rose
- **팔레트**: 깊은 청록 + 먼지장미 + 부드러운 복숭아
- **핵심**: **녹색 완전 탈피한 힐링** — 청록의 세련미 + 장미의 따뜻함 (Verô Branding, Tiffany Kenyon)
- **KNK 적용 포인트**: KNK 레드 는 청록의 보색 → CTA 강조 자연스러움. 빅터 AI 캐릭터에 분홍 액센트
- **위험**: 한국 B2B 시장에 분홍은 호불호 → 액센트 한정

---

## 🎯 빅터 1차 추천 — 대표 결재 후 v5 시안 제작

### Top 3 후보 조합

#### 옵션 A: **"Toss × Linear"** — 한국형 정밀 미니멀
- 베이스: Linear (모노 + 정밀)
- 모서리: Toss (16px 둥근 + 친근)
- 액센트: KNK 레드(#A5282C)
- 키워드: **신뢰·정밀·한국적 친근감**
- 김 부장도 첫 사용에 이해 ✅ / 매거진톤 v4 의 "차가움" 보완 ✅

#### 옵션 B: **"Apple Bento × Earthy Wellness"** — 모듈 힐링
- 베이스: 벤토 그리드 (12-15 카드)
- 톤: Earthy (세이지 + 클레이 + 테라코타)
- 액센트: KNK 레드
- 키워드: **모던·힐링·정보 풍부**
- 데이터 풍부한 영업·자재 화면에 적합 ✅ / 일러스트·아이콘 추가 제작 부담 ⚠️

#### 옵션 C: **"Muji × Stripe Dashboard"** — 침묵 속 데이터
- 베이스: Muji (순백·MA·여백)
- 데이터: Stripe (4-카드 KPI + sparkline)
- 액센트: KNK 레드 + 깊은 청록
- 키워드: **고요·고급·데이터 명료**
- 프리미엄 분위기 ✅ / 그래픽 약하면 단조로움 ⚠️

---

## 📋 다음 단계 (대표 결재 대기)

1. **대표 1차 선정**: 20선 중 ★ 표시 또는 위 A/B/C 옵션 선택
2. **v5 시안 제작**: 선정된 방향으로 PREVIEW 시안 3종 (메인·매출·로그인)
3. **대표 2차 검토**: PREVIEW 시안 보고 디테일 조정
4. **승인 시 _TO_01 발주서**: 정책 §4-A 30 grep 표준 적용
5. **이전 v4 CX23c 발주서 처리**:
   - 옵션 X: 폐기 (v5로 완전 교체)
   - 옵션 Y: 부분 보존 (벤토·구조 유지 + 톤만 v5 로 교체)

---

## 📎 첨부

- 본 README
- 후속 시안 폴더: `_04_v5_레퍼런스20선/PREVIEW_*` (대표 선정 후 제작)
- 이전 시안 보존: `_03_v4_탐색_6옵션/` (참고용)

---

## 📚 출처 (Sources)

### A. 미니멀 SaaS
- [7 SaaS UI Design Trends in 2026 — SaaSUI Blog](https://www.saasui.design/blog/7-saas-ui-design-trends-2026)
- [Dashboard Design Patterns for Modern Web Apps 2026 — Art of Styleframe](https://artofstyleframe.com/blog/dashboard-design-patterns-web-apps/)
- [Linear App Review 2026 — siit.io](https://www.siit.io/tools/trending/linear-app-review)
- [bitjaru/styleseed — GitHub (Toss·Stripe·Linear·Vercel·Notion 디자인 시스템)](https://github.com/bitjaru/styleseed)
- [10 Best SaaS Website Designs of 2026 — Azuro Digital](https://azurodigital.com/saas-website-examples/)

### B·F. 벤토·에디토리얼
- [Bento Grid Dashboard Design: Complete Guide 2026 — Orbix Studio](https://www.orbix.studio/blogs/bento-grid-dashboard-design-aesthetics)
- [Best Bento Grid Design Examples 2026 — Mockuuups Studio](https://mockuuups.studio/blog/post/best-bento-grid-design-examples/)
- [Sites Of The Year — Awwwards](https://www.awwwards.com/websites/sites_of_the_year/)
- [Editorial Layout — Awwwards](https://www.awwwards.com/inspiration/editorial-layout)
- [50 Best Dashboard Design Examples for 2026 — Muz.li](https://muz.li/blog/best-dashboard-design-examples-inspirations-for-2026/)

### C·D. 글래스·네오브루탈
- [UI Design Trend 2026 #2: Glassmorphism and Liquid Design Make a Comeback — Mohan Kumar S, Bootcamp](https://medium.com/design-bootcamp/ui-design-trend-2026-2-glassmorphism-and-liquid-design-make-a-comeback-50edb60ca81e)
- [Glassmorphism: What It Is and How to Use It in 2026 — Inverness Design Studio](https://invernessdesignstudio.com/glassmorphism-what-it-is-and-how-to-use-it-in-2026)
- [Brutalism vs Neubrutalism in UI Design — CC Creative](https://www.cccreative.design/blogs/brutalism-vs-neubrutalism-in-ui-design)
- [12 Product Design Trends for 2026 — UX Pilot](https://uxpilot.ai/blogs/product-design-trends)

### E. 일본 미니멀
- [Japanese Minimalism in UI Design for Digital Products — Fireart Studio](https://fireart.studio/blog/japanese-minimalism-in-ui-design-for-digital-products/)
- [Simplicity & Minimalism — An Introduction to Muji — sabukaru](https://sabukaru.online/articles/muji)
- [The Minimalist Aesthetics of Muji Products — Encyclopedia of Design](https://encyclopedia.design/2023/10/28/the-minimalist-aesthetics-of-muji-products-a-design-perspective/)

### G. 한국 엔터프라이즈
- [Naver Works Selected as Official Platform for Three Korean Ministries — Seoul Economic Daily 2026.03](https://en.sedaily.com/technology/2026/03/04/naver-works-selected-as-official-platform-for-three-korean)
- [Naver Cloud: Inside South Korea's Leading Cloud Platform — Medium / Ivan Porta](https://gtrekter.medium.com/naver-cloud-a-look-inside-the-south-koreas-leading-cloud-platform-63be6d529fef)
- [Naver D2SF-Backed Startups at CES 2026 — Korea Herald](https://www.koreaherald.com/article/10642726)

### H. 힐링·웰니스
- [Luxury Color Palettes for Wellness Brands — Haute Stock Blog](https://hautestock.co/luxury-color-palettes-for-wellness-brands/)
- [24 Aesthetic Colour Palettes for Soulful Brands — The Brand Alchemists](https://thebrandalchemists.com/blogs/news/holistic-brand-color-palettes-2025)
- [Best Color Palette for Health and Wellness — Verô Branding](https://www.verobranding.com/blog/color-palette-for-health-and-wellness)
- [The Color of Calm: Color Psychology in Wellness Web Design — Beautiful Brand And Web Design](https://marketingwiththeagency.com/the-color-of-calm-mastering-color-psychology-in-wellness-web-design/)
- [Branding Your Therapy Practice: 5 Color Palettes — Tiffany Kenyon Design](https://www.tiffanykenyondesign.com/blog-branding/color-palettes-therapy-practice)
- [2026 Web Design Color Trends — DIT Blog](https://www.designingit.com/blog/2026-web-design-color-trends/)

---

**발행**: 2026-04-29 · 05 디자인팀 빅터
**상태**: 🟡 **20선 큐레이션 완료 · 대표 1차 선정 대기**
**다음**: 대표 ★ 표시 또는 A/B/C 옵션 선정 → v5 PREVIEW 시안 3종 제작 시작
