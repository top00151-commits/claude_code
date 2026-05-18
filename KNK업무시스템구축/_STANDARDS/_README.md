# 📐 _STANDARDS/ — 전 팀 공통 표준 가이드라인

> 모든 실무팀이 절대 준수해야 하는 표준. 임의 변경 금지.

## 📂 문서 인덱스

### 🎨 디자인 표준
- `디자인_의뢰서_HAIST_WORKS_v1.md` — 시각·UX 의뢰서 (Claude Design 입력값)
- `_TEAM_ORIENTATION.md` — 전 팀 오리엔테이션 (목표·역할·결재 라인)
- `_TEAM_ORIENTATION_root.md` — 루트 레벨 오리엔테이션 (옛판)
- `04_운영테스트팀_핸드오프_2026-04-23.md` — 운영테스트팀 인수인계
- `HAIST_WORKS_*.md` — 설계분석/설문/심화리서치 (참고)

### 💻 코드 표준
- `_INDEX_코드구조.md` — 폴더/모듈 구조 인덱스
- `_DEPLOY_배포_가이드.md` — 배포 절차
- `_RUN_사용자_매뉴얼.md` — 사용자 매뉴얼

## 🎯 주요 토큰 (현재 적용)

### 컬러 (Quiet Tone v3 — v5H226z51)
```
--qv-surface:    #ffffff   (카드 / 페이지헤드 배경)
--qv-surface-2:  #f7f8fa   (본문 배경, 호버)
--qv-surface-3:  #eef0f4   (헤더 배경, dim 강조)
--qv-line:       #eef0f4   (옅은 보더)
--qv-line-2:     #e2e8f0   (입력창 보더)
--qv-line-3:     #cbd5e1   (강조 보더)
--qv-ink:        #0f172a   (제목, mgmt-no, KPI 값)
--qv-ink-2:      #334155   (본문)
--qv-ink-3:      #64748b   (메타)
--qv-ink-4:      #94a3b8   (비활성)

--knk-red:       #a5282c   (KNK 빨강 - 로고/빅터/CTA/위험만)
```

### 사업부 컬러
```
--biz-t: #c2410c   (검사기, T)
--biz-m: #1e40af   (자동화, M)
--biz-e: #6d28d9   (기타, E)
--biz-c: #047857   (소모품, C)
```

### 간격 / 라운드 / 그림자
```
--space-1~9: 4/8/12/16/20/24/32/40/48 px
--radius: sm 6 / md 10 / lg 14 / xl 20 / pill 999
--shadow-1: 0 1px 2px rgba(15,23,42,0.04), 0 1px 3px rgba(15,23,42,0.06)
```

### 타이포
- 본문 폰트: Pretendard / Segoe UI / Malgun Gothic
- 숫자/코드: monospace tabular-nums
- 본문 14px / 라벨 12px / 제목 24px

## 🚫 절대 금지 (전 팀 공통)

1. ❌ chrome.html 구조 변경 (사이드바/탑바)
2. ❌ DB 스키마 변경 (`data/knk.db`)
3. ❌ 라우트 URL 변경
4. ❌ Jinja 변수명 변경
5. ❌ 메뉴 코드(M-XX-XX) 변경
6. ❌ 권한 분기 (`{% if user.is_admin %}`) 변경
7. ❌ 외부 라이브러리 추가 (Tailwind, jQuery 등)
8. ❌ 타사 브랜드 자산 직접 사용

## 🔍 디버그 모드

URL에 `?debug=1` 추가 또는 `Ctrl+Shift+D` 단축키 → 영역명 + 크기 표시
- 빅터-각 팀 의사소통 시 영역명 그대로 사용 (예: "kpi-bar 높이 줄여")

## 📝 변경 절차

표준 변경이 필요하면:
1. 변경 사유 + 영향 범위 + 대안 정리해서 빅터(01)에게 제안
2. 빅터 → 대표 결재
3. 결재 후 빅터가 이 폴더 문서 갱신
4. 갱신 후 전 팀 통보 (`99_DISPATCH/` 채널)
