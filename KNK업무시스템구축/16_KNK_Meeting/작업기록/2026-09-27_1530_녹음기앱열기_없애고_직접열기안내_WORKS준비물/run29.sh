#!/bin/bash
# 사용: run28.sh <app_new|app_base> — z1128 사본으로 휴대폰 시험 서버(8936)를 띄우고 ui_recapp_z1129 을 돌린다
SP="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad"
W29="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-27_1530_녹음기앱열기_없애고_직접열기안내_WORKS준비물"
R="$SP/z1127/reg"; APPN="${1:-app_new}"; PORT=8936
APPW="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1129/$APPN"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"; P312="/c/Users/top00/AppData/Local/Programs/Python/Python312/python.exe"
"$W29/killport.sh" "$PORT" || { echo "포트 $PORT 못 비움"; exit 1; }
rm -f "$R/srv_$PORT.log"
( cd "$R" && "$P313" run_phrec_app.py "$APPW" "$PORT" > "$R/srv_$PORT.log" 2>&1 & )
for i in $(seq 1 120); do grep -q "^READY" "$R/srv_$PORT.log" 2>/dev/null && { sleep 2; break; }; sleep 1; done
grep -q "^READY" "$R/srv_$PORT.log" || { echo "READY 안 뜸"; tail -5 "$R/srv_$PORT.log"; exit 1; }
cp "$R/seed_phrec.json" "$W29/seed_phrec.json"
echo "[$APPN] 서버 준비 — 시험 시작"
timeout 900 "$P312" "$W29/ui_recapp_z1129.py" "$PORT" > "$W29/ui_recapp_z1129_$APPN.log" 2>&1
tail -6 "$W29/ui_recapp_z1129_$APPN.log"
echo "통과: $(grep -c '✅' "$W29/ui_recapp_z1129_$APPN.log") · 실패: $(grep -c '❌' "$W29/ui_recapp_z1129_$APPN.log")"
"$W29/killport.sh" "$PORT" >/dev/null 2>&1
