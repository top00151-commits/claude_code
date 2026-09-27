#!/bin/bash
# z1128 배포 — origin/main 위에 파일 2개(meeting_form.html·BAT)만 얹어 커밋·푸시(작업 트리·인덱스는 안 건드림)
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-27_1443_녹음기앱열기_intent주소_문법고침_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1128/idx_z1128"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"; B=$(git hash-object -w --no-filters "$W/$src") || exit 1; git update-index --cacheinfo 100644,$B,"$dst" || exit 1; done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
fix(works/meeting): 「📱 녹음기 앱 열기」 주소를 문법대로(데이터 없는 intent:) · 못 열릴 수 있음을 사실대로 (z1128)

라이브 검증 중 발견(안드로이드·크롬 공개 소스 확인):
- intent://#Intent;… 는 남은 「//」가 그대로 요청의 데이터가 된다(Intent.parseUri) →
  MAIN·LAUNCHER 걸개는 data 칸이 없어 IntentFilter.matchData 가 NO_MATCH_DATA →
  어느 기종에서도 앱을 못 찾고 곧바로 fallback 으로 떨어졌다. → intent:#Intent;… 로 고침.
- 크롬 문서: BROWSABLE 을 적어 둔 화면만 이 방법으로 열 수 있다 → 녹음기가 그 표시를 안 가졌으면
  그래도 안 열린다(대표 휴대폰에서만 판정) → 화면 글에 「안 열리는 기종도 있습니다 · 홈 화면에서
  「음성 녹음」을 직접 열어 주세요(효과는 같습니다)」를 나란히 적었다.

같은 검증에서 확인: 운영에서 80분(147MB) 휴대폰 녹음 → 조각 4개 → 본문 23,099자 이미 성공(09-26 18:33).

검증: 화면 시험 35(고치기 전 파일로는 6 실패) · 회귀 묶음 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
