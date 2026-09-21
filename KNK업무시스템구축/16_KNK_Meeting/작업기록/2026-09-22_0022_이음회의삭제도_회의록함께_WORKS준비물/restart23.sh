#!/bin/bash
# 사용: restart23.sh <app_new|app_base> <port> — 그 포트 주인을 멈추고 빈 것을 확인한 뒤 run_z1123_app.py 로 띄움
W="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-22_0022_이음회의삭제도_회의록함께_WORKS준비물"
APPN="${1:-app_new}"; PORT="${2:-8942}"
APP="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1123/$APPN"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
"$W/killport.sh" "$PORT" || { echo "포트 $PORT 비우지 못함 — 중지"; exit 1; }
mkdir -p "$W/seed_$APPN" && cd "$W/seed_$APPN" && rm -f "srv_$PORT.log" seed_del.json
cp "$W/run_z1123_app.py" ./run_z1123_app.py
"$P313" run_z1123_app.py "$APP" "$PORT" > "srv_$PORT.log" 2>&1 &
for i in $(seq 1 120); do if grep -q "^READY" "srv_$PORT.log" 2>/dev/null; then sleep 2; echo "READY ${APPN} ${PORT} (${i}s)"; exit 0; fi; sleep 1; done
echo "READY 안 뜸"; tail -8 "srv_$PORT.log"; exit 1
