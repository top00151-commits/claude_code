@echo off
title HAIST WORKS - Auto Deploy SETUP (run once)
echo ============================================
echo   HAIST WORKS  -  AUTO DEPLOY  (SETUP, run ONCE)
echo ============================================
echo.
echo  This installs a NAS job that pulls the latest code
echo  every minute and restarts the app ONLY when changed.
echo  You may be asked for the NAS password ONE time.
echo.
echo --------------------------------------------
ssh -p 31201 root@o.knknara.co.kr "cd /opt/knk_haist && git pull && bash deploy/setup_auto_deploy.sh"
echo --------------------------------------------
echo.
if %ERRORLEVEL%==0 (
  echo  SETUP DONE if you see '=== SETUP DONE ===' above.
  echo  From now on, every change goes LIVE automatically within ~1 minute.
  echo  You do NOT need to run this again, and you do NOT need WORKS_BAEPO.bat anymore.
) else (
  echo  [WARNING] Setup error. Show the messages above to Victor.
)
echo.
pause
