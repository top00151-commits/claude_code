# -*- coding: utf-8 -*-
"""z1191z121 견적서 읽기(app/quote_sheets.py) — 기술영업팀 표본 견적서(참고자료 · 깃허브에 안 올림)로
   ① 앞장(최종) 고르기 ② 머리(업체명·견적일) ③ 항목 줄 수량×단가=금액 ④ 선택표 = 수량 든 줄만 ⑤ 원가 시트·칸은 권한 있을 때만
   표본이 없는 PC 에서는 ⑤(만든 엑셀)만 돈다. 비밀번호 걸린 표본은 풀린 사본(scratchpad qt_dec)이 있을 때만."""
import glob, io, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
import quote_sheets as Q
R = []
def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:200]))

# ⑤ 만든 엑셀: 앞장 + 원가 시트 + 숨긴 열 + 선택표
import openpyxl
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "견적서"
ws["B4"] = "견적일자:"; ws["D4"] = "2026. 11. 23"; ws["B5"] = "업 체 명:"; ws["D5"] = "시험상사"; ws["B6"] = "담 당 자:"; ws["D6"] = "홍길동 프로님"; ws["B7"] = "품   명:"; ws["D7"] = "시험 검사기"
for j, h in enumerate(["No.", "품명 및 규격", "수량", "", "단가(KRW)", "금액(KRW)", "비 고", "원가"]):
    ws.cell(row=9, column=2 + j, value=h or None)
ws.cell(row=10, column=2, value=1); ws.cell(row=10, column=3, value="케이스"); ws.cell(row=10, column=4, value=2); ws.cell(row=10, column=5, value="SET")
ws.cell(row=10, column=6, value=100000); ws.cell(row=10, column=7, value=200000); ws.cell(row=10, column=9, value=70000)
ws.cell(row=11, column=2, value=2); ws.cell(row=11, column=3, value="검사항목"); ws.cell(row=11, column=4, value=1); ws.cell(row=11, column=6, value=654000); ws.cell(row=11, column=7, value=650000)
ws.cell(row=13, column=2, value="특이사항")
s2 = wb.create_sheet("세부항목")
for j, h in enumerate(["구분", "항목", "품명", "수량", "단가", "금액", "5% NEGO"]):
    s2.cell(row=1, column=1 + j, value=h)
for i in range(2, 22):
    s2.cell(row=i, column=3, value="부품%d" % i); s2.cell(row=i, column=5, value=1000 * i)
    if i in (3, 7):
        s2.cell(row=i, column=4, value=1); s2.cell(row=i, column=6, value=1000 * i); s2.cell(row=i, column=7, value=950 * i)
s3 = wb.create_sheet("원가"); s3["A1"] = "원가표"; s3["A2"] = "비밀원가줄"
s4 = wb.create_sheet("숨김"); s4["A1"] = "숨긴 시트"; s4.sheet_state = "hidden"
buf = io.BytesIO(); wb.save(buf)
b = Q.read_book(buf.getvalue())
fr = b["fronts"][b["front"]] if b["front"] is not None else None
check("만든 엑셀: 앞장 1장 고름 · 업체 시험상사 · 견적일", fr and fr["meta"].get("customer") == "시험상사" and fr["meta"].get("qdate"), fr and fr["meta"])
its = fr["items"] if fr else []
check("항목 2줄 · 케이스 2 SET × 100,000 = 200,000", len(its) == 2 and its[0]["qty"] == 2 and its[0]["unit"] == "SET" and its[0]["unit_price"] == 100000 and its[0]["amount"] == 200000, its)
check("원가 칸(70,000)은 항목에 안 들어감", all(it["amount"] != 70000 for it in its), its)
sh = {s["title"]: s for s in b["sheets"]}
check("세부항목 = 선택표 · 수량 든 줄 2개", sh["세부항목"]["select"] and len(sh["세부항목"]["applied"]) == 2, sh["세부항목"].get("applied"))
check("원가 시트·숨긴 시트 = 회사 안(internal)", sh["원가"]["internal"] and sh["숨김"]["internal"], (sh["원가"]["internal"], sh["숨김"]["internal"]))
check("숨긴 시트는 앞장 후보 아님", all(f["title"] != "숨김" for f in b["fronts"]), [f["title"] for f in b["fronts"]])
v0 = Q.view_of(b, False); v1 = Q.view_of(b, True)
check("권한 없음: 원가·숨김 시트 안 보임", [s["title"] for s in v0["sheets"]] == ["견적서", "세부항목"], [s["title"] for s in v0["sheets"]])
check("권한 없음: 앞장 원가 열 값 지움(70,000 안 보임)", all(70000 not in r for r in v0["sheets"][0]["rows"]), "")
check("권한 있음: 시트 4장 다 보임", len(v1["sheets"]) == 4, len(v1["sheets"]))
t0 = " ".join(t for _s, _r, t in Q.search_rows(b, False)); t1 = " ".join(t for _s, _r, t in Q.search_rows(b, True))
check("찾기: 권한 없으면 「비밀원가줄」 안 걸림 · 있으면 걸림", "비밀원가줄" not in t0 and "비밀원가줄" in t1, "")
check("찾기: 선택표는 수량 든 줄만(부품3·부품7 O · 부품5 X)", "부품3" in t0 and "부품7" in t0 and "부품5" not in t0, "")
check("찾기: 앞장 줄은 다 걸림(검사항목)", "검사항목" in t0, "")

