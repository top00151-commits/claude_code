#!/bin/bash
# z1125 회귀 묶음 — 고친 사본(z1125/app_new · 지울 때 녹음 파일도)으로 기존 시험 전부
SP="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad"
B="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록"
W="$B/2026-09-26_2121_회의록지울때_녹음파일도함께_WORKS준비물"; W23="$B/2026-09-22_0022_이음회의삭제도_회의록함께_WORKS준비물"; W24="$B/2026-09-22_0815_모아보기_회의록열기_이름맞춤_WORKS준비물"
R="$SP/z1125/reg"; APPW="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1125/app_new"
APPU="$SP/z1125/app_new"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"; P312="/c/Users/top00/AppData/Local/Programs/Python/Python312/python.exe"
OUT="$R/reg_summary.txt"; : > "$OUT"
listening(){ powershell -NoProfile -Command "@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { \$_.LocalPort -ge 8890 -and \$_.LocalPort -le 8999 }).Count"; }
echo "시작 전 89xx 듣는 포트: $(listening)" >> "$OUT"
kill_port(){ "$W/killport.sh" "$1" || { echo "[포트 $1] 비우지 못함 — 시험 중지" >> "$OUT"; return 1; }; }
start(){ local run="$1" port="$2"; shift 2; kill_port "$port" || return 1; rm -f "$R/srv_$port.log"
  ( cd "$R" && "$P313" "$run" "$@" > "$R/srv_$port.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_$port.log" 2>/dev/null && { sleep 2; return 0; }; sleep 1; done
  echo "[$run] READY 안 뜸" >> "$OUT"; tail -3 "$R/srv_$port.log" >> "$OUT"; return 1; }
res(){ local name="$1" log="$2"; echo "== $name: $(grep -E '합계|통과 [0-9]+ [·/] 실패|=====.*통과|결과: [0-9]+ ?(/|통과)' "$log" | tail -1)" >> "$OUT"; grep -E "^\s*(FAIL|\[FAIL\])|❌|Traceback" "$log" | head -6 >> "$OUT"; }
# 1) 녹음 화면(z1113) · 휴대폰 폭 · 뒤로 가기(z1114)
start run_rec_app.py 8934 "$APPW" 8934 && { timeout 900 "$P312" "$B/2026-09-18_1016_회의록_녹음서버저장_창닫혀도끝내기_WORKS준비물/ui_rec.py" "$R" > "$R/ui_rec.log" 2>&1; res ui_rec "$R/ui_rec.log"; }
start run_rec_app.py 8934 "$APPW" 8934 && { timeout 900 "$P312" "$B/2026-09-18_1016_회의록_녹음서버저장_창닫혀도끝내기_WORKS준비물/phone_fit_rec.py" "$R" > "$R/phone_fit.log" 2>&1; res phone_fit_rec "$R/phone_fit.log"; }
start run_rec_app.py 8934 "$APPW" 8934 && { timeout 900 "$P312" "$B/2026-09-18_2249_회의록_녹음중뒤로가기_다른앱경고_WORKS준비물/ui_back.py" "$R" > "$R/ui_back.log" 2>&1; res ui_back "$R/ui_back.log"; }
kill_port 8934
# 2) 휴대폰 녹음기·넘기기·녹음기 기본·공유 화면·모아보기 화면(z1119)
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2110_회의록_휴대폰녹음기로녹음_WORKS준비물/ui_phrec.py" 8936 > "$R/ui_phrec.log" 2>&1; res ui_phrec "$R/ui_phrec.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2206_회의록_이음회의시작도녹음기로_WORKS준비물/ui_lead.py" "$R" > "$R/ui_lead.log" 2>&1; res ui_lead "$R/ui_lead.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2320_회의록_안드로이드는녹음기가기본_WORKS준비물/ui_first.py" "$R" > "$R/ui_first.log" 2>&1; res ui_first "$R/ui_first.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-20_2240_회의록_녹음기공유로자동정리_WORKS준비물/ui_share.py" 8936 > "$R/ui_share.log" 2>&1; res ui_share "$R/ui_share.log"; }
start run_phrec_app.py 8936 "$APPW" 8936 && { timeout 900 "$P312" "$B/2026-09-21_1830_회의카드모아보기_끝났는데회의중_WORKS준비물/ui_cards_rec.py" 8936 > "$R/ui_cards_rec.log" 2>&1; res ui_cards_rec "$R/ui_cards_rec.log"; }
kill_port 8936
# 3) 마이크 안내 · 4) 나갈 때 알림 · 5) 창 닫힌 녹음 맨 위(z1120)
start run_mic_app.py 8932 && { timeout 900 "$P312" "$B/2026-09-17_1414_녹음화면PC안내문구_WORKS준비물/mic_text_test.py" "$R" > "$R/mic_text.log" 2>&1; res mic_text_test "$R/mic_text.log"; }
kill_port 8932
start run_app_guard.py 8895 "$APPW" && { timeout 900 "$P312" "$R/pw_guard.py" > "$R/pw_guard.log" 2>&1; res pw_guard "$R/pw_guard.log"; }
kill_port 8895
start run_resume_app.py 8937 "$APPW" 8937 && { timeout 900 "$P312" "$R/ui_resume_z1122.py" "$R" > "$R/ui_resume.log" 2>&1; res ui_resume "$R/ui_resume.log"; }
kill_port 8937
# 6) 모아보기 원래 화면(z1108 · 8921 + 가짜 이음 8922)
kill_port 8921; kill_port 8922
W19="$B/2026-09-21_1830_회의카드모아보기_끝났는데회의중_WORKS준비물"
( cd "$W19" && rm -f seed.json && KNK_APP_DIR="$APPW" "$P313" run_preview_z1119.py > "$R/preview.log" 2>&1 & )
for i in $(seq 1 90); do [ -f "$W19/seed.json" ] && curl -s -m 2 -o /dev/null http://127.0.0.1:8921/api/version && break; sleep 1; done; sleep 3
timeout 900 "$P312" "$W24/ui_test_cards_z1124.py" > "$R/ui_test_cards.log" 2>&1; res ui_test_cards_z1124 "$R/ui_test_cards.log"
kill_port 8921; kill_port 8922; rm -f "$W19/seed.json"
# 7) z1122 삭제 화면 46 · z1123 화면(취소 알림 안내) — 서버를 새로 띄워 각각
"$W/restart25.sh" app_new 8942 >> "$OUT" 2>&1 && { timeout 900 "$P312" "$W24/ui_del_z1124.py" "$W/seed_app_new" > "$R/ui_del.log" 2>&1; res ui_del_z1124 "$R/ui_del.log"; }
"$W/restart25.sh" app_new 8942 >> "$OUT" 2>&1 && { timeout 900 "$P312" "$W23/ui_z1123.py" "$W/seed_app_new" > "$R/ui_z1123.log" 2>&1; res ui_z1123 "$R/ui_z1123.log"; }
kill_port 8942
# 8) 서버 시험(TestClient)
for t in "2026-09-18_1016_회의록_녹음서버저장_창닫혀도끝내기_WORKS준비물/verify_rec.py" "2026-09-20_2240_회의록_녹음기공유로자동정리_WORKS준비물/verify_share.py" "2026-09-18_2249_회의록_녹음중뒤로가기_다른앱경고_WORKS준비물/verify_msg_rec.py" "2026-09-21_1830_회의카드모아보기_끝났는데회의중_WORKS준비물/verify_cards_rec.py" "2026-09-21_2200_이음카드_이어서녹음_rec_mine_WORKS준비물/verify_msg_mine.py" "2026-09-17_0845_회의카드모아보기_WORKS준비물/verify_cards.py" "2026-09-21_2313_회의록삭제_두번확인_이음회의연동_WORKS준비물/verify_del.py" "2026-09-22_0022_이음회의삭제도_회의록함께_WORKS준비물/verify_z1123.py" "2026-09-26_2121_회의록지울때_녹음파일도함께_WORKS준비물/verify_z1125.py"; do
  n=$(basename "$t" .py); ( cd "$APPU" && rm -rf data meeting_audio && timeout 900 "$P313" "$B/$t" > "$R/$n.log" 2>&1 ); res "$n" "$R/$n.log"; done
echo "끝난 뒤 89xx 듣는 포트: $(listening)" >> "$OUT"
echo "ALLDONE" >> "$OUT"
