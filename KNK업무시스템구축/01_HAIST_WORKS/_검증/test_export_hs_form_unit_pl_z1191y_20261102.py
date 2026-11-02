# -*- coding: utf-8 -*-
"""z1191y 시험 — 옛 양식 → 최종 양식: 수량 단위는 원본 줄마다 그대로 · 원본 패킹이 비면 인보이스 품목으로 채운다
   대표 2026-11-02 「수량 단위를 기존 원본과 다르게 만들었어 … 세트 단위가 있었는데 다 모두 EA 단위로 바뀌었고, 단위는 바꾸면 안 돼 …
   두 번째 시트에 보면 패킹이라는 시트가 있는데 거기에도 앞쪽 시트에 있는 내용, 품명, 수량 이런 거를 양식 맞게끔 다 채워줘」
  §1 일반: 줄마다 EA · SET · PCS(틀에 없는 단위) · G 칸 글자 · 단위 없음 → 같은 줄 같은 단위 · 틀 8번째 줄 SET 이 안 새어 나옴
  §2 빈 패킹 → 인보이스 품목(품명 · 수량 · 단위)으로 · 수책은 관리코드(B)도 · 중량 · 부피는 비움
  §3 원본 패킹에 품목이 있으면 그것을 옮김(전과 같음) · 패킹 단위는 패킹 칸 형식
  §4 대조가 단위 다름을 잡는다 · §5 서식 만들기 · §6 화면 글 · §7 실물(수출자료 폴더 있을 때만)
"""
import contextlib
import glob
import io
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import openpyxl                                    # noqa: E402
from app import hs_form_convert as C               # noqa: E402

OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


FMT = {"EA": '###,###\\ "EA"', "SET": '###,###\\ "SET"', "PCS": '###,###\\ "PCS"', "": "General"}


def head(ws, no):
    for ref, v in (("A1", " COMMERCIAL  INVOICE"), ("A2", "1) Shipper / Exporter"), ("F2", "8) No. & Date of Invoice"),
                   ("B4", "KNK CO.,LTD"), ("G4", no), ("H4", "DATE:"), ("A10", "2) For Account & Risk of Messrs"),
                   ("B12", "KNK VINA Co., Ltd."), ("A31", "12) Marks and Number of PKGS"), ("D31", "13) Description of Goods"),
                   ("F31", " 14) Q'ty /Unit"), ("H31", "15) Unit Price"), ("I31", "16) Amount")):
        ws[ref] = v


def pl_sheet(wb, items=None):
    pl = wb.create_sheet("PACKING LIST")
    for ref, v in (("A1", "PACKING LIST"), ("A35", "12) Marks and Number of PKGS"), ("D35", "13) Description of Goods"),
                   ("F35", " 14) Q'ty /Unit"), ("H35", "Net -"), ("I35", "Gross-"), ("J35", "Measurement"), ("H36", "Weight"), ("I36", "Weight")):
        pl[ref] = v
    items = items or []
    for i, (d, q, u) in enumerate(items):
        pl.cell(37 + i, 4, d)
        c = pl.cell(37 + i, 6, q)
        c.number_format = FMT[u]
        pl["H37"], pl["I37"] = 10, 12
    t = 37 + len(items) + (1 if items else 27)
    pl.cell(t, 1, "TOTAL")
    for col in "HIJ":
        pl["%s%d" % (col, t)] = "=SUM(%s37:%s%d)" % (col, col, t - 1)


ROWS = [  # (품명, 수량, 단가, 형식 단위, G 칸 글자)
    ("PART-A", 15, 2.0, "EA", None), ("PART-B", 30, 1.0, "EA", None), ("PART-C", 5, 3.0, "EA", None),
    ("PART-D", 5, 4.0, "EA", None), ("PART-E", 10, 5.0, "EA", None), ("PART-F", 5, 6.0, "EA", None),
    ("PART-G", 10, 7.0, "EA", None), ("PART-H(8번째)", 5, 8.0, "EA", None), ("MIC RUBBER", 20, 1.5, "EA", None),
    ("PIN BLOCK", 1, 900.0, "SET", None), ("CABLE TIE", 100, 0.1, "PCS", None), ("SPRING", 50, 0.4, "", "SET"),
    ("NO UNIT ITEM", 3, 2.0, "", None),
]


