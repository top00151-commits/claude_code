@echo off
chcp 65001 >nul
echo.
echo   윈도우 아이콘 캐시 새로고침
echo   ==============================
echo   옛 아이콘이 바탕화면/작업표시줄에 남아있을 때 사용합니다.
echo   실행하면 작업표시줄/바탕화면이 잠깐 사라졌다 다시 나타납니다 (정상).
echo.
echo   계속하려면 아무 키나 누르세요 (취소: 창 닫기)...
pause >nul
echo.
echo   [1/3] 탐색기 종료...
taskkill /f /im explorer.exe >nul 2>&1
echo   [2/3] 아이콘 캐시 삭제...
del /a /f /q "%localappdata%\IconCache.db" >nul 2>&1
del /a /f /q "%localappdata%\Microsoft\Windows\Explorer\iconcache*.db" >nul 2>&1
ie4uinit.exe -show >nul 2>&1
echo   [3/3] 탐색기 재시작...
start explorer.exe
echo.
echo   완료! 아이콘이 새로 그려집니다.
echo   (그래도 옛 아이콘이면: 바로가기 삭제 + 작업표시줄 고정 해제 후 앱 재설치)
echo.
pause
