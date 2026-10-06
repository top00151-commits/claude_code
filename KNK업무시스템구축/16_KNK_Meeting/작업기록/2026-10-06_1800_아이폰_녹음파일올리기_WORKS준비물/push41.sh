#!/bin/bash
# z1141 배포 — origin/main 위에 파일 2개(meeting_form.html · BAT)만 얹어 커밋·푸시
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-10-06_1800_아이폰_녹음파일올리기_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1141/idx_z1141"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in \
  "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" \
  "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"
  B=$(git hash-object -w --no-filters "$W/$src") || exit 1
  git update-index --add --cacheinfo 100644,$B,"$dst" || exit 1
done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
fix(works/meeting): 아이폰에서 「📁 녹음 파일 올리기」가 먹통이던 것 (z1141)

직원 신고(2026-10-06): 박성수 프로(사번 317 · 아이폰) — 「녹음파일 올리기 눌러서 누르면 반응이 없어」
(`기산로 3.m4a` 15.5MB · 30:10)

실측: 서버에 요청이 아예 안 들어왔다(올리기 기록 0건) → 휴대폰 안에서 막힌 것.
용량·길이·서버 설정 문제가 아니다(같은 날 14:56 에는 성공한 적 있음).

아이폰에서 알려진 두 가지를 함께 고쳤다:
- 고를 수 있는 파일 조건이 `audio/*` 하나뿐이라 아이폰이 좁게 해석해 녹음 파일이 안 눌리는 일이 있다
  → 서버 `_MEETING_AUDIO_EXT` 와 똑같이 확장자 12개를 함께 적었다
  (.m4a .mp3 .mp4 .wav .webm .ogg .oga .aac .3gp .mpeg .mpga .caf — 고를 수 있는데 서버가 퇴짜 놓지 않게)
- `display:none` 은 아이폰에서 파일 고르기 창 자체가 안 열리는 일이 있다
  → `.knk-file-vh`(안 보이게 하되 「없는 것」으로 만들지 않음 · 자리도 차지하지 않음)

🔴 「📱 녹음기로 바로 녹음」(recFileCap)의 accept 는 그대로 뒀다 — 확장자를 붙이면 아이폰이
   녹음기 대신 파일 고르기를 열 수 있다. 숨기는 방식만 함께 바꿨다.
🔎 크롬으로는 아이폰 파일 고르기를 재현할 수 없다 → 신고자 실물 확인 필요.

검증: 화면 16(지금 운영 코드로는 4 실패) · 파일 고르기 창 열림 두 자리 · 실제 .m4a 올리기 ·
화면 회귀 14종 전부 통과 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
