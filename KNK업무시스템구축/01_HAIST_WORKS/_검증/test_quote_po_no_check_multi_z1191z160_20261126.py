# -*- coding: utf-8 -*-
"""z1191z160 시험 — 견적서·고객 발주서: 내용 검토(금액 비교·경고·「확인했음」) 없앰 · 수주마다 여러 장 모두 같은 자격으로 남고 보임
대표 2026-11-26 원문: 「견적서, 발주서 등록할때 내용을 검토해서 맞는지 안맞는지를 확인하는 기능 … 검토하는 기능을 빼줘. 사용자들이 등록하는걸 믿고
진행할수있게. 또 발주서,견적서가 무조건 하나만 등록되는건 아니야. 여러개가 등록이 될수도있는부분이라 이부분도 제한을 풀어줘.」
  §1 한 수주에 견적서 2장(상세 올리기 1 + 견적 관리 붙이기 1) — 둘 다 남음(디스크 파일도) · 올린 답에 금액 비교 알림 없음
  §2 한 수주에 고객 발주서 2장(상세 올리기 1 + 견적 관리 붙이기 1) — 둘 다 남음 · 최종·이전 구분 없음
  §3 보이는 곳 모두에 두 장씩: 상세(견적서 줄·수주 카드·수주별 표) · 견적 관리 · 칩(프로젝트 목록 📎) · 수주 상세 · 발주서 보기 · zip · 엑셀
  §4 화면에 「금액 다름」「확인했음」「이전 발주서」「예전 파일은 지워」「최종」(발주서) 없음 · 「확인했음」 주소 없음
  §5 견적서 없는 수주 = 앞 수주 견적서를 따라가지 않고 「없음」
  §6 「견적서로 채우기」 경고 없음 · 후보 찾기 금액 같음/다름 없음 · 수주 칸 확인에서 이미 있는 수주에도 붙음
  §7 그대로인 것: 빼기 · 수주 2개 이상인데 안 고르면 멈춤 · 단계 줄(1 수주번호 고르기 → 2 올리기 → 3 다시 올리기(점선) → 4 끝) · 화면 스크립트 문법(node)
  임시 DB · TestClient · 운영 아님"""
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import zipfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z160-test-only-not-a-real-key"   # 시험용 가짜 값
import app.database as D  # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z160_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("name_en", "TEXT"),
                     ("name_vi", "TEXT"), ("phone", "TEXT"), ("dept_code", "TEXT"), ("must_change_pw", "INTEGER DEFAULT 0")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
    if not conn.execute("SELECT 1 FROM teams WHERE id=1").fetchone():
        if "code" in tcols:
            conn.execute("INSERT INTO teams (id, code, name) VALUES (1, '01', '기술영업팀')")
        else:
            conn.execute("INSERT INTO teams (id, name) VALUES (1, '기술영업팀')")
    else:
        conn.execute("UPDATE teams SET name='기술영업팀' WHERE id=1")
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, can_view_sales, can_use_sales, "
                 "can_view_logistics, can_use_logistics) VALUES ('가상영업', 'admin', 'Z160', 'Z160', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='Z160'").fetchone())
    conn.execute("INSERT OR IGNORE INTO field_access_policy (category, team_id) VALUES ('sales_amount', 1)")
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객을')")
    CU = conn.execute("SELECT id FROM customers WHERE name='가상고객을'").fetchone()[0]
    from datetime import date as _d
    T0 = _d.today().isoformat()
    conn.execute("INSERT INTO projects (mgmt_code, name, customer_id, customer_name, currency, order_amount, order_date, due_date, stage, sales_name) "
                 "VALUES ('971M2611', '여러 장 시험', ?, '가상고객을', 'KRW', 0, ?, ?, '수주확정', '가상영업')", (CU, T0, T0))
    P = conn.execute("SELECT id FROM projects WHERE mgmt_code='971M2611'").fetchone()[0]

    def so(no, amt, label, od):
        conn.execute("INSERT INTO orders (project_id, order_no, customer_id, currency, total_amount, order_date, due_date, status) "
                     "VALUES (?, ?, ?, 'KRW', ?, ?, ?, 'CONFIRMED')", (P, no, CU, amt, od, od))
        oid = conn.execute("SELECT id FROM orders WHERE order_no=?", (no,)).fetchone()[0]
        conn.execute("INSERT INTO order_items (order_id, amount, unit_price, unit_label) VALUES (?, ?, ?, ?)", (oid, amt, amt, label))
        return oid

    O1 = so("Y-261126-1", 1000000, "1호기", T0)     # 견적서·발주서 2장씩 올릴 수주
    O2 = so("Y-261126-2", 1000000, "2호기", T0)     # 금액이 같아도 앞 수주 견적을 따라가지 않아야 함

