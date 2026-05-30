# [05 디자인팀 → 01 메인] Pretendard 번들링 가이드 #01

> **발신**: 05 디자인팀 세션 빅터
> **수신**: 01 메인 세션
> **일자**: 2026-04-21
> **대표 승인**: "그렇게 해" (2026-04-21) — Pretendard 번들링 선택 (A) 확정
> **상위 정책**: `05_HAIST_WORKS_디자인팀/04_라이선스_상표권_정책.md` §1-4

---

## 1. 왜 번들링하나

- 직원 PC 에 Pretendard 설치 유무에 관계없이 **모든 사람이 동일 화면**을 봄
- 공장·출장·회선 약한 환경에서도 **외부 CDN 호출 없이** 즉시 렌더
- SIL OFL 1.1 이 허용하는 범위 내 (상업 사용 OK, LICENSE 동봉만 하면 끝)

## 2. 01 세션 적용 절차 (5 단계)

### Step 1 — 폴더 생성
```
01_HAIST_WORKS/
└── static/
    └── fonts/              ← 신규 생성
```

### Step 2 — 폰트 파일 다운로드

Pretendard 공식 저장소의 최신 릴리스에서 **Variable 폰트 1개**만 받으면 weight 400/600/800 모두 커버됨.

- **공식 소스**: https://github.com/orioncactus/pretendard/releases (latest release 의 `Pretendard-x.x.x.zip`)
- **필요 파일 2개**:
  1. `PretendardVariable.woff2` (약 200KB, variable font)
  2. `OFL.txt` (라이선스 원문, 약 4KB)
- **배치 위치**: `static/fonts/` 아래 그대로.

다운로드 대안 (zip 내려받기 싫으면 개별 raw 링크):
- `https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/web/variable/woff2/PretendardVariable.woff2`
- `https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/OFL.txt`

### Step 3 — CSS @font-face 선언 추가

`static/style.css` **파일 최상단** (기존 CSS 앞에) 아래 블록을 붙여 주세요:

```css
/* ==========================================================
   Pretendard Variable — SIL OFL 1.1
   https://github.com/orioncactus/pretendard
   License file: static/fonts/OFL.txt
   ========================================================== */
@font-face {
  font-family: "Pretendard Variable";
  font-weight: 45 920;       /* variable range */
  font-style: normal;
  font-display: swap;         /* 로딩 중에도 폴백으로 먼저 그려 UX 끊김 방지 */
  src: url("/static/fonts/PretendardVariable.woff2") format("woff2-variations");
}
```

그리고 기존 CSS 의 `body` 또는 루트 폰트 선언을 아래 폴백 체인으로 통일:

```css
:root {
  --font-family: "Pretendard Variable", "Pretendard",
                 system-ui, -apple-system, "Segoe UI", Roboto,
                 "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
}

html, body, input, button, textarea, select {
  font-family: var(--font-family);
}
```

### Step 4 — 프로젝트 루트 `LICENSE` 파일 생성

`01_HAIST_WORKS/LICENSE` 파일을 생성하고, 본 핸드오프 함께 전달되는 `LICENSE_sample.txt` 내용을 그대로 복사해 주세요.

### Step 5 — 버전 캐시 무효화

`base.html` 상단 CSS 링크의 쿼리 버전을 증가:
```html
<link rel="stylesheet" href="/static/style.css?v=20260421pretendard">
```

---

## 3. 용량 · 성능 영향

- `PretendardVariable.woff2`: 약 **200KB**. 첫 페이지 로드 1회만 전송, 이후 브라우저 캐시.
- 현재 `/cockpit` 100KB 대비 2배지만, **캐시·gzip·font-display:swap** 조합으로 체감 느림 없음.
- 외부 CDN 호출 0건 → 네트워크 신뢰성·개인정보 유출 걱정 없음.

---

## 4. 검증 기준

적용 완료 후 아래 4가지 확인:
- [ ] Windows PC (Pretendard 미설치) 에서 로그인·홈 화면 글씨가 **Pretendard로** 보임
- [ ] `/cockpit`, `/changes`, `/admin` 도 동일하게 Pretendard
- [ ] F12 개발자 도구 Network 탭에서 `googleapis`·`cdnjs` 등 **외부 도메인 호출 0건**
- [ ] 프로젝트 루트 `LICENSE` 파일 존재 · `static/fonts/OFL.txt` 존재

---

## 5. 5 세션 수용 범위 회신 양식

- [ ] 가이드대로 번들링 완료 (커밋 해시 기재:           )
- [ ] 부분 수용 (어떤 Step 생략 기재)
- [ ] 보류 (사유:           )
- [ ] 추가 질문 (아래 자유 기재)

**회신 위치**: `05_HAIST_WORKS_디자인팀/_FROM_01_Pretendard응답_01.md`

---

**발행**: 2026-04-21 · 05 디자인팀 세션 빅터
**첨부**: `LICENSE_sample.txt` (본 폴더 내), `fonts_font-face_snippet.css` (본 폴더 내)
