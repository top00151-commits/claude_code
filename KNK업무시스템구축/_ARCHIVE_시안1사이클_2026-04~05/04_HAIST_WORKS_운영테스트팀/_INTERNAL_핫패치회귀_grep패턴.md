# [04 INTERNAL] 힐링 핫패치 회귀 grep 패턴 사전 준비

> 작성: 04 운영테스트팀 빅터 · 일자: 2026-04-25
> 목적: 01 회신 도착 즉시 grep 4/4 PASS 재현
> 사전 조건: 01 P1 (i18n FAIL · 빅터도크 FAIL) 회신 수령 후 즉시 실행

---

## A. 회귀 검증 grep 패턴 4종

### G1. 빅터 도크 토글 함수 무결성
```
패턴: victorToggleDock\s*\(
대상: 01_HAIST_WORKS/app/templates/base.html
기대: ≥ 2건 (헤더 트리거 onclick + 도크 닫기 버튼)
FAIL 조건: < 2 또는 함수 정의부 없음
```

### G2. i18n 키 누락 가드 (`{{ i.* | default(...) }}`)
```
패턴: \{\{\s*i\.[a-z_]+\s*\|\s*default\(
대상: 01_HAIST_WORKS/app/templates/base.html
기대: ≥ 30건 (헤더·사이드바·도크 전반)
FAIL 조건: default 가드 없는 i.* 키 존재 시 i18n 미정의 경로에서 빈 문자열 노출
```

### G3. 사이드바 height + overflow 정의
```
패턴: \.sidebar\s*\{[^}]*height:\s*calc\(100vh
대상: 01_HAIST_WORKS/static/style.css
기대: ≥ 1건 (line 618 부근)
multiline: true
FAIL 조건: 0건 시 사이드바 무한 길이로 도크 위치 오작동 우려
```

### G4. 빅터 도크 컨테이너 + aria-label 동시 존재
```
패턴1: id=["']victorTrigger["']
패턴2: aria-label=["'][^"']*빅터[^"']*["']
대상: 01_HAIST_WORKS/app/templates/base.html
기대: 두 패턴 모두 동일 라인 또는 동일 element 내
FAIL 조건: 한쪽만 있으면 도크 트리거 식별 불완전
```

---

## B. 자동화 스크립트 골격 (Bash, 미실행)

```bash
#!/usr/bin/env bash
# 04_HAIST_WORKS_hotpatch_regression.sh
# 사용: 01 회신 도착 후 04 세션에서 실행
set -uo pipefail

ROOT="C:/Users/top00/JR/Claude 코드/KNK업무시스템구축/01_HAIST_WORKS"
BASE="$ROOT/app/templates/base.html"
CSS="$ROOT/static/style.css"

PASS=0; FAIL=0
check() {
  local name="$1" expected="$2" actual="$3"
  if [ "$actual" -ge "$expected" ]; then
    echo "[PASS] $name : $actual ≥ $expected"
    PASS=$((PASS+1))
  else
    echo "[FAIL] $name : $actual < $expected"
    FAIL=$((FAIL+1))
  fi
}

# G1
n1=$(grep -cE 'victorToggleDock\s*\(' "$BASE")
check "G1 victorToggleDock"        2  "$n1"

# G2
n2=$(grep -cE '\{\{\s*i\.[a-z_]+\s*\|\s*default\(' "$BASE")
check "G2 i18n default guard"      30 "$n2"

# G3 (multiline은 awk 보조)
n3=$(awk '/\.sidebar[[:space:]]*\{/,/\}/' "$CSS" | grep -cE 'height:\s*calc\(100vh')
check "G3 sidebar height calc"     1  "$n3"

# G4
n4a=$(grep -cE 'id=["'\'']victorTrigger["'\'']' "$BASE")
n4b=$(grep -cE 'aria-label=["'\''][^"'\'']*빅터' "$BASE")
n4=$(( n4a < n4b ? n4a : n4b ))
check "G4 victorTrigger+aria"      1  "$n4"

echo "===== RESULT: $PASS PASS / $FAIL FAIL ====="
exit $FAIL
```

---

## C. 실행 절차 (01 회신 도착 후)

1. 01 P1 회신 수령 확인 → `_FROM_01_*` 파일 존재 여부
2. 위 스크립트 dry-run (수동 grep 4건)
3. 4/4 PASS 확인되면 `_TO_09팀장_2026-04-25_핫패치회귀결과.md` 발행
4. 1건이라도 FAIL 시 즉시 09 팀장에게 보고 + 01 재요청

---

## D. 비간섭 원칙 재확인

- 본 스크립트는 grep 전용 — 코드/DB/서버 미접촉
- 서버 기동 불필요 (정적 분석만)
- 01 회신 도착 전 선제 실행 금지

---

*04 빅터 · 2026-04-25 · T3/3 (사전 준비 완료, 실행 대기)*