import app.main as M  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

M.get_user = lambda request: ADMIN
FAKE = {"fields": {}}
M._qr61.read_quote = lambda raw, name, pw="": {"ok": True, "fields": dict(FAKE["fields"]), "warnings": []}
cl = TestClient(M.app, follow_redirects=False)
XL = b"PK\x03\x04" + b"0" * 64
PDF = b"%PDF-1.4 test"
R = []


def check(l, c, g=""):
    R.append(bool(c)); print(("✅ " if c else "❌ ") + l + ("" if c else "  → " + str(g)[:400]))


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def rows(sql, *a):
    with D.db_session() as c:
        return [tuple(r) for r in c.execute(sql, a).fetchall()]


def strip_comments(h):
    """그려진 화면에서 사람이 보는 글만 — 스크립트·꾸밈·HTML 주석 뺌(낱말 검사가 주석에 걸리지 않게)."""
    h = re.sub(r"<script\b.*?</script>", "", h, flags=re.S)
    h = re.sub(r"<style\b.*?</style>", "", h, flags=re.S)
    return re.sub(r"<!--.*?-->", "", h, flags=re.S)


print("§1 한 수주에 견적서 2장")
FAKE["fields"] = {"amount": 7777777, "currency": "KRW"}   # 수주 금액(1,000,000)과 다른 금액 — 예전이면 ⚠
j1 = q(cl.post, "/api/project-quote/attach/%d" % P, data={"order_id": str(O1)}, files={"file": ("견적_1호기_가.xlsx", XL, "application/vnd.ms-excel")}).json()
check("상세 올리기 ok · 금액 비교 알림·바꾸기 표시 없음", j1.get("ok") and j1.get("n_so") == 1 and not any(k in j1 for k in ("diff_sos", "amt_read", "replaced")), j1)
rd = q(cl.post, "/api/project-quote/read", files={"file": ("견적_1호기_나.xlsx", XL, "application/vnd.ms-excel")}).json()
pl = q(cl.post, "/api/project-quote/place", data={"tok": rd["tok"], "pid": P, "order_id": O1}).json()
check("견적 관리 붙이기 ok · 그 수주 견적서 2장(예전 것 지우지 않음)", pl.get("ok") and pl.get("n_so") == 2 and "replaced" not in pl, pl)
QF = rows("SELECT id, orig_name, stored FROM project_quote_files WHERE project_id=? AND order_id=? ORDER BY id", P, O1)
check("DB: 1호기 견적서 2장 모두", [x[1] for x in QF] == ["견적_1호기_가.xlsx", "견적_1호기_나.xlsx"], QF)
check("디스크: 두 파일 모두 있음", all(os.path.isfile(os.path.join(M._z61_dir(), x[2])) for x in QF))
check("변경 이력에 「예전 것 지움」 없음", rows("SELECT COUNT(*) FROM project_history WHERE project_id=? AND note LIKE '%예전 것 지움%'", P)[0][0] == 0)

print("§2 한 수주에 고객 발주서 2장")
u1 = q(cl.post, "/api/customer-po/upload", data={"pid": P, "order_id": O1}, files={"file": ("발주서_1호기_가.pdf", PDF, "application/pdf")}).json()
check("상세 발주서 올리기 ok · 「이전 발주서」 숫자 없음", u1.get("ok") and u1.get("placed") and u1.get("n_so") == 1 and "prev" not in u1, u1)
u2 = q(cl.post, "/api/customer-po/upload", files={"file": ("발주서_Y-261126-1_나.pdf", PDF, "application/pdf")}).json()
check("견적 관리 발주서 올리기 → 후보 = 그 수주 · 이미 1장 있음", u2.get("ok") and not u2.get("placed") and [x["oid"] for x in u2.get("cands") or []] == [O1]
      and u2["cands"][0]["has"] == 1, u2)
p2 = q(cl.post, "/api/customer-po/place", data={"tok": u2["tok"], "pid": P, "order_id": O1}).json()
check("붙이기 ok · 그 수주 발주서 2장", p2.get("ok") and p2.get("n_so") == 2 and "prev" not in p2, p2)
PF = rows("SELECT id, orig_name, stored FROM project_po_files WHERE project_id=? AND order_id=? ORDER BY id", P, O1)
check("DB·디스크: 발주서 2장 모두", [x[1] for x in PF] == ["발주서_1호기_가.pdf", "발주서_Y-261126-1_나.pdf"]
      and all(os.path.isfile(os.path.join(M._z143_dir(), x[2])) for x in PF), PF)
