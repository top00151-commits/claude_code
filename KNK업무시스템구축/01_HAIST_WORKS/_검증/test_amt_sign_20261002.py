# -*- coding: utf-8 -*-
"""z1135 시험 — 금액 칸에 마이너스(네고·할인)를 칠 수 있는가 (이새롬 프로 신고 2026-10-02).

신고 원문: "마이너스 건은 세금계산서 입력을 해도 플러스로 인식됩니다."
실측(999T2606 SENSOR): 수주 금액 **-1,865,000** 인데 1차 세금계산서는 **+1,865,000**.
원인: 금액 칸 타이핑 재포맷 `value.replace(/[^0-9.]/g,'')` 가 '-' 를 **키 입력 즉시** 지웠다.
      z1095 의 '.'(소수점) 삭제와 같은 종류 — 그때는 10배, 이번엔 부호가 뒤집힌다.

이 시험은 **진짜 코드**만 본다.
  §2 는 공용 `_v5_partials/knk_amt.html` 원문을 뽑아 node 로 실제 실행한다(한 글자씩 치는 것까지).
  §4 는 규정을 어긴 코드 9종을 만들어 배포 전 검사기가 정말 잡는지 본다.

실행:  python _검증/test_amt_sign_20261002.py
"""
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
SHARED = os.path.join(TPL, "_v5_partials", "knk_amt.html")
BOARD = os.path.join(TPL, "schedule_board.html")
DETAIL = os.path.join(TPL, "project_detail.html")

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


def js_block(src, pat):
    """원문을 그대로 잘라 온다 — 코드를 베껴 시험하지 않기 위해."""
    m = re.search(pat, src)
    assert m, "원문을 못 찾음: %s" % pat
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
    raise AssertionError(pat)


shared = read(SHARED)
board = read(BOARD)
detail = read(DETAIL)

# ════════════════════════════════════════════════════════════════════
sec("§1. 소스 — 부호를 지우던 자리가 남아 있는가")
# ════════════════════════════════════════════════════════════════════
chk("공용 타이핑 포맷이 맨 앞 마이너스를 지킨다",
    "neg" in js_block(shared, r"function fmtAmtTyping\(v\)\s*"))
chk("공용 저장 변환도 부호를 지킨다(맨 앞 1개만)",
    "neg" in js_block(shared, r"function amtToRaw\(v\)\s*"))
chk("작업일정표가 공용 부품을 포함한다", 'include "_v5_partials/knk_amt.html"' in board)
chk("작업일정표 자체 사본이 공용을 부른다(사본 로직 제거)",
    "knkFmtAmtTyping" in js_block(board, r"function _fmtAmtTyping\(v\)\s*"))
chk("프로젝트 상세도 공용 부품을 포함한다", 'include "_v5_partials/knk_amt.html"' in detail)

_left = len(re.findall(r"replace\(\s*/\[\^0-9\.\]/g", board))
chk("작업일정표에 부호를 지우던 자리 0곳", _left == 0, "%d곳" % _left)
chk("세금계산서 팝업 2곳이 공용 저장 변환을 쓴다",
    board.count("av=window.knkAmtToRaw(pa.value)") == 2,
    "%d곳" % board.count("av=window.knkAmtToRaw(pa.value)"))
chk("호기별 표 저장도 공용을 쓴다", "_uxSave(iid,f,window.knkAmtToRaw(t.value),t)" in board)
chk("프로젝트 상세 폴백도 부호를 지킨다", "[^0-9.\\-]" in detail)

# ════════════════════════════════════════════════════════════════════
sec("§2. 진짜 JS 실행 — 공용 부품 원문을 node 로 돌린다")
# ════════════════════════════════════════════════════════════════════
js_typing = js_block(shared, r"function fmtAmtTyping\(v\)\s*")
js_raw = js_block(shared, r"function amtToRaw\(v\)\s*")
js_show = js_block(shared, r"function fmtAmtShow\(v, ccy\)\s*")

