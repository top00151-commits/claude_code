#!/bin/bash
# z1139 회귀 묶음 — 고친 사본(z1139/app_new · 정리 글 바로 고치기)
SP="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad"
B="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록"
W="$B/2026-09-27_1252_안드로이드_녹음기앱으로_계속녹음_WORKS준비물"; W29="$B/2026-09-27_1530_녹음기앱열기_없애고_직접열기안내_WORKS준비물"; W30="$B/2026-09-27_1900_휴대폰은녹음기한길만_화면단순화_WORKS준비물"; W31="$B/2026-09-27_2040_회의종료단추_공유안내_WORKS준비물"; W32="$B/2026-09-29_2103_참석자도_녹음과_회의록작성_WORKS준비물"; W34="$B/2026-09-29_2230_참석자명단_이음과맞추기_WORKS준비물"; W35="$B/2026-10-05_1120_녹음파일올리기_바로보이게_WORKS준비물"; W39="$B/2026-10-06_0012_정리글_바로고치기_WORKS준비물"; W40="$B/2026-10-06_1330_받아쓰기모델_교체_WORKS준비물"; W26="$B/2026-09-26_2305_취소알림문구_새규칙맞춤_WORKS준비물"; W25="$B/2026-09-26_2121_회의록지울때_녹음파일도함께_WORKS준비물"; W23="$B/2026-09-22_0022_이음회의삭제도_회의록함께_WORKS준비물"; W24="$B/2026-09-22_0815_모아보기_회의록열기_이름맞춤_WORKS준비물"
R="$SP/z1127/reg"; APPW="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1140/app_new"
APPU="$SP/z1140/app_new"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"; P312="/c/Users/top00/AppData/Local/Programs/Python/Python312/python.exe"
OUT="$W40/reg_summary_z1140.txt"; : > "$OUT"
listening(){ powershell -NoProfile -Command "@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { \$_.LocalPort -ge 8890 -and \$_.LocalPort -le 8999 }).Count"; }
echo "시작 전 89xx 듣는 포트: $(listening)" >> "$OUT"
kill_port(){ "$W/killport.sh" "$1" || { echo "[포트 $1] 비우지 못함 — 시험 중지" >> "$OUT"; return 1; }; }
start(){ local run="$1" port="$2"; shift 2; kill_port "$port" || return 1; rm -f "$R/srv_$port.log"
  ( cd "$R" && "$P313" "$run" "$@" > "$R/srv_$port.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_$port.log" 2>/dev/null && { sleep 2; return 0; }; sleep 1; done
  echo "[$run] READY 안 뜸" >> "$OUT"; tail -3 "$R/srv_$port.log" >> "$OUT"; return 1; }
res(){ local name="$1" log="$2"; echo "== $name: $(grep -E '합계|통과 [0-9]+ [·/] 실패|=====.*통과|결과: [0-9]+ ?(/|통과)' "$log" | tail -1)" >> "$OUT"; grep -E "^\s*(FAIL|\[FAIL\])|❌|Traceback" "$log" | head -6 >> "$OUT"; }
# 8) 서버 시험(TestClient)
for t in "2026-09-18_1016_회의록_녹음서버저장_창닫혀도끝내기_WORKS준비물/verify_rec.py" "2026-09-20_2240_회의록_녹음기공유로자동정리_WORKS준비물/verify_share.py" "2026-09-18_2249_회의록_녹음중뒤로가기_다른앱경고_WORKS준비물/verify_msg_rec.py" "2026-09-21_1830_회의카드모아보기_끝났는데회의중_WORKS준비물/verify_cards_rec.py" "2026-09-21_2200_이음카드_이어서녹음_rec_mine_WORKS준비물/verify_msg_mine.py" "2026-09-17_0845_회의카드모아보기_WORKS준비물/verify_cards.py" "2026-09-21_2313_회의록삭제_두번확인_이음회의연동_WORKS준비물/verify_del.py" "2026-09-22_0022_이음회의삭제도_회의록함께_WORKS준비물/verify_z1123.py" "2026-09-26_2305_취소알림문구_새규칙맞춤_WORKS준비물/verify_z1126.py" "2026-09-27_2040_회의종료단추_공유안내_WORKS준비물/verify_end_z1131.py" "2026-09-29_2103_참석자도_녹음과_회의록작성_WORKS준비물/verify_attendee_z1133.py" "2026-09-29_2230_참석자명단_이음과맞추기_WORKS준비물/verify_att_sync_z1134.py" "2026-10-06_0012_정리글_바로고치기_WORKS준비물/verify_sumedit_z1139.py"; do
  n=$(basename "$t" .py); ( cd "$APPU" && rm -rf data meeting_audio && timeout 900 "$P313" "$B/$t" > "$R/$n.log" 2>&1 ); res "$n" "$R/$n.log"; done
echo "끝난 뒤 89xx 듣는 포트: $(listening)" >> "$OUT"
echo "ALLDONE" >> "$OUT"

echo "ALLDONE-40" >> "$OUT"