def old_somo(pl_items=None, n=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INVOICE"
    head(ws, "KNK-261199-1")
    for col, t in zip("LMNOPQR", ("Origin", "Manufacturer", "invoice %", "C/O", "SIZE", "HS CODE", "Tên hàng")):
        ws["%s31" % col] = t
    rows = ROWS if n is None else ROWS[:n]
    for i, (d, q, p, u, g) in enumerate(rows):
        r = 34 + i
        ws.cell(r, 3, i + 1)
        ws.cell(r, 4, d)
        c = ws.cell(r, 6, q)
        c.number_format = FMT[u]
        if g:
            ws.cell(r, 7, g)
        ws.cell(r, 8, p)
        ws.cell(r, 9, "=F%d*H%d" % (r, r))
        ws.cell(r, 12, "KOREA")
    t = 34 + len(rows) + 1
    ws.cell(t, 1, "TOTAL")
    ws.cell(t, 9, "=SUM(I33:I%d)" % (t - 1))
    pl_sheet(wb, pl_items)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def old_suchaek_empty_pl():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INVOICE"
    head(ws, "KNK-261199-2")
    for col, t in zip("KLMNO", ("ORIGIN", "SUPPLIER", "CATEGORY", "HS CODE", "Tên hàng")):
        ws["%s31" % col] = t
    for i, (d, q, u) in enumerate((("VALVE", 3, "EA"), ("UNIT SET", 1, "SET"), ("BOLT", 40, "EA"))):
        r = 34 + i
        ws.cell(r, 2, "006M2601")
        ws.cell(r, 4, d)
        c = ws.cell(r, 6, q)
        c.number_format = FMT[u]
        ws.cell(r, 8, 2.0)
        ws.cell(r, 9, "=F%d*H%d" % (r, r))
        ws.cell(r, 11, "JAPAN")
    ws.cell(38, 1, "TOTAL")
    pl_sheet(wb, None)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def units_out(out, kind):
    T = C._template(kind)
    bk = C._book(out)
    xu = C._xf_units(bk["zip"].read("xl/styles.xml").decode("utf-8"))
    res = {}
    for key in ("INV", "PL"):
        info = T["sheets"][key]
        res[key] = {r: (xu[s] if s < len(xu) else "") for r, s in C._col_style_ids(bk["zip"].read(info["path"]).decode("utf-8"), 6).items()}
    return res, bk, T


def cell(bk, T, key, r, c):
    return C._v(bk["cells"](T["sheets"][key]["path"]), r, c)


print("§1 일반 — 줄마다 단위 그대로")
res = C.convert(old_somo(), "소모품")
check("바꿈 · 대조 통과", res.get("converted") and res.get("ok"), res.get("bad") or res.get("error"))
U, bk, T = units_out(res["out"], "소모품")
f_inv = T["sheets"]["INV"]["first"]
want = [u or g or "" for (_, _, _, u, g) in ROWS]
got = [U["INV"].get(f_inv + i) for i in range(len(ROWS))]
check("인보이스 13줄 단위 = 원본(EA … SET · PCS · G 칸 SET · 단위 없음)", got == want, list(zip(want, got)))
check("틀 8번째 줄(대표 260921 SET 자리) = 원본 EA", U["INV"].get(f_inv + 7) == "EA", U["INV"].get(f_inv + 7))
check("PIN BLOCK = SET", U["INV"].get(f_inv + 9) == "SET")
check("틀에 없던 PCS 도 그대로(새 서식)", U["INV"].get(f_inv + 10) == "PCS")
check("G 칸 「SET」 = 단위로 옮김 · 뺀 값에 G 없음", U["INV"].get(f_inv + 11) == "SET" and "G" not in res["report"]["dropped"],
      res["report"]["dropped"].get("G"))
check("단위 없는 줄 = 단위 없이(지어내지 않음)", U["INV"].get(f_inv + 12) == "")
check("보고 셈(인보이스)", res["report"]["units"] == {"EA": 9, "SET": 2, "PCS": 1, "(단위 없음)": 1}, res["report"]["units"])

print("§2 빈 패킹 → 인보이스 품목으로")
f_pl = T["sheets"]["PL"]["first"]
check("패킹 품목 13줄 채움(pl_from_inv)", res["report"]["pl_from_inv"] == 13, res["report"]["pl_from_inv"])
check("패킹 품명 · 수량 = 인보이스", all(cell(bk, T, "PL", f_pl + i, 4) == ROWS[i][0] and cell(bk, T, "PL", f_pl + i, 6) == ROWS[i][1]
                                       for i in range(len(ROWS))))
check("패킹 단위 = 인보이스 단위", [U["PL"].get(f_pl + i) for i in range(len(ROWS))] == want)
check("패킹 중량 · 부피는 비움(원본에 없음)", all(cell(bk, T, "PL", f_pl + i, c) in (None, "") for i in range(len(ROWS)) for c in (8, 9, 10)))
check("패킹 다음 줄은 빈칸(줄 수 = 품목 수)", cell(bk, T, "PL", f_pl + len(ROWS), 4) in (None, ""))
r2 = C.convert(old_suchaek_empty_pl(), "수책")
U2, bk2, T2 = units_out(r2["out"], "수책")
p2 = T2["sheets"]["PL"]["first"]
check("수책 빈 패킹 → 관리코드(B) · 품명 · 수량 · 단위", r2.get("ok") and [cell(bk2, T2, "PL", p2 + i, 2) for i in range(3)] == ["006M2601"] * 3
      and [cell(bk2, T2, "PL", p2 + i, 4) for i in range(3)] == ["VALVE", "UNIT SET", "BOLT"]
      and [U2["PL"].get(p2 + i) for i in range(3)] == ["EA", "SET", "EA"], r2.get("bad"))

print("§3 원본 패킹에 품목이 있으면 그것을 옮김")
r3 = C.convert(old_somo(pl_items=[("PACK-1", 2, "SET"), ("PACK-2", 7, "EA")], n=4), "소모품")
U3, bk3, T3 = units_out(r3["out"], "소모품")
p3 = T3["sheets"]["PL"]["first"]
check("원본 패킹 2줄 그대로(인보이스로 안 덮음)", r3.get("ok") and r3["report"]["pl_from_inv"] == 0
      and cell(bk3, T3, "PL", p3, 4) == "PACK-1" and cell(bk3, T3, "PL", p3 + 1, 4) == "PACK-2" and cell(bk3, T3, "PL", p3 + 2, 4) in (None, ""),
      r3.get("bad"))
check("패킹 단위 = 패킹 칸 형식(SET · EA)", [U3["PL"].get(p3), U3["PL"].get(p3 + 1)] == ["SET", "EA"])

print("§4 대조가 단위 다름을 잡는다")
src = C.extract(old_somo(n=3))
out, exp, rep = C.build(src, "소모품")
exp2 = dict(exp, units={k: ("SET" if v == "EA" else v) for k, v in exp["units"].items()})
bad = C.verify(out, src, "소모품", exp2)
check("기대 단위를 SET 으로 바꾸면 대조 실패", any("단위" in b for b in bad), bad[:2])
check("원래 기대값이면 통과", not C.verify(out, src, "소모품", exp))

print("§5 서식 만들기")
sx = C._template("소모품")["bytes"]
import zipfile                                     # noqa: E402
sx = zipfile.ZipFile(io.BytesIO(sx)).read("xl/styles.xml").decode("utf-8")
xu = C._xf_units(sx)
ea = next(i for i, u in enumerate(xu) if u == "EA")
cache = {}
s1, sx1 = C._unit_style(sx, ea, "EA", cache)
check("같은 단위면 그 서식 그대로", s1 == str(ea) and sx1 == sx)
s2, sx2 = C._unit_style(sx, ea, "BOX", cache)
s3, sx3 = C._unit_style(sx2, ea, "BOX", cache)
check("새 단위 BOX → 서식 하나 늘고 다시 부르면 같은 번호", C._xf_units(sx2)[int(s2)] == "BOX" and s3 == s2 and sx3 == sx2)
s4, sx4 = C._unit_style(sx, ea, "", {})
check("단위 없음 → 숫자만 형식", C._xf_units(sx4)[int(s4)] == "" and '###,###"' not in sx4.split("<cellXfs")[0][-200:])
check("_unit_of", C._unit_of('###,###\\ "SET"') == "SET" and C._unit_of('General"EA"') == "EA" and C._unit_of("General") == ""
      and C._unit_of('"US$"#,##0.00') == "")

print("§6 화면 글")
main = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
html = io.open(os.path.join(ROOT, "app", "templates", "export_hs_fill.html"), encoding="utf-8").read()
check("기록 요약에 units · pl_from_inv", '"units": rp.get("units") or {}, "pl_from_inv": rp.get("pl_from_inv", 0)' in main)
check("결과 카드 글", "수량 단위는 올린 파일 그대로(" in html and "줄은 인보이스 품목으로 채움(중량·부피는 비어 있음)" in html)

print("§7 실물(수출자료 · 이 PC 에만)")
REAL = os.path.join(ROOT, "수출자료")
if not os.path.isdir(REAL):
    print("  (수출자료 폴더 없음 — 건너뜀)")
else:
    for name, kind, want_inv in (("Invoice&packinglist_VN(261110).xlsx", "소모품", {"EA": 19, "SET": 1}),
                                 ("Invoice&packinglist_VN(260126).xlsx", None, {"EA": 30, "SET": 4})):
        ps = glob.glob(os.path.join(REAL, "**", name), recursive=True)
        if not ps:
            print("  (%s 없음)" % name)
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            rr = C.convert(open(ps[0], "rb").read(), kind or "auto")
        uu = rr.get("report", {}).get("units")
        check("%s 바꿈 · 대조 통과 · 단위 %s" % (name, uu), rr.get("ok") and uu == want_inv, rr.get("bad"))
        if "261110" in name:
            check("261110 패킹 19줄 = 인보이스 품목", rr["report"]["pl_from_inv"] == 19 and rr["report"].get("pl_units") == {"EA": 18, "SET": 1},
                  (rr["report"]["pl_from_inv"], rr["report"].get("pl_units")))

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
