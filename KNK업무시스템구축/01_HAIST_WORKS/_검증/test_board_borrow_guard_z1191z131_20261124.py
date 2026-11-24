# -*- coding: utf-8 -*-
"""z1191z131 (대표 11-24 「같은 유형 미리 막기」) — 작업일정표가 같은 관리번호 다른 수주 값을 빌려 그리지 않게
   1 수주번호 빈 줄 = 수주 1개일 때만 최신 수주번호 빌림
   2 호기 0건 줄 세금계산서 = 수주 2개 이상이면 관리번호 전체 호기로 대신 안 함(빈칸)
   3 호기 0건 줄 상태 = 수주 2개 이상이면 그 수주(orders.status) 상태
   4 발주일·납기 = 수주 2개 이상이면 그 수주 값 → 빈칸(관리번호 값 안 빌림)
   5 z129 연기 판정 표 열쇠 = (관리번호 id, 수주번호)
   6 합산 줄 납기 = 취소 품목 뺌(모두 취소면 예전대로)
   7 출하+보류만 남은 줄 = 「보류」(지연 아님)
   글자 확인 + 순수 함수 직접 호출 + 메모리 sqlite 로 _board_split_lines_map 실행."""
import ast, os, sqlite3, sys
from contextlib import contextmanager
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))
m = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()

# ── (a) 글자 확인
check("주석 z1191z131 이 여러 곳에", m.count("z1191z131 (대표 11-24 「같은 유형 미리 막기」)") >= 10, m.count("z1191z131"))
check("1 수주번호: 수주 2개 이상이면 빌리지 않음(작업일정표 두 곳)",
      m.count('_iu["so_no"] = _ln["so_no"] or ("" if _z131_multi_so(_ln) else info.get("so_no")) or ""') == 2)
check("1 수주번호: 부서일정표도", '_iu["so_no"] = _ln.get("so_no") or ("" if _m131 else info.get("so_no")) or ""' in m)
check("1 옛 빌림 줄은 남지 않음", '_iu["so_no"] = _ln["so_no"] or info.get("so_no") or ""' not in m
      and '_iu["so_no"] = _ln.get("so_no") or info.get("so_no") or ""' not in m)
check("2 세금계산서: 호기 0건 + 수주번호 + 수주 2개 이상 → 관리번호 전체로 안 대신함",
      'if not iids and _row.get("so_no") and _z131_multi_so(_row):' in m)
check("2 화면 줄에 수주 수 실음(n_sos131)", m.count('_iu["n_sos131"] = _ln.get("n_sos131") or 0') == 2)
check("3 상태: 수주 2개 이상 + 수주번호 → 그 수주 상태(세 곳)",
      m.count('_z131_so_status_ko(_ln.get("so_status131")) if (_z131_multi_so(_ln) and _ln.get("so_no")) else p.get("status"))') == 2
      and '_z131_so_status_ko(_ln.get("so_status131")) if (_m131 and _ln.get("so_no")) else p.get("status"))' in m)
check("4 날짜: 수주 2개 이상 → 그 수주 발주일·납기(작업일정표 두 곳)",
      m.count('_iu["due_date"] = (_ln["due_date"] or _ln.get("so_due131") or "")') == 2
      and m.count('_iu["order_date"] = (_ln["order_date"] or _ln.get("so_ord131") or "")') == 2)
check("4 날짜: 부서일정표도", '_iu["due_date"] = (_ln.get("due_date") or _ln.get("so_due131") or "")' in m)
check("5 연기 판정 표 열쇠 = (관리번호 id, 수주번호)",
      "_so_iids129.setdefault((_pid, _r[5]), []).append(_iid)" in m
      and '_so_iids129.get((_row.get("ref_id"), _row.get("so_no") or ""))' in m
      and "_so_iids129.setdefault(_r[5], [])" not in m)
check("6 합산 줄 납기: 취소 품목 뺌(모두 취소면 전부)",
      '_ditems131 = [_it for _it in _citems if str(_it.get("i_ust") or "").strip() != "취소"] or _citems' in m)
check("6 호기 상태 읽기(i_ust)", '", oi.unit_status AS i_ust" if "unit_status" in _oi_cols' in m)
check("지연 판정 = 상태 출하·취소·보류 제외(보류면 지연 아님)",
      m.count('info["is_delay"] = bool(dd and dd < today and status not in ("출하", "취소", "보류"))') >= 2
      and '"delay": sum(1 for r in rows if r["is_delay"])' in m)

