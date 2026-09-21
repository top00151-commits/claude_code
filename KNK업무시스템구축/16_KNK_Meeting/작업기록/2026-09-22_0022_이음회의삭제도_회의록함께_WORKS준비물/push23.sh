#!/bin/bash
# z1123 배포 — origin/main 위에 파일 4개만 얹어 커밋·푸시(작업 트리·인덱스는 건드리지 않음)
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-22_0022_이음회의삭제도_회의록함께_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1123/idx_z1123"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
P="KNK업무시스템구축/01_HAIST_WORKS/app"
for pair in "main.py|$P/main.py" "sso_client.py|$P/sso_client.py" "meeting_form.html|$P/templates/meeting_form.html" "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"; B=$(git hash-object -w --no-filters "$W/$src") || exit 1; git update-index --cacheinfo 100644,$B,"$dst" || exit 1; done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -6
MSG=$(cat <<'EOM'
feat(works/meeting): 이음 🗓 회의에서 지워도 WORKS 회의록까지 함께 — 서버 입구 + 확인 창용 칸 + 취소 알림 안내 (z1123)

대표 결정(09-22 00시): 시작 전 회의를 지우면 참석자에게 취소 알림 · 이음 🗓 회의 창에서 지울 때도 카드 숨김
(회의 알림 방에서 카드 메시지를 지울 때는 아님) · 🗓 에서 지우면 WORKS 회의록(녹음·정리)도 함께 —
작성자·관리자일 때만 · WORKS 에 못 닿으면 아무것도 안 지움 · 🗓 삭제도 두 번 확인. 이음 쪽은 세션 10.

- POST /api/meeting/msg/delete(서버 전용 · 공유키): 이음이 자기 회의를 지우기 전에 부름
  · 회의록 작성자(▶ 회의 시작을 누른 사람)·관리자(admin/ceo) → deleted · 회의록 없음 → none
  · 등록 담당·다른 직원 → kept(not_allowed) · 사번 모름 → kept(viewer_not_found)
  · 🔴 여기서 이음을 다시 부르지 않음(서로 부르며 돌지 않게) · 지우면 활동 기록 · 모아보기 저장본 비움
- msg/status 에 can_delete(WORKS 🗑 삭제와 같은 판단) — 이음 🗓 「삭제」 첫 확인 창 미리보기용
- WORKS 🗑 삭제 뒤 이음이 취소 알림을 보냈으면(notified) 「🔔 … 참석자 N명에게 「회의가 취소되었습니다」」

검증: 서버 45 · 화면 10(고치기 전 파일로는 실패) · z1122 삭제 서버 33·화면 46 · 회귀 19종 · 표준 검사기.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
