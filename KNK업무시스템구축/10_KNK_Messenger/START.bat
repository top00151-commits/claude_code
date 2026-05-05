@echo off
chcp 65001 > nul
REM === KNK Messenger 시작 스크립트 ===
REM LAST UPDATE: 2026-05-06 00:30 - 1차 MVP + 결재반영 + 베타팀시드 + Web Push + Excel + 반응
cd /d "%~dp0"
echo.
echo ============================================
echo   KNK Messenger ^(10_KNK_Messenger^)
echo   사내 업무 전용 메신저
echo ============================================
echo.
echo  [PC]      http://localhost:5050
echo  [휴대폰]  http://[이 PC IP]:5050   ^(같은 와이파이 필요^)
echo.
echo  테스트 계정:
echo    - 대표:   kjr     ^(비번 knk1234^)
echo    - 베타:   lhr / lh / okh / bsj / ajy / lsr   ^(비번 knk1234^)
echo.
echo  주요 기능:
echo    - 아이템 카드 ^(고객사 x 모델^)
echo    - 메시지 -^> 요청 승격 + 마감일 추적
echo    - 사진/파일 업로드 + 갤러리 + 라이트박스
echo    - 전사 한글 검색 + 일간 다이제스트
echo    - 메시지 반응 + @멘션
echo    - PWA ^(홈화면 설치 + 오프라인 캐시 + Web Push^)
echo    - Excel 이력 내보내기
echo.
echo  중지: Ctrl+C
echo ============================================
echo.
py app.py
pause
