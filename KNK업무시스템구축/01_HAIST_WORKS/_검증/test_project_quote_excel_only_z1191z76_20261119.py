# -*- coding: utf-8 -*-
"""z1191z76 시험 (대표 2026-11-19 「이 견적서 등록은 무조건 엑셀파일만 업로드 될수있도록해.. 이유는 최종 견적서를 등록을해야
  향후에 수정할때 최종을 수정할수있어.. 꼭 엑셀파일만 등록할수있게해주고 등록한 엑셀파일은 다운로드 할수있게도 해줘야해.」)
  임시 DB · TestClient · 운영 아님 · AI 는 흉내
"""
import contextlib, io, json, os, re, sys, tempfile
from datetime import date, timedelta, datetime, timezone
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z76-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z76_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()


def ins(c, table, row):
    cols = {r[1] for r in c.execute("PRAGMA table_info(%s)" % table)}
    ks = [k for k in row if k in cols]
    c.execute("INSERT INTO %s (%s) VALUES (%s)" % (table, ",".join('"%s"' % k for k in ks), ",".join("?" * len(ks))), [row[k] for k in ks])
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


FUT = (date.today() + timedelta(days=20)).isoformat()
with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0"), ("biz_divs", "TEXT"), ("rank", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    for col in ("alias", "sub_biz_no"):
        if col not in {r[1] for r in c.execute("PRAGMA table_info(customers)")}:
            c.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    TEAM = ins(c, "teams", {"name": "가상검사기팀", "code": "T61", "entity": "KOR", "display_order": 1})
    for nm, emp, vs, us in (("가영업", "T961", 1, 1), ("나등록", "T962", 0, 1), ("다물류", "T963", 0, 0), ("라영업", "T964", 1, 1)):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics, rank, team_id) "
                  "VALUES (?, 'member', ?, ?, 'sso_only_no_local_password', 1, 1, ?, ?, 1, 1, '프로', ?)", (nm, emp, emp, vs, us, TEAM))
    UA = dict(c.execute("SELECT * FROM users WHERE employee_no='T961'").fetchone())
    UB = dict(c.execute("SELECT * FROM users WHERE employee_no='T962'").fetchone())
    UC = dict(c.execute("SELECT * FROM users WHERE employee_no='T963'").fetchone())
    UD = dict(c.execute("SELECT * FROM users WHERE employee_no='T964'").fetchone())
    CU = ins(c, "customers", {"name": "가상전자(주)", "alias": "가상전자"})
    CM1 = ins(c, "customers", {"name": "삼가상기 수원", "sub_biz_no": "0001"})
    CM2 = ins(c, "customers", {"name": "삼가상기 부산", "sub_biz_no": "0002"})

import app.main as M  # noqa: E402
import app.ai_client as AI  # noqa: E402
import app.quote_reader as QR  # noqa: E402
import app.sso_client as SSO  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
CUR = {"u": UA}
M.get_user = lambda request: CUR["u"]
with contextlib.redirect_stdout(io.StringIO()):
    try:
        M.startup()
    except Exception as _e:
        print("startup:", _e)
SSO.notify_via_messenger = lambda *a, **k: {"ok": True, "sent": 0}   # 이음 보내기 막기(시험)
CALLS = []
AIRESP = {"v": None, "avail": True}
AI.ai_available = lambda: AIRESP["avail"]
AI.ai_vision = lambda img, mime, prompt, **k: (CALLS.append(("vision", len(img), prompt)) or (True, AIRESP["v"]))
AI.ai_chat = lambda prompt, **k: (CALLS.append(("chat", 0, prompt)) or (True, AIRESP["v"]))
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg, got=None):
    global OK, FAIL
    if cond:
        OK += 1; print("  ✅", msg)
    else:
        FAIL += 1; print("  ❌", msg, "" if got is None else ("  ← %r" % (got,)))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def as_(u):
    CUR["u"] = u


def png_bytes():
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (60, 40), (255, 255, 255)).save(b, format="PNG"); return b.getvalue()


PNG = png_bytes()
TOUCH = {"supplier": "주식회사 케이엔케이", "customer": "가상전자", "customer_dept": "", "contact_name": "차주송 님", "contact_title": "팀장",
         "supplier_pic": "", "item_name": "TOUCH 타공검사기", "model_code": "", "qty": 1, "unit": "SET", "currency": "₩",
         "unit_price": "11,300,000", "amount": 11300000, "quote_date": "2026. 11. 13.", "quote_no": "",
         "delivery_terms": "발주서 접수 후 4주 소요", "valid_terms": "발행일로부터 1개월", "payment_terms": "납품일로 부터 30일 이내"}


def upload(name="TOUCH 센서검사기 견적서_261113.png", raw=PNG, resp=TOUCH):
    AIRESP["v"] = json.dumps(resp, ensure_ascii=False) if isinstance(resp, dict) else resp
    return q(cl.post, "/api/project-quote/read", files={"file": (name, raw, "application/octet-stream")})


def row(tok):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM project_quote_files WHERE tok=?", (tok,)).fetchone()
        return dict(r) if r else None