# ①~④ 표본(있을 때만)
SRC = r"C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\참고자료\기술영업팀\견적서"
DEC = r"C:\Users\top00\AppData\Local\Temp\claude\6a070250569d191f\253155a4-9ae3-48dd-a684-59fc5743a588\scratchpad\qt_dec"
files = []
for k in ("검사기", "자동화"):
    for p in sorted(glob.glob(os.path.join(SRC, k, "*.xlsx"))):
        d = os.path.join(DEC, k, os.path.basename(p))
        raw = open(d if os.path.exists(d) else p, "rb").read()
        if raw[:4] == b"PK\x03\x04":
            files.append((os.path.basename(p), raw))
if files:
    n_front = n_full = n_ok = 0
    for name, raw in files:
        b = Q.read_book(raw)
        f = b["fronts"][b["front"]] if b["front"] is not None else None
        n_front += 1 if f else 0
        for it in (f["items"] if f else []):
            if it["qty"] is not None and it["unit_price"] is not None and it["amount"] is not None:
                n_full += 1
                n_ok += 1 if abs(it["qty"] * it["unit_price"] - it["amount"]) <= max(1, abs(it["amount"]) * 0.001) else 0
    check("표본 %d장: 앞장 모두 고름(%d)" % (len(files), n_front), n_front == len(files), n_front)
    _e = [x for x in files if x[0].startswith("260223_EFEM")]
    if _e:   # 자동화 양식: 앞장 「비고」 오른쪽 「가공품 / 0.1」 = 내부 계산 칸 → 권한 없으면 안 보임
        _b = Q.read_book(_e[0][1]); _v = Q.view_of(_b, False)["sheets"][0]; _h = _b["sheets"][0]["header_row"]
        check("EFEM: 비고 오른쪽 「가공품」 칸은 권한 없으면 안 보임", "가공품" not in [str(x) for x in _v["rows"][_h]], _v["rows"][_h])
    _m = [x for x in files if x[0].startswith("1209")]
    if _m:   # 원가 계산서 모양: 「원가요소」 칸은 항목 이름(원가 칸 아님) → 일반관리비·이윤·견적가 줄 이름이 보여야 함
        _b = Q.read_book(_m[0][1]); _n = [it["name"] for it in _b["fronts"][_b["front"]]["items"]]
        check("측정선별기: 일반관리비·이윤·최종 공급가 줄 이름 있음", all(any(k in (x or "") for x in _n) for k in ("일반관리비", "이윤", "최종 공급가")), _n)
    check("표본 항목: 수량·단가·금액 다 있는 줄 %d 중 수량×단가=금액 %d (원본 자체가 다른 5줄 제외 97%% 이상)" % (n_full, n_ok), n_full and n_ok >= 0.97 * n_full, (n_full, n_ok))
else:
    print("· 표본 견적서 없음 — 만든 엑셀 시험만")
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
