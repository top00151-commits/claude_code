#!/bin/bash
# z1142 배포 — origin/main 위에 파일 4개(ai_client · main · admin_ai_settings · BAT)만 얹어 커밋·푸시
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-10-07_1130_회의록_용어로_바로잡기_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1142/idx_z1142"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in \
  "ai_client.py|KNK업무시스템구축/01_HAIST_WORKS/app/ai_client.py" \
  "main.py|KNK업무시스템구축/01_HAIST_WORKS/app/main.py" \
  "admin_ai_settings.html|KNK업무시스템구축/01_HAIST_WORKS/app/templates/admin_ai_settings.html" \
  "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"
  B=$(git hash-object -w --no-filters "$W/$src") || exit 1
  git update-index --add --cacheinfo 100644,$B,"$dst" || exit 1
done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -6
MSG=$(cat <<'EOM'
feat(works/meeting): 받아쓴 글의 잘못 들린 우리 회사 말을 「정리」에서 바로잡기 (z1142)

대표 지시(2026-10-07): 「우리 용어(MSCC·파트리스트) → MSCC가 아니고 MLCC 야... 해봐」

왜:
앞선 진단(2026-10-07 대회의실 녹음)에서 소리가 작으면 AI 가 못 알아듣고 메운다는 것을 증명했다
(같은 회의 안에서 앞 9분 -40dB · 뒤 5분 -25dB → 같은 소리를 두 방식으로 받아쓴 글의 일치율 73.2% vs 95.4%).
못 들은 말은 못 살린다. 다만 아는 낱말은 맥락으로 바로잡을 수 있다 — 그것만 한다.

만든 것:
- 관리자 → AI 설정에 「회의록에서 바로잡을 우리 회사 말」 칸(app_settings.meeting_terms)
  빈 값 = 기본 목록 · "-" 한 글자 = 끄기 · 4,000자까지
- ai_extract_meeting 이 [이번 회의 정보] 뒤에 그 목록을 붙여 보낸다
  함께 보내는 규칙: 원문에 없는 말은 절대 넣지 않는다 / 제목과 어긋나면 이 목록을 따른다
- 기본 목록: MLCC(MSC·MSCC·MHC 로 잘못 들림), FPCB, 파트리스트(카트리스트), 표면저항(표면장),
  정전기, 러버, PVC, 비딩(입찰), OK/NG 판정, 출하 검사기, 치수 검사, 외관 검사,
  텔레센트릭 렌즈, 코그넥스, 오픈CV, YOLO

실측(같은 회의 원문 3,648자 · 5회 반복):
- 표면장 → 표면저항, 카트리스트 → 파트리스트 = 5/5 바로잡힘
- 목록에만 있고 회의에 없던 말(코그넥스·YOLO·텔레센트릭) = 0회 (억지로 넣지 않는다)
- 회의 제목까지 바로잡으면 MSCC 0 · MLCC 4

🔴 받아쓴 원문(body)은 한 글자도 바꾸지 않는다 — 바로잡기는 정리 글에서만 일어난다
   (사람이 원문과 대조할 수 있어야 한다).
🔴 회의 제목에 틀린 말이 적혀 있으면 그 말만은 흔들린다(7번 ↔ 1번) → 제목도 함께 고쳐야 확실하다.
🔴 _MEETING_EXTRACT_SYSTEM 본문은 한 글자도 건드리지 않았다(실증된 프롬프트 불변).

검증: 서버 동작 18/18(지금 운영 코드로는 8 실패) · 관리자 화면 22/22 두 번(옛 코드는 칸이 없어 멈춤) ·
화면 회귀 14종 358건 전부 통과 · 표준 검사기 전부 통과 · 개념 추적기 6개 층 확인.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
