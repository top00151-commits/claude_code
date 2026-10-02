# -*- coding: utf-8 -*-
"""z1132 시험 — 작업일정표 날짜 칸 (이새롬 프로 신고 2026-09-29).

신고 원문
  1. 발주일, 납품일도 발행일처럼 **달력창이 뜨게** 해주세요.
  2. 발행일 입력시 **날짜로만** 입력되게 해주세요. 발행일에 금액을 입력해도 저장이 됩니다.

이 시험은 **진짜 코드**만 본다.
  §2 는 schedule_board.html 에서 _dateOk/_normDate/_mkCellInput 원문을 뽑아 node 로 실제 실행한다.
  §3 은 app/database.py 의 date_cell_ok 원문을 뽑아 실제로 돌린다(운영에서 발견된 실제 값으로).
  §4 는 규정을 어긴 코드 10종을 만들어 배포 전 검사기가 정말 잡는지 본다.

실행:  python _검증/test_date_cell_20260929.py
"""
import ast
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "app", "templates")
BOARD = os.path.join(TPL, "schedule_board.html")
DBPY = os.path.join(ROOT, "app", "database.py")
MAINPY = os.path.join(ROOT, "app", "main.py")

OK = FAIL = 0


def sec(t):
    print("\n" + "━" * 72)
    print(t)
    print("━" * 72)


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅ %s" % name)
    else:
        FAIL += 1
        print("  ❌ %s%s" % (name, ("   ← %s" % got) if got else ""))


def read(p):
    return io.open(p, encoding="utf-8").read()


def js_block(src, start_pat):
    """`start_pat` 다음의 '{' 부터 짝이 맞는 '}' 까지 — 코드를 베끼지 않으려고 원문을 잘라 온다."""
    m = re.search(start_pat, src)
    assert m, "원문을 못 찾음: %s" % start_pat
    i = src.index("{", m.end() - 1)
    depth, j = 0, i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start(): j + 1]
        j += 1
    raise AssertionError("괄호 짝이 안 맞음")


board = read(BOARD)

# ════════════════════════════════════════════════════════════════════
sec("§1. 소스 — 공용 한 벌이 제자리에 있는가")
# ════════════════════════════════════════════════════════════════════
chk("화면에 공용 _mkCellInput() 이 있다", "function _mkCellInput(" in board)
chk("화면에 공용 _dateOk() 가 있다", "function _dateOk(" in board)
chk("_mkCellInput 이 날짜 칸에 달력(knk-cal)을 붙인다",
    "knk-cal" in js_block(board, r"function _mkCellInput\(field, cur\)\s*"))
chk("발주일·납품일·거래명세서가 날짜 칸 목록에 있다",
    all(f in board for f in ("'order_date'", "'due_date'", "'statement_date'")))
chk("세금계산서 발행일 3차수도 날짜 칸 목록에 있다",
    all(f in board for f in ("'tax_invoice_date'", "'tax_invoice_date2'", "'tax_invoice_date3'")))

_raw = len(re.findall(r"const inp=document\.createElement\('input'\); inp\.className='cell-input'; inp\.value=cur; inp\.autocomplete='off';\n", board))
chk("표 편집칸을 직접 만드는 자리가 남아 있지 않다(날짜 편집기 2곳)", _raw == 0, "%d곳" % _raw)
chk("편집칸이 공용으로 만들어진다", board.count("_mkCellInput(td.dataset.edit, cur)") == 2,
    "%d곳" % board.count("_mkCellInput(td.dataset.edit, cur)"))
chk("달력을 누른 blur 는 기다렸다 마무리한다(_bindCellBlur)",
    board.count("_bindCellBlur(inp, td.dataset.edit, finish);") == 4,
    "%d곳" % board.count("_bindCellBlur(inp, td.dataset.edit, finish);"))

_saves = ("startEdit", "startUnitEdit", "startTaxInvEdit", "_uxSave")
for fn in _saves:
    b = js_block(board, r"(?m)^function " + fn + r"\(")
    chk("%s 가 저장 전 _dateOk() 를 거친다" % fn, "_dateOk" in b)
chk("세금계산서 발행일 팝업 2곳 모두 막는다",
    board.count("if(!_dateOk(dv)){ _dateWarn(); pd.focus(); return; }") == 2)
