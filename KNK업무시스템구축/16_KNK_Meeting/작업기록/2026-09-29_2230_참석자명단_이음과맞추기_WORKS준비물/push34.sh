#!/bin/bash
# z1134 배포 — origin/main 위에 파일 2개(main.py · BAT)만 얹어 커밋·푸시
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-29_2230_참석자명단_이음과맞추기_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1134/idx_z1134"; rm -f "$GIT_INDEX_FILE"
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
feat(works/meeting): 이음에서 참석자를 바꾸면 WORKS 회의록 명단도 따라간다 (z1134)

대표 지시(2026-09-29): 「이음에서 참석자를 나중에 바꿔도 WORKS 명단은 「회의 시작」을 누른 시점 값으로
남습니다 → 이거 맞춰」. z1133 부터 그 명단이 곧 권한(녹음·올리기·회의록 작성·회의 종료)이라,
명단이 낡으면 새 참석자가 아무것도 못 하고 빠진 사람이 계속 고칠 수 있었다.

- 새 도우미 `_msg_sync_attendees(c, m, att_emps, externals)` — 사번은 정확히 1명일 때만 연결(추측 금지) ·
  계정 없는 사람은 이름만 · 뺄 사람만 빼고 새로 온 사람만 넣는다(멱등) · `attendees_text` 도 같은 순서로
- 새 입구 `POST /api/meeting/msg/attendees`(서버 전용 공유키) — 이음이 참석자를 바꿔 저장한 뒤 한 번 부른다
  · 회의록이 아직 없으면 아무것도 만들지 않고 `result:"none"` · 이음을 되부르지 않음
  · 참석자 칸이 아예 없는 본문은 400 으로 거절(부르는 쪽 실수로 전원이 지워지지 않게)
- 「▶ 회의 시작」이 다시 불릴 때도 같은 도우미로 맞춘다(안전망 · 처음 만들기는 예전 그대로)
- 대표 결정: 빠진 사람은 그 뒤로 못 고침(이미 올린 것은 남음) · 녹음 중인 사람은 빼지 않음(끝난 뒤 빠짐) ·
  작성자·이음 등록 담당은 명단과 무관하게 그대로

검증: 서버 48(지금 운영 코드로는 25 실패) · 회귀 26종 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
