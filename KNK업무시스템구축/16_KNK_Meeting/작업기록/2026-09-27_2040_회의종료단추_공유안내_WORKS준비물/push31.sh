#!/bin/bash
# z1131 배포 — origin/main 위에 파일 5개(main.py · meeting_form.html · meetings.html · 마이그 · BAT)만 얹어 커밋·푸시
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-27_2040_회의종료단추_공유안내_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1131/idx_z1131"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in \
  "main.py|KNK업무시스템구축/01_HAIST_WORKS/app/main.py" \
  "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" \
  "meetings.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meetings.html" \
  "m_z1131_meeting_end.py|KNK업무시스템구축/01_HAIST_WORKS/app/migrations/m_z1131_meeting_end.py" \
  "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"
  B=$(git hash-object -w --no-filters "$W/$src") || exit 1
  git update-index --add --cacheinfo 100644,$B,"$dst" || exit 1
done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -6
MSG=$(cat <<'EOM'
feat(works/meeting): 「⏹ 회의 종료」 단추 + 공유 안내를 사실대로 (z1131)

대표 지시(2026-09-27): 「회의 종료는 어디서 선택할 수 있지? … 종료시간 이전에 끝났을 때는?」
  지금 규칙은 ①녹음이 붙거나 정리되면 즉시 종료 ②녹음 없으면 예정 끝 시각에 자동 종료
  ③녹음 중이면 끝 시각 뒤 12시간 — **사람이 누를 곳이 없었다**.

- meetings.ended_at (마이그 m_z1131_meeting_end · idempotent) + POST /api/meeting/{id}/end(되돌리기 포함)
- 회의록 상세 머리줄에 「⏹ 회의 종료」 / 「✅ 종료됨 · 시:분」 / 「↩ 종료 되돌리기」 (이음 회의에만)
- 누를 수 있는 사람: 작성자(총괄)·관리자/대표·이음 등록자
- 이음·모아보기에 넘기는 칸에 ended·ended_at → 모아보기 카드는 시간 규칙보다 **먼저** 본다
  (이음 회의 카드도 같게 하려면 세션 10 작업 — 요청문 전달)

또 하나(대표 신고): 녹음기 공유 목록에 KNK WORKS 가 없다(그 폰에는 이음만 설치) →
  안내 ②를 「📁 녹음 파일 올리기」 먼저로 바꾸고, 공유는 「앱을 깔아 두면(크롬 ⋮ → 앱 설치)」으로 적었다.

검증: 서버 23 · 화면 22(지금 운영 파일로는 ended_at 칸이 없어 아예 안 돎) · 회귀 24종 전부 통과(실패 0) · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
