# -*- coding: utf-8 -*-
"""z1191z63·z64 시험(z61 바탕) — z64: 빼기 = 바로 지움 · 되돌리기·30일 보관 없음 · 「등록된 견적서가 없습니다.」 (대표 2026-11-18 「이화면에서 견적서 등록을 할수있게 … 견적서에 기록되어있는 기본적인 정보들이 자동으로 작성」)
  대표 결정: 품명→장비명 · 모델명은 MODEL 칸 있을 때만 · 파일은 프로젝트에 첨부로 보관 · AI 로 읽기
  ① 값 정리(숫자 쪼개짐·통화·날짜·호칭) · 경고(받은 견적서 · 수량×단가≠합계)
  ② /api/project-quote/read — 저장 위치·표·고객사 맞추기(하나/여럿/없음)·권한·금액 권한·확장자·크기·AI 없음
  ③ [등록] 하면 그 프로젝트에 붙음 · 남의 것은 안 붙음 · 변경 이력 · 상세에 📄 링크(금액 권한자만) · 파일 열기 권한
  ④ 3일 지난 미등록 파일 정리 · 다시 열었을 때 상태 · 등록 화면에 띠(수정 화면엔 없음)
  임시 DB · TestClient · AI 는 가짜(실제 호출 없음) · 운영 아님
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z63-test-only-not-a-real-key"
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z63_")
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
# z1191z76 (대표 11-19 「견적서 등록은 무조건 엑셀파일만」): 운영은 이제 엑셀만 받는다. 이 시험은 읽기·보관·빼기를 보려고
#   예전 파일 종류(PDF·사진)를 그대로 쓴다 — 엑셀만 규칙은 test_project_quote_excel_only_z1191z76_20261119.py 에서 본다.
M._Z76_XL_EXTS = M._qr61.EXTS
M._z76_is_excel = lambda name, raw: True
M._Z76_XL_MSG = "PDF·엑셀(xlsx·xls)·사진(png·jpg) 파일만 올릴 수 있습니다."
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



# ─────────────── z1191z63 ───────────────
#  대표 11-18: 「견적빼기는 견적 등록하는 화면에는 무조건 넣어줘」 · 「빼기는 올린사람 또는 관리자 기술영업팀 인원(등록,빼기할때 항상 누가 했는지 이력 남길것)」
with D.db_session() as c:
    TS = ins(c, "teams", {"name": "기술영업팀", "code": "01", "entity": "KOR", "display_order": 0})
    for nm, emp, role, team in (("마기술", "T971", "member", TS), ("바관리", "T972", "admin", TEAM)):
        c.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics, rank, team_id) "
                  "VALUES (?, ?, ?, ?, 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1, '프로', ?)", (nm, role, emp, emp, team))
    UT = dict(c.execute("SELECT * FROM users WHERE employee_no='T971'").fetchone())
    UADM = dict(c.execute("SELECT * FROM users WHERE employee_no='T972'").fetchone())


def hist(pid):
    with D.db_session() as c:
        return [dict(x) for x in c.execute("SELECT changed_by, old_value, new_value, note FROM project_history WHERE project_id=? AND field='견적서 파일' ORDER BY id", (pid,)).fetchall()]


def attach(pid, name):
    q(cl.post, "/api/project-quote/attach/%d" % pid, files={"file": (name, b"%PDF-1.4 x", "application/pdf")})
    with D.db_session() as c:
        return c.execute("SELECT id FROM project_quote_files WHERE project_id=? AND orig_name=? ORDER BY id DESC", (pid, name)).fetchone()[0]


def rm(fid):
    r = q(cl.post, "/api/project-quote/remove/%d" % fid); return r.status_code, r.json()


def back(fid):
    r = q(cl.post, "/api/project-quote/restore/%d" % fid); return r.status_code, r.json()


print("§1 올리기 이력 = 누가")
as_(UA)
tok = upload(name="가영업이 올린 견적서.png").json()["tok"]
P, _ = reg(model="TP-63", quote_tok=tok)
F1 = row(tok)["id"]
h = hist(P)
check(len(h) == 1 and h[0]["changed_by"] == UA["id"] and "가영업" in h[0]["note"], "등록 화면에서 올림 → 이력에 올린 사람(번호·이름)", h)
as_(UD)
# z1191z160 (대표 11-26 「여러 개 등록될 수 있게」): 남이 올린 견적서가 있어도 더 올림 — 남의 것은 지우지 않으므로 막지 않음
r105 = q(cl.post, "/api/project-quote/attach/%d" % P, files={"file": ("라영업이 더 올린 견적서.pdf", b"%PDF-1.4 x", "application/pdf")})
with D.db_session() as c:
    _n160 = [x[0] for x in c.execute("SELECT orig_name FROM project_quote_files WHERE project_id=? ORDER BY id", (P,)).fetchall()]
check(r105.status_code == 200 and r105.json().get("ok") and _n160 == ["가영업이 올린 견적서.png", "라영업이 더 올린 견적서.pdf"],
      "z1191z160: 라영업도 같은 수주에 더 올림 · 가영업 것은 그대로", (r105.json(), _n160))
_s160, _j160 = rm(r105.json()["fid"])
check(_s160 == 200 and _j160.get("ok"), "잘못 올린 것은 올린 사람이 「빼기」(그대로 됨)", _j160)
as_(UA)
P2, _ = reg(model="TP-63B", quote_tok="")
as_(UD)
F2 = attach(P2, "라영업이 올린 견적서.pdf")
h = hist(P2)
check(h[-1]["changed_by"] == UD["id"] and "라영업" in h[-1]["note"] and "상세 화면" in h[-1]["note"], "상세에서 올림 → 이력에 올린 사람", h[-1])

print("§2 누가 뺄 수 있나 — 올린 사람 · 관리자 · 기술영업팀")
as_(UD)
hd = q(cl.get, "/project/%d" % P2).text
check(hd.count('class="z63-rm"') == 1 and 'data-fid="%d" data-name="라영업이 올린 견적서.pdf"' % F2 in hd
      and 'class="z63-rm"' not in q(cl.get, "/project/%d" % P).text, "라영업(올린 사람 아님·일반)은 자기가 올린 것에만 🗑", hd.count('class="z63-rm"'))
s_, j = rm(F1)
check(s_ == 403 and "올린 사람과 기술영업팀만" in j["message"], "라영업이 가영업 것을 빼려 하면 403 「올린 사람과 기술영업팀만」", j)
as_(UT)
check(q(cl.get, "/project/%d" % P).text.count('class="z63-rm"') + q(cl.get, "/project/%d" % P2).text.count('class="z63-rm"') == 2, "기술영업팀(마기술)은 모두 🗑")
as_(UADM)
check(q(cl.get, "/project/%d" % P).text.count('class="z63-rm"') + q(cl.get, "/project/%d" % P2).text.count('class="z63-rm"') == 0 and rm(F1)[0] == 403,
      "관리자(바관리)는 남의 것 못 뺌(대표 「관리자는 빼자」) · 403")
as_(UC)
check(rm(F1)[0] == 403 and 'class="z63-rm"' not in q(cl.get, "/project/%d" % P).text, "금액 권한 없는 다물류 → 단추 없음 · 403")

print("§3 빼기 → 파일·줄 바로 지움 · 이력(누가) · 되돌리기 없음(z64)")
as_(UT)
with D.db_session() as c:
    st1 = c.execute("SELECT stored FROM project_quote_files WHERE id=?", (F1,)).fetchone()[0]
fp1 = os.path.join(TMP, "project_quotes", st1)
s_, j = rm(F1)
with D.db_session() as c:
    n1 = c.execute("SELECT COUNT(*) FROM project_quote_files WHERE id=?", (F1,)).fetchone()[0]
check(s_ == 200 and j["ok"] and n1 == 0 and not os.path.exists(fp1), "기술영업팀이 뺌 → 줄·파일 바로 지움(30일 보관 없음)", (s_, n1, os.path.exists(fp1)))
h = hist(P)
check(h[-1]["changed_by"] == UT["id"] and h[-1]["old_value"] == "가영업이 올린 견적서.png" and h[-1]["new_value"] == "" and "빼기 · 마기술" in h[-1]["note"],
      "이력: 「견적서 파일: 가영업이 올린 … → (빈칸)」 · 「빼기 · 마기술」", h[-1])
as_(UA)
hd = q(cl.get, "/project/%d" % P).text
check("가영업이 올린 견적서.png</a>" not in hd and "라영업이 올린 견적서.pdf</a>" in q(cl.get, "/project/%d" % P2).text, "상세 목록에서 사라짐(다른 견적서는 그대로)")
check(q(cl.get, "/projects/%d/quote-files/%d" % (P, F1)).status_code == 404, "뺀 파일 주소는 404")
s_, j = rm(F1)
check(s_ == 404 and len(hist(P)) == len(h), "두 번 빼면 「이미 뺐을 수 있습니다」 · 이력 늘지 않음", j)
check(q(cl.post, "/api/project-quote/restore/%d" % F2).status_code in (404, 405) and "z63-undo" not in hd and "되돌리기" not in hd, "되돌리기 없음(주소·단추 모두)")
F3 = attach(P, "가영업 두번째 견적서.pdf")

print("§4 견적 올리는 화면마다 빼기")
as_(UA)
hq = q(cl.get, "/projects/%d/quick-edit" % P).text
he = q(cl.get, "/projects/%d/edit" % P).text
check('class="z63-have"' in hq and hq.count('class="z63-rm"') == 1 and "이 프로젝트에 붙은 견적서" in hq, "간편 수정: 「이 프로젝트에 붙은 견적서」 + 🗑(가영업은 자기 것 하나)")
check('class="z63-have"' in he and he.count('class="z63-rm"') == 1, "고급 편집: 같은 목록 + 🗑")
i_f = he.find('<form method="post" action="/projects/%d/edit"' % P); i_h = he.find('class="z63-have"'); i_fe = he.find("</form>", i_f)
check(i_f < i_h < i_fe and 'type="button" class="z63-rm"' in he, "목록은 양식 안 · 🗑 은 type=button(누르면 저장되지 않음)")
as_(UT)
check(q(cl.get, "/projects/%d/quick-edit" % P).text.count('class="z63-rm"') == 1, "기술영업팀이 열면 수정 화면에도 🗑(1장 · z1191z105)")
as_(UA)
hn = q(cl.get, "/projects/quick?biz_div=T").text
check('class="z63-have"' not in hn and 'id="z61qX"' in hn, "새 등록 화면: 붙은 견적서 목록 없음 · 올린 견적서는 「빼기」(z61)")
check(hq.count("window.__z63rows=1") == 1 and q(cl.get, "/project/%d" % P).text.count("window.__z63rows=1") == 1, "빼기·보기 스크립트는 화면에 한 벌")

print("§5 z63 때 숨겨 둔 견적서 → 목록 볼 때 바로 지움 · 「등록된 견적서가 없습니다.」")
with D.db_session() as c:
    st2 = c.execute("SELECT stored FROM project_quote_files WHERE id=?", (F2,)).fetchone()[0]
    c.execute("UPDATE project_quote_files SET removed_at='2026-11-18 22:27', removed_by=? WHERE id=?", (UD["id"], F2))   # 예전 방식(숨김)
as_(UA)
hd2 = q(cl.get, "/project/%d" % P2).text
hd = q(cl.get, "/project/%d" % P).text
with D.db_session() as c:
    gone = c.execute("SELECT COUNT(*) FROM project_quote_files WHERE id=?", (F2,)).fetchone()[0] == 0
check(gone and not os.path.exists(os.path.join(TMP, "project_quotes", st2)) and "라영업이 올린 견적서.pdf</a>" not in hd2, "숨겨 둔 것은 상세를 열 때 파일·줄 지움(대표 PP1-1.png 같은 경우)")
none_hidden = re.search(r'<div class="z63-none" style="[^"]*display:none;[^"]*">등록된 견적서가 없습니다.</div>', hd)
check(none_hidden and "가영업 두번째 견적서.pdf</a>" in hd, "견적서가 남아 있으면 「등록된 견적서가 없습니다.」는 숨김")
as_(UT)
rm(F3)
hd = q(cl.get, "/project/%d" % P).text
check(re.search(r'<div class="z63-none" style="margin-top:6px;font-size:12px;color:#64748b;">등록된 견적서가 없습니다.</div>', hd) and 'class="z62-qrow"' not in hd,
      "다 빼면 「등록된 견적서가 없습니다.」")
as_(UA)
P0, _ = reg(model="TP-64", quote_tok="")
h0 = q(cl.get, "/project/%d" % P0).text; e0 = q(cl.get, "/projects/%d/quick-edit" % P0).text
check("등록된 견적서가 없습니다." in h0 and 'class="z63-have"' in e0 and "등록된 견적서가 없습니다." in e0,
      "처음부터 없을 때도 상세·수정 화면에 「등록된 견적서가 없습니다.」")
check(any("빼기 · 마기술" in x["note"] for x in hist(P)), "지워도 이력(누가 뺐는지)은 남음")

print()
print("결과: ✅ %d · ❌ %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
