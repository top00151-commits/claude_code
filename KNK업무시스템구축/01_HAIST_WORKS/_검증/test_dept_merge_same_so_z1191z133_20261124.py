# -*- coding: utf-8 -*-
"""z1191z133 (대표 11-24 「전사일정표 관리번호·수주번호 같은 줄 하나로 · 수량 합 · 작업일정표는 건들지 말 것」)
   _dsx_merge_same_so_z133 를 main.py 에서 떼어 직접 돌려 본다(main 전체를 불러오지 않음)."""
import ast, os, sys
from datetime import date
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
tree = ast.parse(src)
fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_dsx_merge_same_so_z133"][0]
ns = {}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "z133", "exec"), ns)
M = ns["_dsx_merge_same_so_z133"]
def pd(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None
def mk(info, od, dd, st, kind):
    info["dday"] = dd.day if dd else None
    info["is_delay"] = bool(dd and dd < date(2026, 11, 24) and st not in ("출하", "취소", "보류"))
    return info
def row(oid, qty, uids, od="2026-11-16", dd="2026-12-01", unit="", lab="", dly=False):
    return {"so_oid": oid, "qty": qty, "uids": uids, "order_date": od, "due_date": dd, "board_unit": unit, "is_parts": False,
            "qty_form": "", "is_bqty": False, "unit_label": lab, "is_delay": dly, "_st133": "진행중", "multi": False}
out = M([row(3039, 1, [1], lab="1호기"), row(3039, 1, [2], lab="2호기"), row(3039, 1, [3], lab="3호기")], mk, pd)
check("같은 수주 단가만 다른 세 줄 → 한 줄 · 수량 3", len(out) == 1 and out[0]["qty"] == 3, out)
check("호기 목록 합침(1·2·3) · 여러 대 표시", out[0]["uids"] == [1, 2, 3] and out[0]["multi"] is True, out[0])
check("도우미 칸(_st133) 안 남음", "_st133" not in out[0], out[0].keys())
out = M([row(1, 1, [1], dd="2026-12-01"), row(1, 2, [2, 3], od="2026-11-10", dd="2026-12-10")], mk, pd)
check("납기 다르면 발주일 = 이른 날 · 납기 = 늦은 날", out[0]["order_date"] == "2026-11-10" and out[0]["due_date"] == "2026-12-10" and out[0]["qty"] == 3, out[0])
out = M([row(1, 1, [1], dd="2026-11-20", dly=True), row(1, 1, [2], dd="2026-12-10")], mk, pd)
check("한 줄이라도 지연이면 지연", out[0]["is_delay"] is True, out[0])
out = M([row(1, 1, [1], unit="EA"), row(1, 1, [2], unit="SET")], mk, pd)
check("수량 단위 다르면 안 합침", len(out) == 2, out)
out = M([row(1, 1, [1]), row(2, 1, [2])], mk, pd)
check("다른 수주는 안 합침", len(out) == 2, out)
out = M([row(None, 1, [1]), row(None, 1, [2])], mk, pd)
check("수주번호 없는 줄은 안 합침", len(out) == 2, out)
out = M([row(1, "", [1]), row(1, 1, [2])], mk, pd)
check("한 줄만 있으면 그대로(1개 수주)", len(M([row(5, 2, [9])], mk, pd)) == 1 and M([row(5, 2, [9])], mk, pd)[0]["qty"] == 2)
s = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
i = s.index("def dept_schedule(")
j = s.index("rows.extend(_dsx_merge_same_so_z133(_prow133, _mk, _pd))")
check("전사 일정표(dept_schedule) 안에서만 합침", i < j < s.index("def ", i + 30) or j > i)
check("작업일정표(schedule_board)는 합치는 함수 안 씀", s.count("_dsx_merge_same_so_z133(") == 2, s.count("_dsx_merge_same_so_z133("))
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