# ── 함수 꺼내기
tree = ast.parse(m)
NEED = {"_board_agg_status", "_z131_multi_so", "_z131_so_status_ko", "_inject_oi_tax_into_rows",
        "_board_split_lines_map", "_board_in_frag", "_merge_units_same", "_find_note_z12", "_join_notes981",
        "_ti_dcol", "_ti_acol", "_ti_mcol"}
src = []
for nd in tree.body:
    if isinstance(nd, ast.FunctionDef) and nd.name in NEED:
        src.append(ast.get_source_segment(m, nd))
    elif isinstance(nd, ast.Assign) and any(getattr(t, "id", "") in ("_Z42_SO_ST", "_TI_MAX") for t in nd.targets):
        src.append(ast.get_source_segment(m, nd))
DB = sqlite3.connect(":memory:")
DB.row_factory = sqlite3.Row

@contextmanager
def _dbs():
    yield DB

class _PWF:
    @staticmethod
    def so_form_label_key(**k):
        return ("", "")

ns = {"db_session": _dbs, "_pwf": _PWF}
exec("\n\n".join(src), ns)
check("함수 꺼내기", all(n in ns for n in NEED), [n for n in NEED if n not in ns])

# ── 7 _board_agg_status
agg = ns["_board_agg_status"]
check("7 출하+보류 → 보류", agg(["출하", "보류"]) == "보류", agg(["출하", "보류"]))
check("7 출하+보류+취소 → 보류", agg(["출하", "보류", "취소"]) == "보류")
check("7 진행중 섞임 → 진행중", agg(["출하", "보류", "진행중"]) == "진행중")
check("7 빈칸(None 아님 '') 섞임 → 진행중", agg(["출하", "보류", ""]) == "진행중")
check("7 출하만 → 출하", agg(["출하", "출하"]) == "출하")
check("7 출하+취소 → 출하", agg(["출하", "취소"]) == "출하")
check("7 보류만 → 보류", agg(["보류"]) == "보류")
check("7 취소만 → 취소", agg(["취소"]) == "취소")
check("7 호기 0건 → ''", agg([]) == "" and agg([None]) == "")

# ── 3 수주 상태 변환
sk = ns["_z131_so_status_ko"]
check("3 SHIPPED/INVOICED/PAID → 출하", sk("SHIPPED") == sk("INVOICED") == sk("paid") == "출하")
check("3 CANCELLED → 취소 · HOLD → 보류", sk("CANCELLED") == "취소" and sk("HOLD") == "보류")
check("3 그 밖 → 진행중", sk("CONFIRMED") == sk("DRAFT") == sk("QUOTED") == sk("") == sk(None) == "진행중")
mu = ns["_z131_multi_so"]
check("수주 수 판정: 2 이상만 True · 표시 없음 = False", mu({"n_sos131": 2}) and not mu({"n_sos131": 1}) and not mu({}) and not mu(None))

# ── 2 세금계산서 주입
inj = ns["_inject_oi_tax_into_rows"]
oi_map = {11: {"stmt": "2026-10-01", "t1d": "2026-10-02", "t1a": 100}}
r_multi = {"kind": "project", "ref_id": 1, "so_no": "SO-2", "n_sos131": 2, "unit_iids": [],
           "statement_date": "옛값", "tax_invoice_date": "옛값"}
r_one = {"kind": "project", "ref_id": 1, "so_no": "SO-1", "n_sos131": 1, "unit_iids": []}
r_old = {"kind": "project", "ref_id": 1, "unit_iids": []}   # 표시 없는 옛 줄(진단 화면 등)
inj([r_multi, r_one, r_old], oi_map, {1: [11]})
check("2 수주 2개 이상 · 호기 0건 → 빈칸(다른 수주 세금계산서 안 빌림)",
      r_multi["statement_date"] == "" and r_multi["tax_invoice_date"] == "" and r_multi["tax_invoice_amt1"] == "", r_multi)
check("2 수주 1개 → 예전대로 관리번호 호기 합계", r_one["tax_invoice_date"] == "2026-10-02" and r_one["tax_invoice_amt1"] == 100, r_one)
check("2 표시 없는 옛 줄 → 예전대로", r_old["tax_invoice_date"] == "2026-10-02")
r_iid = {"kind": "project", "ref_id": 1, "so_no": "SO-2", "n_sos131": 2, "unit_iids": [11]}
inj([r_iid], oi_map, {1: [11]})
check("2 수주 2개 이상이라도 줄 호기 있으면 그 호기 값", r_iid["tax_invoice_amt1"] == 100)

