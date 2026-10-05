#!/bin/bash
# z1138 배포 — origin/main 위에 파일 2개(meeting_form.html · BAT)만 얹어 커밋·푸시
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-10-05_1120_녹음파일올리기_바로보이게_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1138/idx_z1138"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in \
  "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" \
  "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"
  B=$(git hash-object -w --no-filters "$W/$src") || exit 1
  git update-index --add --cacheinfo 100644,$B,"$dst" || exit 1
done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
fix(works/meeting): 「📁 녹음 파일 올리기」를 회의록 맨 위 큰 단추로 (z1138)

대표 지시(2026-10-05): 「회의록 작성시 녹음을 휴대폰 녹음기로 녹음을 하고 그걸 올리는 메뉴가 바로
보이질 않아 찾는데 조금 어려워… 녹음한 파일 올리기 아이콘이 쉽게 보였으면 해」

원인: 올리기 단추가 「🔧 다시 하기 · 녹음 추가(필요할 때만)」 접힌 칸 안에만 있었다. 휴대폰 녹음기로
녹음을 마치고 회의록을 다시 열면 그 칸은 접힌 채 화면 아래(폰 순서 11)로 내려가 올리는 자리로 보이지
않았다. 게다가 안내문은 「📁 녹음 파일 올리기」, 단추는 「📁 음성 파일 올리기」로 이름이 달랐다.

- 새 칸 `#recUpTop` — 진행 카드 바로 아래(폰 order:2 · PC 는 DOM 위쪽) · 큰 단추(108px) + 안내 한 줄
- 대표 결정: 녹음이 없을 때만 크게 보인다 → 녹음이 들어오면(올리기 성공·이 화면 녹음 시작) 감춘다 ·
  녹음 중이던 회의는 그 자리가 「🔴 녹음 중이던 회의」
- 올리는 길은 하나만 — 새 입력칸을 기존 `onPickFile` 에 이어 붙임(검사·업로드·자동 정리 그대로)
- 접힌 칸 안의 알림 글은 안 보이므로 `recSt` 가 맨 위 칸에도 같은 글을 쓴다
- 이름 통일 10곳 — 「📁 음성 파일 올리기」 → 「📁 녹음 파일 올리기」
- `.mf-section` 의 display 가 hidden 을 덮어 `#recUpTop[hidden]{display:none !important}`

검증: 화면 22(지금 운영 코드로는 2개 실패 뒤 중단) · 회귀 묶음 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
