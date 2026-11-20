# -*- coding: utf-8 -*-
"""z1191z86 시험 — 수출 단가 점검 조건(사용자가 정함) · 범위 밖 줄 허용/고치기 고르기
  대표 2026-11-20 「조건을 사용자가 넣을수있게」 · 「기존에 나간 단가와 얼마가 차이가 나는지 … 범위를 정하는 거고 …
  벗어나면 알람 … 허용을 할 건지 말 건지를 선택을 받고 다음을 진행」
  §1 모듈(app/export_price) · §2 조건 화면·저장 · §3 ① 올림 → 범위 밖 줄 → 받기 막힘 → 고르기 → 받기
  §4 「고치기」 단가는 다음 비교 기준에서 뺌 · §5 조건 바꾸면 다시 점검 · §6 화면 글
  임시 DB · 임시 폴더 · 가짜 인보이스(가짜 품목) · 운영 아님
"""
import contextlib, io, json, os, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z86-test-only-not-a-real-key"
import openpyxl  # noqa: E402
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z86_")
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


with D.db_session() as c:
    have = {r[1] for r in c.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("rank", "TEXT"), ("biz_divs", "TEXT"), ("name_vi", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    T1 = ins(c, "teams", {"name": "가상영업팀", "code": "T86A", "display_order": 1})

    def user(nm, emp, role="member", **kw):
        row = dict(name=nm, role=role, employee_no=emp, login_id=emp, password="sso_only_no_local_password", is_active=1, team_id=T1, rank="프로")
        row.update(kw)
        ins(c, "users", row)
        return dict(c.execute("SELECT * FROM users WHERE employee_no=?", (emp,)).fetchone())
    A = user("가수출", "T861", can_view_sales=1, can_use_sales=1)
    N = user("나일반", "T862")

import app.main as M  # noqa: E402
import app.export_board as EB  # noqa: E402
import app.export_price as XP  # noqa: E402
import app.export_check as X  # noqa: E402
from app.hs_fill import norm_key  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
EB._CFG["hs_fill_dir"] = M._HS_FILL_DIR = os.path.join(TMP, "hs_fill")
EB._CFG["base"] = TMP
EB._CFG["go_live"] = "2026-01-01"
os.makedirs(EB._CFG["hs_fill_dir"], exist_ok=True)
CUR = {"u": A}


def _gu(request):
    with D.db_session() as c:
        r = c.execute("SELECT u.*, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=? AND u.is_active=1",
                      (CUR["u"]["id"],)).fetchone()
    return dict(r) if r else None


M.get_user = _gu
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def chk(cond, msg, got=None):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if cond else (OK, FAIL + 1)
    print(("  [OK] " if cond else "  [FAIL] ") + msg + ("" if cond or got is None else "   ← %r" % (got,)))


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def make_final(items, ino):
    """일반통관 최종 양식(z1191p 시험과 같은 모양) — items=[(규격, 수량, 단가, HS, 품명)]"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INVOICE"
    ws["A1"] = "COMMERCIAL  INVOICE"; ws["F2"] = "8) No. & Date of Invoice"; ws["G4"] = ino
    heads = {"A": "12) Marks and Number of PKGS", "D": "13) Description of Goods", "F": " 14) Q'ty /Unit", "H": "15) Unit Price",
             "I": "16) Amount", "K": "COMPANY", "L": "IMAGE", "M": "Origin", "P": "C/O", "R": "HS CODE", "S": "Tên hàng"}
    for col, v in heads.items():
        ws[col + "31"] = v
    r = 34
    for desc, q, p, hs, vn in items:
        ws["D%d" % r], ws["F%d" % r], ws["H%d" % r], ws["I%d" % r] = desc, q, p, q * p
        ws["R%d" % r], ws["S%d" % r], ws["M%d" % r] = hs, vn, "KOREA"
        r += 1
    ws["A%d" % (r + 1)] = "TOTAL"
    wb.create_sheet("PACKING LIST")["A1"] = "PACKING LIST"
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def up(items, ino):
    return quiet(cl.post, "/export/hs-fill", files={"file": ("Invoice&packinglist_VN(%s).xlsx" % ino[4:10], make_final(items, ino))})


# 지난 수출(1월) — 같은 규격 3개 단가 10.00
with D.db_session() as c:
    M._hs_fill_log_ensure(c)
    M._hs_hist_ensure(c)
    c.execute("INSERT INTO export_hist_inv(invoice_no, inv_date, kind, file_name, source, n_lines, total_amount, reg_by) VALUES(?,?,?,?,?,?,?,?)",
              ("KNK-260101-1", "2026-01-01", "일반통관", "old.xlsx", "register", 3, 30.0, A["id"]))
    for d in ("PRICE-UP-A", "PRICE-DOWN-B", "PRICE-SAME-C"):
        c.execute("INSERT INTO export_hist_line(invoice_no, inv_date, kind, part_key, descr, qty, unit_price, amount, hs_code, vn_name) VALUES(?,?,?,?,?,?,?,?,?,?)",
                  ("KNK-260101-1", "2026-01-01", "일반통관", norm_key(d), d, 1, 10.0, 10.0, "85365099", "Giả"))

print("§1 모듈 — 처음 값 15%(대표 11-20) · 구분 · 범위 판정 · 글")
with D.db_session() as c:
    rs = XP.rules(c)
chk(rs["수책통관"]["up"] == 15.0 and rs["일반통관"]["down"] == 15.0 and set(rs) == set(XP.KINDS), "처음 값 = 두 구분 모두 오름·내림 15%(대표 11-20)", rs)
chk(XP.kind_of(["일반통관"]) == "일반통관" and XP.kind_of("수책") == "수책통관" and XP.kind_of("수책·소모품") == "" and XP.kind_of("예전 양식") == "",
    "양식 → 구분(섞이거나 모르면 빈칸)")
chk(XP.tol({"수책통관": {"up": 12, "down": None}, "일반통관": {"up": 30, "down": 25}}, "") == (12, 25), "구분 모름 = 두 구분 중 좁은 값(빈칸은 빼고)")
chk(XP.out_of_range(20.1, 20, 20) and not XP.out_of_range(20.0, 20, 20) and XP.out_of_range(-20.1, 20, 20) and not XP.out_of_range(-90, 20, None),
    "범위: 넘어야 알림(같으면 안 넘음) · 내림 빈칸이면 내림은 안 봄")
chk(XP.rule_text(15, None) == "오름 15% 넘으면 알림" and XP.rule_text(None, None) == "단가는 안 봄" and XP.pkey(1.23456789) == "1.2346",
    "조건 글 · 단가 열쇠(소수 넷째 자리)")
doc = X.read(make_final([("PRICE-UP-A", 1, 12.0, "85365099", "Giả")], "KNK-261101-9"))
hist = {norm_key("PRICE-UP-A"): (10.0, "85365099", "KNK-260101-1", "2026-01-01")}
r15 = X.check(doc, hist, None, (15, None))
r30 = X.check(doc, hist, None, (30, 30))
rno = X.check(doc, hist, None, (None, None))
it = next((i for i in r15["items"] if "px" in i), {})
chk(it.get("title", "").startswith("정한 단가 범위를 벗어난 규격 1") and it["px"][0]["diff"] == 20.0 and it["px"][0]["last_inv"] == "KNK-260101-1",
    "서류 점검: 오름 15% 조건이면 +20% 줄을 찾음(줄마다 고를 자료 px)", it)
chk(not any("px" in i for i in r30["items"]) and not any("px" in i for i in rno["items"]), "오름 30% · 「안 봄」이면 찾지 않음")

print("§2 조건 화면 · 저장(누가·언제 기록 · 그사이 바뀌면 409 · 숫자만)")
pg = cl.get("/export/rules")
chk(pg.status_code == 200 and "단가 점검 <em>조건</em>" in pg.text and 'data-k="수책통관"' in pg.text and 'data-k="일반통관"' in pg.text,
    "조건 화면 200 · 두 구분 칸")
chk('"일반통관": [' in pg.text and "처음 값" in pg.text, "지난 수출 이력의 단가 변화를 화면에 넘김(적는 대로 「몇 줄이 걸리는지」 미리 보기)")
OLD = {"수책통관": {"up": 15, "down": 15}, "일반통관": {"up": 15, "down": 15}}
r = cl.post("/export/rules", json={"old": OLD, "new": {"일반통관": {"up": "16", "down": "16"}}})
chk(r.status_code == 200 and r.json().get("changed") == 1, "일반통관을 오름·내림 16% 로 저장", r.text)
with D.db_session() as c:
    rs = XP.rules(c)
    lg = c.execute("SELECT * FROM export_price_rule_log ORDER BY id DESC").fetchone()
chk(rs["일반통관"]["up"] == 16 and rs["일반통관"]["by"] == A["id"] and rs["수책통관"]["up"] == 15, "저장됨 · 바꾼 사람 · 수책은 그대로", rs)
chk(lg and lg["old_value"] == "오름 15% · 내림 15% 넘으면 알림" and lg["new_value"] == "오름 16% · 내림 16% 넘으면 알림", "바꾼 기록(전 → 후)", dict(lg) if lg else None)
r = cl.post("/export/rules", json={"old": OLD, "new": {"일반통관": {"up": "10", "down": "10"}}})
chk(r.status_code == 409, "그사이 다른 사람이 바꿨으면(옛 값이 다름) 409", r.status_code)
OLD["일반통관"] = {"up": 16, "down": 16}
chk(cl.post("/export/rules", json={"old": OLD, "new": {"일반통관": {"up": "abc", "down": ""}}}).status_code == 400
    and cl.post("/export/rules", json={"old": OLD, "new": {"일반통관": {"up": "2000", "down": ""}}}).status_code == 400, "숫자 아님 · 1000 넘음 → 400")
r = cl.post("/export/rules", json={"old": OLD, "new": {"일반통관": {"up": "15", "down": "15"}}})
chk(r.status_code == 200, "일반통관 다시 15%")
OLD["일반통관"] = {"up": 15, "down": 15}
CUR["u"] = N
chk(cl.get("/export/rules").status_code == 303 and cl.post("/export/rules", json={"old": OLD, "new": {}}).status_code == 403
    and cl.post("/export/price-ack", json={"invoice_no": "KNK-261120-1", "items": []}).status_code == 403, "수출 권한 없으면 화면 303 · 저장 403 · 고르기 403")
CUR["u"] = A

print("§3 ① 올림 → 범위 밖 줄 → 받기 막힘 → 허용/고치기 → 받기")
NO = "KNK-261120-1"
ITEMS = [("PRICE-UP-A", 2, 12.0, "85365099", "Giả"), ("PRICE-DOWN-B", 1, 8.0, "85365099", "Giả"),
         ("PRICE-SAME-C", 1, 11.0, "85365099", "Giả"), ("PRICE-UP-A", 3, 12.0, "85365099", "Giả")]
j = up(ITEMS, NO).json()
hi = j.get("hist") or {}
pr = hi.get("price") or []
chk(j.get("ok") and hi.get("kind") == "일반통관" and hi.get("up") == 15 and hi.get("rule") == "오름 15% · 내림 15% 넘으면 알림",
    "① 결과 = 이 인보이스 구분(일반통관)의 조건", {k: hi.get(k) for k in ("kind", "up", "down", "rule")})
chk(sorted({p["desc"] for p in pr}) == ["PRICE-DOWN-B", "PRICE-UP-A"] and all(p.get("key") for p in pr) and hi.get("n_open") == 2,
    "+20% 와 -20% 줄을 찾음(+10% 는 안 넘음) · 같은 규격·같은 단가 두 줄은 한 번 고름 → 남은 고르기 2", [(p["desc"], p["diff"]) for p in pr])
chk(sorted(hi.get("reasons") or []) == sorted(XP.REASONS), "허용 까닭 목록을 함께 줌")
lid = j["log_id"]
with D.db_session() as c:
    nn = c.execute("SELECT COUNT(*) FROM export_price_need WHERE log_id=?", (lid,)).fetchone()[0]
chk(nn == 2, "받기 전 확인용으로 범위 밖 줄 2개를 적어 둠", nn)
r = cl.get("/export/hs-fill/%d/download" % lid)
chk(r.status_code == 303 and r.headers["location"] == "/export/s/%s?need=%d#price" % (NO, lid), "고르기 전 받기 → 선적 건 화면의 단가 칸으로", r.headers.get("location"))
pg = cl.get("/export/s/%s?need=%d" % (NO, lid))
chk(pg.status_code == 200 and '"need": %d' % lid in pg.text and "PRICE-DOWN-B" in pg.text and "window.XP" in pg.text,
    "선적 건 화면: 단가 고르기 자료(px) · 다 고르면 받을 파일 번호 · 고르기 화면 스크립트")
chk("정한 단가 범위를 벗어난 규격 2 — 고를 것 2" in pg.text, "서류 점검 줄 = 「고를 것 2」(확인할 것)")
bd = cl.get("/export").text
chk("단가가 정한 범위 밖 2줄 — 허용/고치기 고르기" in bd, "보드 「손이 필요한 일」에 단가 고르기")
A_ = next(p for p in pr if p["desc"] == "PRICE-UP-A")
B_ = next(p for p in pr if p["desc"] == "PRICE-DOWN-B")


def ack(p, dec, reason="", no=NO):
    return cl.post("/export/price-ack", json={"invoice_no": no, "items": [dict(p, decision=dec, reason=reason)]})


chk(ack(A_, "allow").status_code == 400 and ack(A_, "maybe", "x").status_code == 400 and ack(A_, "allow", "x", no="").status_code == 400,
    "허용인데 까닭 없음 · 이상한 고르기 · 번호 없음 → 400")
r = ack(A_, "allow", XP.REASONS[0])
chk(r.status_code == 200 and r.json()["items"][0]["decision"] == "allow" and r.json()["items"][0]["by_name"], "A 허용(까닭) 저장 · 누가 고른지 돌려줌", r.text)
with D.db_session() as c:
    chk(XP.open_count(c, lid) == (1, NO), "남은 고르기 1", XP.open_count(c, lid))
chk(cl.get("/export/hs-fill/%d/download" % lid).status_code == 303, "하나 남았으면 받기 아직 막힘")
r = ack(B_, "fix")
chk(r.status_code == 200, "B 고치기 저장")
r = cl.get("/export/hs-fill/%d/download" % lid)
chk(r.status_code == 200 and r.content[:2] == b"PK", "다 골랐으면 받기 열림(채운 엑셀)", r.status_code)
with D.db_session() as c:
    lg = [dict(x) for x in c.execute("SELECT * FROM export_ship_log WHERE invoice_no=? AND field='단가 확인' ORDER BY id", (NO,))]
chk(len(lg) == 2 and "허용 — " + XP.REASONS[0] in lg[0]["new_value"] and "+20.0%" in lg[0]["new_value"] and "고치기" in lg[1]["new_value"],
    "선적 건 바뀐 기록에 「단가 확인」 두 줄(무엇을 · 지난번 · 차이 · 고른 것)", [x["new_value"] for x in lg])
pg = cl.get("/export/s/" + NO).text
chk("정한 단가 범위를 벗어난 규격 2 — 고치기 1" in pg, "고치기가 있으면 서류 점검 줄 = 오류(고치기 1)")
bd = cl.get("/export").text
chk("단가가 정한 범위 밖" not in bd and "(단가 고치기 1 포함)" in bd, "보드: 고르기 알림은 사라지고 「고치기 포함 오류」로")
r = ack(A_, "")
with D.db_session() as c:
    chk(r.status_code == 200 and XP.open_count(c, lid)[0] == 1, "고른 것 지우기(바꾸기) → 다시 남은 고르기 1")
ack(A_, "allow", "직접 적은 까닭")
j2 = up(ITEMS, NO).json()
pr2 = j2["hist"]["price"]
chk(j2["hist"]["n_open"] == 0 and {p["desc"]: p["decision"] for p in pr2} == {"PRICE-UP-A": "allow", "PRICE-DOWN-B": "fix"}
    and next(p for p in pr2 if p["desc"] == "PRICE-UP-A")["reason"] == "직접 적은 까닭",
    "같은 파일을 다시 올리면 고른 것이 그대로(같은 단가) → 남은 고르기 0", [(p["desc"], p.get("decision")) for p in pr2])
chk(cl.get("/export/hs-fill/%d/download" % j2["log_id"]).status_code == 200, "다시 올린 기록도 바로 받기")
j3 = up([("PRICE-UP-A", 2, 12.5, "85365099", "Giả")], NO).json()
chk(j3["hist"]["n_open"] == 1, "단가를 바꿔 올리면(12.5) 새로 고름", j3["hist"].get("n_open"))

print("§4 「고치기」로 고른 단가는 다음 인보이스의 「지난번」 기준에서 뺀다")
with D.db_session() as c:
    c.execute("INSERT INTO export_hist_line(invoice_no, inv_date, kind, part_key, descr, qty, unit_price, amount, hs_code, vn_name) VALUES(?,?,?,?,?,?,?,?,?,?)",
              (NO, "2026-11-20", "일반통관", norm_key("PRICE-DOWN-B"), "PRICE-DOWN-B", 1, 8.0, 8.0, "85365099", "Giả"))
j4 = up([("PRICE-DOWN-B", 1, 10.0, "85365099", "Giả")], "KNK-261121-1").json()
chk(j4["hist"]["price"] == [] and j4["hist"]["checked"] == 1, "B 10.00 ↔ 지난번은 고치기 8.00 이 아니라 1월 10.00 → 범위 안", j4["hist"]["price"])
pg = cl.get("/export/s/KNK-261121-1").text
chk("정한 단가 범위를 벗어난" not in pg and "단가는 정한 범위 안" in pg, "선적 건 서류 점검도 같은 기준(고치기 단가 뺌)")
with D.db_session() as c:
    c.execute("DELETE FROM export_price_ack WHERE invoice_no=? AND part_key=?", (NO, norm_key("PRICE-DOWN-B")))
j5 = up([("PRICE-DOWN-B", 1, 10.0, "85365099", "Giả")], "KNK-261121-1").json()
chk([p["desc"] for p in j5["hist"]["price"]] == ["PRICE-DOWN-B"] and j5["hist"]["price"][0]["last"] == 8.0,
    "(대조) 고치기를 지우면 8.00 이 기준 → +25% 로 걸림", j5["hist"]["price"])

print("§5 조건을 바꾸면 진행 중 건도 다시 점검")
OLD = {"수책통관": {"up": 15, "down": 15}, "일반통관": {"up": 15, "down": 15}}
r = cl.post("/export/rules", json={"old": OLD, "new": {"일반통관": {"up": "", "down": ""}}})
chk(r.status_code == 200, "일반통관 = 단가 안 봄(빈칸)", r.text)
pg = cl.get("/export/s/" + NO).text
chk("정한 단가 범위를 벗어난" not in pg and "단가 조건: 단가는 안 봄" in pg, "선적 건 다시 점검 → 단가 줄 없음 · 조건 글", None)
j6 = up(ITEMS, NO).json()
chk(j6["hist"]["price"] == [] and j6["hist"]["rule"] == "단가는 안 봄" and cl.get("/export/hs-fill/%d/download" % j6["log_id"]).status_code == 200,
    "① 도 같은 조건(안 봄) → 받기 바로")

print("§6 화면 글")
hf = cl.get("/export/hs-fill").text
chk("window.XP" in hf and "xp-mount" in hf and "hfMount()" in hf and "hf-dl" in hf and "±' + tol" not in hf, "① 화면: 고르기 상자 · 받기 닫기 · 옛 ±tol 표 없음")
chk("⚙ 단가 점검 조건" in cl.get("/export").text, "보드에 「⚙ 단가 점검 조건」 단추")
src = io.open(os.path.join(ROOT, "app", "templates", "_export_price_z86.html"), encoding="utf-8").read()
chk("남은 ' + n.open + '줄 모두 허용" in src and "직접 적기" in src and "바꾸기" in src, "고르기 상자: 모두 허용 · 직접 적기 · 바꾸기")
mp = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
chk(sum(1 for ln in mp.splitlines() if "_mail_site" in ln) == 24, "main.py _mail_site 줄 24 그대로")

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
