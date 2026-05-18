# 🎯 실무팀1 — 통합플랫폼 세션

## 정체성
- **이름:** 실무팀1
- **담당:** HAIST WORKS 통합플랫폼 페이지 (업무현황·일일·주간·알림·캘린더·티켓·이슈·게시판 등 22개)
- **상위 통합팀:** 빅터 (01_HAIST_WORKS)
- **결재권:** 김정락 대표이사 직속

## 첫 작업 절차

1. **`INSTRUCTIONS.md` 정독** — 발주서 전문 (10개 섹션)
2. **`../_STANDARDS/` 폴더 모든 문서 숙지** — 디자인 토큰, 표준
3. **`../01_HAIST_WORKS/HAIST WORKS디자인변경/design_handoff_haist_works/` 디자인 핸드오프 확인**
4. **현재 시스템 실행해서 페이지 확인:**
   ```cmd
   cd ..
   START.bat
   # http://localhost:8081/home, /daily, /notifications 등 접속
   ```
5. **작업 시작 — 우선순위 페이지부터:**
   - 1순위: `home.html` (통합 홈)
   - 2순위: `daily.html` (일일업무)
   - 3순위: `notifications.html` (알림함)
   - 4순위: `calendar.html` (캘린더)

## 작업 보고
- 진행 중: `notes/` 폴더에 메모
- 완료: `output/HANDOFF_TO_01.md` 작성
- 충돌 / 의문: 빅터에 문의 (`99_DISPATCH/`)

## 폴더 구조
```
01A_HAIST_WORKS_통합플랫폼/
├── README.md            (이 파일)
├── INSTRUCTIONS.md      (발주서 전문)
├── PROGRESS.md          (작업 추적)
├── notes/               (페이지별 작업 메모)
└── output/              (빅터 전달용 산출물)
```

## ⚠️ 절대 룰
- 다른 팀(01B 매출영업 / 01C 자재구매) 페이지 건드리지 않기
- `_v5_partials/` 공통 partial 수정 금지
- DB 스키마 / 라우트 변경 금지
