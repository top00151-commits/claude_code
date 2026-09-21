#!/bin/bash
# z1124 배포 — origin/main 위에 파일 2개(meetings.html·BAT)만 얹어 커밋·푸시(작업 트리·인덱스는 건드리지 않음)
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-22_0815_모아보기_회의록열기_이름맞춤_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1124/idx_z1124"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in "meetings.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meetings.html" "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"; B=$(git hash-object -w --no-filters "$W/$src") || exit 1; git update-index --cacheinfo 100644,$B,"$dst" || exit 1; done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
fix(works/meeting): 「🗓 회의 카드 모아보기」 단추 이름 「📝 회의록 화면」 → 「📋 회의록 열기」 (z1124)

대표 지시(09-22 08시): 「회의록 열기로 맞춰」 — 이음 회의 카드(v807 · 진행 중·정리 중·실패)와 같은 이름.
가는 곳·여는 방식은 그대로(이름만) · 녹음하던 본인은 「🎙 이어서 녹음」·정리 끝은 「📋 회의록 보기」 그대로.
업무 시간(특히 08:50~09:30)을 피해 저녁에 배포.

검증: 고치기 전 파일로 새 이름 시험 실패(모아보기 원래 화면·삭제 화면) · 회귀 전부 · 표준 검사기.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