# ─────────────── z1191z62 ───────────────
#  대표 11-18: ① 「수정화면에서는 견적서 등록하는곳이 없는데」 → 수정 두 곳(금액·수량은 참고) · [저장] 때 보관 · 상세 「＋ 견적서 올리기」
#             ② 「암호가 걸려있는 엑셀을 넣으면 업로드 화면에서 비밀번호를 입력하고 등록」
import types  # noqa: E402
PW_OK = "Kz-9!암호"


def xlsx_bytes(rows):
    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active
    for r in rows:
        ws.append(r)
    b = io.BytesIO(); wb.save(b); return b.getvalue()


PLAIN = xlsx_bytes([["견 적 서"], ["업 체 명", "가상전자"], ["품 명", "가상 패널 검사기"], ["수량", 1, "단가", 5000000]])
LOCKED = QR._OLE + b"FAKE-ENCRYPTED-PAYLOAD" * 20   # 암호 걸린 xlsx = OLE 통(가짜 내용)


class FakeOffice:   # msoffcrypto 대역 — 맞는 비밀번호면 PLAIN 을 내놓는다
    def __init__(self, fh):
        self.raw = fh.read(); self.pw = None

    def is_encrypted(self):
        return self.raw[:8] == QR._OLE

    def load_key(self, password=None):
        self.pw = password

    def decrypt(self, out):
        if self.pw != PW_OK:
            raise ValueError("bad key")
        out.write(PLAIN)


FAKE = types.ModuleType("msoffcrypto"); FAKE.OfficeFile = FakeOffice
sys.modules["msoffcrypto"] = FAKE
XL_RESP = dict(TOUCH, customer="가상전자", item_name="가상 패널 검사기", contact_name="", contact_title="", unit_price=5000000, amount=5000000)

TOK1 = ""
REG = {"quick": "1", "customer_name": "가상전자(주)", "customer_id": str(CU), "biz_div": "T", "project_type": "NEW_EQUIP", "po_type": "신규",
       "status": "진행중", "confirm_now": "1", "order_date": "2026-11-18", "due_date": FUT, "currency": "KRW", "unit_qty": "1", "unit_price": "11,300,000",
       "name": "TSP", "model": "", "equip_name": "TOUCH 타공검사기", "quotation_date": "2026-11-13", "quote_tok": TOK1}


def reg(**kw):
    f = dict(REG); f.update(kw)
    f.setdefault("model", "TP-1")
    r = q(cl.post, "/projects/new", data=f)
    loc = r.headers.get("location", "")
    m = re.search(r"/project/(\d+)", loc)
    return (int(m.group(1)) if m else None), loc




def nrows():
    with D.db_session() as c:
        M._z61_table(c)
        return c.execute("SELECT COUNT(*) FROM project_quote_files").fetchone()[0]


print("§1 등록·수정 「견적서로 채우기」 = 엑셀만(서버)")
as_(UA)
n0 = nrows(); CALLS.clear()
for nm, raw, why in (("견적서.png", PNG, "사진"), ("견적서.pdf", b"%PDF-1.4 x", "PDF"), ("견적서.jpg", PNG, "사진(jpg)"), ("견적서.docx", b"PK\x03\x04abc", "워드")):
    j = upload(name=nm, raw=raw).json()
    check(not j["ok"] and "엑셀 파일(xlsx·xls)만" in j["message"] and "최종 견적서" in j["message"], "%s(%s) → 「엑셀 파일(xlsx·xls)만 · 최종 견적서를 고칠 수 있게」" % (why, nm), j.get("message"))
check(nrows() == n0 and not CALLS, "거절한 파일은 저장도 · AI 읽기도 안 함", (nrows(), n0, len(CALLS)))
j = upload(name="이름만엑셀.xlsx", raw=PNG).json()
check(not j["ok"] and "엑셀 파일이 아닙니다" in j["message"] and nrows() == n0, "이름만 .xlsx 인 사진 → 「엑셀 파일이 아닙니다」", j.get("message"))
j = upload(name="가상 견적서 최종.xlsx", raw=PLAIN, resp=XL_RESP).json()
check(j["ok"] and j["read_ok"] and j["fields"]["item_name"] == "가상 패널 검사기" and nrows() == n0 + 1, "진짜 엑셀(xlsx) → 읽고 보관 대기", j.get("message"))
TOKX = j["tok"]
jl = upload(name="암호 견적서.xlsx", raw=LOCKED, resp=XL_RESP).json()
check(jl["ok"] and jl["need_password"], "암호 걸린 엑셀(통 모양 D0 CF 11 E0) → 받고 비밀번호 칸", jl.get("message"))
jx = upload(name="옛 엑셀.xls", raw=QR._OLE + b"x" * 64, resp=XL_RESP).json()
jm = upload(name="매크로.xlsm", raw=PLAIN, resp=XL_RESP).json()
check(jx["ok"] and jm["ok"], "옛 엑셀(xls) · 매크로 엑셀(xlsm)도 받음", (jx.get("message"), jm.get("message")))