chk("묶음 세금계산서 발행일도 막는다", "if(!_dateOk(datev))" in board)
chk("일괄수정도 막는다", "if(_isDateField(field)){ val=_normDate(val); if(!_dateOk(val))" in board)

dbsrc = read(DBPY)
chk("서버에 공용 date_cell_ok() 가 있다", "def date_cell_ok(" in dbsrc)
chk("서버 셀 저장이 날짜를 검사한다", "if field in DATE_CELL_FIELDS and not date_cell_ok(val):" in dbsrc)
mainsrc = read(MAINPY)
# z1136: '정확히 3곳'으로 세면 같은 검사를 쓰는 새 입구가 생길 때마다 깨진다 — '3곳 이상'으로 본다.
#        어느 함수가 거치는지는 검사기 check_date_cell_guard ④ 가 이름으로 확인한다(§4).
chk("서버 세금계산서·호기·묶음 3곳도 검사한다", mainsrc.count("_logi.date_cell_ok(") >= 3,
    "%d곳" % mainsrc.count("_logi.date_cell_ok("))

# ════════════════════════════════════════════════════════════════════
sec("§2. 진짜 JS 실행 — 화면 원문을 node 로 돌린다")
# ════════════════════════════════════════════════════════════════════
js_dateok = js_block(board, r"function _dateOk\(s\)\s*")
js_norm = js_block(board, r"function _normDate\(s\)\s*")
js_isdate = js_block(board, r"function _isDateField\(f\)\s*")
js_mk = js_block(board, r"function _mkCellInput\(field, cur\)\s*")
js_fields = re.search(r"var _DATE_FIELDS = \[[^\]]*\];", board).group(0)

PROBE = """
'use strict';
__FIELDS__
__ISDATE__
__DATEOK__
__NORM__
/* 아주 작은 화면 흉내 — _mkCellInput 이 달력을 붙이는지만 본다 */
var _attached = [];
globalThis.window = { KnkCal: { attach: function(i){ _attached.push(i); } } };
var KnkCal = window.KnkCal;
var document = { createElement: function(){
  return { className:'', value:'', autocomplete:'', placeholder:'', _attrs:{},
           classList: { _c: [], add: function(x){ this._c.push(x); },
                        contains: function(x){ return this._c.indexOf(x) >= 0; } },
           setAttribute: function(k,v){ this._attrs[k] = v; } };
} };
__MK__
var out = {};
out.ok   = ['2026-09-29','2026-02-28','2024-02-29','2026-12-31',''].map(_dateOk);
out.bad  = ['2,280,000','2280000','2026-02-31','2026-13-01','2026-1-5','2026-01-28-1',
            '2026-02-6','확인 중','2026/09/29','오늘','2026-09-29 14:00','-','2023-02-29'].map(_dateOk);
out.norm = ['260618','20260618','2026.06.18','2026/6/8','2026-6-8','2,280,000','확인 중'].map(_normDate);
out.normOk = out.norm.map(_dateOk);
var dcell = _mkCellInput('due_date', '2026-09-29');
var ncell = _mkCellInput('note', '메모');
out.dateHasCal  = dcell.classList.contains('knk-cal');
out.dateHasCell = dcell.classList.contains('cell-input') || dcell.className === 'cell-input';
out.datePlace   = dcell.placeholder;
out.noteHasCal  = ncell.classList.contains('knk-cal');
out.attachedN   = _attached.length;
out.isDate = ['order_date','due_date','statement_date','tax_invoice_date','tax_invoice_date3']
               .map(_isDateField).concat(['note','qty','price','name'].map(_isDateField));
console.log(JSON.stringify(out));
"""
PROBE = (PROBE.replace("__FIELDS__", js_fields).replace("__ISDATE__", js_isdate)
              .replace("__DATEOK__", js_dateok).replace("__NORM__", js_norm)
              .replace("__MK__", js_mk))

tmpd = tempfile.mkdtemp(prefix="z1132_")
jsf = os.path.join(tmpd, "probe.js")
io.open(jsf, "w", encoding="utf-8", newline="\n").write(PROBE)
node_ok = True
try:
    raw = subprocess.check_output(["node", jsf], stderr=subprocess.STDOUT).decode("utf-8", "replace")
    R = json.loads(raw.strip().splitlines()[-1])
except Exception as e:
    print("  ⚠ node 실행 불가 — §2 건너뜀: %s" % e)
    R, node_ok = {}, False

