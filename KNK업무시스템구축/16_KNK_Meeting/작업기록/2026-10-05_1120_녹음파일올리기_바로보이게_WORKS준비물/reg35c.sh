#!/bin/bash
# z1138 남은 시험 — 마이크 안내 1종 + 앞 묶음에서 시간 때문에 못 돈 서버 시험 6종
SP="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad"
B="/c/Users/top00/JR/Claude 코드/KNK업무시스템구축/16_KNK_Meeting/작업기록"
W35="$B/2026-10-05_1120_녹음파일올리기_바로보이게_WORKS준비물"
R="$SP/z1127/reg"
APPW="C:/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1138/app_new"
APPU="$SP/z1138/app_new"
P313="/c/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"; P312="/c/Users/top00/AppData/Local/Programs/Python/Python312/python.exe"
OUT="$W35/reg_summary_z1138c.txt"; : > "$OUT"
kill_port(){ "$W35/killport.sh" "$1" || { echo "[포트 $1] 비우지 못함 — 중지" >> "$OUT"; return 1; }; }
res(){ local name="$1" log="$2"; echo "== $name: $(grep -E '합계|통과 [0-9]+ [·/] 실패|=====.*통과|결과: [0-9]+ ?(/|통과)' "$log" | tail -1)" >> "$OUT"; grep -E "^\s*(FAIL|\[FAIL\])|❌|Traceback" "$log" | head -6 >> "$OUT"; }

# ── ① 마이크 안내 (run_mic_app.py 는 옆 파일 which_app.txt 로 앱 사본을 고른다)
printf '%s' "$APPW" > "$R/which_app.txt"
kill_port 8932 && { rm -f "$R/srv_8932.log"; ( cd "$R" && "$P313" run_mic_app.py > "$R/srv_8932.log" 2>&1 & )
  for i in $(seq 1 120); do grep -q "^READY" "$R/srv_8932.log" 2>/dev/null && { sleep 2; break; }; sleep 1; done
  if grep -q "^READY" "$R/srv_8932.log" 2>/dev/null; then
    timeout 900 "$P312" "$B/2026-09-17_1414_녹음화면PC안내문구_WORKS준비물/mic_text_test.py" "$R" > "$R/mic_text.log" 2>&1
    res mic_text_test "$R/mic_text.log"
  else echo "== mic_text_test: READY 안 뜸(실측 없음)" >> "$OUT"; tail -3 "$R/srv_8932.log" >> "$OUT"; fi; }
kill_port 8932

# ── ② 서버 시험 6종 (TestClient · 사본 DB 를 새로 만들어 각각)
for t in "2026-09-21_2313_회의록삭제_두번확인_이음회의연동_WORKS준비물/verify_del.py" \
         "2026-09-22_0022_이음회의삭제도_회의록함께_WORKS준비물/verify_z1123.py" \
         "2026-09-26_2305_취소알림문구_새규칙맞춤_WORKS준비물/verify_z1126.py" \
         "2026-09-27_2040_회의종료단추_공유안내_WORKS준비물/verify_end_z1131.py" \
         "2026-09-29_2103_참석자도_녹음과_회의록작성_WORKS준비물/verify_attendee_z1133.py" \
         "2026-09-29_2230_참석자명단_이음과맞추기_WORKS준비물/verify_att_sync_z1134.py"; do
  n=$(basename "$t" .py); ( cd "$APPU" && rm -rf data meeting_audio && timeout 900 "$P313" "$B/$t" > "$R/$n.log" 2>&1 ); res "$n" "$R/$n.log"; done
echo "ALLDONE-SRV" >> "$OUT"
