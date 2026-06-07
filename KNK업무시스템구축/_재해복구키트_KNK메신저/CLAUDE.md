# CLAUDE.md — KNK 메신저 (이 파일은 Claude Code가 자동으로 읽습니다)

> **새 클로드에게:** 이 폴더는 ㈜케이엔케이(KNK) **사내 업무 메신저**의 전체 소스입니다.
> 이 문서 하나로 "이 프로젝트가 무엇이고, 어떻게 고치고, 어떻게 배포하고, 망가졌을 때
> 어떻게 되살리는지"를 즉시 파악할 수 있도록 만들었습니다. **먼저 이 문서를 끝까지 읽으세요.**
> 더 깊은 맥락(과거 결정 이유 등)은 `docs/프로젝트_히스토리.md` 에 있습니다.

---

## 0. 한눈에 (가장 중요한 것만)

| 항목 | 값 |
|---|---|
| 무엇 | 사내 전용 메신저 (실시간 채팅·프로젝트방·업무요청·파일공유·AI번역·푸시) |
| 기술 | Python **Flask** + **SQLite(WAL)** + **Socket.IO** / 설치형 웹앱(PWA) |
| 공개 주소 | **https://haist.knknara.co.kr/msg/** (BASE_PATH = `/msg`) |
| 운영 서버 | 사내 **Synology NAS** 도커 컨테이너 (외부 클라우드 미사용) |
| 코드 백업 | GitHub `git@github.com:top00151-commits/knk-messenger.git` (branch `main`) |
| 최고관리자(소유자) | **`top0015@knknara.co.kr`** (`app.py` `OWNER_USERNAME`) |
| 핵심 파일 | `app.py`(서버) · `static/js/app.js`(클라이언트) · `static/js/i18n.js`(다국어) · `templates/chat.html` |

---

## 1. 배포 방법 (코드 고친 뒤 반영하는 법)

표준 순서는 **수정 → 커밋 → 배포 → GitHub 백업** 입니다.

```powershell
# 1) 커밋
git add <고친파일>
git commit -m "설명"

# 2) 프로덕션(NAS)에 배포  ← 반드시 이 스크립트로
& "deploy\sync_to_synology.ps1"

# 3) GitHub 백업
git push origin main
```

- 배포 스크립트가 파일 업로드 → 컨테이너 재시작 → `/healthz` 200 확인까지 자동 수행합니다.
- 읽기 전용 진단만 하려면: `& "deploy\sync_to_synology.ps1" -Diag` (업로드·재시작 안 함)
- **`-ExecutionPolicy Bypass` 붙이지 마세요.** 그냥 위처럼 실행합니다.

## 2. 절대 지켜야 할 안전 규칙 (위반 금지)

1. **비밀값을 화면에 출력(echo/print)하지 말 것** — 특히 `$env:KNK_NAS_KEY`, `$env:KNK_NAS_PASSWORD`. 존재 여부만 확인하고 값은 절대 표시 금지.
2. **프로덕션 SSH 직접 접속(`root@o.knknara.co.kr`)으로 읽기/쓰기는 사용자 명시 승인 후에만.** 평상시 배포는 위 스크립트로만.
3. **`deploy/reset_beta_data.py` 는 명시적 지시 전까지 절대 실행 금지** (베타 데이터 초기화 — 위험).
4. **사용자 대신 `gh auth login` / 계정 생성 / 비밀번호 입력 금지.**
5. **지시 받으면 즉시 착수 금지 → 먼저 이해한 내용을 정리해 보고하고, 확인받은 뒤 진행** (대표 직접 지시, 절대준수).
6. 파일 생성·수정은 `KNK업무시스템구축\` 폴더 내부에서만.

## 3. 운영 구조 & 장애 주의

- 컨테이너 안: **nginx + cron + knk-messenger(gunicorn eventlet, single worker, 5050)** 를 **supervisord** 가 관리.
- ⚠️ **컨테이너 PID 1 = bash** (supervisord 아님). 과거 supervisord 데몬이 죽어 502 장애 발생 → 아무도 안 살려서 영구 다운된 사례 있음.
  - 재발 방지: 배포 스크립트에 supervisord 자동 재기동 분기 추가됨 + nginx autostart=true.
  - 외부 워치독(`deploy/nas_watchdog.sh`)을 DSM 작업 스케줄러에 등록하는 것이 근본 대비책 (전산 담당자 작업).
- 설치 경로(NAS): `/opt/knk_messenger`. **소스코드는 GitHub 와 NAS 양쪽에 모두 존재**합니다.

## 4. 망가졌을 때 되살리기 (재해 복구)

PC를 포맷했거나 새 PC/새 클로드에서 시작할 때:

```powershell
# 저장소를 받은 폴더에서 1줄 실행 → 무엇이 준비됐고 무엇이 빠졌는지 점검·안내
& "deploy\recover_setup.ps1"
```

이 스크립트가 Git 설치·저장소·필수 환경변수(NAS 접속·배포키)의 **존재 여부만** 점검하고(값은 안 봄),
빠진 것을 어떻게 채우는지 안내합니다. 비밀값 3~4개는 보안상 **사람이 직접** 입력해야 하며, 그 뒤로는 자동입니다.
자세한 복구 절차·체크리스트는 스크립트 출력과 `docs/프로젝트_히스토리.md` 참고.

## 5. 사람 친화 한글 용어 (UI 문구 작성 시)

화면·메뉴는 쉬운 한글로. 영문 약어·기술용어를 그대로 노출하지 말 것 (예: 워크플로우→"일 순서", 노드→"일"). 외부 상용 제품명은 UI/코드/문서에 직접 거론 금지(중립 명칭 사용).

## 6. 다국어 (i18n)

- `static/js/i18n.js` 의 `I18N = {ko, vi, en}` 딕셔너리 + `window.KNK_t(key)`.
- HTML: `data-i18n`(텍스트) / `data-i18n-html`(innerHTML) / `data-i18n-ph`(placeholder) / `data-i18n-title`(title).
- **세 언어 키 개수가 항상 동일해야 함** (배포 전 키 패리티 검증).
- 브라우저 자동번역 끄기 위해 `<html translate="no">` + `<meta name="google" content="notranslate">` 필수 (베트남어가 "베트남사람" 으로 오역된 버그 있었음).
