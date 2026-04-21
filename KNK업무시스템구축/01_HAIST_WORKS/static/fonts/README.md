# Pretendard 폰트 번들 — 사용자 작업 안내

## 다운로드 필요 (1회)

이 폴더에 다음 2개 파일을 배치해 주세요:

### 1. `PretendardVariable.woff2`
- **다운로드**: https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/web/variable/woff2/PretendardVariable.woff2
- 약 200KB

### 2. `OFL.txt`
- **다운로드**: https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/OFL.txt
- 약 4KB (라이선스 원문)

## 또는 zip 일괄 다운로드

https://github.com/orioncactus/pretendard/releases (latest release의 `Pretendard-x.x.x.zip` 받아서 위 2개 파일만 추출)

## 검증

배치 후 브라우저 F12 → Network 탭에서:
- `PretendardVariable.woff2` 200 OK 응답
- 외부 도메인 호출 0건

## 미배치 시

`.woff2` 파일이 없어도 시스템 폰트(맑은 고딕, Segoe UI 등)로 자동 폴백 — **앱 동작은 정상**.
다만 직원 PC 별로 화면 글꼴이 다르게 보일 수 있음.

## 라이선스

SIL OFL 1.1 — 상업 사용 허용. `OFL.txt` 동봉 의무 (이 폴더에 함께 배치).

---
**근거**: `05_HAIST_WORKS_디자인팀/_세션01_전달/_TO_01_Pretendard번들링가이드_01.md`
**대표 승인**: 2026-04-21 "그렇게 해" (옵션 A 번들링 확정)
