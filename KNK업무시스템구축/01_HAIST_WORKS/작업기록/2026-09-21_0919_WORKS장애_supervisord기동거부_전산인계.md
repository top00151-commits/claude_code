# WORKS 접속 불가 (2026-09-21 07:31~08:43) — 원인·조치·남은 일 (전산 인계)

- **작성**: 2026-09-21 (월) 09:19 KST
- **대상**: 전산 담당자
- **현재 상태**: ✅ **서비스 정상**(08:43 복구). 단 **자동 복구 장치가 반쪽** — 아래 §5 한 번만 해 주시면 끝납니다.

---

## 1. 한 줄 요약

**월요일 새벽 백업 뒤 컨테이너가 재시작됐는데, supervisor 설정에 이미 없어진 앱 두 개(메일·메신저)가 남아 있어 프로세스 관리자(supervisord)가 아예 기동을 거부했고, 그 바람에 WORKS까지 뜨지 못했습니다.**
백업이 무엇을 바꾼 것이 아니라, **재시작할 때만 드러나는 문제**가 약 한 달 전부터 잠겨 있었습니다.

## 2. 무슨 일이 있었나 (시간순 · 로그 근거)

| 시각 | 일어난 일 | 근거 |
| --- | --- | --- |
| 09-20 23:58:14 | WORKS 배포 후 **정상 기동** | `supervisord.log` 「knk-works entered RUNNING state」 |
| ~09-21 07:20:06 | 앱이 **7시간 22분 정상 서비스** | `logs/uvicorn.log` 마지막 기록 |
| 02:00~07:30 | 월요일 정기 NAS 백업 시간대 | 운영 기준 |
| **07:31:14** | **컨테이너 자체 재시작** | `ps -o lstart -p 1` = Mon Sep 21 07:31:14 |
| 07:31:16 | 포털(PM2)·nginx 등은 기동 · **supervisord는 기동 거부** | `ps` · supervisord 부재 |
| 07:35:44~07:43:39 | 워치독이 6회 복구 시도 → 모두 실패 → 「DEGRADED(관찰만)」 | `logs/watchdog.log` |
| 08:38 | 대표님 신고(화면: Synology 「페이지를 발견하지 못했습니다」 = 502) | — |
| **08:43** | WORKS 직접 기동 → **복구** | 외부 `GET /api/version` 200 |
| 08:44:55 | 워치독 「생존확인 정상 회복」 | `logs/watchdog.log` |

## 3. 진짜 원인

supervisord 가 기동할 때 낸 오류(워치독 로그에 6회 기록):

```
Error: The directory named as part of the path /opt/knk_mail/logs/uvicorn.log
       does not exist in section 'program:knk-mail'
       (file: '/etc/supervisor/conf.d/knk-mail.conf')
```

- `/opt/knk_mail` 과 `/opt/knk_messenger` **폴더가 통째로 없습니다.**
  (메신저는 이미 **별도 컨테이너(32202·5052)** 로 옮겨졌고, 이 컨테이너에는 **설정만 남아** 있었습니다)
- supervisord 는 설정에 적힌 **로그 경로가 하나라도 없으면 전체 기동을 거부**합니다.
  → `knk-works`(WORKS)·`nginx`·`cron` 까지 함께 못 뜹니다.
- **왜 하필 오늘**: 컨테이너 재시작이 **2026-08-17 06:31 이후 오늘이 처음**(35일 만)이었습니다.
  그 사이 두 폴더가 사라져 **다음 재시작 때 터질 지뢰**가 놓인 상태였습니다.
  (`logs/watchdog.log` 의 「watchdog 시작」 기록으로 재시작 이력 확인: 07-20 · 07-27 · 08-03 · 08-10 · 08-17 · **09-21**)

**전날 WORKS 배포와는 무관합니다.** 배포된 앱은 23:58 정상 기동해 07:20까지 서비스했고, 변경 파일은 WORKS 화면·`main.py`·시작 BAT 뿐입니다(supervisor 설정·메일·메신저 폴더 무접촉).

## 4. 제가 이미 한 조치