# ── 메모리 sqlite 로 _board_split_lines_map
DB.executescript("""
CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT);
CREATE TABLE projects(id INTEGER PRIMARY KEY, project_type TEXT);
INSERT INTO projects VALUES(1,'NEW_EQUIP'),(2,'NEW_EQUIP'),(3,'NEW_EQUIP'),(4,'NEW_EQUIP');
CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INTEGER, order_no TEXT, status TEXT, so_type TEXT,
  total_amount REAL, unit_qty INTEGER, order_date TEXT, due_date TEXT, ship_to TEXT, currency TEXT);
CREATE TABLE order_items(id INTEGER PRIMARY KEY, order_id INTEGER, unit_label TEXT, unit_price REAL, amount REAL,
  qty INTEGER, order_date TEXT, due_date TEXT, ship_to TEXT, currency TEXT, unit_status TEXT);
-- 관리번호 1: 수주 2개(SO-A 호기 있음 · SO-B 호기 없음 · SHIPPED) + 취소 수주 1개(세지 않음)
INSERT INTO orders VALUES(1,1,'SO-A','CONFIRMED','',100,1,'2026-09-01','2026-11-01','','KRW');
INSERT INTO orders VALUES(2,1,'SO-B','SHIPPED','',50,1,'2026-09-05','2026-11-20','','KRW');
INSERT INTO orders VALUES(3,1,'SO-X','CANCELLED','',10,1,'','','','KRW');
INSERT INTO order_items VALUES(11,1,'1호기',100,100,1,'','','','','진행중');
-- 관리번호 2: 수주 1개(부품 · 품목 둘 · 늦은 납기 품목은 취소)
INSERT INTO orders VALUES(4,2,'SO-P','CONFIRMED','PARTS_EXPORT',30,1,'2026-09-01','2026-11-05','','KRW');
INSERT INTO order_items VALUES(21,4,'부품A',10,10,1,'','2026-11-10','','','진행중');
INSERT INTO order_items VALUES(22,4,'부품B',20,20,1,'','2026-12-30','','','취소');
-- 관리번호 3: 소모품 합산 줄 · 첫 품목(취소)의 납기가 먼저 잡히던 경우
INSERT INTO orders VALUES(5,3,'SO-C','CONFIRMED','CONSUMABLE',30,1,'2026-09-01','2026-11-05','','KRW');
INSERT INTO order_items VALUES(31,5,'소모품A',10,10,1,'','2026-12-31','','','취소');
INSERT INTO order_items VALUES(32,5,'소모품B',20,20,1,'','2026-11-15','','','진행중');
-- 관리번호 4: 소모품 합산 줄 · 모두 취소 → 예전대로(첫 품목 납기)
INSERT INTO orders VALUES(6,4,'SO-D','CONFIRMED','CONSUMABLE',30,1,'2026-09-01','2026-11-05','','KRW');
INSERT INTO order_items VALUES(41,6,'소모품A',10,10,1,'','2026-12-01','','','취소');
INSERT INTO order_items VALUES(42,6,'소모품B',20,20,1,'','2026-12-02','','','취소');
""")
mp = ns["_board_split_lines_map"](unfold_sos=True)
l1 = mp.get(1) or []
check("관리번호 1: 취소 아닌 수주 2개 → 줄 2개", len(l1) == 2, l1)
lb = next((x for x in l1 if x.get("so_no") == "SO-B"), {})
check("줄마다 n_sos131=2(취소 수주 안 셈)", all(x.get("n_sos131") == 2 for x in l1), [x.get("n_sos131") for x in l1])
check("호기 0건 줄(SO-B): 그 수주 상태·발주일·납기 실림",
      lb.get("so_status131") == "SHIPPED" and lb.get("so_due131") == "2026-11-20" and lb.get("so_ord131") == "2026-09-05" and not lb.get("iids"), lb)
check("3 호기 0건 줄 상태 = 그 수주 상태(출하) → 지연 아님",
      (agg([]) or (sk(lb.get("so_status131")) if (mu(lb) and lb.get("so_no")) else "진행중")) == "출하")
l2 = (mp.get(2) or [{}])[0]
check("6 부품 합산 줄 납기: 취소 품목(12-30) 빼고 최댓값 11-10", l2.get("due_date") == "2026-11-10", l2.get("due_date"))
check("수주 1개 관리번호 → n_sos131=1(예전 동작 길)", l2.get("n_sos131") == 1)
l3 = (mp.get(3) or [{}])[0]
check("6 소모품 합산 줄 납기: 취소 품목 빼고 첫 값 11-15", l3.get("due_date") == "2026-11-15", l3.get("due_date"))
l4 = (mp.get(4) or [{}])[0]
check("6 모두 취소면 예전대로(첫 품목 납기 12-01)", l4.get("due_date") == "2026-12-01", l4.get("due_date"))

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
