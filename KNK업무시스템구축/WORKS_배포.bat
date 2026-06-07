@echo off
title HAIST WORKS - NAS Deploy
echo ============================================
echo   HAIST WORKS  -  NAS Deploy (one click)
echo ============================================
echo.
echo  Connecting to NAS: git pull + restart app
echo  (OK if you see "knk-works: started" below)
echo.
echo --------------------------------------------
ssh -p 31201 root@o.knknara.co.kr "cd /opt/knk_haist && git pull && supervisorctl restart knk-works && echo [Deployed version:] && git log --oneline -1"
echo --------------------------------------------
echo.
if %ERRORLEVEL%==0 (
  echo  DONE. If you see "knk-works: started" above, it is LIVE.
) else (
  echo  [WARNING] Error occurred. Show the messages above to Victor.
)
echo.
pause
