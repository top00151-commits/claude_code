# KNK Eum MAIL — NAS 배포 런북 (전산담당자용 · 그대로 따라 하기)

독립 메일 앱을 메신저처럼 **별도 주소·별도 프로세스**로 가동합니다.
> ⚠ **메일주소·MX 무관** — 새로 만드는 건 웹 접속용 서브도메인 1개뿐. `@knknara.co.kr` 메일 라우팅은 건드리지 않습니다.

## 0. 코드 받기 (둘 중 하나)
- **(권장) 메일 전용 repo**: `git clone <메일 repo> /volume1/web/knk-eum-mail`
- **(repo 없으면) 모노레포 경로 사용**: 기존 백업 repo `claude_code` 의
  `KNK업무시스템구축/15_KNK_Mail/` 를 `/volume1/web/knk-eum-mail` 로 배치
- 갱신: WORKS 와 동일하게 1분 cron `git -C /volume1/web/knk-eum-mail pull` → 변경 시 supervisor restart

## 1. 파이썬 의존성
```sh
cd /volume1/web/knk-eum-mail
python3 -m pip install -r requirements.txt
```

## 2. 환경설정
```sh
cp deploy/.env.example deploy/.env
# deploy/.env 편집: SESSION_SECRET(무작위)·KNK_SSO_SERVICE_KEY(메신저 공유키)·KNK_MAIL_KEY·AI키
```
- `KNK_MAIL_DATA`/`KNK_MAIL_DB` = 영구 볼륨 경로 (백업 대상에 포함)

## 3. 프로세스 등록 (supervisor — 메신저와 동일 방식)
- `deploy/supervisor_knk-eum-mail.conf` 의 경로를 실제 경로로 수정 → supervisor 설정에 추가
- `supervisorctl reread && supervisorctl update && supervisorctl start knk-eum-mail`
- 점검: `curl http://127.0.0.1:8201/healthz` → `{"ok": true, ...}`

## 4. 새 서브도메인 + SSL + 리버스프록시 (DSM)
1. **DNS**: `mail.knknara.co.kr` → NAS 공인 IP (A/CNAME). *기존 메일 DNS와 충돌 없는 이름인지 확인 — 필요 시 `eummail.` 등 대체*
2. **SSL**: DSM 제어판 → 보안 → 인증서 → `mail.knknara.co.kr` 발급/지정
3. **리버스프록시**: DSM 제어판 → 로그인 포털 → 고급 → 리버스 프록시 → 추가
   - 소스: `https` / `mail.knknara.co.kr` / 443
   - 대상: `http` / `localhost` / `8201`
   - (큰 첨부 대비) 사용자 정의 헤더/본문 크기 제한 충분히

## 5. 최종 점검
- `https://mail.knknara.co.kr/healthz` → `{"ok": true}`
- 로그인(`/login` → KNK Eum 메신저 SSO)은 **메신저 측 SSO 등록 완료 후** 동작
  (→ `작업기록_2026-06-14_메일독립_메신저SSO_요청서.md`)

## 6. 안전
- `deploy/.env` 는 git 에 안 올라갑니다(비밀값 보호). 백업만 별도 보관.
- `KNK_MAIL_DEV_LOGIN` 은 운영에서 **반드시 0**.
- 메일 DB(`mail.db`)·첨부(`data/`)를 NAS 정기백업 대상에 포함.

> 연계 문서: `작업기록_2026-06-14_메일독립_전산담당자_요청서.md`(요약) · 본 런북(상세 절차)
