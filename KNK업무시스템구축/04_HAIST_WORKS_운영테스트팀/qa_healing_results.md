
## S1-A 매출 KPI 권한 분기


### CEO kjr (`kjr` role=ceo)
- `/home` → 200 | final=/home
- 매출 키워드 노출: `{'₩': 0, '매출': 4, 'monthly_revenue': 0, 'yoy_delta': 0, '이번 달 매출': 0, '억': 0, '🔒': 1, '경영진': 2}`
- 기대: ₩금액 노출 + 🔒뱃지. 결과: **🔴 FAIL**
- `/dashboard` 직접 접근 → 200 | final=/dashboard
  CEO 정상 접근 기대 → 🟢 PASS

### 팀장 정성진 (`정성진` role=leader)
- `/home` → 200 | final=/home
- 매출 키워드 노출: `{'₩': 0, '매출': 3, 'monthly_revenue': 0, 'yoy_delta': 0, '이번 달 매출': 0, '억': 0, '🔒': 0, '경영진': 1}`
- 기대: 매출 금액 미노출. 결과: **🟢 PASS**
- `/dashboard` 직접 접근 → 200 | final=/team
  비경영진 차단 기대 → 🟢 PASS

### 평직원 마준영 (`마준영` role=member)
- `/home` → 200 | final=/home
- 매출 키워드 노출: `{'₩': 0, '매출': 3, 'monthly_revenue': 0, 'yoy_delta': 0, '이번 달 매출': 0, '억': 0, '🔒': 0, '경영진': 1}`
- 기대: 매출 금액 미노출. 결과: **🟢 PASS**
- `/dashboard` 직접 접근 → 200 | final=/home
  비경영진 차단 기대 → 🟢 PASS

## S1-B 빅터 도크 포지셔닝


홈 페이지 빅터 도크 마크업 검사 (CEO 시점):
- `class="...dock..."` 매치 수: 24 종
  예시: ['class="dock-welcome"', 'class="dock-tab"', 'class="dock"', 'class="dock-head"', 'class="dock-head-row"']
- `.dock-tab` 발견: 1 (기대 0건 — 미수정 시 0보다 큼)
- inline `.dock { position: fixed }` 패턴: 0 건 (기대 0)
- 🤖/빅터/Victor 키워드: 42
- Ctrl+K 단축키 안내: True
- 헤더 사용자칩·로그아웃: True

## S3 i18n 회귀 (3종 언어 + 중국어 부재)


홈 페이지 내 언어 옵션 마크업: [('ko', '🇰🇷 한국어'), ('vi', '🇻🇳 Tiếng Việt'), ('en', '🇺🇸 English'), ('vi', '🇻🇳 베트남어'), ('en', '🇺🇸 영어'), ('ko', '🇰🇷 한국어'), ('ja', '🇯🇵 일본어'), ('zh-CN', '🇨🇳 중국어')]
- lang=ko 적용 후 핵심 라벨: {'업무현황': 2, '내 계정': 1, '로그아웃': 1}
- lang=vi 적용 후 핵심 라벨: {'Công việc': 3, 'Tài khoản': 1, 'Đăng xuất': 1}
- lang=en 적용 후 핵심 라벨: {'Overview': 1, 'My Account': 1, 'Logout': 1}
- 중국어 옵션 존재 여부: 🔴 FAIL — 부적절 노출

## S2 힐링 톤 시간대 인사말·페르소나 인상

홈 인사말 키워드: {'오늘도 평안': 0, '안녕하세요': 0, '좋은 아침': 0, 'Good': 0, 'Xin chào': 0, '오늘 하루도': 0}
힐링 토큰 키워드: {'sage': 4, 'Sage': 0, '#7A9A7E': 0, 'healing': 1, '힐링': 0, 'amber': 0, '앰버': 0}