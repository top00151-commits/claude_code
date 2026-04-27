# 작업 카드 — Pretendard 폰트 파일 다운로드 및 배치

> **작업자**: 직원 1명 (아무나 PC 앞에 앉은 사람)
> **소요 시간**: 약 5~10 분
> **난이도**: ⭐ (클릭 + 복사 + 붙여넣기만)
> **사전 승인**: 김정락 대표 (2026-04-21, SIL OFL 1.1 상업 사용)
> **관련 자산 라이선스**: Pretendard = SIL Open Font License 1.1 (무료 상업 사용 허용)

---

## 준비물

- Windows PC + 웹브라우저 (Chrome/Edge 등)
- 프로젝트 폴더 접근 권한: `C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS\`

---

## 단계

### Step 1. 폰트 파일 다운로드 (1파일)

아래 링크를 브라우저 주소창에 **통째로 붙여넣고 Enter**:

```
https://github.com/orioncactus/pretendard/releases/latest
```

→ 최신 Release 페이지가 열림 → 스크롤 내려 **Assets** 항목 확인.

다운로드할 파일 (하나만):
- **`Pretendard-x.x.x.zip`** (숫자가 가장 큰 최신 버전의 zip 파일)

클릭 → 다운로드 시작 → 끝.

### Step 2. 압축 풀기

다운로드된 `Pretendard-x.x.x.zip` 을 **우클릭 → 압축 풀기** (알집이든 윈도우 기본이든 OK).

압축이 풀린 폴더 안에서 다음 2개 파일만 찾습니다:

1. **`web/variable/woff2/PretendardVariable.woff2`** (약 200KB)
2. **`packages/pretendard/OFL.txt`** (약 4KB) — 폴더 경로가 다를 수 있음. OFL.txt 또는 LICENSE 유사한 이름의 파일 찾으면 됨.

### Step 3. 파일 배치

아래 폴더로 이동:
```
C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\01_HAIST_WORKS\static\fonts\
```

- 폴더가 없으면 **폴더 생성** (`fonts` 이름으로).
- 여기에 Step 2 의 **2개 파일을 복사·붙여넣기**.

최종 상태:
```
01_HAIST_WORKS/
  static/
    fonts/
      PretendardVariable.woff2   ← 이 파일
      OFL.txt                    ← 이 파일
      README.md                  ← 이미 있음 (그대로 둠)
```

### Step 4. 확인

1. 서버 재시작 (배치 파일 `START.bat` 더블클릭 또는 기존 서버 창 닫고 다시 열기).
2. 브라우저에서 `http://localhost:8081` 접속 → 로그인.
3. 화면 글씨가 **Pretendard 폰트로 보이면 성공**. (맑은 고딕보다 살짝 더 모던·얇음)
4. 더 확실하게: **F12 누르기 → Network 탭 → Ctrl+R 새로고침 → `PretendardVariable.woff2`** 파일이 목록에 나오면 성공.

### Step 5. 끝!

- 외부 CDN 호출 없음 (네트워크 차단 공장·출장에서도 OK)
- 모든 직원 PC 에서 같은 글씨체로 통일
- 다음 서버 재시작·배포 때 자동으로 계속 적용됨

---

## 문제가 생기면

| 증상 | 원인 | 해결 |
|---|---|---|
| 글씨가 Pretendard 로 안 바뀜 | 브라우저 캐시 | Ctrl+Shift+R (강제 새로고침) |
| F12 Network 에 `PretendardVariable.woff2` 404 | 파일 위치 틀림 | Step 3 경로 재확인 |
| 압축 해제 후 `PretendardVariable.woff2` 가 없음 | 다운받은 버전에 variable 폰트 미포함 | 다른 버전의 zip 시도 또는 디자인팀에 문의 |
| 파일 이름이 대소문자 다름 (PretendardVariable.WOFF2 등) | 윈도우는 대소문자 무시하지만 일부 서버는 구분 | 소문자로 통일 권장 |

---

## 기술 메모 (직원 무시해도 됨)

- 이미 `static/style.css` 최상단에 `@font-face` 선언돼 있음 (01 세션이 적용 완료)
- `font-display: swap` 덕분에 파일 배치 **전에도** 앱은 시스템 폰트로 정상 동작
- LICENSE 파일 (`01_HAIST_WORKS/LICENSE`) 에 Pretendard SIL OFL 1.1 고지 이미 포함

---

## 완료 보고

작업 끝나면 대표님 또는 05 디자인팀에게 한 줄만:

> "Pretendard 배치 완료 — `static/fonts/` 에 2파일 넣고 서버 재시작, 글씨체 적용 확인."

---

**작성**: 05 디자인팀 세션 빅터
**일자**: 2026-04-24
**원 출처**: `_TO_01_Pretendard번들링가이드_01.md` Step 2 (사용자 작업 위임분)