PROBE = """
'use strict';
__TYPING__
__RAW__
__SHOW__
/* 사람이 한 글자씩 치는 것 — 칠 때마다 재포맷되는 실제 동작 그대로 */
function typeIn(keys){ var v=''; for (var i=0;i<keys.length;i++){ v = fmtAmtTyping(v + keys[i]); } return v; }
var o = {};
o.typed_neg      = typeIn('-1865000');
o.typed_pos      = typeIn('1865000');
o.typed_minus    = typeIn('-');
o.typed_dec      = typeIn('-1234.56');
o.fmt_from_saved = fmtAmtTyping('-1865000');          /* 저장값을 칸에 되비칠 때 */
o.roundtrip      = amtToRaw(fmtAmtTyping('-1865000')); /* 고쳐도 값이 안 변해야 한다 */
o.raw_neg        = amtToRaw('-1,865,000');
o.raw_pos        = amtToRaw('1,865,000');
o.raw_dec        = amtToRaw('-1,234.56');
o.raw_only_minus = amtToRaw('-');                      /* 숫자 없음 = 지우기 */
o.raw_mid_minus  = amtToRaw('1-2');                    /* 중간 부호는 버린다 */
o.raw_dbl_minus  = amtToRaw('--5');
o.fmt_dbl_minus  = fmtAmtTyping('--5');
o.show_krw       = fmtAmtShow(-1865000, 'KRW');
o.show_usd       = fmtAmtShow(-1234.5, 'USD');
/* 옛 방식 한 줄 — 신고 재현 */
o.old_way        = ('-1,865,000').replace(/[^0-9.]/g, '');
console.log(JSON.stringify(o));
"""
PROBE = (PROBE.replace("__TYPING__", js_typing).replace("__RAW__", js_raw)
              .replace("__SHOW__", js_show))

tmpd = tempfile.mkdtemp(prefix="z1135_")
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
    chk("\U0001F534신고 재현 — 옛 방식은 '-1,865,000' 에서 부호를 지운다",
        R["old_way"] == "1865000", R["old_way"])
    chk("⭐한 글자씩 쳐서 -1865000 → '-1,865,000'",
        R["typed_neg"] == "-1,865,000", R["typed_neg"])
    chk("양수는 지금까지와 똑같다", R["typed_pos"] == "1,865,000", R["typed_pos"])
    chk("'-' 만 쳐도 남는다(이어서 숫자를 칠 수 있다)", R["typed_minus"] == "-", R["typed_minus"])
    chk("외화 소수까지 — -1234.56 → '-1,234.56'", R["typed_dec"] == "-1,234.56", R["typed_dec"])
    chk("저장값을 칸에 되비칠 때도 부호 유지",
        R["fmt_from_saved"] == "-1,865,000", R["fmt_from_saved"])
    chk("⭐열었다 그대로 저장해도 값이 안 변한다(z1095 류 10배 사고 방지)",
        R["roundtrip"] == "-1865000", R["roundtrip"])
    chk("저장 변환 — '-1,865,000' → '-1865000'", R["raw_neg"] == "-1865000", R["raw_neg"])
    chk("저장 변환 — 양수 그대로", R["raw_pos"] == "1865000", R["raw_pos"])
    chk("저장 변환 — 외화 소수", R["raw_dec"] == "-1234.56", R["raw_dec"])
    chk("'-' 만 있으면 빈 값(지우기)", R["raw_only_minus"] == "", repr(R["raw_only_minus"]))
    chk("중간 부호 '1-2' 는 버린다(서버에서 깨지지 않게)", R["raw_mid_minus"] == "12", R["raw_mid_minus"])
    chk("부호 두 개 '--5' 는 하나로", R["raw_dbl_minus"] == "-5" and R["fmt_dbl_minus"] == "-5",
        "%s / %s" % (R["raw_dbl_minus"], R["fmt_dbl_minus"]))
    chk("표시 — KRW 음수 '-1,865,000'", R["show_krw"] == "-1,865,000", R["show_krw"])
    chk("표시 — 외화 음수 소수 2자리", R["show_usd"] == "-1,234.50", R["show_usd"])

# ════════════════════════════════════════════════════════════════════
sec("§3. 서버 — 음수를 받는가 (코드 확인)")
# ════════════════════════════════════════════════════════════════════
import ast

main_src = read(os.path.join(ROOT, "app", "main.py"))
db_src = read(os.path.join(ROOT, "app", "database.py"))
chk("세금계산서 금액 저장이 float 로 받는다(부호 제한 없음)",
    'av = float(str(value).replace(",", ""))' in main_src)


def func_src(src, name):
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name:
            return ast.get_source_segment(src, n) or ""
    return None


_NEG_GUARD = re.compile(r"(tax_invoice_amt\w*|unit_price|amount|total_amount)[^=<>!\n]*<\s*0")
for src, fn in ((main_src, "schedule_board_unit_field"),
                (main_src, "schedule_board_row_tax"),
                (main_src, "schedule_tax_invoice_issue"),
                (db_src, "schedule_cell_update")):
    body = func_src(src, fn)
    chk("%s() 에 음수 차단이 없다(신고 경로)" % fn,
        body is not None and not _NEG_GUARD.search(body),
        "못 찾음" if body is None else "음수 차단 있음")

# 다른 곳의 음수 차단은 **의도된 업무 규칙**이다 — 새로 생기면 여기서 드러난다
known = {("app/main.py", "_proj_import_parse_xlsx"),      # 엑셀 업로드: 단가는 0 이상
         ("app/main.py", "export_ci_create"),             # 수출 CI 금액은 음수 불가
         ("app/database.py", "part_price_create")}        # 자재 단가표(세션05 영역) — ⛔무접촉