print("§2 화면 — 고르는 창도 엑셀만 · 안내 글")
hq = q(cl.get, "/projects/quick").text
inp = re.search(r'<input type="file" id="z61qFile" accept="([^"]+)"', hq)
check(inp and inp.group(1).startswith(".xlsx,.xlsm,.xls,") and ".pdf" not in inp.group(1) and ".png" not in inp.group(1), "등록 화면 파일 고르기 창 = 엑셀만(.pdf·.png 없음)", inp and inp.group(1))
check("엑셀 파일(xlsx·xls)만</b> 올릴 수 있습니다(나중에 고칠 때 최종 견적서를 그대로 고칠 수 있게)" in hq and "📎 견적서 엑셀 고르기" in hq and "PDF·엑셀·사진" not in hq,
      "안내: 「엑셀 파일(xlsx·xls)만 … 최종 견적서를 그대로 고칠 수 있게」 · 단추 「📎 견적서 엑셀 고르기」")
check("/\.(xlsx|xlsm|xls)$/i.test(file.name||'')" in hq, "끌어다 놓은 파일도 화면에서 먼저 엑셀인지 봄")

print("§3 등록 → 프로젝트에 엑셀 보관 → 내려받기")
P1, loc = reg(model="TP-76", quote_tok=TOKX)
check(P1 and row(TOKX)["project_id"] == P1, "등록하면 그 엑셀이 프로젝트에 붙음", loc)
hd = q(cl.get, "/project/%d" % P1).text
fid = row(TOKX)["id"]
check('href="/projects/%d/quote-files/%d"' % (P1, fid) in hd and "⬇ 엑셀 내려받기" in hd, "상세 「견적서」 칸에 「⬇ 엑셀 내려받기」")
r = q(cl.get, "/projects/%d/quote-files/%d" % (P1, fid))
cd = r.headers.get("content-disposition", "")
check(r.status_code == 200 and r.content == PLAIN and cd.startswith("attachment;") and "filename*=UTF-8''" in cd
      and "spreadsheetml" in r.headers.get("content-type", ""), "내려받기 = 올린 엑셀 그대로(바이트 같음 · 원래 이름 · 엑셀 형식)", (r.status_code, cd, r.headers.get("content-type")))
check(r.headers.get("cache-control", "").startswith("private"), "남의 컴퓨터 캐시에 안 남김(private)")
dinp = re.search(r'<input type="file" class="z62-up-file" accept="([^"]+)"', hd)
check(dinp and ".pdf" not in dinp.group(1) and "＋ 견적서 엑셀 올리기" in hd, "상세 「＋ 견적서 엑셀 올리기」도 엑셀만", dinp and dinp.group(1))

print("§4 상세에서 더 올리기 = 엑셀만 · 고친 것을 올리면 「최신」")
for nm, raw in (("나중 견적서.pdf", b"%PDF-1.4 x"), ("나중 견적서.png", PNG), ("가짜.xlsx", b"%PDF-1.4 x")):
    rj = q(cl.post, "/api/project-quote/attach/%d" % P1, files={"file": (nm, raw, "application/octet-stream")}).json()
    check(rj["ok"] is False and "엑셀" in rj["message"], "상세 올리기 %s → 거절" % nm, rj)
PLAIN2 = xlsx_bytes([["견 적 서 (수정)"], ["품 명", "가상 패널 검사기"], ["수량", 2, "단가", 4800000]])
rj = q(cl.post, "/api/project-quote/attach/%d" % P1, files={"file": ("가상 견적서 최종_수정1.xlsx", PLAIN2, "application/octet-stream")}).json()
check(rj["ok"], "고친 엑셀 올리기 → 보관", rj)
hd = q(cl.get, "/project/%d" % P1).text
i_new = hd.find("가상 견적서 최종_수정1.xlsx</a>"); i_badge = hd.find(">최신</span>")
check(hd.count(">최신</span>") == 1 and 0 < i_new < i_badge and i_badge - i_new < 400 and hd.find("가상 견적서 최종.xlsx</a>") < i_new,
      "엑셀이 둘 → 나중에 올린 「…_수정1.xlsx」에만 「최신」", (hd.count(">최신</span>"), i_new, i_badge))
fs = M._z61_quote_files(P1)
check([x.get("latest", False) for x in fs] == [False, True], "목록 자료: 마지막 엑셀만 latest", [(x["orig_name"], x.get("latest")) for x in fs])
P2, _ = reg(model="TP-77", quote_tok="")
q(cl.post, "/api/project-quote/attach/%d" % P2, files={"file": ("하나뿐.xlsx", PLAIN, "application/octet-stream")})
check(">최신</span>" not in q(cl.get, "/project/%d" % P2).text, "견적서가 하나뿐이면 「최신」 표시 없음")

print("§5 권한 — 금액 못 보는 사람은 내려받기 못 함")
as_(UC)
r = q(cl.get, "/projects/%d/quote-files/%d" % (P1, fid))
check(r.status_code == 403, "다물류(매출 보기·쓰기 권한 없음) → 403", r.status_code)
as_(UA)

print()
print("결과: PASS %d / FAIL %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
