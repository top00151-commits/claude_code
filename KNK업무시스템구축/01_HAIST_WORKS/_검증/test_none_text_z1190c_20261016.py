# -*- coding: utf-8 -*-
"""z1190c 시험 — 빈 칸이 글자 「None」 으로 저장·표시되던 것 (z1190 배포 전 확인에서 발견 · 2026-10-16)
  원인: Jinja |default('') 는 DB NULL(None)을 바꾸지 않는다 → 수정 화면 입력 칸에 글자 None → 손대지 않고 저장해도 그대로 남음
        (운영 읽기만: 프로젝트 9개 — 2차 발주처 6 · 담당자 칸 4~9 · 2차가 글자 None 이면 2단 발주로도 판정)
  §1 서버(임시 DB · TestClient)
     수정 화면(정식·빠른) 입력 칸에 value="None" 없음 · 화면 그대로 다시 저장해도 NULL 그대로 · 2단 아님 ·
     옛 화면이 글자 None 을 보내도 서버가 빈칸으로 · 진짜 값은 그대로 · 상세 화면 제안서·견적서·최종 고객 빈 값 = 「—」
  §2 바뀐 곳 원문
"""
import contextlib
import io
import os
import re
import sys
import tempfile
from html.parser import HTMLParser

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1190c-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1190c_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"),
                     ("name_en", "TEXT"), ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"),
                     ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version) "
                 "VALUES ('가상관리자', 'admin', 'T901', 'T901', 'sso_only_no_local_password', 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T901'").fetchone())
    ccols = {r[1] for r in conn.execute("PRAGMA table_info(customers)")}
    for col in ("alias", "country"):
        if col not in ccols:
            conn.execute("ALTER TABLE customers ADD COLUMN %s TEXT" % col)
    conn.execute("INSERT INTO customers (name, alias, country) VALUES ('(주) 가상드림동탄', '가상드림(동탄)', '')")
    CID = conn.execute("SELECT id FROM customers WHERE alias='가상드림(동탄)'").fetchone()[0]

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0
TXT = ("secondary_customer", "cc_name", "cc_dept", "cc_position", "cc_phone", "cc_email", "cc_note")


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


class FormGrab(HTMLParser):
    """action 이 want 로 끝나는 <form> 안의 칸을 브라우저가 보내는 대로 모은다(체크 안 된 상자·disabled·버튼 제외)."""

    def __init__(self, want):
        super().__init__(convert_charrefs=True)
        self.want, self.inform, self.fields, self._sel, self._ta = want, False, [], None, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.inform = (a.get("action") or "").endswith(self.want)
            return
        if not self.inform or "disabled" in a:
            return
        if tag == "input":
            n, t = a.get("name"), (a.get("type") or "text").lower()
            if not n or t in ("submit", "button", "file", "image", "reset"):
                return
            if t in ("checkbox", "radio") and "checked" not in a:
                return
            self.fields.append((n, a.get("value") if a.get("value") is not None else ("on" if t in ("checkbox", "radio") else "")))
        elif tag == "select":
            self._sel = [a.get("name"), None, None]
        elif tag == "option" and self._sel is not None:
            v = a.get("value") or ""
            if self._sel[2] is None:
                self._sel[2] = v
            if "selected" in a:
                self._sel[1] = v
        elif tag == "textarea":
            self._ta = [a.get("name"), ""]

    def handle_endtag(self, tag):
        if tag == "form":
            self.inform = False
        elif tag == "select" and self._sel is not None:
            if self._sel[0]:
                self.fields.append((self._sel[0], self._sel[1] if self._sel[1] is not None else (self._sel[2] or "")))
            self._sel = None
        elif tag == "textarea" and self._ta is not None:
            if self._ta[0]:
                self.fields.append((self._ta[0], self._ta[1]))
            self._ta = None

    def handle_data(self, data):
        if self._ta is not None:
            self._ta[1] += data


def grab(html, want):
    g = FormGrab(want)
    g.feed(html)
    out = {}
    for k, v in g.fields:
        out.setdefault(k, []).append(v)
    return out


def proj(pid):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone())


