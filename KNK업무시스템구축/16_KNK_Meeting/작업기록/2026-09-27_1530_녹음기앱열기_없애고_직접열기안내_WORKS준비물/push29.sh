#!/bin/bash
# z1129 배포 — origin/main 위에 파일 2개(meeting_form.html·BAT)만 얹어 커밋·푸시(작업 트리·인덱스는 안 건드림)
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-27_1530_녹음기앱열기_없애고_직접열기안내_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1129/idx_z1129"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"; B=$(git hash-object -w --no-filters "$W/$src") || exit 1; git update-index --cacheinfo 100644,$B,"$dst" || exit 1; done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
fix(works/meeting): 「녹음기 앱 열기」 단추를 없애고 「홈 화면에서 직접 열기」 3단계 안내로 (z1129)

대표 실물(2026-09-27): 단추를 4번 눌렀고 4번 다 크롬이 거부해 안내로 되돌아왔다(운영 로그 ?recapp=manual 4회).
크롬 문서: BROWSABLE 을 적어 둔 화면만 이 방법으로 열 수 있다 → 삼성 「음성 녹음」은 웹에서 못 연다.
게다가 옛 단추는 누를 때 회의록을 먼저 만들어, 실패할 때마다 빈 회의록이 남았다(46·47·49 정리함).

- 새 회의록 화면: 단추 삭제 → 3단계 안내 카드(①홈 화면 「음성 녹음」 ②공유 → KNK WORKS ③＋ 새 회의록으로 정리)
- 상세 화면: 「📱 휴대폰 녹음기로 녹음할게요」(이 회의 표시 + 30초 자동 시작 취소 · 화면 이동 없음)
- 이음 「▶ 회의 시작」 30초 고르기·기기별 안내·상자 글 전부 새 길에 맞춤
- intent 여는 코드·주소 전부 삭제(빈 회의록이 생기던 길도 함께 사라짐)

검증: 새 화면 33(고치기 전 파일로는 실패) · 회귀 24종 전부 통과(실패 0) · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
