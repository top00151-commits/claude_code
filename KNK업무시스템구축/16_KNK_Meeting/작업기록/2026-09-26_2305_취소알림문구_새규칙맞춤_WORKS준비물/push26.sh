#!/bin/bash
# z1126 배포 — origin/main 위에 파일 2개(meeting_form.html·BAT)만 얹어 커밋·푸시(작업 트리·인덱스는 건드리지 않음)
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-26_2305_취소알림문구_새규칙맞춤_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1126/idx_z1126"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"; B=$(git hash-object -w --no-filters "$W/$src") || exit 1; git update-index --cacheinfo 100644,$B,"$dst" || exit 1; done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
fix(works/meeting): 회의 취소 알림 글을 새 규칙에 맞춤 — 「참석자 N명에게 알림」·확인 창 미리 안내 (z1126)

대표 결정(09-26): 「다른 참석자 있으면 알림」 — 이음 v821(23:19 LIVE)이 시작 전·후 구분 없이
「나 말고 참석자가 있으면」 취소 알림을 보낸다(혼자 만든 회의는 조용히).
발단: 「삭제하면 그냥 삭제돼서 기존 회의를 취소한 건지 원래 없었던 건지 헷갈린다」.

- 삭제 뒤 알림: 「🔔 시작 전 회의라 참석자 N명…」 → 「🔔 참석자 N명에게 「회의가 취소되었습니다」 알림이 갔습니다」
- 첫 확인 창(이음 회의도 함께 지울 때): 「(나 말고 참석자가 있으면 「회의가 취소되었습니다」 알림이 갑니다)」
- 옛 규칙을 말하던 주석도 교체

검증: 서버 21 · 화면 13(고치기 전 파일로는 2·3개 실패) · 회귀 24종 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
