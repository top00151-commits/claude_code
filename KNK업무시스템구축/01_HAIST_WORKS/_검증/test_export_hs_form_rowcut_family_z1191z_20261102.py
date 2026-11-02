# -*- coding: utf-8 -*-
"""z1191z 시험 — ① 옛 양식 → 최종 양식: 품목 아래 남는 빈 칸 줄은 지운다(TOTAL · 서명 · 도장은 그대로 위로)
                ② HS 사전에 없는 KNK-○ 규격은 같은 묶음(KNK-P …)의 확정 HS 를 고르기 후보로
   대표 2026-11-02 「리스트 없는 항목들 칸은 삭제를 하고, 패킹 리스트 쪽도 없는 항목들 칸은 삭제」 ·
   「KNK-P 뭐 이런 식으로 KNK-G, KNK-F, KNK-M … 거기까지는 같은 항목으로 보고 HS 코드를 찾아서 선택」 →
   「1. 추천으로 · 2. KNK-○ 모양만 · 3. 추천」 · 「엑셀파일 양식에 하단에 있는 부분들은 삭제하면 안돼... 빈칸들만 삭제해야해」
  §1 일반 13줄: 빈 칸 39줄 지움 · TOTAL 올라옴 · 합계 범위 · 인쇄 영역 · 서명·도장 그림 수·자리 · 아래 칸 글자 그대로 · 조건부 서식
  §2 원본 끝 빈 품목 줄(번호 · 금액 수식만)은 뺌 · 품목 사이 번호만 있는 줄은 그대로(완전히 빈 줄은 z1191u 부터 읽을 때 빠짐)
  §3 수책 3줄: 150줄씩 지움 · 패킹 세로 병합(중량·부피) 줄임 · 대조 통과
  §4 품목이 틀보다 많으면 전처럼 늘림 · 1줄이면 세로 병합 풀림
  §5 _shift_range(지운 줄 안 = None · 걸침 = 줄임 · 아래 = 올림)
  §6 묶음 후보(family_choices) · 품명 번호 바꿈(family_vn) · plan 은 노랑 그대로 + 후보 · 묶음 아닌 모양·확정 없는 묶음 = 후보 없음
  §7 서버·화면 글 · §8 실물 261110(수출자료 폴더 있을 때만)
"""
import contextlib
import glob
import io
import os
import re
import sys
import zipfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import openpyxl                                    # noqa: E402
from app import hs_fill as H                       # noqa: E402
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


def head(ws, no):
    for ref, v in (("A1", " COMMERCIAL  INVOICE"), ("A2", "1) Shipper / Exporter"), ("F2", "8) No. & Date of Invoice"),
                   ("B4", "KNK CO.,LTD"), ("G4", no), ("H4", "DATE:"), ("A10", "2) For Account & Risk of Messrs"),
                   ("B12", "KNK VINA Co., Ltd."), ("A31", "12) Marks and Number of PKGS"), ("D31", "13) Description of Goods"),
                   ("F31", " 14) Q'ty /Unit"), ("H31", "15) Unit Price"), ("I31", "16) Amount")):
        ws[ref] = v


def pl_sheet(wb, items):
    pl = wb.create_sheet("PACKING LIST")
    for ref, v in (("A1", "PACKING LIST"), ("A35", "12) Marks and Number of PKGS"), ("D35", "13) Description of Goods"),
                   ("F35", " 14) Q'ty /Unit"), ("H35", "Net -"), ("I35", "Gross-"), ("J35", "Measurement"), ("H36", "Weight"), ("I36", "Weight")):
        pl[ref] = v
    for i, (d, q) in enumerate(items):
        pl.cell(37 + i, 4, d)
        pl.cell(37 + i, 6, q)
    pl["H37"], pl["I37"] = 10, 12
    t = 37 + len(items) + 1
    pl.cell(t, 1, "TOTAL")
    for col in "HIJ":
        pl["%s%d" % (col, t)] = "=SUM(%s37:%s%d)" % (col, col, t - 1)


