#!/bin/bash
# 사용: restart20.sh <app_new|app_base> <port>
W="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-21_2108_회의록_창닫힌녹음_맨위이어서녹음_WORKS준비물"
APPN="${1:-app_new}"; PORT="${2:-8937}"
APP="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1120/$APPN"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
netstat -ano | grep -E "LISTENING.*:$PORT " | awk '{print $5}' | sort -u | while read pid; do powershell -NoProfile -Command "Stop-Process -Id $pid -Force" 2>/dev/null; done
sleep 2
cd "$W" && rm -f "resume_$PORT.log" seed_resume.json
"$P313" run_resume_app.py "$APP" "$PORT" > "resume_$PORT.log" 2>&1 &
for i in $(seq 1 90); do if grep -q "^READY" "resume_$PORT.log" 2>/dev/null; then sleep 2; echo "READY ${APPN} ${PORT} (${i}s)"; grep "^READY" "resume_$PORT.log"; exit 0; fi; sleep 1; done
echo "READY 안 뜸"; tail -5 "resume_$PORT.log"; exit 1
