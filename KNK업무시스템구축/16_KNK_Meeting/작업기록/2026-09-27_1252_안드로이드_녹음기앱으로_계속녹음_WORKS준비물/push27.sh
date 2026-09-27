#!/bin/bash
# z1127 배포 — origin/main 위에 파일 2개(meeting_form.html·BAT)만 얹어 커밋·푸시(작업 트리·인덱스는 건드리지 않음)
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-27_1252_안드로이드_녹음기앱으로_계속녹음_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1127/idx_z1127"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"; B=$(git hash-object -w --no-filters "$W/$src") || exit 1; git update-index --cacheinfo 100644,$B,"$dst" || exit 1; done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
feat(works/meeting): 안드로이드 녹음 — 「📱 녹음기 앱 열기」를 첫 선택으로(다른 앱을 봐도 계속 녹음) (z1127)

대표 실사(09-26): capture 로 연 녹음기는 '불려 나온 모드'라 다른 앱으로 넘어가면 녹음을 끝내고 저장하고
길이 상한도 걸린다(대표 사진 「최대 05:16」) → 옛 부제 「다른 앱을 봐도 끊기지 않아요」는 거짓이었다.

- 새 단추: 녹음기 앱 자체를 여는 intent(LAUNCHER · 삼성/구글 자동 선택) → 알림줄에 남아 계속 녹음
- 끝난 파일: 녹음기 「공유 → KNK WORKS」(설치 앱) 또는 「📁 음성 파일 올리기」
- 옛 단추는 「📱 녹음기로 바로 녹음(짧은 회의)」로 작게 · 한계를 사실대로
- 못 열면 ?recapp=manual 로 돌아와 손으로 여는 길 안내(상세=상자 · 새 회의록=상태줄)

검증: 새 화면 31(고치기 전 실패) · 휴대폰 3종 새 문구(45·26·25) · 창 닫힌 녹음 74 · 회귀 전부 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
