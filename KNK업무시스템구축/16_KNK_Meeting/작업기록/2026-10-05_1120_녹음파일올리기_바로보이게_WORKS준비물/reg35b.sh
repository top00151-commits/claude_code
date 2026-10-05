#!/bin/bash
# z1138 재확인 묶음 — ① 고친 시험 3종 + 내 새 시험 + 떨림 의심 1종 ② 앞 묶음에서 시간 때문에 못 돈 서버 시험 6종
SP="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad"
B="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록"
W="$B/2026-09-27_1252_안드로이드_녹음기앱으로_계속녹음_WORKS준비물"
W30="$B/2026-09-27_1900_휴대폰은녹음기한길만_화면단순화_WORKS준비물"
W35="$B/2026-10-05_1120_녹음파일올리기_바로보이게_WORKS준비물"
R="$SP/z1127/reg"
APPW="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1138/app_new"
APPU="$SP/z1138/app_new"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"; P312="/c/Users/top00/AppData/Local/Programs/Python/Python312/python.exe"
OUT="$W35/reg_summary_z1138b.txt"; : > "$OUT"
kill_port(){ "$W35/killport.sh" "$1" || { echo "[포트 $1] 비우지 못함 — 중지" >> "$OUT"; return 1; }; }
start(){ local run="$1" port="$2"; shift 2; kill_port "$port" || return 1; rm -f "$R/srv_$port.log"
  ( cd "$R" && "$P313" "$run" "$@" > "$R/srv_$port.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_$port.log" 2>/dev/null && { sleep 2; return 0; }; sleep 1; done
  echo "[$run] READY 안 뜸" >> "$OUT"; tail -3 "$R/srv_$port.log" >> "$OUT"; return 1; }
res(){ local name="$1" log="$2"; echo "== $name: $(grep -E '합계|통과 [0-9]+ [·/] 실패|=====.*통과|결과: [0-9]+ ?(/|통과)' "$log" | tail -1)" >> "$OUT"; grep -E "^\s*(FAIL|\[FAIL\])|❌|Traceback" "$log" | head -6 >> "$OUT"; }

# ── ① 휴대폰 묶음(8936): 고친 시험 3종 중 2종 + 내 시험 + 떨림 의심
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W30/ui_phrec_z1130.py" 8936 > "$R/ui_phrec.log" 2>&1; res ui_phrec "$R/ui_phrec.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W30/ui_lead_z1130.py" "$R" > "$R/ui_lead.log" 2>&1; res ui_lead "$R/ui_lead.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W30/ui_simple_z1130.py" 8936 > "$R/ui_recapp.log" 2>&1; res ui_simple "$R/ui_recapp.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W35/ui_recup_z1138.py" 8936 "$R" > "$R/ui_recup.log" 2>&1; res ui_recup_z1138 "$R/ui_recup.log"; }
kill_port 8936
# ── ② 창 닫힌 녹음(8937): 고친 시험 1종
start run_resume_app.py 8937 "$APPW" 8937 && { timeout 900 "$P312" "$W30/ui_resume_z1130.py" "$R" > "$R/ui_resume.log" 2>&1; res ui_resume "$R/ui_resume.log"; }
kill_port 8937
echo "ALLDONE-UI" >> "$OUT"
