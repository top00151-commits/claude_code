#!/bin/bash
# z1139 배포 — origin/main 위에 파일 3개(main.py · meeting_form.html · BAT)만 얹어 커밋·푸시
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-10-06_0012_정리글_바로고치기_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1139/idx_z1139"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in \
  "main.py|KNK업무시스템구축/01_HAIST_WORKS/app/main.py" \
  "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" \
  "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"
  B=$(git hash-object -w --no-filters "$W/$src") || exit 1
  git update-index --add --cacheinfo 100644,$B,"$dst" || exit 1
done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -5
MSG=$(cat <<'EOM'
feat(works/meeting): 「📋 회의록 정리」 글을 사람이 바로 고친다 (z1139)

대표 지시(2026-10-05): 「회의록 정리시 음성 인식이 잘못되어서 잘못 작성한 부분은 어떻게 수정을 해야하지?」
그때까지 정리 글은 읽기 전용이고 서버도 AI 정리로만 썼다 → 낱말 하나를 고치려 해도 원문을 고쳐
「🔄 다시 정리」로 AI 를 통째로 다시 돌려야 했고, 그러면 다른 문장 표현까지 바뀌었다.
대표 결정: 「정리 글을 바로 고치기」.

- 새 입구 `POST /api/meeting/{mid}/summary` — 고친 글을 그대로 저장(AI 를 부르지 않는다)
  · 권한은 회의록 고치기와 같다(작성자·이음 등록 담당·관리자/대표·그 회의 참석자 — z1133)
  · 먼저 저장 충돌(base_ts) 409 · 활동기록 `meeting_summary_edit` 로 누가 고쳤는지 남김
  · 20000자 상한 · 앞뒤 빈칸만 다듬고 줄바꿈 보존 · 같은 글이면 changed=false
- 화면: 정리 칸 머리에 「✏ 고치기」(고칠 수 있는 사람에게만) → 그 자리가 글칸으로 · 「💾 정리 저장」·「취소」
  · 🔴 `#sumEditWrap[hidden], #mtgSummary[hidden] { display:none !important }`(display 가 hidden 을 덮는다)
- 🔴 손으로 고친 뒤 「🔄 다시 정리」를 누르면 한 번 묻는다(고친 글이 사라지므로)
- 결정사항·할 일·회의 원문·제목·장소는 건드리지 않는다

검증: 서버 27(지금 운영 코드로는 18 실패) · 화면 23(1 실패 뒤 중단) · 회귀 묶음 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
