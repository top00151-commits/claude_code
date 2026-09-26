#!/bin/bash
# z1125 배포 — origin/main 위에 파일 3개(main.py·meeting_form.html·BAT)만 얹어 커밋·푸시(작업 트리·인덱스는 건드리지 않음)
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-09-26_2121_회의록지울때_녹음파일도함께_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1125/idx_z1125"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in "main.py|KNK업무시스템구축/01_HAIST_WORKS/app/main.py" "meeting_form.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/meeting_form.html" "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"; B=$(git hash-object -w --no-filters "$W/$src") || exit 1; git update-index --cacheinfo 100644,$B,"$dst" || exit 1; done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
feat(works/meeting): 회의록을 지우면 그 회의의 녹음 파일도 서버에서 함께 지움 (z1125)

대표 결정(09-26): 「지울때 함께 지워」 — 전에는 DB 줄만 지우고 meeting_audio/meeting_<번호>/ 가 서버에 남았다
(화면에선 안 보이지만 파일은 남음 · 운영 고아 폴더 27개 32.8MB 실측).

- 새 도우미 _meeting_audio_purge: 그 회의 폴더 하나만 · meeting_audio 밖·_share 는 안 건드림
  · 지우다 실패해도 회의록 삭제는 유지(기록만) · 디스크가 느릴 수 있어 스레드에서
- WORKS 🗑 삭제 · 이음 🗓 삭제 입구(msg/delete · result=deleted 일 때만) 둘 다에서 호출
  🔴 이음과 무관한 회의 길에는 run_in_threadpool 이름이 없어 부르는 자리마다 불러온다
- 확인 창 글에 「녹음 파일도 서버에서 지워집니다」

검증: 서버 19(고치기 전 파일로는 실패) · 회귀 전부 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
