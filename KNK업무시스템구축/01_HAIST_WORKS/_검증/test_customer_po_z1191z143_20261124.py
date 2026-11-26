# -*- coding: utf-8 -*-
"""z1191z143 (대표 11-24 「견적 관리 화면에 고객사에서 받은 발주서도 등록 · 등록한 발주서는 관리번호 또는 수주번호 상세보기에서 견적서처럼」):
고객 발주서 — 파일 종류 확인 · 엑셀 금액 읽기 · 자리 후보 · 권한 · 화면 글 · 화면 스크립트 문법
z1191z160 (대표 11-26 「검토하는 기능을 빼줘 · 여러 개 등록될 수 있게」)로 바꾼 것: §3 금액 비교(same) 시험 → 「비교 함수 없음」 ·
  §4 최종/이전·금액 판정 → 「여러 장 같은 자격(최근 위) · 비교 없음」 · §6 확인했음 주소 없음 · §7 화면 글(최종·이전·확인했음 없음 · 「더 올리기」)"""
import io, contextlib, os, re, sqlite3, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from app import customer_po as P
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:300]))


# 1 파일 종류 = 확장자 + 첫 바이트
check("PDF·PNG·JPG·엑셀(xlsx·xls) 받음", P.kind_of("a.pdf", b"%PDF-1.4 x") == "pdf" and P.kind_of("a.PNG", b"\x89PNG\r\n") == "img"
      and P.kind_of("a.jpg", b"\xff\xd8\xff\xe0") == "img" and P.kind_of("a.xlsx", b"PK\x03\x04..") == "xl"
      and P.kind_of("a.xls", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1") == "xl")
# z1191z163 (대표 11-26 발주서 등록 안 됨 · 「사용자들이 등록하는걸 믿고」): 문서 보안(DRM) 걸린 파일도 받음 — 확장자 목록 밖만 막음
check("확장자가 PDF·엑셀이면 내용이 달라도(DRM 등) 받음 · 다른 확장자는 안 받음", P.kind_of("a.pdf", b"PK\x03\x04") == "pdf" and P.kind_of("b.xlsx", b"<DRM>") == "xl" and P.kind_of("a.exe", b"MZ") is None and P.kind_of("a.hwp", b"x") is None)

# 2 엑셀 금액 읽기(AI 없음)
import openpyxl
from app import quote_sheets as QS


def book(cells):
    wb = openpyxl.Workbook(); ws = wb.active
    for (r, c_), v in cells.items():
        ws.cell(row=r, column=c_, value=v)
    b = io.BytesIO(); wb.save(b)
    return QS.read_book(b.getvalue())


a, ccy, lab = P.read_amount(book({(1, 1): "발 주 서", (3, 1): "품명", (3, 2): "수량", (4, 1): "PBA 검사기", (4, 2): 2,
                                  (8, 1): "공급가액", (8, 3): 4020000, (9, 1): "부가세", (9, 3): 402000, (10, 1): "합계", (10, 3): 4422000}))
check("공급가액 옆 숫자 먼저(합계보다)", a == 4020000 and "공급가" in lab, (a, lab))
a, ccy, lab = P.read_amount(book({(2, 1): "Unit: USD", (5, 1): "Total Amount", (6, 1): 12500.5}))
check("Total 아래 숫자 · 통화 USD", a == 12500.5 and ccy == "USD", (a, ccy))
check("합계 글이 없으면 금액 없음", P.read_amount(book({(1, 1): "메모", (1, 2): 100}))[0] is None)

# 3 z1191z160: 금액 비교 함수 없음(읽은 금액은 보여 주기만)
check("z1191z160: 발주서 금액 비교 함수(same) 없음", not hasattr(P, "same"))

# 4 z1191z160: 여러 장 모두 같은 자격 — 최종·이전 구분 없음 · 금액 비교 없음
fs = [{"id": 1, "kind": "pdf", "amount": None}, {"id": 5, "kind": "xl", "amount": 3900000, "currency": "KRW"}, {"id": 3, "kind": "img", "amount": None}]
st = P.slot_status(fs, 4020000, "KRW")
check("여러 장 모두 목록(최근 위) · 최종·이전 칸 없음", [x["id"] for x in st["files"]] == [5, 3, 1] and "final" not in st and "prev" not in st, st)
check("엑셀 금액이 수주와 달라도 ⚠ 없음(st = ok)", st["st"] == "ok" and P.slot_status([fs[1]], 4020000, "KRW")["st"] == "ok")
check("없음 = none · 빈 목록", P.slot_status([]) == {"files": [], "st": "none"})

# 5 main 연결 — 자리 후보 · 화면 상태
with contextlib.redirect_stdout(io.StringIO()):
    import app.main as M
c = sqlite3.connect(":memory:"); c.row_factory = sqlite3.Row
c.execute("CREATE TABLE projects(id INTEGER PRIMARY KEY, mgmt_code TEXT, name TEXT, customer_name TEXT, is_archived INTEGER)")
c.execute("CREATE TABLE orders(id INTEGER PRIMARY KEY, project_id INTEGER, order_no TEXT, status TEXT, order_date TEXT, currency TEXT, total_amount REAL)")
P.table(c)
c.executemany("INSERT INTO projects VALUES(?,?,?,?,0)", [(1, "006T2608", "PBA", "한국성전"), (2, "010T2601", "다른 것", "다른회사")])
c.executemany("INSERT INTO orders VALUES(?,?,?,?,?,?,?)", [(1, 1, "T-260826-1", "SHIPPED", "2026-08-26", "KRW", 2010000),
                                                          (2, 1, "T-260911-1", "CANCELLED", "2026-09-11", "KRW", 1),
                                                          (3, 1, "T-261016-4", "CONFIRMED", "2026-10-16", "KRW", 4020000)])
cs, pick, why = M._z143_cands(c, "PO_T-261016-4_한국성전.pdf")
check("파일 이름의 수주번호 → 그 수주 하나 · 미리 고름", len(cs) == 1 and cs[0]["oid"] == 3 and pick == 0 and "수주번호" in why, cs)
cs, pick, why = M._z143_cands(c, "006T2608 발주서.xlsx")
check("관리번호만 → 취소 뺀 수주들만(관리번호 자리 없음 · z1191z156) · 고르기(미리 안 고름)", [x["oid"] for x in cs] == [1, 3] and pick is None, cs)
check("취소 수주 번호는 후보 아님", M._z143_cands(c, "T-260911-1.pdf")[0] == [])
check("번호가 없으면 후보 없음(찾기로)", M._z143_cands(c, "scan_001.jpg")[0] == [])
c.execute("INSERT INTO project_po_files(tok, project_id, order_id, orig_name, stored, kind, by_id, created_at) VALUES('a',1,3,'old.pdf','x/a.pdf','pdf',1,'2026-11-01 10:00')")
check("자리 후보에 「이미 있는 발주서 수」(z1191z160: 함께 남음)", M._z143_cands(c, "T-261016-4.pdf")[0][0]["has"] == 1)

# 6 권한·안전(코드)
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
blk = src[src.index("# ═══ z1191z143"):min(src.index("# z1191z59 (대표 2026-11-18"), src.find("# ═══ z1191z150") if "# ═══ z1191z150" in src else len(src))]   # z1191z150 블록(견적서·발주서 모아 보기)은 따로
check("올리기·붙이기·찾기 = can_use_sales·can_view_sales", blk.count("if not (can_use_sales(u) and can_view_sales(u)):") >= 3)
check("z1191z160: 발주서 금액 「확인했음」 주소 없음", '@app.post("/api/customer-po/ack/' not in src and "amt_ack_by=?" not in blk)
check("보기·내려받기 = can_view_sales · 빼기 = 올린 사람·기술영업팀(z63)", blk.count("if not can_view_sales(u):") >= 2 and "_z63_can_remove(u, dict(r))" in blk)
check("저장 이름 = 임의 글자(올린 파일 이름을 경로에 쓰지 않음) · 20MB", 'stored = f"{sub}/{tok}{ext}"' in blk and "_qr61.MAX_BYTES" in blk)
check("다시 올려도 예전 발주서를 지우지 않음(올리기·붙이기에 DELETE 없음)",
      "DELETE" not in blk[blk.index("async def api_customer_po_upload_z143"):blk.index("@app.get(\"/api/customer-po/search\")")].replace("DELETE FROM project_po_files WHERE id=?\", (r[\"id\"],))", "")
      .split("_z143_cleanup(c)")[0] and "DELETE" not in blk[blk.index("async def api_customer_po_place_z143"):blk.index("@app.post(\"/api/customer-po/remove/{fid}\")")])
check("견적서 표와 따로(project_po_files) — 견적 숫자에 안 섞임", "project_po_files" in blk and "project_quote_files" not in blk)

# 7 화면 글
T = lambda *p: open(os.path.join(ROOT, "app", "templates", *p), encoding="utf-8").read()
q = T("sales_quotations.html")
check("견적 관리: 「고객 발주서」 칸 · 위 「고객 발주서 올리기」 · 줄마다 올리기", "<th title=\"z1191z143" in q and "고객 발주서 올리기" in q and q.count("z143-up") >= 2 and "z143-box" in q)
pd = T("project_detail.html")
check("프로젝트 상세: 위 「고객 발주서」 칸 + 수주 카드 「📄 발주서」", "고객 발주서</dt>" in pd and "📄 발주서" in pd and "_v5_partials/po_rows.html" in pd)
od = T("sales_order_detail.html")
check("수주 상세: 「📄 고객 발주서」 + 관리번호 전체 발주서 줄", "📄 고객 발주서" in od and "_v5_partials/po_rows.html" in od)
pr = T("_v5_partials", "po_rows.html")
check("발주서 줄: 여러 장 반복 · 보기 · 내려받기 · 빼기 · 「더 올리기」", all(k in pr for k in ("{% for _pf in _pfs %}", "👁 보기", "⬇ 내려받기", "z143-rm", "발주서 더 올리기")))
_prx = re.sub(r"\{#.*?#\}", "", pr, flags=re.S)   # 설명 주석 뺀 화면 글
check("z1191z160 발주서 줄: 최종·이전 발주서·확인했음·금액 다름 글 없음", not any(k in _prx for k in ("최종", "이전 발주서", "z143-ack", "확인했음", "금액 다름")), [k for k in ("최종", "이전 발주서", "z143-ack", "확인했음", "금액 다름") if k in _prx])
_cv = T("customer_po_view.html")
check("보기 화면: PDF 틀 · 사진 · 엑셀 시트 표 · 같은 수주 발주서 목록", all(k in _cv for k in ("<iframe", "<img", "qv-g", "같은 수주의 발주서")))
check("z1191z160 보기 화면: 최종·이전 발주서·확인했음·금액 다름 없음", not any(k in re.sub(r"\{#.*?#\}", "", _cv, flags=re.S) for k in ("이전 발주서", "is_final", "확인했음", "금액 다름", "z143-ack")))

# 8 화면 스크립트 문법(node · 작은따옴표 글 안 줄바꿈 같은 실수 — z141 사고 재발 막기)
node = None
for cand in ("node", r"C:\Program Files\nodejs\node.exe"):
    try:
        subprocess.run([cand, "--version"], capture_output=True, check=True); node = cand; break
    except Exception:
        pass
if node:
    bad = []
    for rel in (("sales_quotations.html",), ("project_detail.html",), ("sales_order_detail.html",), ("customer_po_view.html",),
                ("_v5_partials", "po_rows.html"), ("_v5_partials", "po_script.html"), ("_v5_partials", "spa_nav.html")):
        s = T(*rel)
        for k, m in enumerate(re.finditer(r"<script(?![^>]*src)[^>]*>(.*?)</script>", s, re.S)):
            b = re.sub(r"\{%.*?%\}", "", m.group(1), flags=re.S); b = re.sub(r"\{\{.*?\}\}", "0", b, flags=re.S); b = re.sub(r"\{#.*?#\}", "", b, flags=re.S)
            fd, fp = tempfile.mkstemp(suffix=".js"); os.write(fd, b.encode("utf-8")); os.close(fd)
            r = subprocess.run([node, "--check", fp], capture_output=True, text=True, encoding="utf-8")
            os.remove(fp)
            if r.returncode:
                bad.append("/".join(rel) + "#%d " % k + r.stderr.strip().split("\n")[0][-120:])
    check("바꾼 화면 스크립트 문법 모두 통과(node)", not bad, bad)
else:
    print("… node 가 없어 스크립트 문법 검사는 건너뜀")
print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
