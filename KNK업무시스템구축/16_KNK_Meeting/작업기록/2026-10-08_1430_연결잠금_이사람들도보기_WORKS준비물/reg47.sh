#!/bin/bash
# z1147·z1148 회귀 묶음 — 고친 사본(z1147/app_new)
SP="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad"
B="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록"
W="$B/2026-09-27_1252_안드로이드_녹음기앱으로_계속녹음_WORKS준비물"; W30="$B/2026-09-27_1900_휴대폰은녹음기한길만_화면단순화_WORKS준비물"; W31="$B/2026-09-27_2040_회의종료단추_공유안내_WORKS준비물"; W32="$B/2026-09-29_2103_참석자도_녹음과_회의록작성_WORKS준비물"; W35="$B/2026-10-05_1120_녹음파일올리기_바로보이게_WORKS준비물"; W39="$B/2026-10-06_0012_정리글_바로고치기_WORKS준비물"; W41="$B/2026-10-06_1800_아이폰_녹음파일올리기_WORKS준비물"; W43="$B/2026-10-07_1330_화면녹음막고_휴대폰녹음기안내_WORKS준비물"; W44="$B/2026-10-08_0900_음성메모_새메뉴_WORKS준비물"
R="$SP/z1147/reg"; mkdir -p "$R"; APPW="$SP/z1147/app_new"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"; P312="/c/Users/top00/AppData/Local/Programs/Python/Python312/python.exe"
OUT="$B/2026-10-08_1430_연결잠금_이사람들도보기_WORKS준비물/reg_summary_z1147.txt"; : > "$OUT"
listening(){ powershell -NoProfile -Command "@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { \$_.LocalPort -ge 8890 -and \$_.LocalPort -le 8999 }).Count"; }
echo "시작 전 89xx 듣는 포트: $(listening)" >> "$OUT"
kill_port(){ "$W/killport.sh" "$1" || { echo "[포트 $1] 비우지 못함 — 시험 중지" >> "$OUT"; return 1; }; }
start(){ local run="$1" port="$2"; shift 2; kill_port "$port" || return 1; rm -f "$R/srv_$port.log"
  ( cd "$R" && "$P313" "$run" "$@" > "$R/srv_$port.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_$port.log" 2>/dev/null && { sleep 2; return 0; }; sleep 1; done
  echo "[$run] READY 안 뜸" >> "$OUT"; tail -3 "$R/srv_$port.log" >> "$OUT"; return 1; }
res(){ local name="$1" log="$2"; echo "== $name: $(grep -E '합계|통과 [0-9]+ [·/] 실패|=====.*통과|결과: [0-9]+ ?(/|통과)' "$log" | tail -1)" >> "$OUT"; grep -E "^\s*(FAIL|\[FAIL\])|❌|Traceback" "$log" | head -6 >> "$OUT"; }
RUN44="$R/run_vn_app.py"; RUNREC="$R/run_rec_app.py"; RUNPH="$R/run_phrec_app.py"


echo "runner: rec=$RUNREC ph=$RUNPH" >> "$OUT"
start "$RUNREC" 8934 "$APPW" 8934 && { timeout 900 "$P312" "$W30/ui_rec_z1130.py" "$R" > "$R/ui_rec.log" 2>&1; res ui_rec "$R/ui_rec.log"; }
start "$RUNREC" 8934 "$APPW" 8934 && { timeout 900 "$P312" "$B/2026-09-18_1016_회의록_녹음서버저장_창닫혀도끝내기_WORKS준비물/phone_fit_rec.py" "$R" > "$R/phone_fit.log" 2>&1; res phone_fit_rec "$R/phone_fit.log"; }
start "$RUNREC" 8934 "$APPW" 8934 && { timeout 900 "$P312" "$W30/ui_back_z1130.py" "$R" > "$R/ui_back.log" 2>&1; res ui_back "$R/ui_back.log"; }
kill_port 8934
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W30/ui_phrec_z1130.py" 8936 > "$R/ui_phrec.log" 2>&1; res ui_phrec "$R/ui_phrec.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W30/ui_lead_z1130.py" "$R" > "$R/ui_lead.log" 2>&1; res ui_lead "$R/ui_lead.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W30/ui_first_z1130.py" "$R" > "$R/ui_first.log" 2>&1; res ui_first "$R/ui_first.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2240_회의록_녹음기공유로자동정리_WORKS준비물/ui_share.py" 8936 > "$R/ui_share.log" 2>&1; res ui_share "$R/ui_share.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-21_1830_회의카드모아보기_끝났는데회의중_WORKS준비물/ui_cards_rec.py" 8936 > "$R/ui_cards_rec.log" 2>&1; res ui_cards_rec "$R/ui_cards_rec.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W30/ui_simple_z1130.py" 8936 > "$R/ui_recapp.log" 2>&1; res ui_simple "$R/ui_recapp.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W31/ui_end_z1131.py" 8936 "$R" > "$R/ui_end.log" 2>&1; res ui_end_z1131 "$R/ui_end.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W32/ui_attendee_z1133.py" 8936 "$R" > "$R/ui_att.log" 2>&1; res ui_attendee_z1133 "$R/ui_att.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W35/ui_recup_z1138.py" 8936 "$R" > "$R/ui_recup.log" 2>&1; res ui_recup_z1138 "$R/ui_recup.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W39/ui_sumedit_z1139.py" 8936 "$R" > "$R/ui_sumedit.log" 2>&1; res ui_sumedit_z1139 "$R/ui_sumedit.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W41/ui_filepick_z1141.py" 8936 "$R" > "$R/ui_filepick.log" 2>&1; res ui_filepick_z1141 "$R/ui_filepick.log"; }
start "$RUNPH" 8936 "$APPW" 8936 && { timeout 900 "$P312" "$W43/ui_block_z1143.py" 8936 "$R" > "$R/ui_block.log" 2>&1; res ui_block_z1143 "$R/ui_block.log"; }
kill_port 8936
kill_port 8939 && { rm -f "$R/srv_8939.log"; ( cd "$W44" && "$P313" run_vn_app.py "$APPW" 8939 > "$R/srv_8939.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_8939.log" 2>/dev/null && { sleep 2; break; }; sleep 1; done
  timeout 900 "$P312" "$W44/ui_vn_z1144.py" 8939 > "$R/ui_vn.log" 2>&1; res ui_vn_z1144 "$R/ui_vn.log"; }
kill_port 8939
Z="$SP/z1147"
kill_port 8941 && { rm -f "$R/srv_8941.log"; ( cd "$Z" && "$P313" run_vw_app.py "$APPW" 8941 > "$R/srv_8941.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_8941.log" 2>/dev/null && { sleep 2; break; }; sleep 1; done
  cp "$Z/seed_vw.json" "$Z/seed_vw.json.bak" 2>/dev/null
  timeout 900 "$P312" "$Z/ui_vw_z1148.py" 8941 > "$R/ui_vw.log" 2>&1; res ui_vw_z1148 "$R/ui_vw.log"; }
kill_port 8941
echo "끝난 뒤 89xx 듣는 포트: $(listening)" >> "$OUT"
echo "ALLDONE-47" >> "$OUT"
