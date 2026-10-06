#!/bin/bash
# z1139 회귀 묶음 — 고친 사본(z1139/app_new · 정리 글 바로 고치기)
SP="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad"
B="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록"
W="$B/2026-09-27_1252_안드로이드_녹음기앱으로_계속녹음_WORKS준비물"; W29="$B/2026-09-27_1530_녹음기앱열기_없애고_직접열기안내_WORKS준비물"; W30="$B/2026-09-27_1900_휴대폰은녹음기한길만_화면단순화_WORKS준비물"; W31="$B/2026-09-27_2040_회의종료단추_공유안내_WORKS준비물"; W32="$B/2026-09-29_2103_참석자도_녹음과_회의록작성_WORKS준비물"; W34="$B/2026-09-29_2230_참석자명단_이음과맞추기_WORKS준비물"; W35="$B/2026-10-05_1120_녹음파일올리기_바로보이게_WORKS준비물"; W39="$B/2026-10-06_0012_정리글_바로고치기_WORKS준비물"; W26="$B/2026-09-26_2305_취소알림문구_새규칙맞춤_WORKS준비물"; W25="$B/2026-09-26_2121_회의록지울때_녹음파일도함께_WORKS준비물"; W23="$B/2026-09-22_0022_이음회의삭제도_회의록함께_WORKS준비물"; W24="$B/2026-09-22_0815_모아보기_회의록열기_이름맞춤_WORKS준비물"
R="$SP/z1127/reg"; APPW="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1139/app_new"
APPU="$SP/z1139/app_new"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"; P312="/c/Users/top00/AppData/Local/Programs/Python/Python312/python.exe"
OUT="$W39/reg_summary_z1139b.txt"; : > "$OUT"
listening(){ powershell -NoProfile -Command "@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { \$_.LocalPort -ge 8890 -and \$_.LocalPort -le 8999 }).Count"; }
echo "시작 전 89xx 듣는 포트: $(listening)" >> "$OUT"
kill_port(){ "$W/killport.sh" "$1" || { echo "[포트 $1] 비우지 못함 — 시험 중지" >> "$OUT"; return 1; }; }
start(){ local run="$1" port="$2"; shift 2; kill_port "$port" || return 1; rm -f "$R/srv_$port.log"
  ( cd "$R" && "$P313" "$run" "$@" > "$R/srv_$port.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_$port.log" 2>/dev/null && { sleep 2; return 0; }; sleep 1; done
  echo "[$run] READY 안 뜸" >> "$OUT"; tail -3 "$R/srv_$port.log" >> "$OUT"; return 1; }
res(){ local name="$1" log="$2"; echo "== $name: $(grep -E '합계|통과 [0-9]+ [·/] 실패|=====.*통과|결과: [0-9]+ ?(/|통과)' "$log" | tail -1)" >> "$OUT"; grep -E "^\s*(FAIL|\[FAIL\])|❌|Traceback" "$log" | head -6 >> "$OUT"; }
printf "%s" "$APPW" > "$R/which_app.txt"   # run_mic_app.py 는 이 파일로 앱 사본을 고른다
# 3) 마이크 안내 · 4) 나갈 때 알림 · 5) 창 닫힌 녹음 맨 위(z1120)
start run_mic_app.py 8932 && { timeout 900 "$P312" "$B/2026-09-17_1414_녹음화면PC안내문구_WORKS준비물/mic_text_test.py" "$R" > "$R/mic_text.log" 2>&1; res mic_text_test "$R/mic_text.log"; }
kill_port 8932
#    임시 폴더에만 있었고 지워졌다(준비물 폴더에 저장돼 있지 않았다). 같은 자리는 ui_back 이 일부 덮는다
#    (「저장 전 글 + 뒤로 가기 → 확인창」). 이번 변경은 나갈 때 알림 코드를 건드리지 않는다.
kill_port 8895
start run_resume_app.py 8937 "$APPW" 8937 && { timeout 900 "$P312" "$W30/ui_resume_z1130.py" "$R" > "$R/ui_resume.log" 2>&1; res ui_resume "$R/ui_resume.log"; }
kill_port 8937
# 6) 모아보기 원래 화면(z1108 · 8921 + 가짜 이음 8922)
kill_port 8921; kill_port 8922
W19="$B/2026-09-21_1830_회의카드모아보기_끝났는데회의중_WORKS준비물"
( cd "$W19" && rm -f seed.json && KNK_APP_DIR="$APPW" "$P313" run_preview_z1119.py > "$R/preview.log" 2>&1 & )
for i in $(seq 1 90); do [ -f "$W19/seed.json" ] && curl -s -m 2 -o /dev/null http://127.0.0.1:8921/api/version && break; sleep 1; done; sleep 3
timeout 900 "$P312" "$W24/ui_test_cards_z1124.py" > "$R/ui_test_cards.log" 2>&1; res ui_test_cards_z1124 "$R/ui_test_cards.log"
kill_port 8921; kill_port 8922; rm -f "$W19/seed.json"
# 7) z1122 삭제 화면 46 · z1123 화면(취소 알림 안내) — 서버를 새로 띄워 각각
"$W35/restart35.sh" app_new 8942 >> "$OUT" 2>&1 && { timeout 900 "$P312" "$W24/ui_del_z1124.py" "$W35/seed_app_new" > "$R/ui_del.log" 2>&1; res ui_del_z1124 "$R/ui_del.log"; }
"$W35/restart35.sh" app_new 8942 >> "$OUT" 2>&1 && { timeout 900 "$P312" "$W26/ui_z1126.py" "$W35/seed_app_new" > "$R/ui_z1123.log" 2>&1; res ui_z1126 "$R/ui_z1123.log"; }
kill_port 8942
echo "ALLDONE-B" >> "$OUT"