found = set()
for rel, src in (("app/main.py", main_src), ("app/database.py", db_src)):
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        seg = ast.get_source_segment(src, n) or ""
        if _NEG_GUARD.search(seg):
            found.add((rel, n.name))
chk("서버의 음수 차단은 알려진 3곳뿐(새로 생기면 드러난다)",
    found == known, sorted(found ^ known))

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
    def run(shared_sub=None, board_sub=None, extra=None):
        """진짜 소스를 복사해 한 군데만 망가뜨린 뒤 검사기를 돌린다(원본은 안 건드린다)."""
        d = tempfile.mkdtemp(prefix="z1135m_")
        os.makedirs(os.path.join(d, "app", "templates", "_v5_partials"), exist_ok=True)
        sh = shared.replace(*shared_sub) if shared_sub else shared
        bd = board.replace(*board_sub) if board_sub else board
        ps = os.path.join(d, "app", "templates", "_v5_partials", "knk_amt.html")
        pb = os.path.join(d, "app", "templates", "schedule_board.html")
        io.open(ps, "w", encoding="utf-8", newline="").write(sh)
        io.open(pb, "w", encoding="utf-8", newline="").write(bd)
        files = [ps, pb]
        if extra is not None:
            pe = os.path.join(d, "app", "templates", "x.html")
            io.open(pe, "w", encoding="utf-8", newline="").write(extra)
            files.append(pe)
        _T = CS.TPL
        CS.TPL = os.path.join(d, "app", "templates")
        try:
            return CS.check_amt_sign(files)
        finally:
            CS.TPL = _T
            shutil.rmtree(d, ignore_errors=True)

    chk("⭐지금 코드 — 위반 0건", len(run()) == 0, run()[:2])

    MUT = [
        ("① 공용 타이핑이 부호를 버림",
         dict(shared_sub=("var neg = /^\\s*-/.test(v);", "var neg = false;  // zz"))),
        ("① 공용 저장 변환에서 부호 보기를 뺌",
         dict(shared_sub=("var neg = s.charAt(0) === '-';", "var neg = false;"))),
        ("① 공용 함수 이름이 바뀜",
         dict(shared_sub=("function fmtAmtTyping(v)", "function fmtAmtTypingX(v)"))),
        ("② 화면이 다시 [^0-9.] 로 금액 저장",
         dict(board_sub=("av=window.knkAmtToRaw(pa.value);",
                         "av=(pa.value||'').replace(/[^0-9.]/g,'');"))),
        ("② 호기별 표가 다시 부호를 버림",
         dict(board_sub=("_uxSave(iid,f,window.knkAmtToRaw(t.value),t)",
                         "_uxSave(iid,f,(t.value||'').replace(/[^0-9.]/g,''),t)"))),
        ("③ 타이핑 포맷 사본 부활",
         dict(board_sub=("function _fmtAmtTyping(v){ return window.knkFmtAmtTyping(v); }",
                         "function _fmtAmtTyping(v){ return String(v).replace(/[^0-9.]/g,''); }"))),
        ("② 다른 화면에 새로 생긴 금액 칸",
         dict(extra="<script>\nvar amt=el.value.replace(/[^0-9.]/g,'');  // 단가\n</script>")),
    ]
    for nm, kw in MUT:
        hits = run(**kw)
        chk("어긴 코드를 잡는다 — %s" % nm, len(hits) >= 1, "%d건" % len(hits))

    GOOD = [
        ("부호를 지키는 올바른 형태", "<script>\nvar amt=v.replace(/[^0-9.\\-]/g,'');  // 금액\n</script>"),
        ("날짜 정규화(금액 아님)", "<script>\nvar d=s.replace(/[^0-9]/g,'');\nif(d.length===8) return d;\n</script>"),
        ("주석 줄", "<script>\n// var a=v.replace(/[^0-9.]/g,'');  // 금액\n</script>"),
        ("Jinja 주석", "{# var a=v.replace(/[^0-9.]/g,''); 금액 #}\n<script>var z=1;</script>"),
        ("공용을 부르는 사본", "<script>\nfunction _fmtAmtTyping(v){ return window.knkFmtAmtTyping(v); }\n</script>"),
    ]
    for nm, body in GOOD:
        hits = run(extra=body)
        chk("멀쩡한 코드는 안 잡는다 — %s" % nm, len(hits) == 0, "%d건" % len(hits))

shutil.rmtree(tmpd, ignore_errors=True)
print("\n" + "=" * 72)
print("결과: %d/%d 통과%s" % (OK, OK + FAIL, "" if not FAIL else "  — ❌ 실패 %d" % FAIL))
print("=" * 72)
sys.exit(1 if FAIL else 0)
