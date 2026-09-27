#!/bin/bash
# z1130 배포 — origin/main 위에 파일 2개(meeting_form.html·BAT)만 얹어 커밋·푸시(작업 트리·인덱스는 안 건드림)
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-27_1900_휴대폰은녹음기한길만_화면단순화_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1130/idx_z1130"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"; B=$(git hash-object -w --no-filters "$W/$src") || exit 1; git update-index --cacheinfo 100644,$B,"$dst" || exit 1; done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
fix(works/meeting): 휴대폰은 녹음기 한 길만 — 화면 단순화 + 「녹음 시작」 먹통 고침 (z1130)

대표 신고(2026-09-27): 「녹음기로 녹음할게요를 누르면 아래로 내려가고, 녹음 시작을 눌러도 아무 변화가 없다.
너무 복잡하게 순서가 꼬였다. 다른 방법을 찾아 달라.」

🔴 버그: 「휴대폰 녹음기로 녹음할게요」가 _phrecChosen 을 켜 두면 recStart 가 조용히 되돌아갔다
   (서버 요청 0건·오류 표시도 없음 · 화면 시험으로 재현) → 사람이 「녹음 시작」을 직접 누르면 표시를 푼다.

단순화(대표 결정 「휴대폰은 녹음기 한 길만」):
- 새 회의록·상세 화면 = 안내 2줄(홈 화면 「음성 녹음」 → 공유 → KNK WORKS) + 「📁 올리기」만
- 이 화면 녹음·짧은 녹음·기기별 안내는 「다른 방법」 접기 안으로(녹음이 시작되거나 멈춘 녹음 상자가 뜨면 자동으로 펼침)
- 이음 「▶ 회의 시작」의 30초 자동 시작 삭제(화면을 떠나 있으면 빈 녹음이 된다)
- 옛 고르기 상자(recPhoneLead)는 안드로이드에서 쓰지 않음 · 아이폰·PC 는 그대로

검증: 새 화면 33(지금 운영 파일로는 4) · 회귀 24종 전부 통과(실패 0) · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