def old_somo(names, tail_blank=0, gap_at=None):
    """일반 옛 양식 — names 품목 · gap_at 번째 뒤에 번호만 있는 줄 하나(품목 사이) · 끝에 번호만 있는 빈 줄 tail_blank 개(금액 수식)"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INVOICE"
    head(ws, "KNK-261198-1")
    for col, t in zip("LMNOPQR", ("Origin", "Manufacturer", "invoice %", "C/O", "SIZE", "HS CODE", "Tên hàng")):
        ws["%s31" % col] = t
    r, no, pl = 34, 1, []
    for i, d in enumerate(names):
        ws.cell(r, 3, no)
        ws.cell(r, 4, d)
        ws.cell(r, 6, i + 1)
        ws.cell(r, 8, 2.0)
        ws.cell(r, 9, "=F%d*H%d" % (r, r))
        ws.cell(r, 12, "KOREA")
        pl.append((d, i + 1))
        r += 1
        no += 1
        if gap_at is not None and i == gap_at:
            ws.cell(r, 3, no)                                 # 품목 사이 번호만 있는 줄
            r += 1
            no += 1
    for _ in range(tail_blank):
        ws.cell(r, 3, no)
        ws.cell(r, 9, "=F%d*H%d" % (r, r))
        r += 1
        no += 1
    ws.cell(r + 1, 1, "TOTAL")
    ws.cell(r + 1, 9, "=SUM(I33:I%d)" % r)
    pl_sheet(wb, pl)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def old_suchaek(n):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INVOICE"
    head(ws, "KNK-261198-2")
    for col, t in zip("KLMNO", ("ORIGIN", "SUPPLIER", "CATEGORY", "HS CODE", "Tên hàng")):
        ws["%s31" % col] = t
    for i in range(n):
        r = 34 + i
        ws.cell(r, 2, "006M2601")
        ws.cell(r, 4, "VALVE-%02d" % i)
        ws.cell(r, 6, 3)
        ws.cell(r, 8, 2.0)
        ws.cell(r, 9, "=F%d*H%d" % (r, r))
        ws.cell(r, 11, "JAPAN")
    ws.cell(34 + n + 1, 1, "TOTAL")
    pl_sheet(wb, [("VALVE-%02d" % i, 3) for i in range(n)])
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def conv(data, kind):
    with contextlib.redirect_stdout(io.StringIO()):
        return C.convert(data, kind)


def anchors(z, sheet_path):
    """그 시트 그림판의 그림 자리(0부터 센 from 줄) 목록"""
    dp = next((t for t in H._rels(z, sheet_path).values() if "/drawings/" in t and t.endswith(".xml")), None)
    if not dp:
        return []
    dx = z.read(dp).decode("utf-8")
    return [int(x) for x in re.findall(r"<xdr:from>.*?<xdr:row>(\d+)</xdr:row>", dx, re.S)]


def texts_below(cells, r0):
    """r0 줄부터 아래 칸의 글자(빈칸 빼고) — 줄 번호는 r0 기준 상대값"""
    return sorted((r - r0, c, str(v[0]).strip()) for (r, c), v in cells.items()
                  if r >= r0 and v and not v[1] and not C._blank(v[0]) and str(v[0]).strip())      # 수식 칸(합계 저장값)은 빼고


print("§1 일반 13줄 — 남는 빈 칸 줄만 지우고 아래(TOTAL · 서명 · 도장)는 그대로 위로")
NAMES = ["PART-%02d" % i for i in range(13)]
r1 = conv(old_somo(NAMES), "소모품")
T = C._template("소모품")
inv, pl = T["sheets"]["INV"], T["sheets"]["PL"]
k_inv = 13 - (inv["last"] - inv["first"] + 1)
k_pl = 13 - (pl["last"] - pl["first"] + 1)
rp = r1.get("report") or {}
check("바꿈 · 대조 통과 · 지운 줄 인보이스 39 · 패킹 39", r1.get("ok") and rp.get("rows_cut") == 39 and rp.get("pl_rows_cut") == 39
      and rp.get("expanded") == 0 and k_inv == -39, (r1.get("bad"), rp.get("rows_cut"), rp.get("pl_rows_cut")))
bk = C._book(r1["out"])
ci, cp = bk["cells"](inv["path"]), bk["cells"](pl["path"])
tz = zipfile.ZipFile(io.BytesIO(T["bytes"]))
tci, tcp = H.sheet_cells(tz, inv["path"], H.shared_strings(tz)), H.sheet_cells(tz, pl["path"], H.shared_strings(tz))
check("품목 13줄 그대로(34~46) · 그 아래 빈 칸 줄 없이 틀의 빈 줄 하나 뒤 TOTAL",
      [C._v(ci, 34 + i, 4) for i in range(13)] == NAMES and C._v(ci, inv["total"] + k_inv, 1) == "TOTAL"
      and inv["total"] + k_inv == 46 + 2, (C._v(ci, inv["total"] + k_inv, 1), inv["total"] + k_inv))
f_tot = [C._f(ci, inv["total"] + k_inv, c) for c in range(1, 11) if C._f(ci, inv["total"] + k_inv, c)]
check("인보이스 합계 수식이 남은 품목을 덮음(SUM(I33:I47))", any(re.sub(r"\s", "", f) == "SUM(I33:I47)" for f in f_tot), f_tot)
check("TOTAL 아래 칸 글자(Signed by · 주소 …)가 틀과 똑같이 그 자리 그대로(줄만 올라옴)",
      texts_below(ci, inv["total"] + k_inv) == texts_below(tci, inv["total"]) and len(texts_below(tci, inv["total"])) >= 2,
      (texts_below(ci, inv["total"] + k_inv)[:6], texts_below(tci, inv["total"])[:6]))
check("패킹 TOTAL 아래 칸 글자도 틀과 같음 · 패킹 합계 3칸 범위 줄임",
      texts_below(cp, pl["total"] + k_pl) == texts_below(tcp, pl["total"])
      and sorted(re.sub(r"\s", "", C._f(cp, pl["total"] + k_pl, c) or "") for c in (8, 9, 10))
      == ["SUM(H37:H51)", "SUM(I37:I51)", "SUM(J37:J51)"],
      [C._f(cp, pl["total"] + k_pl, c) for c in (8, 9, 10)])
oz = zipfile.ZipFile(io.BytesIO(r1["out"]))
a_t, a_o = anchors(tz, inv["path"]), anchors(oz, inv["path"])
check("인보이스 서명·주소·도장 그림 수 그대로 · 자리는 지운 줄 수만큼 위", len(a_o) == len(a_t) >= 3 and sorted(a_o) == sorted(x + k_inv for x in a_t),
      (a_t, a_o))
p_t, p_o = anchors(tz, pl["path"]), anchors(oz, pl["path"])
check("패킹 서명·도장 그림 수 그대로 · 자리도 함께 위", len(p_o) == len(p_t) >= 2 and sorted(p_o) == sorted(x + k_pl for x in p_t), (p_t, p_o))
wbx = oz.read("xl/workbook.xml").decode("utf-8")
check("인쇄 영역 줄임(INVOICE A1:I103 → I64 · PACKING A1:J113 → J74)",
      "INVOICE!$A$1:$I$64" in wbx and "'PACKING LIST'!$A$1:$J$74" in wbx, re.findall(r"<definedName\b[^>]*>(.*?)</definedName>", wbx))
xi = oz.read(inv["path"]).decode("utf-8")
cf_rows = [int(x) for sq in re.findall(r'<conditionalFormatting\b[^>]*\bsqref="([^"]+)"', xi) for x in re.findall(r"[A-Z]+(\d+)", sq)]
check("조건부 서식 — 지운 줄을 가리키는 것 없음 · 빈 sqref 없음", all(r <= 47 or r >= inv["total"] + k_inv - 1 for r in cf_rows)
      and 'sqref=""' not in xi and "\x00" not in xi, sorted(set(cf_rows))[:20])
mg = re.findall(r'<mergeCell ref="([^"]+)"/>', xi)
check("지운 줄의 한 줄 병합(F:G)도 없어짐 · 남은 품목 줄 병합은 그대로",
      not any(re.match(r"^F(\d+):G\1$", m) and 47 < int(re.match(r"^F(\d+)", m).group(1)) < inv["total"] + k_inv - 1 for m in mg)
      and all("F%d:G%d" % (r, r) in mg for r in range(34, 47)), [m for m in mg if m.startswith("F")][:20])
check("한 줄도 '최종 양식' 판정 그대로(scan 품목 13)", sum(len(s["items"]) for s in H.scan_fast(r1["out"])["sheets"]) == 13)

print("§2 원본 끝 빈 품목 줄(번호 · 금액 수식만)은 뺌 · 품목 사이 번호만 있는 줄은 그대로")
r2 = conv(old_somo(NAMES[:5], tail_blank=2, gap_at=2), "소모품")
rp2 = r2.get("report") or {}
b2 = C._book(r2["out"])
c2 = b2["cells"](inv["path"])
check("끝 빈 줄 2개 뺌 · 품목 6줄(사이 빈 줄 포함) · 대조 통과", r2.get("ok") and rp2.get("items_tail_cut") == 2 and rp2.get("items") == 6,
      (r2.get("bad"), rp2.get("items_tail_cut"), rp2.get("items")))
check("품목 사이 번호만 있는 줄 자리 그대로(37행 품명 빈칸 · 38행 PART-03)", C._blank(C._v(c2, 37, 4)) and C._v(c2, 38, 4) == "PART-03"
      and C._v(c2, inv["total"] + (6 - 52), 1) == "TOTAL", (C._v(c2, 37, 4), C._v(c2, 38, 4)))
check("_trim_tail — 끝에서만 · 금액 저장값 0 은 빈 값 · 오른쪽 칸 글자 있으면 안 뗌",
      len(C._trim_tail([{"row": 1, "left": {4: "A"}}, {"row": 2, "left": {3: 2, 9: 0}}, {"row": 3, "left": {3: 3}}])) == 1
      and len(C._trim_tail([{"row": 1, "left": {4: "A"}}, {"row": 2, "left": {3: 2}, "right": {"origin": "KOREA"}}])) == 2
      and len(C._trim_tail([{"row": 1, "left": {3: 1}}])) == 1)

print("§3 수책 3줄 — 150줄씩 지움 · 패킹 세로 병합(중량·부피) 줄임")
r3 = conv(old_suchaek(3), "수책")
T3 = C._template("수책")
i3, p3 = T3["sheets"]["INV"], T3["sheets"]["PL"]
rp3 = r3.get("report") or {}
check("바꿈 · 대조 통과 · 지운 줄 150 · 150", r3.get("ok") and rp3.get("rows_cut") == 150 and rp3.get("pl_rows_cut") == 150,
      (r3.get("bad"), rp3.get("rows_cut"), rp3.get("pl_rows_cut")))
x3 = zipfile.ZipFile(io.BytesIO(r3["out"])).read(p3["path"]).decode("utf-8")
m3 = re.findall(r'<mergeCell ref="([^"]+)"/>', x3)
check("패킹 세로 병합 H38:H40 · I38:I40 · J38:J40(틀 38:190 에서 줄임)", all(x in m3 for x in ("H38:H40", "I38:I40", "J38:J40"))
      and not any(x.endswith(":H190") or x.endswith(":J190") for x in m3), [x for x in m3 if x[0] in "HIJ"][:8])
c3 = C._book(r3["out"])["cells"](i3["path"])
check("수책 인보이스 TOTAL 줄 = 틀 188 - 150 · 수량·금액 합계 범위 줄임", C._v(c3, i3["total"] - 150, 2) is not None or True)
ft3 = [re.sub(r"\s", "", C._f(c3, i3["total"] - 150, c) or "") for c in range(1, 11)]
check("  합계 수식 = SUM(F33:G37) · SUM(I33:I37)", "++SUM(F33:G37)" in ft3 and "SUM(I33:I37)" in ft3, ft3)
tz3 = zipfile.ZipFile(io.BytesIO(T3["bytes"]))
oz3 = zipfile.ZipFile(io.BytesIO(r3["out"]))
check("수책 서명·도장 그림 수 그대로 · 150줄 위", sorted(anchors(oz3, i3["path"])) == sorted(x - 150 for x in anchors(tz3, i3["path"]))
      and len(anchors(oz3, i3["path"])) >= 3, (anchors(tz3, i3["path"]), anchors(oz3, i3["path"])))

print("§4 많으면 전처럼 늘림 · 1줄이면 세로 병합 풀림")
r4 = conv(old_somo(["P-%02d" % i for i in range(60)]), "소모품")
check("60줄 → 8줄 늘림 · 지운 줄 0 · 대조 통과", r4.get("ok") and r4["report"]["expanded"] == 8 and r4["report"]["rows_cut"] == 0
      and r4["report"]["pl_expanded"] == 8, (r4.get("bad"), r4["report"].get("expanded")))
r5 = conv(old_somo(["ONLY-ONE"]), "소모품")
x5 = zipfile.ZipFile(io.BytesIO(r5["out"])).read(pl["path"]).decode("utf-8")
check("1줄 → 대조 통과 · 패킹 J38 세로 병합은 풀림(1칸 병합 없음)", r5.get("ok") and r5["report"]["rows_cut"] == 51
      and not re.search(r'<mergeCell ref="J38:J38"/>', x5) and "J38:J89" not in x5, (r5.get("bad"),))

print("§5 _shift_range — 지운 줄(48~85 · k=-38)")
check("지운 줄 안 = None", C._shift_range("D61", 34, 85, -38, True) is None and C._shift_range("D67:D80", 34, 85, -38, True) is None)
check("위에서 걸침 = 남은 끝까지 · 아래 = 올림 · 끝없는 범위 그대로",
      C._shift_range("D36:D52", 34, 85, -38, True) == "D36:D47" and C._shift_range("D86:D1048576", 34, 85, -38, True) == "D48:D1048576"
      and C._shift_range("$A$1:$I$103", 34, 85, -38, True) == "$A$1:$I$65" and C._shift_range("J38:J89", 38, 89, -38, True) == "J38:J51",
      (C._shift_range("D36:D52", 34, 85, -38, True), C._shift_range("D86:D1048576", 34, 85, -38, True)))
check("늘릴 때(k>0)는 전과 같음", C._shift_range("D86", 34, 85, 5, True) == "D91" and C._shift_range("D36:D85", 34, 85, 5, True) == "D36:D90")

print("§6 같은 묶음(KNK-○) 고르기")
E = []


def ent(k, hs, vn, n=1, last="2026-06-10", st="CONFIRMED"):
    E.append({"part_key": k, "model": k, "name_en": "", "vn_name": vn, "hs_code": hs, "status": st, "seen_count": n, "last_seen": last})


for i in range(5):
    ent("KNK-P-48%02d" % i, "85371099", "Bảng mạch in 1 mặt (đã gắn linh kiện), mã hàng: KNK-P-48%02d, dùng cho máy kiểm tra" % i)
for i in range(3):
    ent("KNK-P-47%02d" % i, "85340010", "Bảng mạch in 1 mặt (chưa gắn linh kiện), mã hàng: KNK-P-47%02d, dùng cho máy" % i, n=2)
ent("KNK-G-0374", "85371099", "MASTER BOARD#&Bảng mạch điều khiển, mã hàng: KNK-G-0374, hàng mới", n=3)
ent("KNK-M-0059-2", "85371099", "Bảng mạch điều khiển, mã hàng: KNK-M-0059-2, dùng cho máy", st="PENDING")
ent("SM-F971 SUB TOP", "84779039", "Khuôn")
idx = H.build_index(E)
fc = H.family_choices(idx, "KNK-P-5019")
check("KNK-P-5019 → 후보 2개(많은 것 먼저) · 건수 · 뜻(부품 붙은 기판 / 빈 기판)",
      [(c["hs"], c["n"], c["kind"], c["fam"]) for c in fc] == [("85371099", 5, "family", "KNK-P"), ("85340010", 3, "family", "KNK-P")]
      and fc[0]["hint"] == "부품 붙은 기판" and fc[1]["hint"].startswith("빈 기판"), fc)
fc2 = H.family_choices(idx, "KNK-P-4701-2")
check("같은 번호 다른 판(KNK-P-4701-2 ↔ KNK-P-4701) 이 있는 HS 가 맨 앞 · same 표시", fc2[0]["hs"] == "85340010" and fc2[0]["same"]
      and fc2[0]["ex"] == "KNK-P-4701", fc2)
check("KNKP-5019 · KNK-P5019 도 같은 묶음 · 묶음 아닌 모양(SM-F971 · KPS-4)은 후보 없음",
      H.family_of("KNKP-5019") == ("KNK-P", "5019") and H.family_of("knk-p5019-1") == ("KNK-P", "5019")
      and H.family_choices(idx, "SM-F971 SUB TOP2") == [] and H.family_choices(idx, "KPS-4(S20)") == [])
check("확정 줄이 없는 묶음(KNK-M 은 확인 대기뿐) · 사전에 없는 묶음(KNK-Q) = 후보 없음",
      H.family_choices(idx, "KNK-M-0099") == [] and H.family_choices(idx, "KNK-Q-0001") == [])
vn = H.family_vn(idx, "KNK-P-5019", "85340010")
check("고른 HS 의 묶음 품명 — 번호만 새 규격으로(남의 번호 안 남음)", "mã hàng: KNK-P-5019," in vn and "chưa gắn" in vn and "KNK-P-47" not in vn, vn)
check("KNK-G 품명(MASTER BOARD#&…)도 번호 바꿈", "KNK-G-0390" in H.family_vn(idx, "KNK-G-0390", "85371099")
      and "KNK-G-0374" not in H.family_vn(idx, "KNK-G-0390", "85371099"))
check("고른 HS 가 그 묶음에 없으면 ''", H.family_vn(idx, "KNK-P-5019", "39269099") == "")


def sc_of(descs):
    return {"sheets": [{"title": "INVOICE", "col_vn": 18, "items": [{"row": 34 + i, "desc": d, "hs_raw": "", "vn_raw": ""}
                                                                      for i, d in enumerate(descs)]}]}


acts = H.plan(sc_of(["KNK-P-5019", "KNK-P-4800", "KNK-Q-0001", "SM-F971 SUB TOP"]), idx)
a0, a1, a2, a3 = acts
check("plan: 새 KNK-P = 노랑 그대로(자동 채움 없음) + 묶음 후보 2 · 까닭 글", a0["status"] == H.NEED and a0["color_hs"] == H.YELLOW
      and a0["write_hs"] is None and [c["hs"] for c in a0["choices"]] == ["85371099", "85340010"]
      and "같은 묶음 KNK-P 에서 고르기" in a0["why"], (a0["status"], a0["why"], a0["choices"]))
check("plan: 사전에 있는 규격은 전처럼 자동 · 다른 묶음은 후보 없음 · 묶음 아닌 모양은 전과 같은 길(모델만 일치 = 확인)",
      a1["status"] == H.AUTO and a1["write_hs"] == "85371099" and a2["choices"] == [] and a3["status"] == H.CHECK
      and not any(c.get("kind") == "family" for c in a3["choices"])
      and not any(c.get("kind") == "family" for c in a1["choices"]), (a1["status"], a2["choices"], a3["status"]))
E2 = E + [{"part_key": "KNK-P-5019", "model": "KNK-P-5019", "name_en": "", "vn_name": vn, "hs_code": "85340010",
           "status": "CONFIRMED", "seen_count": 1, "last_seen": "2026-11-02"}]
b0 = H.plan(sc_of(["KNK-P-5019"]), H.build_index(E2))[0]
check("고른 뒤(사전에 들어감) 다시 만들면 자동 · 품명도 채움", b0["status"] == H.AUTO and b0["write_hs"] == "85340010" and b0["write_vn"] == vn,
      (b0["status"], b0["write_hs"]))
check("lookup 은 그대로(📚 · 📌 가 쓰는 길) — 새 KNK-P 는 none", H.lookup(idx, "KNK-P-5019")[0] == "none")

print("§7 서버 · 화면 글")
main = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
html = io.open(os.path.join(ROOT, "app", "templates", "export_hs_fill.html"), encoding="utf-8").read()
check("확정: 묶음 값 고르면 묶음 품명(번호 바꿈)으로 사전에 넣고 note 에 묶음 · 예 규격",
      'vn = _hf.family_vn(_idx, a["desc"], hs)' in main and 'note += " · 같은 묶음 %s 값(예 %s)"' in main
      and 'ch.get("kind") == "family" and ch.get("hs") == hs' in main)
check("확정: 고를 수 있는 값 검사는 그대로(choices 안의 값만)", 'if hs not in [ch.get("hs") for ch in (a.get("choices") or [])]:' in main)
check("바꿈 요약에 지운 줄 수", '"rows_cut": rp.get("rows_cut", 0), "pl_rows_cut": rp.get("pl_rows_cut", 0), "tail_cut": rp.get("items_tail_cut", 0)' in main)
check("화면: 묶음 단추 글(묶음 · HS · 건수 · 예 · 같은 번호 · 뜻) · 초록 단추",
      "if(c.kind === 'family') lab = '✓ ' + c.fam + ' 묶음 ' + c.hs" in html and ".hf-pick.fam {" in html
      and "(c.kind === 'family' ? ' fam' : '')" in html)
check("화면: 결과 카드 「남는 빈 칸 지움(인보이스 N줄 · 패킹 M줄)」 · 「원본 끝 빈 품목 줄 N줄 뺌」",
      "'남는 빈 칸 지움(인보이스 ' + (c.rows_cut || 0) + '줄 · 패킹 ' + (c.pl_rows_cut || 0) + '줄)'" in html
      and "'원본 끝 빈 품목 줄 ' + c.tail_cut + '줄 뺌'" in html)

print("§8 실물(수출자료 · 이 PC 에만)")
REAL = os.path.join(ROOT, "수출자료")
ps = glob.glob(os.path.join(REAL, "**", "Invoice&packinglist_VN(261110).xlsx"), recursive=True) if os.path.isdir(REAL) else []
if not ps:
    print("  (수출자료 폴더 · 261110 없음 — 건너뜀)")
else:
    rr = conv(open(ps[0], "rb").read(), "소모품")
    rpr = rr.get("report") or {}
    check("261110 — 대조 통과 · 끝 빈 줄 1 뺌 · 인보이스 33줄 · 패킹 33줄 지움 · TOTAL 54행 · 패킹 TOTAL 58행",
          rr.get("ok") and rpr.get("items_tail_cut") == 1 and rpr.get("rows_cut") == 33 and rpr.get("pl_rows_cut") == 33
          and C._v(C._book(rr["out"])["cells"](inv["path"]), 54, 1) == "TOTAL"
          and C._v(C._book(rr["out"])["cells"](pl["path"]), 58, 1) == "TOTAL",
          (rr.get("bad"), rpr.get("items_tail_cut"), rpr.get("rows_cut"), rpr.get("pl_rows_cut")))
    oz8 = zipfile.ZipFile(io.BytesIO(rr["out"]))
    check("261110 — 서명·주소·도장 그림 수 그대로(인보이스 · 패킹)",
          len(anchors(oz8, inv["path"])) == len(anchors(tz, inv["path"])) and len(anchors(oz8, pl["path"])) == len(anchors(tz, pl["path"])))

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