check("이력에 「이전 발주서」 없음", rows("SELECT COUNT(*) FROM project_history WHERE project_id=? AND note LIKE '%이전 발주서%'", P)[0][0] == 0)

print("§3 보이는 곳 모두에 두 장씩")
QN, PN = ["견적_1호기_가.xlsx", "견적_1호기_나.xlsx"], ["발주서_1호기_가.pdf", "발주서_Y-261126-1_나.pdf"]
hd = q(cl.get, "/project/%d" % P).text
check("상세 열림", "971M2611" in hd)
ql = hd[hd.find(">견적서</dt>"):hd.find("고객 발주서</dt>")]
check("상세 「견적서」 칸: 두 장 줄 모두", all(n in ql for n in QN) and ql.count('class="z62-qrow"') == 2, ql.count('class="z62-qrow"'))
card = hd[hd.find("📋 견적서 2장"):hd.find("📋 견적서 2장") + 3000] if "📋 견적서 2장" in hd else ""
check("수주 카드: 「📋 견적서 2장」 · 「📄 발주서 2장」 · 파일 이름 모두", card and all(n in card for n in QN) and "📄 발주서 2장" in card and all(n in card for n in PN))
t150 = hd[hd.find('id="docs150"'):]
t150 = t150[:t150.find("</dd>")]
check("수주별 견적·발주서 표: 1호기 칩에 견적서 2·발주서 2", all(("/quotes/%d" % x[0]) in t150 for x in QF) and all(("/customer-po/%d\"" % x[0]) in t150 for x in PF), t150[:300])
check("수주별 표 요약: 견적 없는 수주 1(2호기) · 발주서 없는 수주 1", re.search(r"견적 없는 수주 <b[^>]*>1</b>", t150) and re.search(r"발주서 없는 수주 <b[^>]*>1</b>", t150))
hq = q(cl.get, "/sales/quotations?period=all").text
row1 = hq[hq.find('data-oid="%d"' % O1):]
row1 = row1[:row1.find("</tr>")]
check("견적 관리 1호기 줄: 견적서 2 · 발주서 2 · 「＋ 더 올리기」", all(n in row1 for n in QN + PN) and row1.count("＋ 더 올리기") == 2, row1[:300])
check("견적 관리 요약: 견적서 있음 1 / 2건 · 없음 1건", re.search(r"견적서 있음</div><div class=\"n\">1 <span[^>]*>/ 2건", hq) and re.search(r"견적서 없음</div><div class=\"n\">1건", hq))
hl = q(cl.get, "/projects?view=docs").text
chips = hl[hl.find("971M2611"):]
chips = chips[:chips.find("</tr>")]
check("프로젝트 목록 📎 칩: 1호기 견적서 2 · 발주서 2 · 2호기 「견적 없음」", all(("/quotes/%d" % x[0]) in chips for x in QF)
      and all(("/customer-po/%d\"" % x[0]) in chips for x in PF) and "견적 없음" in chips, chips[:400])
ho = q(cl.get, "/sales/orders/%d" % O1).text
po_sec = ho[ho.find('id="po143"'):]
check("수주 상세 「📄 고객 발주서」: 2장 모두 · 줄마다 빼기", all(n in po_sec[:8000] for n in PN) and po_sec[:8000].count("z143-rm") >= 2)
hv = q(cl.get, "/customer-po/%d" % PF[0][0]).text
check("발주서 보기: 같은 수주 발주서 2장 목록 · 최종/이전 표시 없음", "같은 수주의 발주서 2장" in hv and all(n in hv for n in PN)
      and "이전 발주서" not in strip_comments(hv) and ">최종<" not in hv)
z = q(cl.get, "/projects/%d/docs.zip" % P)
names = zipfile.ZipFile(io.BytesIO(z.content)).namelist() if z.status_code == 200 else []
check("zip: 견적서 2 · 발주서 2 모두 · 「이전/」 폴더 없음", z.status_code == 200 and sum("견적서" in n and n.endswith(".xlsx") for n in names) == 2
      and sum("발주서" in n and n.endswith(".pdf") for n in names) == 2 and not any(n.startswith("이전/") for n in names), names)
