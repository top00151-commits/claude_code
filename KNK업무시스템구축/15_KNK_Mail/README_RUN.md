# KNK Eum MAIL — 독립 앱 실행 안내 (골격 / Phase 1)

WORKS와 **완전 분리**된 별도 메일 앱입니다. 자체 DB(`data/mail.db`)·자체 세션·메신저 SSO.

## 로컬 실행 (개발)

```powershell
cd 15_KNK_Mail
pip install -r requirements.txt
$env:KNK_MAIL_DEV_LOGIN = "1"   # 로컬 개발 로그인 우회(운영 금지)
python run.py                    # → http://127.0.0.1:8201
```

- `http://127.0.0.1:8201/healthz` → DB·테이블 상태 점검(JSON)
- `http://127.0.0.1:8201/` → 로그인(개발 로그인) → 받은편지함(독립 DB 조회)

## 주요 환경변수 (운영은 NAS `.env`)

| 변수 | 용도 | 기본 |
|---|---|---|
| `KNK_MAIL_DB` | 메일 DB 경로 | `data/mail.db` |
| `KNK_MAIL_DATA` | 데이터/첨부 폴더 | `15_KNK_Mail/data` |
| `KNK_MAIL_SESSION_SECRET` | 세션 서명키 | (운영 필수 변경) |
| `KNK_MAIL_SSO_AUDIENCE` | 메신저 SSO audience | `knk-mail` |
| `KNK_SSO_SERVICE_KEY` | 직원명부 동기화 서버키 | (메신저와 공유) |
| `KNK_MAIL_KEY` | 가져오기 비번 암호화(Fernet) | (없으면 키파일 자동) |
| `KNK_MAIL_DEV_LOGIN` | 로컬 로그인 우회 | `0`(off) |
| `KNK_MAIL_HTTPS_ONLY` | 세션쿠키 Secure | `0` |

## 진행 단계

- **Phase 1(골격)**: 앱 기동·DB 스키마·세션/헬퍼·독립 레이아웃·기본 메일함 ← 현재
- Phase 2: 메일 모듈(store/send/fetch)·47 라우트·실제 템플릿·AI·첨부 이식
- Phase 3: repo·배포 문서·전산담당자/메신저 요청서
- Phase 4: 전환(WORKS에서 메일 라우트 제거 + 새 주소 연결)

> 설계서: `01_HAIST_WORKS/작업기록/작업기록_2026-06-14_메일_독립분리_설계서_별도DB_새주소.md`
