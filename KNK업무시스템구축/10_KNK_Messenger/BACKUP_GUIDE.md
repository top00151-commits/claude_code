# KNK Messenger 자동 백업 가이드

## 1. 수동 백업

```cmd
cd 10_KNK_Messenger
backup.bat
```

`backups\messenger_YYYY-MM-DD_HHMM.db` + `uploads_YYYY-MM-DD_HHMM.zip` 생성. 14일 이상 된 백업 자동 삭제.

## 2. Windows 작업스케줄러 자동 실행

매일 새벽 3시 자동 백업:

```powershell
# PowerShell 관리자 권한으로 실행
$action = New-ScheduledTaskAction -Execute "C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\10_KNK_Messenger\backup.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable
Register-ScheduledTask -TaskName "KNK_Messenger_Backup" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest
```

확인:
```cmd
schtasks /query /tn "KNK_Messenger_Backup"
```

해제:
```cmd
schtasks /delete /tn "KNK_Messenger_Backup" /f
```

## 3. 매월 1일 자동 정리 (12개월 지난 메시지 삭제)

```powershell
# 매월 1일 새벽 4시 실행 — 자동 삭제 정책
# 단, 사용자가 로그인된 세션 쿠키 필요. 운영에서는 별도 admin token 도입 권장.
# 현재는 수동 실행 권장:
#   1) 브라우저로 로그인 (kjr)
#   2) 개발자도구 콘솔에서 fetch('/api/admin/cleanup', {method:'POST'}).then(r=>r.json()).then(console.log)
```

운영(클라우드 Linux)에서는 다음 cron이 더 적합:

```bash
# crontab -e
0 3 * * * cd /opt/knk_messenger && sqlite3 data/messenger.db ".backup backups/messenger_$(date +\%Y\%m\%d).db"
0 4 1 * * curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" https://msg.knknara.com/api/admin/cleanup
```

(클라우드 운영 시 `X-Admin-Token` 인증 추가 필요 — 다음 사이클)

## 4. 백업 복원

서버 중지 후:
```cmd
copy backups\messenger_2026-05-06_0300.db data\messenger.db /Y
copy uploads_2026-05-06_0300.zip data\
powershell -NoProfile -Command "Expand-Archive -Path data\uploads_2026-05-06_0300.zip -DestinationPath data\uploads -Force"
```

## 5. 외부 클라우드 동기화 (운영 권장)

### Google Drive — `rclone` 무료
```cmd
rclone config
rclone sync backups gdrive:knk_messenger_backup/
```

### S3 (Lightsail 호스팅 시 자연)
```bash
aws s3 sync backups s3://knk-messenger-backup/ --delete
```

`backup.bat` 끝에 추가하면 자동.