def resubmit(page, pid, override=None):
    """수정 화면을 열어 그 칸 그대로(+override) 다시 저장 — 사람이 손대지 않고 「저장」 누른 것과 같다."""
    r = cl.get(page)
    f = grab(r.text, "/projects/%d/edit" % pid)
    f["unlock_verified"] = ["1"]   # 잠금 해제 확인창 통과(화면 스크립트가 채우는 값)
    p0 = proj(pid)   # 고객사 칸은 「고객 고르기」 스크립트(KNKCust)가 숨은 칸 customer_name·customer_id 를 만들어 채운다
    f.setdefault("customer_name", [p0.get("customer_name") or ""])
    f.setdefault("customer_id", [str(p0.get("customer_id") or "")])
    for k, v in (override or {}).items():
        f[k] = [v]
    with contextlib.redirect_stdout(io.StringIO()):
        rr = cl.post("/projects/%d/edit" % pid, data={k: (v if len(v) > 1 else v[0]) for k, v in f.items()})
    return r.status_code, len(f), rr.status_code, rr.headers.get("location", "")


print("=" * 78)
print("§1 서버")
print("=" * 78)
BASE = {"quick": "1", "biz_div": "T", "project_type": "NEW_EQUIP", "status": "진행중", "confirm_now": "1",
        "order_date": "2026-10-02", "due_date": "2026-10-20", "equip_name": "기능검사기", "model": "PBA",
        "unit_qty": "1", "shipment_form": "ASSEMBLY", "currency": "KRW", "is_export": "0", "po_type": "신규",
        "customer_name": "가상드림(동탄)", "customer_id": str(CID), "unit_price": "1000", "order_amount": "1000",
        "unit_amount[]": ["1000"]}
for nm in ("z1190c-A", "z1190c-B"):
    with contextlib.redirect_stdout(io.StringIO()):
        cl.post("/projects/new", data=dict(BASE, name=nm))
with D.db_session() as c:
    PA = dict(c.execute("SELECT * FROM projects WHERE name='z1190c-A'").fetchone())
    PB = dict(c.execute("SELECT * FROM projects WHERE name='z1190c-B'").fetchone())
check("0 준비: 2차·담당자 칸이 빈(NULL) 프로젝트 둘", all(PA.get(k) is None for k in TXT) and all(PB.get(k) is None for k in TXT),
      {k: PA.get(k) for k in TXT})

r = cl.get("/projects/%d/edit" % PA["id"])
check("1 정식 수정 화면: 입력 칸에 value=\"None\" 없음", r.status_code == 200 and r.text.count('value="None"') == 0,
      (r.status_code, r.text.count('value="None"')))
r = cl.get("/projects/%d/quick-edit" % PA["id"])
check("2 빠른 수정 화면: 입력 칸에 value=\"None\" 없음", r.status_code == 200 and r.text.count('value="None"') == 0,
      (r.status_code, r.text.count('value="None"')))

st = resubmit("/projects/%d/edit" % PA["id"], PA["id"])
a = proj(PA["id"])
check("3 정식 수정 화면을 손대지 않고 저장 → 저장됨 · 2차·담당자 칸 NULL 그대로 · 2단 아님",
      st[0] == 200 and st[2] == 303 and "error" not in st[3] and all(a.get(k) is None for k in TXT) and not a.get("two_tier_order"),
      (st, {k: a.get(k) for k in TXT}, a.get("two_tier_order")))
st = resubmit("/projects/%d/quick-edit" % PB["id"], PB["id"])
b = proj(PB["id"])
check("4 빠른 수정 화면을 손대지 않고 저장 → 저장됨 · NULL 그대로 · 2단 아님",
      st[0] == 200 and st[2] == 303 and "error" not in st[3] and all(b.get(k) is None for k in TXT) and not b.get("two_tier_order"),
      (st, {k: b.get(k) for k in TXT}, b.get("two_tier_order")))

st = resubmit("/projects/%d/edit" % PA["id"], PA["id"], {k: "None" for k in TXT})
a = proj(PA["id"])
check("5 옛 화면이 글자 None 을 보내도 → 서버가 빈칸(NULL) · 2단 아님",
      st[2] == 303 and "error" not in st[3] and all(a.get(k) is None for k in TXT) and not a.get("two_tier_order"),
      (st, {k: a.get(k) for k in TXT}, a.get("two_tier_order")))