1. **WORKS 직접 기동**(08:41:13, pid 2286) — supervisord 가 쓰는 것과 **완전히 같은 스크립트**
   `/opt/knk_haist/.venv/bin/run_knk_works.sh` 를 `nohup` 으로 실행. 현재 5051 정상 대기 중, uvicorn **1개만** 떠 있음(중복 없음).
2. **빠진 로그 폴더 2개 생성**(프로세스는 건드리지 않음) — 다음에 또 재시작이 나더라도 supervisord 가 뜨도록:
   `/opt/knk_mail/logs`, `/opt/knk_messenger/logs`
3. nginx(pid 236 master)는 **건드리지 않았습니다.**

## 5. 전산에서 해 주실 일 (10초 · 업무시간 피해서)

지금 WORKS 는 supervisord 관리 밖에서 돌고 있어, **죽어도 워치독이 자동으로 못 살립니다.**
아래를 한 번 해 주시면 원래대로(supervisord 관리 + 워치독 자동 복구) 돌아옵니다.

> ⚠ **08:50~09:30 은 출근 몰림 시간이라 재기동 금지**(대표 규칙). 저녁 또는 한가한 시간에.

윈도우 PowerShell 에서(한 줄씩):

```bash
ssh -p 32201 root@o.knknara.co.kr "pkill -f '/opt/knk_haist/.venv/bin/uvicorn'"
```

```bash
ssh -p 32201 root@o.knknara.co.kr "supervisord -c /etc/supervisor/supervisord.conf"
```

```bash
ssh -p 32201 root@o.knknara.co.kr "sleep 15; supervisorctl status; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5051/api/version"
```

- `knk-works` 가 **RUNNING**, 마지막 줄이 **200** 이면 끝입니다.
- `knk-mail`·`knk-messenger` 는 **FATAL** 로 남습니다(앱 폴더가 없으니 정상적인 결과). WORKS 동작에는 지장 없습니다.
- `nginx` 도 FATAL 이 날 수 있습니다 — **이미 떠 있는 nginx(pid 236)는 절대 kill 하지 마세요.** 그것이 진짜 서비스용입니다.

### 근본 정리(권장 · 위 조치 뒤 여유 있을 때)

없어진 앱 설정을 빼 두면 앞으로 재시작 때 이런 일이 없습니다.

```bash
ssh -p 32201 root@o.knknara.co.kr "cd /etc/supervisor/conf.d; mv knk-messenger.conf knk-messenger.conf.disabled-20260921"
```

- 메일(`knk-mail.conf`)은 **§6 확인 뒤** 판단해 주세요.
- 되돌리려면 `.disabled-20260921` 을 떼고 supervisord 재기동하면 됩니다.

## 6. 별건 — 메일 서비스가 죽어 있습니다

- supervisor 설정상 메일은 `/opt/knk_mail` 에서 **포트 8201** 로 도는 앱인데, **폴더 자체가 없습니다.**
- 즉 이 컨테이너의 **메일 서비스는 오래전부터 떠 있지 않습니다**(언제부터인지는 §7 참고).
- WORKS 화면 안의 메일 기능과는 별개일 수 있으니, **메일이 실제로 필요한지 / 어디로 옮겼는지** 확인 부탁드립니다.

## 7. 정직하게 밝힐 점 (조사 한계)

- 08:39 에 복구하려고 `/opt/knk_mail/logs` 를 만들면서 **`/opt` 폴더의 수정 시각이 덮였습니다.**
  그래서 **두 폴더가 정확히 언제 없어졌는지는 이제 확인할 수 없습니다.** 2026-08-17 ~ 09-21 사이라는 것만 압니다.
- 컨테이너가 **왜** 07:31 에 재시작됐는지(백업 후 자동 재시작인지, 다른 작업인지)는 컨테이너 바깥(NAS/Docker) 기록이라 제가 볼 수 없습니다. **전산에서 확인 부탁드립니다.**
- 메모리·디스크는 넉넉했고(메모리 여유 29GB · `/opt` 사용률 15%), OOM 흔적은 없었습니다.

## 8. 지금 상태 확인 방법 (누구나)

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://works.knknara.co.kr/api/version
```

**200** 이면 정상입니다. (09:19 기준 200 · 버전 `672f943`)
