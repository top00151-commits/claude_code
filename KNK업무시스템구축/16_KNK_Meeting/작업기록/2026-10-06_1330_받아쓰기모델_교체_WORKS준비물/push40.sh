#!/bin/bash
# z1140 배포 — origin/main 위에 파일 2개(ai_client.py · BAT)만 얹어 커밋·푸시
cd "/c/Users/top00/JR/Claude 코드" || exit 1
W="KNK업무시스템구축/16_KNK_Meeting/작업기록/2026-10-06_1330_받아쓰기모델_교체_WORKS준비물/out"
export GIT_INDEX_FILE="/c/Users/top00/AppData/Local/Temp/claude/C--Users-top00-JR-Claude---/31b97fce-95eb-4c01-8a66-eddd91b2bd12/scratchpad/z1140/idx_z1140"; rm -f "$GIT_INDEX_FILE"
git read-tree origin/main || exit 1
for pair in \
  "ai_client.py|KNK업무시스템구축/01_HAIST_WORKS/app/ai_client.py" \
  "KNK_시작.bat|KNK업무시스템구축/KNK_시작.bat"; do
  src="${pair%%|*}"; dst="${pair##*|}"
  B=$(git hash-object -w --no-filters "$W/$src") || exit 1
  git update-index --add --cacheinfo 100644,$B,"$dst" || exit 1
done
TREE=$(git write-tree) && git -c core.quotepath=false diff --stat origin/main $TREE | tail -4
MSG=$(cat <<'EOM'
fix(works/meeting): 받아쓰기 모델을 이음과 같은 gpt-transcribe 로 (z1140)

대표 지시(2026-10-06): 「녹음 파일을 너무 잘못 분석을 한 것 같아.. 이건 교정 사전을 사용한다고 해서
해결될 사항은 아닌 것 같아」

같은 녹음 5분을 다섯 번 받아써 비교(운영 회의 53):
- 🔴 지금 모델(whisper-1)은 **회의 앞 20초를 통째로 빠뜨렸다**
- 코그넥스→「코고넥스」 · 동글→「동굴」 · OKNG→「OK 엔지」 · 2D→「3D」 · 기술적으로→「교수적으로」
- gpt-transcribe 는 그 낱말을 거의 다 맞히고 더 빠르다(15초→8~10초). 값도 더 싸다.
- 이음(메신저)은 2026-07-31 대표 지시로 이미 바꿔 석 달째 쓰고 있다.

- `ai_client.ai_transcribe` 한 함수만 교체 — 모델=`KNK_WORKS_STT_MODEL`(기본 gpt-transcribe),
  실패하면 `KNK_WORKS_STT_FALLBACK`(기본 whisper-1)로 자동으로 한 번 더
- 신형은 `response_format=json` + `extra_body.languages`(복수) / 구형은 `language`(단수)
- 🔴 넣지 않은 것(재 보고 뺌): 한국어 지정(효과 없고 베트남 직원 52명 회의를 망칠 위험) ·
  힌트 낱말(이득 없음) · 소리 품질 96kbps(효과 증명 못 함)
- 🔧 되돌리기 = 환경변수 `KNK_WORKS_STT_MODEL=whisper-1` 한 줄

검증: 서버 22(옛 코드로는 바로 중단) · 실제 녹음으로 끝까지 성공(10초·2,011자) ·
회귀 서버 13종 전부 통과 · 표준 검사기.

EOM
)
C=$(echo "$MSG" | git commit-tree $TREE -p origin/main) && echo "commit=$C" && git push origin $C:main 2>&1 | tail -1 && date '+푸시 %H:%M:%S'