txt = zipfile.ZipFile(io.BytesIO(z.content)).read([n for n in names if n.endswith(".txt")][0]).decode("utf-8-sig") if names else ""
check("zip 안내: 따라가기·이전 폴더 말 없음 · 견적서 없는 수주 Y-261126-2", "따라갑니다" not in txt and "「이전」" not in txt and "Y-261126-2" in txt, txt[:300])
ex = q(cl.get, "/sales/quotations/export.xlsx?period=all")
import openpyxl  # noqa: E402
wb = openpyxl.load_workbook(io.BytesIO(ex.content))
vals = [[c.value for c in r] for r in wb.active.iter_rows()]
flat = " ".join(str(v) for r in vals for v in r if v is not None)
check("엑셀 내보내기: 1호기 견적서 2줄 · 「금액 다름」 없음", ex.status_code == 200 and all(n in flat for n in QN) and "금액 다름" not in flat
      and sum(1 for r in vals if "Y-261126-1" in [str(v) for v in r]) == 2, ex.status_code)

print("§4 검토 글·주소 없음")
bad = []
for nm, html in (("상세", hd), ("견적 관리", hq), ("목록 📎", hl), ("수주 상세", ho), ("발주서 보기", hv)):
    s = strip_comments(html)
    for w in ("금액 다름", "확인했음", "이전 발주서", "예전 파일은 지워", "예전 견적서는 지", "수정 발주서", "수정본 올리기", "따라갑니다", "🔗 앞 수주", "앞 수주 견적", "z143-ack", "qm-ack"):
        if w in s:
            bad.append((nm, w))
check("화면 글에 검토·하나만 흔적 없음(금액 다름·확인했음·이전 발주서·예전 파일은 지워·따라감)", not bad, bad)
check("발주서 줄에 「최종」 배지 없음", ">최종</span>" not in hd and ">최종</span>" not in ho)
for url in ("/api/project-quote/ack/%d" % QF[0][0], "/api/quote-so-ack/%d" % O2, "/api/customer-po/ack/%d" % PF[0][0]):
    r = q(cl.post, url)
    check("「확인했음」 주소 없음: %s → %d" % (url.split("/")[2], r.status_code), r.status_code in (404, 405), r.status_code)

print("§5 견적서 없는 수주 = 따라가지 않고 「없음」")
with D.db_session() as c:
    st = M._z141_project(c, P)
check("2호기(금액이 1호기와 같음) = 없음 · 1호기 = 2장", st[O2] == {"st": "none", "fs": []} and len(st[O1]["fs"]) == 2, st)
card2 = hd[hd.find("Y-261126-2"):]
check("수주 카드 2호기 = 「없음 · 올리기 →」", "없음 · 올리기 →" in card2[:20000])
d = M._z150_one(P)
check("수주별 자료: miss_q·miss_p = 파일 0개 수주 수(2호기만)", d["miss_q"] == 1 and d["miss_p"] == 1, (d["miss_q"], d["miss_p"]))

print("§6 「견적서로 채우기」 경고 · 후보 금액 · 수주 칸 확인")
check("견적서 읽기 경고 없음(공급자 다른 회사 · 수량×단가≠합계 · 품명 없음)",
      M._qr61.checks({"supplier": "다른회사", "customer": "(주)케이엔케이", "qty": 2, "unit_price": 10, "amount": 999}) == [])
check("견적서로 채우기 화면 스크립트에 ⚠ 경고 줄 그리기 없음",
      "j.warnings" not in open(os.path.join(ROOT, "app", "templates", "_v5_partials", "quote_fill.html"), encoding="utf-8").read())
FAKE["fields"] = {"amount": 1000000, "currency": "KRW", "customer": "가상고객을"}
rd2 = q(cl.post, "/api/project-quote/read", files={"file": ("971M2611_새견적.xlsx", XL, "application/vnd.ms-excel")}).json()
cd = q(cl.get, "/api/quotes-z105/cands?tok=" + rd2["tok"]).json()
check("후보: 금액 같음/다름 없음 · 1호기 「견적서 2장 있음」 · 미리 안 고름", cd.get("pick") is None and not any("same" in x for x in cd["cands"])
      and [x["has"] for x in cd["cands"] if x["oid"] == O1] == [2], cd)