if node_ok:
    chk("⭐신고① — 날짜 칸에 달력이 붙는다(knk-cal)", R["dateHasCal"] is True)
    chk("달력 부품에 실제로 등록된다(KnkCal.attach)", R["attachedN"] == 1, R["attachedN"])
    chk("날짜 칸에 'YYYY-MM-DD' 안내가 붙는다", R["datePlace"] == "YYYY-MM-DD", R["datePlace"])
    chk("날짜가 아닌 칸에는 달력을 안 붙인다(메모)", R["noteHasCal"] is False)
    chk("날짜 칸 판정이 정확하다", R["isDate"] == [True] * 5 + [False] * 4, R["isDate"])
    chk("제대로 된 날짜·빈 값은 통과", all(R["ok"]), R["ok"])
    chk("⭐신고② — 금액('2,280,000')은 막힌다", R["bad"][0] is False)
    chk("숫자만 이어붙인 금액도 막힌다", R["bad"][1] is False)
    chk("없는 날(2026-02-31·2023-02-29)은 막힌다", R["bad"][2] is False and R["bad"][12] is False)
    chk("없는 달(2026-13-01)은 막힌다", R["bad"][3] is False)
    chk("운영에서 나온 실제 오염값도 막힌다(2026-01-28-1 · 2026-02-6 · 확인 중)",
        R["bad"][5] is False and R["bad"][6] is False and R["bad"][7] is False)
    chk("시각이 붙은 값·글자도 막힌다", R["bad"][9] is False and R["bad"][10] is False)
    chk("윤년 2024-02-29 는 통과", R["ok"][2] is True)
    chk("260618·20260618·2026.06.18·2026/6/8 은 서식을 고쳐 통과",
        R["normOk"][:5] == [True] * 5, "%s / %s" % (R["norm"][:5], R["normOk"][:5]))
    chk("고칠 수 없는 값은 서식 정리 뒤에도 막힌다",
        R["normOk"][5] is False and R["normOk"][6] is False, R["norm"][5:])

# ════════════════════════════════════════════════════════════════════
sec("§3. 서버 검사 — database.py 의 date_cell_ok 원문을 그대로 실행")
# ════════════════════════════════════════════════════════════════════
tree = ast.parse(dbsrc)
fn_src = None
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name == "date_cell_ok":
        fn_src = ast.get_source_segment(dbsrc, n)
mod = {}
if fn_src:
    exec(compile(fn_src, "date_cell_ok", "exec"), mod)
    dok = mod["date_cell_ok"]
    chk("서버 함수 추출 성공", True)
    chk("제대로 된 날짜는 통과", all(dok(v) for v in ("2026-09-29", "2024-02-29", "2026-12-31")))
    chk("빈 값(지우기)은 통과", dok("") and dok(None) and dok("   "))
    chk("⭐금액은 막힌다", not dok("2,280,000") and not dok("2280000"))
    chk("운영 오염값 3종을 막는다",
        not dok("2026-01-28-1") and not dok("2026-02-6") and not dok("확인 중"))
    chk("없는 날짜를 막는다", not dok("2026-02-31") and not dok("2026-13-01") and not dok("2023-02-29"))
    chk("자리수가 틀리면 막는다",
        not dok("2026-1-05") and not dok("26-01-05") and not dok("2026-09-292"))
    chk("앞뒤 공백은 다듬어 통과(사람이 붙여넣기 할 때)", dok("  2026-09-29  "))
    chk("서버와 화면 판정이 같다(같은 값 17개)", (not node_ok) or all(
        dok(v) == r for v, r in zip(
            ['2026-09-29', '2026-02-28', '2024-02-29', '2026-12-31', ''], R["ok"])) and all(
        dok(v) == r for v, r in zip(
            ['2,280,000', '2280000', '2026-02-31', '2026-13-01', '2026-1-5', '2026-01-28-1',
             '2026-02-6', '확인 중', '2026/09/29', '오늘', '2026-09-29 14:00', '-', '2023-02-29'], R["bad"])))
else:
    chk("서버 함수 추출 성공", False, "date_cell_ok 를 못 찾음")

# ════════════════════════════════════════════════════════════════════
sec("§4. 배포 전 검사기 역시험 — 어긴 코드를 정말 잡는가")
# ════════════════════════════════════════════════════════════════════
sys.path.insert(0, os.path.join(ROOT, "deploy"))
try:
    import check_standards as CS
