#!/bin/bash
# z1133 배포 — origin/main 위에 파일 2개(main.py · BAT)만 얹어 커밋·푸시
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-29_2103_참석자도_녹음과_회의록작성_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1133/idx_z1133"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in \
  "main.py|KNK업무시스템구축/01_HAIST_WORKS/app/main.py" \
  "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"
  B=$(git hash-object -w --no-filters "$W/$src") || exit 1
  git update-index --add --cacheinfo 100644,$B,"$dst" || exit 1
done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
feat(works/meeting): 회의 참석자도 녹음·녹음파일 올리기·회의록 작성·회의 종료 (z1133)

대표 지시(2026-09-28): 「회의록 녹음 및 녹음파일 올리는거 회의록 정리하는거 지금은 회의 만든 작성자만
허용이 되는 것 같은데… 회의 참석자 누구나 녹음파일 등록 및 회의록 작성할 수 있게 해줘.」
대표 결정(범위): 「⏹ 회의 종료」까지 열고, 🗑 삭제는 그대로(작성자·관리자/대표).

- `_can_edit_meeting` 에 **그 회의 참석자**(meeting_attendees.user_id) 추가 · `_can_end_meeting` 도 같게
- 참석자 명단은 이음 「▶ 회의 시작」이 사번으로 연결해 저장한 것(이름 맞추기 아님 · 운영 43/46 줄 연결)
- 한 번에 열리는 것: 녹음 시작·조각·끝내기 · 📁 올리기 · 공유로 붙이기 · 음성→글자 · 🔄 다시 정리 ·
  본문/제목 저장 · 결정사항·할 일 추가/삭제 · 프로젝트/기회 연결 · ⏹ 회의 종료
- 권한 함수가 DB 를 보므로 열린 커서 `c` 를 받게 하고(부르는 곳 15군데 전달), 안 넘기면 짧게 새로 열어 본다
  (안 넘겼다고 조용히 권한이 사라지지 않게 · WAL 이라 읽기는 서로 막지 않음)

검증: 서버 30(지금 운영 코드로는 10개 실패 뒤 중단) · 화면 12(운영 코드로는 5 실패) · 회귀 26종 전부 통과(실패 0) · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