with D.db_session() as c:   # 수주번호 없는 옛 견적서 1장
    c.execute("INSERT INTO project_quote_files(tok, project_id, order_id, orig_name, stored, by_id, by_name, created_at, attached_at) "
              "VALUES('old160', ?, NULL, '옛_견적.xlsx', '202609/old160.xlsx', ?, '가상영업', '2026-09-01 10:00', '2026-09-01 10:00')", (P, ADMIN["id"]))
    LQ = c.execute("SELECT id FROM project_quote_files WHERE tok='old160'").fetchone()[0]
r = q(cl.post, "/api/so-check-file/quote/%d" % LQ, data={"order_id": O1})
check("수주 칸 확인: 견적서 2장 있는 1호기에도 붙음(409 막기 없음) · 이제 3장", r.status_code == 200 and r.json().get("ok")
      and rows("SELECT COUNT(*) FROM project_quote_files WHERE order_id=?", O1)[0][0] == 3, (r.status_code, r.text[:200]))

print("§7 그대로인 것")
rmv = q(cl.post, "/api/project-quote/remove/%d" % LQ).json()
check("견적서 빼기 그대로(그 파일만 · 다른 2장 남음)", rmv.get("ok") and rows("SELECT orig_name FROM project_quote_files WHERE order_id=? AND removed_at IS NULL ORDER BY id", O1) == [(n,) for n in QN])   # z1191z201: 뺀 줄은 30일 보관(목록에서만 빠짐)
rmp = q(cl.post, "/api/customer-po/remove/%d" % PF[1][0]).json()
check("발주서 빼기 그대로(그 파일만 · 다른 1장 남음)", rmp.get("ok") and rows("SELECT orig_name FROM project_po_files WHERE order_id=? AND removed_at IS NULL", O1) == [(PN[0],)])   # z1191z201
FAKE["fields"] = {}
j = q(cl.post, "/api/project-quote/attach/%d" % P, files={"file": ("안고름.xlsx", XL, "application/vnd.ms-excel")}).json()
check("수주 2개인데 안 고르면 여전히 멈춤(견적서)", (not j.get("ok")) and j.get("need_so") and rows("SELECT COUNT(*) FROM project_quote_files WHERE orig_name='안고름.xlsx'")[0][0] == 0, j)
j = q(cl.post, "/api/customer-po/upload", data={"pid": P}, files={"file": ("안고름.pdf", PDF, "application/pdf")}).json()
check("수주 2개인데 안 고르면 여전히 멈춤(발주서)", (not j.get("ok")) and j.get("need_so"), j)
hd = q(cl.get, "/project/%d" % P).text
check("단계 줄: 1 수주번호 고르기 → 2 올리기 → 3 다시 올리기(점선 · 안 올라갔을 때만) → 4 끝 · 금액 확인 단계 없음",
      re.search(r'<li data-i="3" class="[^"]*redo[^"]*"><span class="k">3</span> 다시 올리기\(안 올라갔을 때만\)</li>', hd) and "금액 확인" not in hd
      and "견적서 엑셀 올리기</li>" in hd and "발주서 올리기</li>" in hd)
check("✕ 닫기 그대로(발주서 보기)", "knk_close" in open(os.path.join(ROOT, "app", "templates", "customer_po_view.html"), encoding="utf-8").read())

node = None
for cand in ("node", r"C:\Program Files\nodejs\node.exe"):
    try:
        subprocess.run([cand, "--version"], capture_output=True, check=True); node = cand; break
    except Exception:
        pass
if node:
    bad = []
    for nm, html in (("상세", hd), ("견적 관리", hq), ("목록 📎", hl), ("수주 상세", ho), ("발주서 보기", hv), ("확인 필요", q(cl.get, "/projects/so-check").text)):
        for k, m in enumerate(re.finditer(r"<script(?![^>]*src)(?![^>]*type=\"application/(?:ld\+)?json\")[^>]*>(.*?)</script>", html, re.S)):
            fd, fpth = tempfile.mkstemp(suffix=".js"); os.write(fd, m.group(1).encode("utf-8")); os.close(fd)
            r = subprocess.run([node, "--check", fpth], capture_output=True, text=True, encoding="utf-8")
            os.remove(fpth)
            if r.returncode:
                bad.append(nm + "#%d " % k + r.stderr.strip().split("\n")[0][-160:])
    check("그려진 화면 스크립트 문법 모두 통과(node)", not bad, bad)
else:
    print("… node 가 없어 스크립트 문법 검사는 건너뜀")

print("\n결과: %d 통과 / %d 실패" % (sum(R), len(R) - sum(R)))
sys.exit(0 if all(R) else 1)