except Exception as e:
    print("  ⚠ 검사기 import 실패 — §4 건너뜀: %s" % e)
    CS = None

if CS is not None:
    chk("⭐지금 코드 — 위반 0건", len(CS.check_date_cell_guard()) == 0,
        CS.check_date_cell_guard()[:2])

    def with_mutation(board_sub=None, db_sub=None, main_sub=None):
        """진짜 소스를 복사해 한 군데만 망가뜨린 뒤 검사기를 돌린다(원본은 안 건드린다)."""
        d = tempfile.mkdtemp(prefix="z1132m_")
        os.makedirs(os.path.join(d, "app", "templates"), exist_ok=True)
        b = board
        if board_sub:
            b = b.replace(board_sub[0], board_sub[1], 1)
        io.open(os.path.join(d, "app", "templates", "schedule_board.html"), "w",
                encoding="utf-8", newline="").write(b)
        for rel, src, sub in (("app/database.py", dbsrc, db_sub), ("app/main.py", mainsrc, main_sub)):
            t = src.replace(sub[0], sub[1], 1) if sub else src
            io.open(os.path.join(d, *rel.split("/")), "w", encoding="utf-8", newline="").write(t)
        _R, _T = CS.ROOT, CS.TPL
        CS.ROOT, CS.TPL = d, os.path.join(d, "app", "templates")
        try:
            return CS.check_date_cell_guard()
        finally:
            CS.ROOT, CS.TPL = _R, _T
            shutil.rmtree(d, ignore_errors=True)

    MUT = [
        ("① 달력을 안 붙임", dict(board_sub=("inp.classList.add('knk-cal');", "/* 달력 뺌 */"))),
        ("① 공용 _mkCellInput 삭제", dict(board_sub=("function _mkCellInput(field, cur){",
                                                    "function _mkCellInputX(field, cur){"))),
        ("① 공용 _dateOk 삭제", dict(board_sub=("function _dateOk(s){", "function _dateOkX(s){"))),
        ("② 편집칸을 직접 만듦(startEdit)",
         dict(board_sub=("  const inp=_mkCellInput(td.dataset.edit, cur);   // z1132: 날짜 칸이면 달력이 붙는다",
                         "  const inp=document.createElement('input'); inp.className='cell-input';"))),
        ("③ 표 칸 검사 뺌(startEdit)",
         dict(board_sub=("if(save && !_dateOk(val)){ _dateWarn(); td.textContent=cur||'＋';",
                         "if(false){ _dateWarn(); td.textContent=cur||'＋';"))),
        ("③ 발행일 검사 뺌(startTaxInvEdit)",
         dict(board_sub=("    if(!_dateOk(dv)){ _dateWarn(); pd.focus(); return; }   // z1132: 발행일은 날짜만(신고 ②)\n    const btn=pop.querySelector('.ti-save'); btn.disabled=true;\n    try{\n      await taxSave(",
                         "    const btn=pop.querySelector('.ti-save'); btn.disabled=true;\n    try{\n      await taxSave("))),
        ("③ 호기별 표 검사 뺌(_uxSave)",
         dict(board_sub=("  if(_isDateField(field) && !_dateOk(value)){ _dateWarn(); return; }", "  "))),
        ("④ 서버 셀 저장 검사 뺌",
         dict(db_sub=("if field in DATE_CELL_FIELDS and not date_cell_ok(val):", "if False:"))),
        ("④ 서버 세금계산서 검사 뺌",
         dict(main_sub=("if field in _DATE_F and not _logi.date_cell_ok(value):", "if False:"))),
        ("④ 서버 함수 이름이 바뀜", dict(db_sub=("def schedule_cell_update(", "def schedule_cell_update_x("))),
    ]
    for nm, kw in MUT:
        hits = with_mutation(**kw)
        chk("어긴 코드를 잡는다 — %s" % nm, len(hits) >= 1, "%d건" % len(hits))

    chk("멀쩡한 코드는 안 잡는다(원본 그대로 다시)", len(with_mutation()) == 0)

# ════════════════════════════════════════════════════════════════════
shutil.rmtree(tmpd, ignore_errors=True)
print("\n" + "=" * 72)
print("결과: %d/%d 통과%s" % (OK, OK + FAIL, "" if not FAIL else "  — ❌ 실패 %d" % FAIL))
print("=" * 72)
sys.exit(1 if FAIL else 0)