REAL = {"secondary_customer": "가상최종B", "cc_name": "가상담당", "cc_dept": "구매", "cc_position": "과장",
        "cc_phone": "010-0000-0000", "cc_email": "test@example.invalid", "cc_note": "메모"}
st = resubmit("/projects/%d/edit" % PA["id"], PA["id"], REAL)
a = proj(PA["id"])
check("6 진짜 값은 그대로 저장 · 2차가 있으면 2단",
      st[2] == 303 and "error" not in st[3] and all(a.get(k) == v for k, v in REAL.items()) and a.get("two_tier_order") == 1,
      (st, {k: a.get(k) for k in TXT}, a.get("two_tier_order")))
st = resubmit("/projects/%d/edit" % PA["id"], PA["id"], {"secondary_customer": ""})
a = proj(PA["id"])
check("7 2차를 지우면 NULL(담당자 칸은 그대로)", st[2] == 303 and "error" not in st[3] and a.get("secondary_customer") is None and a.get("cc_name") == "가상담당",
      (st, a.get("secondary_customer"), a.get("cc_name")))

f1190c = getattr(D, "_form_txt1190c", None)
check("8 정리 함수: None·'None'·' None ' → 빈칸 · 'none'·진짜 값은 그대로",
      f1190c is not None and [f1190c(x) for x in (None, "None", " None ", "none", "가상")] == ["", "", "", "none", "가상"],
      [f1190c(x) for x in (None, "None", " None ", "none", "가상")] if f1190c else None)

with D.db_session() as c:   # 운영 6개처럼 2단 표시 켜짐 + 2차 빈 프로젝트(정리 뒤 모습) · 제안서·견적서는 원래 빈 값
    c.execute("UPDATE projects SET two_tier_order=1, secondary_customer=NULL WHERE id=?", (PB["id"],))
r = cl.get("/project/%d" % PB["id"])
h = r.text
check("9 상세 화면: 제안서·견적서 빈 값 = 「—」(전엔 None)",
      r.status_code == 200 and "<dt>제안서</dt><dd>—</dd>" in h and "<dt>견적서</dt><dd>—</dd>" in h,
      (r.status_code, re.findall(r"<dt>(?:제안서|견적서)</dt><dd>[^<]*</dd>", h)))
check("10 상세 화면: 최종 고객(2차) 빈 값 = 「🌐 —」 · 어디에도 <dd>None</dd>·🌐 None 없음",
      "🌐 —</dd>" in h and "<dd>None</dd>" not in h and "🌐 None" not in h,
      (re.findall(r"최종 고객.{0,120}", h)[:1], h.count("<dd>None</dd>")))

print()
print("=" * 78)
print("§2 바뀐 곳 원문")
print("=" * 78)
T = os.path.join(ROOT, "app", "templates")
dbs = open(os.path.join(ROOT, "app", "database.py"), encoding="utf-8").read()
pf = open(os.path.join(T, "project_form.html"), encoding="utf-8").read()
qf = open(os.path.join(T, "project_quick_form.html"), encoding="utf-8").read()
pd = open(os.path.join(T, "project_detail.html"), encoding="utf-8").read()
check("서버: 정리 함수 한 곳 · 담당자 6 + 2차 2(값 · 2단 판정)",
      dbs.count("def _form_txt1190c(v)") == 1 and dbs.count("_form_txt1190c(data.get(") == 8)
simple = re.compile(r"\{\{ project\.[a-z_0-9]+\|default\(''\)( if ed else '')? \}\}")
check("수정 화면 두 곳: project.X|default('') 남은 곳 0", not simple.search(pf) and not simple.search(qf),
      (simple.findall(pf)[:3], simple.findall(qf)[:3]))
check("상세 화면: 제안서·견적서·최종 고객 = or '—'",
      "{{ p.proposal_date or '—' }}" in pd and "{{ p.quotation_date or '—' }}" in pd and "🌐 {{ p.secondary_customer or '—' }}" in pd)

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
