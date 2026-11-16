# -*- coding: utf-8 -*-
"""z1191z28 시험 — 작업일정표: 칸을 고친 뒤 곧바로 다른 칸을 누르면 첫 클릭이 조용히 무시되던 병 (대표 2026-11-16 「진행해」)
  원인: 칸 저장이 서버 응답을 기다리는 동안 잠금(_editing)을 쥐고 있었다 — 그사이 누른 칸은 `if(_editing) return;` 으로 버려짐.
        (예전 코드에서 운영처럼 응답을 0.8초 늦추면: 세금계산서 창 안 뜸 · 두 번째 칸이 안 열려 친 글이 사라짐 · 고객사 다음 클릭 무시)
  고침 규칙(이 시험이 지킨다)
    ① 칸 편집기(startEdit ~ startSelectEdit)는 잠금을 직접 null 로 만들지 않는다 → _edFree(td)(그 칸 잠금일 때만)
    ② 저장을 시작하면(마무리 첫머리) 그 칸 잠금을 푼다 — _edPending(td)
    ③ 칸에서 나갈 때(blur · 날짜 달력 대기 · 고객사 목록 대기)는 잠금만 푼다 — _edRelease(td) (「저장 중」 표시는 안 단다:
       저장 뒤 입력칸이 지워질 때 브라우저가 blur 를 한 번 더 보내 표시가 남던 것을 실측으로 잡음)
    ④ 저장 중인 바로 그 칸은 다시 열지 않는다(표시·남은 입력칸)
  화면 동작은 `scratchpad/realcheck28_run.py`(운영 자료 · 이새롬 권한 · 응답 0.8초 지연)로 확인.
"""
import io, os, re, sys
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = io.open(os.path.join(ROOT, "app", "templates", "schedule_board.html"), encoding="utf-8").read()
OK = FAIL = 0


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", name)
    else:
        FAIL += 1; print("  ❌", name, ("  ← %r" % (got,))[:300] if got != "" else "")


a, b = src.find("function startEdit(td){"), src.find("async function taxSave(")
seg = src[a:b] if (a >= 0 and b > a) else ""
chk("칸 편집기 구간을 찾음(startEdit ~ taxSave 앞)", bool(seg))
chk("공용 세 함수가 있다(_edPending · _edFree · _edRelease)",
    all(("function %s(td)" % f) in src for f in ("_edPending", "_edFree", "_edRelease")))
chk("_edFree · _edRelease 는 그 칸 잠금일 때만 푼다(_editing.td===td)",
    re.search(r"function _edFree\(td\)\{[^\n]*_editing\.td===td", src) is not None
    and re.search(r"function _edRelease\(td\)\{[^\n]*_editing\.td===td", src) is not None)
chk("① 칸 편집기 안에 `_editing=null` 이 없다(모두 _edFree)", "_editing=null" not in seg, seg.count("_editing=null"))
chk("① _edFree(td) 가 20곳 이상(모든 마무리 갈래)", seg.count("_edFree(td)") >= 20, seg.count("_edFree(td)"))
fin = re.findall(r"if\(done\) return; done=true;([^\n]*)", seg)
chk("② 편집기 6개 마무리 첫머리 모두 저장이면 _edPending", len(fin) == 6 and all("_edPending(td)" in x for x in fin), fin)
chk("③ 날짜 칸 blur(달력 대기)는 잠금만 푼다(_edRelease · 「저장 중」 표시 안 함)",
    re.search(r"function _bindCellBlur[\s\S]{0,400}_edRelease\(inp\.closest\('td'\)\)", src) is not None
    and not re.search(r"function _bindCellBlur[\s\S]{0,400}_edPending", src))
chk("③ 고객사 칸 blur(목록 대기 0.18초)도 잠금만 푼다", "_edRelease(td); setTimeout(function(){ finish(true); }, 180)" in seg)
chk("④ 저장 중인 그 칸은 다시 열지 않는다(표시·남은 입력칸 · 알림)",
    re.search(r"function startEdit\(td\)\{\n  if\(_editing\) return;\n  if\(td\.dataset\.knkPending \|\| td\.querySelector\('input\.cell-input, select\.cell-input'\)\)\{ toast\('저장 중", seg) is not None)
print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
