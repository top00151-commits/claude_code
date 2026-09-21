#!/bin/bash
# z1120 회귀 묶음 — 고친 사본(z1120/app_new)으로 기존 녹음 화면 시험들을 차례로
SP="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad"
B="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록"
R="$SP/z1120/reg"; APPW="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1120/app_new"
APPU="$SP/z1120/app_new"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"; P312="/c/Users/top00/AppData/Local/Programs/Python/Python312/python.exe"
OUT="$R/reg_summary.txt"; printf "== ui_rec: 합계: 통과 27 · 실패 0
== phone_fit_rec: 합계: 통과 31 · 실패 0
" > "$OUT"
kill_port(){ netstat -ano | grep -E "LISTENING.*:$1 " | awk '{print $5}' | sort -u | while read pid; do powershell -NoProfile -Command "Stop-Process -Id $pid -Force" 2>/dev/null; done; sleep 2; }
start(){ # $1=runner $2=port $3...=args
  local run="$1" port="$2"; shift 2; kill_port "$port"; rm -f "$R/srv_$port.log"
  ( cd "$R" && "$P313" "$run" "$@" > "$R/srv_$port.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_$port.log" 2>/dev/null && { sleep 2; return 0; }; sleep 1; done
  echo "[$run] READY 안 뜸" >> "$OUT"; tail -3 "$R/srv_$port.log" >> "$OUT"; return 1; }
res(){ local name="$1" log="$2"; echo "== $name: $(grep -E '합계|통과 [0-9]+ · 실패|=====.*통과' "$log" | tail -1)" >> "$OUT"; grep -E "^\s*(FAIL|\[FAIL\])|❌" "$log" | head -8 >> "$OUT"; }

# 1) 녹음 화면(z1113) · 휴대폰 폭 · 뒤로 가기(z1114) — run_rec_app 8934
: # (ui_rec 27/27 끝)  "$R" > "$R/ui_rec.log" 2>&1; res ui_rec "$R/ui_rec.log"; }
: # (phone_fit 31/31 끝)  "$R" > "$R/phone_fit.log" 2>&1; res phone_fit_rec "$R/phone_fit.log"; }
start run_rec_app.py 8934 "$APPW" 8934 && { timeout 900 "$P312" "$B/2026-09-18_2249_회의록_녹음중뒤로가기_다른앱경고_WORKS준비물/ui_back.py" "$R" > "$R/ui_back.log" 2>&1; res ui_back "$R/ui_back.log"; }
kill_port 8934
# 2) 휴대폰 녹음기(z1115) · 넘기기(z1116) · 녹음기 기본(z1118) · 공유 화면(z1117) — run_phrec_app 8936
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2110_회의록_휴대폰녹음기로녹음_WORKS준비물/ui_phrec.py" 8936 > "$R/ui_phrec.log" 2>&1; res ui_phrec "$R/ui_phrec.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2206_회의록_이음회의시작도녹음기로_WORKS준비물/ui_lead.py" "$R" > "$R/ui_lead.log" 2>&1; res ui_lead "$R/ui_lead.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2320_회의록_안드로이드는녹음기가기본_WORKS준비물/ui_first.py" "$R" > "$R/ui_first.log" 2>&1; res ui_first "$R/ui_first.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2240_회의록_녹음기공유로자동정리_WORKS준비물/ui_share.py" 8936 > "$R/ui_share.log" 2>&1; res ui_share "$R/ui_share.log"; }
kill_port 8936
# 3) 마이크 안내(z1107/z1109) — run_mic_app 8932
start run_mic_app.py 8932 && { timeout 900 "$P312" "$B/2026-09-17_1414_녹음화면PC안내문구_WORKS준비물/mic_text_test.py" "$R" > "$R/mic_text.log" 2>&1; res mic_text_test "$R/mic_text.log"; }
kill_port 8932
# 4) 나갈 때 알림(z1106) — run_app_guard 8895
start run_app_guard.py 8895 "$APPW" && { timeout 900 "$P312" "$R/pw_guard.py" > "$R/pw_guard.log" 2>&1; res pw_guard "$R/pw_guard.log"; }
kill_port 8895
# 5) 서버 시험(TestClient) — 녹음 서버 · 공유 받기 · 이음 상태
for t in "2026-09-18_1016_회의록_녹음서버저장_창닫혀도끝내기_WORKS준비물/verify_rec.py" "2026-09-20_2240_회의록_녹음기공유로자동정리_WORKS준비물/verify_share.py" "2026-09-18_2249_회의록_녹음중뒤로가기_다른앱경고_WORKS준비물/verify_msg_rec.py"; do
  n=$(basename "$t" .py); ( cd "$APPU" && rm -rf data meeting_audio && timeout 900 "$P313" "$B/$t" > "$R/$n.log" 2>&1 ); res "$n" "$R/$n.log"; done
# 6) 표준 검사기(고친 사본 트리)
( cd "$SP/z1120/app_shot" && "$P313" deploy/check_standards.py > "$R/standards.log" 2>&1; echo "== check_standards: exit $? · $(tail -2 "$R/standards.log" | tr '\n' ' ')" >> "$OUT" )
echo "ALLDONE" >> "$OUT"
