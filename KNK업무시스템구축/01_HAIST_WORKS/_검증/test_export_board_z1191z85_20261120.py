# -*- coding: utf-8 -*-
"""z1191z85 시험 — 수출 관리 = 선적 건 보드 · 서류 점검 (대표 2026-11-20
  「안지연 프로 입장에서 … 20년 넘게 수출입 실무를 한 배테랑이 만든 프로그램처럼」)
  임시 DB · 임시 폴더 · 가짜 인보이스(가짜 회사·가짜 품목) · 운영 아님
"""
import contextlib, io, json, os, sys, tempfile
from datetime import datetime, timedelta, timezone
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z85-test-only-not-a-real-key"
import openpyxl  # noqa: E402
import app.database as D  # noqa: E402
TMP = tempfile.mkdtemp(prefix="knk_z1191z85_")
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
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("rank", "TEXT"), ("biz_divs", "TEXT")]:
        if col not in have:
            c.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    T1 = ins(c, "teams", {"name": "가상영업팀", "code": "T85A", "display_order": 1})

    def user(nm, emp, role="member", **kw):
        row = dict(name=nm, role=role, employee_no=emp, login_id=emp, password="sso_only_no_local_password", is_active=1, team_id=T1, rank="프로")
        row.update(kw)
        ins(c, "users", row)
        return dict(c.execute("SELECT * FROM users WHERE employee_no=?", (emp,)).fetchone())
    A = user("가수출", "T851", can_view_sales=1, can_use_sales=1)
    N = user("나일반", "T852")

import app.main as M  # noqa: E402
import app.export_board as EB  # noqa: E402
import app.export_check as X  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
EB._CFG["hs_fill_dir"] = os.path.join(TMP, "hs_fill")
EB._CFG["base"] = TMP
EB._CFG["go_live"] = "2026-01-01"        # 시작일 규칙은 §6 에서 따로 본다
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


def chk(cond, msg):
    global OK, FAIL
    OK, FAIL = (OK + 1, FAIL) if cond else (OK, FAIL + 1)
    print(("  [OK] " if cond else "  [FAIL] ") + msg)


def make_inv(no, day, items, pl=True, pl_qty_bump=None, total_off=0.0, weights=(12.5, 15.0, 0.2)):
    """실물 양식 모양(머리 칸 위치 · 31줄 품목 머리 · TOTAL 줄)의 가짜 인보이스. items = [(규격, 수량, 단가, 원산지, C/O, HS, 품명)]"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INVOICE"
    ws["A1"] = "COMMERCIAL  INVOICE"; ws["A2"] = "1) Shipper / Exporter"; ws["B4"] = "FAKE SHIPPER CO"
    ws["G4"] = no; ws["H4"] = "DATE:"; ws["I4"] = datetime.strptime(day, "%Y-%m-%d")
    ws["A10"] = "2) For Account & Risk of Messrs"; ws["F10"] = "T/T"; ws["B12"] = "FAKE VINA Co., Ltd."
    ws["G21"] = "INCOTERMS : C.I.P"; ws["A24"] = "4) Port of Loading"; ws["A25"] = "Incheon, Korea"
    ws["D24"] = "5) Final Destination"; ws["D25"] = "Hanoi, Vietnam"; ws["A28"] = "6) Carrier"; ws["D28"] = "7) Sailing On or About"
    ws["D29"] = datetime.strptime(day, "%Y-%m-%d") + timedelta(days=1)
    ws["A31"] = "12) Marks and Number of PKGS"; ws["D31"] = "13) Description of Goods"; ws["F31"] = " 14) Q'ty /Unit"
    ws["H31"] = "15) Unit Price"; ws["I31"] = "16) Amount"
    ws["L32"] = "Origin"; ws["M32"] = "Manufacturer"; ws["N32"] = "invoice %"; ws["O32"] = "C/O"; ws["Q33"] = "HS code"; ws["R33"] = "Tên hàng"
    r = 34
    tot = 0
    for i, (desc, q, p, org, co, hs, vn) in enumerate(items):
        ws.cell(r, 3, i + 1); ws.cell(r, 4, desc); ws.cell(r, 6, q); ws.cell(r, 8, p); ws.cell(r, 9, round(q * p, 2)); ws.cell(r, 10, "FAKECUST")
        ws.cell(r, 12, org); ws.cell(r, 13, "FAKEMAKER"); ws.cell(r, 14, 0.8); ws.cell(r, 15, co); ws.cell(r, 17, hs); ws.cell(r, 18, vn)
        tot += round(q * p, 2)
        r += 1
    ws.cell(r + 2, 1, "TOTAL"); ws.cell(r + 2, 9, round(tot + total_off, 2))
    if pl:
        p2 = wb.create_sheet("PACKING LIST")
        p2["A1"] = "PACKING LIST"; p2["G4"] = no; p2["I4"] = "DATE :"; p2["J4"] = datetime.strptime(day, "%Y-%m-%d")
        p2["A35"] = "12) Marks and Number of PKGS"; p2["D35"] = "13) Description of Goods"; p2["F35"] = " 14) Q'ty /Unit"
        p2["H35"] = "Net -"; p2["I35"] = "Gross-"; p2["J35"] = "Measurement"
        r = 38
        for i, (desc, q, *_x) in enumerate(items):
            p2.cell(r, 4, desc); p2.cell(r, 6, q + (pl_qty_bump if pl_qty_bump is not None and i == 0 else 0)); r += 1
        if weights:
            p2.cell(r + 1, 1, "TOTAL"); p2.cell(r + 1, 8, weights[0]); p2.cell(r + 1, 9, weights[1]); p2.cell(r + 1, 10, weights[2])
    b = io.BytesIO(); wb.save(b)
    return b.getvalue()


ITEMS = [("FAKE-SENSOR-100", 10, 20.0, "KOREA", "O", "85365099", "Cảm biến giả"),
         ("FAKE-CABLE-2M", 5, 3.5, "CHINA", "X", "85444294", "Dây cáp giả"),
         ("FAKE-RELAY-24V", 4, 8.25, "JAPAN", "X", "85364199", "Rơ le giả")]

print("§1 서류 점검(가짜 인보이스)")
r = X.check(X.read(make_inv("KNK-261101-1", "2026-11-01", ITEMS)))
lv = [i["level"] for i in r["items"]]
chk(r["facts"]["invoice_no"] == "KNK-261101-1" and r["facts"]["inv_date"] == "2026-11-01" and r["facts"]["incoterms"] == "CIP"
    and r["facts"]["pol"] == "Incheon, Korea" and r["facts"]["dest"] == "Hanoi, Vietnam" and r["facts"]["sail_date"] == "2026-11-02"
    and r["facts"]["consignee"] == "FAKE VINA Co., Ltd." and r["facts"]["payment"] == "T/T", "머리 칸 읽기(번호·날짜·조건·구간·선적일·받는 곳·결제)")
chk("err" not in lv and "warn" not in lv, "깨끗한 인보이스 = 오류·확인할 것 없음: %s" % [i["title"] for i in r["items"] if i["level"] in ("err", "warn")])
chk(r["summary"]["lines"] == 3 and abs(r["summary"]["amount"] - 250.5) < 0.01 and r["summary"]["gross"] == 15.0, "줄 수 3 · 합계 250.50 · 총중량 15")
r = X.check(X.read(make_inv("KNK-261101-1", "2026-11-01", ITEMS, pl_qty_bump=1)))
chk(any(i["level"] == "err" and "수량이 다른 줄 1" in i["title"] for i in r["items"]), "패킹 수량 하나 다름 → 오류")
r = X.check(X.read(make_inv("KNK-261101-1", "2026-11-01", ITEMS, total_off=10)))
chk(any(i["level"] == "err" and i["title"].startswith("TOTAL 이 줄 금액 합과 다릅니다") for i in r["items"]), "TOTAL ≠ 줄 합 → 오류")
r = X.check(X.read(make_inv("KNK-261101-1", "2026-11-01", ITEMS[:1] + [("FAKE-CN-PART", 2, 1.0, "CHINA", "O", "39269099", "Giả")])))
chk(any(i["level"] == "warn" and "C/O 「O」" in i["title"] for i in r["items"]), "중국산인데 C/O O → 확인할 것")
r = X.check(X.read(make_inv("KNK-261101-1", "2026-11-01", ITEMS, weights=None)))
chk(any(i["level"] == "warn" and "무게" in i["title"] for i in r["items"]), "패킹 무게 없음 → 확인할 것")
r = X.check(X.read(make_inv("KNK-261101-1", "2026-11-01", ITEMS[:1] + [("FAKE-NOHS", 1, 1.0, "KOREA", "O", "", "")])))
chk(any(i["level"] == "warn" and "HS 코드 8자리가 아닌 줄 1" in i["title"] for i in r["items"]), "HS 빈 줄 → 확인할 것")
from app.hs_fill import norm_key  # noqa: E402
hist = {norm_key("FAKE-SENSOR-100"): (12.0, "85365099", "KNK-260901-1", "2026-09-01"),
        norm_key("FAKE-CABLE-2M"): (3.5, "85442000", "KNK-260901-1", "2026-09-01")}
r = X.check(X.read(make_inv("KNK-261101-1", "2026-11-01", ITEMS + [ITEMS[0]])), hist)
chk(any(i["level"] == "warn" and "HS 가 다른 규격 1" in i["title"] for i in r["items"]), "지난번과 HS 다름 → 확인할 것")
chk(any(i["level"] == "warn" and "단가가 30% 넘게 다른 규격 1" in i["title"] for i in r["items"]), "지난번보다 단가 +67% → 확인할 것(같은 규격 두 줄이어도 한 번)")
chk(X.read(b"not an excel")["ok"] is False, "엑셀이 아니면 읽기 실패로(멈추지 않음)")

print("§2 보드 — 이미 올린 인보이스로 저절로 건이 생김")
KST = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=9)
two_days = (KST - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
today_no = "KNK-%s-1" % KST.strftime("%y%m%d")
with open(os.path.join(EB._CFG["hs_fill_dir"], "fakeA.xlsx"), "wb") as fo:
    fo.write(make_inv(today_no, KST.strftime("%Y-%m-%d"), ITEMS))
with D.db_session() as c:
    M._hs_fill_log_ensure(c)
    M._hs_hist_ensure(c)
    c.execute("INSERT INTO export_hs_fill_log(invoice_no, file_name, form, stored, n_total, n_auto, n_check, n_need, n_keep, filled_by, filled_at) "
              "VALUES(?,?,?,?,?,?,?,?,?,?,?)", (today_no, "fakeA.xlsx", "소모품", "fakeA.xlsx", 3, 1, 1, 1, 0, A["id"], two_days))
    c.execute("INSERT INTO export_hs_fill_log(invoice_no, file_name, form, stored, n_total, n_auto, n_check, n_need, n_keep, filled_by, filled_at) "
              "VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("KNK-261118-1", "fakeB.xlsx", "수책", "gone.xlsx", 40, 40, 0, 0, 0, A["id"], KST.strftime("%Y-%m-%d %H:%M:%S")))
    c.execute("INSERT INTO export_hist_inv(invoice_no, inv_date, kind, file_name, source, n_lines, total_amount, reg_by) VALUES(?,?,?,?,?,?,?,?)",
              ("KNK-260115-1", "2026-01-15", "일반통관", "old.xlsx", "register", 5, 1234.5, A["id"]))
    c.execute("INSERT INTO export_hist_line(invoice_no, inv_date, kind, part_key, descr, qty, unit_price, amount, hs_code, vn_name) VALUES(?,?,?,?,?,?,?,?,?,?)",
              ("KNK-260115-1", "2026-01-15", "일반통관", norm_key("FAKE-SENSOR-100"), "FAKE-SENSOR-100", 1, 12.0, 12.0, "85365099", "Cảm biến giả"))
    # 뒤에 나간 인보이스(2099) — 「지난번」 비교에 쓰면 안 됨
    c.execute("INSERT INTO export_hist_line(invoice_no, inv_date, kind, part_key, descr, qty, unit_price, amount, hs_code, vn_name) VALUES(?,?,?,?,?,?,?,?,?,?)",
              ("KNK-990101-1", "2099-01-01", "일반통관", norm_key("FAKE-RELAY-24V"), "FAKE-RELAY-24V", 1, 99.0, 99.0, "99999999", "Giả"))
    # 최종본이 이력에 들어간 건의 옛 「회신 대기」 기록 — HS 끝난 것으로
    c.execute("INSERT INTO export_hs_fill_log(invoice_no, file_name, form, stored, n_total, n_auto, n_check, n_need, n_keep, filled_by, filled_at) "
              "VALUES(?,?,?,?,?,?,?,?,?,?,?)", ("KNK-260115-1", "old.xlsx", "소모품", "", 5, 1, 2, 2, 0, A["id"], "2026-01-15 09:00:00"))
r = cl.get("/export")
t = r.text
chk(r.status_code == 200 and "진행 중인 선적" in t, "/export = 선적 건 보드 (200)")
chk(today_no in t and "KNK-261118-1" in t, "자동 채움 기록 두 건이 보드에 저절로")
chk("손이 필요한 일" in t and "법인 HS 회신 기다린 지 2일" in t, "법인 회신 이틀 → 손이 필요한 일")
import time  # noqa: E402
for _ in range(100):
    with D.db_session() as c:
        warm = c.execute("SELECT 1 FROM export_ship_check WHERE invoice_no=?", (today_no,)).fetchone()
    if warm:
        break
    time.sleep(0.1)
chk(bool(warm), "보드를 열면 아직 점검 안 한 진행 중 건을 뒤에서 점검(카드 금액·점검 표시)")
from app.export_board import _kind  # noqa: E402
chk(_kind("소모품") == "일반통관" and _kind("수책") == "수책통관" and _kind("예전 양식") == "", "양식 이름 → 통관 구분")
r = cl.get("/export/s/" + today_no)
t = r.text
chk(r.status_code == 200 and "서류 점검" in t and "FAKE VINA Co., Ltd." in t, "건 한 장 열면 파일을 읽어 점검(받는 곳 보임)")
chk("FAKEMAKER" not in t, "제조사·공급사 이름은 안 보임(구매처 = 부서 단위 민감 정보)")
with D.db_session() as c:
    ck = json.loads(c.execute("SELECT result FROM export_ship_check WHERE invoice_no=?", (today_no,)).fetchone()[0])
chk(ck["src_how"] == "HS 자동 채움 파일" and ck["summary"]["lines"] == 3, "점검 출처 = 자동 채움 파일 · 3줄")
chk(any("단가가 30% 넘게" in i["title"] for i in ck["items"]), "지난 수출 이력(1월 12.00)과 비교해 단가 다름을 찾음")
chk(not any("HS 가 다른" in i["title"] for i in ck["items"]), "뒤에 나간 인보이스(2099)는 「지난번」 비교에 안 씀")
r = cl.get("/export/s/KNK-261118-1")
chk(r.status_code == 200 and "점검할 파일이 없습니다" in r.text, "파일 보관 지난 건 = 점검 없음 안내(멈추지 않음)")
chk(cl.get("/export/s/KNK-999999-9").status_code == 303, "없는 건 → 보드로")
chk(cl.get("/export/s/bad%20no").status_code == 303, "이상한 번호 → 보드로")

print("§3 선적·통관·대금 칸 저장 → 단계가 저절로")


def save(no, old, new):
    return cl.post("/export/s/%s/save" % no, json={"old": old, "new": new})


r = save(today_no, {"etd": None}, {"etd": "2026-11-21x"})
chk(r.status_code == 400 and "날짜" in r.json()["error"], "날짜 모양 틀림 → 400")
r = save(today_no, {"etd": None, "eta": None}, {"etd": "2026-11-22", "eta": "2026-11-21"})
chk(r.status_code == 400 and "ETA" in r.json()["error"], "도착이 출발보다 앞 → 400")
r = save(today_no, {"gross_kg": None}, {"gross_kg": "abc"})
chk(r.status_code == 400, "숫자 칸에 글자 → 400")
r = save(today_no, {"ship_mode": None}, {"ship_mode": "로켓"})
chk(r.status_code == 400, "고르는 칸에 없는 값 → 400")
r = save(today_no, {"etd": None, "awb_no": None, "ship_mode": None, "gross_kg": None},
         {"etd": KST.strftime("%Y-%m-%d"), "awb_no": "FAKE-AWB-0001", "ship_mode": "항공", "gross_kg": "1,250.5"})
chk(r.status_code == 200 and r.json() == {"ok": True, "n": 4}, "출발·AWB·운송·무게 저장(4가지)")
with D.db_session() as c:
    row = dict(c.execute("SELECT * FROM export_ship WHERE invoice_no=?", (today_no,)).fetchone())
    logs = [dict(x) for x in c.execute("SELECT * FROM export_ship_log WHERE invoice_no=?", (today_no,))]
chk(row["gross_kg"] == 1250.5 and row["awb_no"] == "FAKE-AWB-0001" and row["updated_by"] == A["id"], "저장 값(쉼표 숫자 풀기) · 바꾼 사람")
chk(len(logs) == 4 and {x["field"] for x in logs} == {"출발(ETD)", "AWB · B/L 번호", "운송", "총중량(kg)"}, "바뀐 기록 4줄(칸 이름으로)")
r = save(today_no, {"awb_no": "OTHER"}, {"awb_no": "FAKE-AWB-0002"})
chk(r.status_code == 409 and r.json().get("conflict"), "그사이 다른 값이면 덮지 않음(409)")
r = save(today_no, {"awb_no": "FAKE-AWB-0001"}, {"awb_no": "FAKE-AWB-0001"})
chk(r.status_code == 200 and r.json()["n"] == 0, "같은 값이면 바뀐 것 0")
t = cl.get("/export").text
chk("FAKE-AWB-0001" in t, "보드 카드에 AWB")
r = save(today_no, {"cleared_at": None, "vn_lane": None, "vn_decl_no": None},
         {"cleared_at": KST.strftime("%Y-%m-%d"), "vn_lane": "황색(서류 심사)", "vn_decl_no": "FAKE-DECL-1"})
chk(r.status_code == 200 and r.json()["n"] == 3, "베트남 통관(신고번호·검사 구분·통관일) 저장")
t = cl.get("/export/s/" + today_no).text
chk('class="ex-step now"><b>베트남 통관</b>' in t, "단계 = 베트남 통관(지금 표시)")

print("§4 서류철 · 최종 인보이스로 다시 점검")
fin = make_inv(today_no, KST.strftime("%Y-%m-%d"), ITEMS, pl_qty_bump=2)
r = cl.post("/export/s/%s/file" % today_no, data={"kind": "invoice"}, files={"file": ("final.pdf", b"%PDF-1.4 fake", "application/pdf")})
chk(r.status_code == 400 and "엑셀" in r.json()["error"], "최종 인보이스 칸에 PDF → 400")
r = cl.post("/export/s/%s/file" % today_no, data={"kind": "awb"}, files={"file": ("run.exe", b"MZ", "application/octet-stream")})
chk(r.status_code == 400, "실행 파일 → 400")
r = cl.post("/export/s/%s/file" % today_no, data={"kind": "invoice"}, files={"file": ("final.xlsx", fin, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
chk(r.status_code == 200 and r.json()["ok"], "최종 인보이스(엑셀) 올림")
with D.db_session() as c:
    ck = json.loads(c.execute("SELECT result FROM export_ship_check WHERE invoice_no=?", (today_no,)).fetchone()[0])
    fid = c.execute("SELECT id FROM export_ship_file WHERE invoice_no=? AND kind='invoice'", (today_no,)).fetchone()[0]
chk(ck["src_how"] == "서류철 최종 인보이스" and any("수량이 다른 줄 1" in i["title"] for i in ck["items"]), "올린 최종본으로 바로 다시 점검 → 수량 오류 찾음")
r = cl.post("/export/s/%s/file" % today_no, data={"kind": "awb"}, files={"file": ("awb.pdf", b"%PDF-1.4 fake awb", "application/pdf")})
chk(r.status_code == 200, "AWB PDF 올림")
r = cl.get("/export/s/%s/file/%d" % (today_no, fid))
chk(r.status_code == 200 and r.content == fin, "서류철 파일 받기(올린 그대로)")
chk(cl.get("/export/s/KNK-261118-1/file/%d" % fid).status_code == 404, "다른 건 번호로는 못 받음")
t = cl.get("/export/s/" + today_no).text
chk("final.xlsx" in t and "awb.pdf" in t and "서류철" in t, "건 화면 서류철에 두 파일")
chk(cl.post("/export/s/%s/check" % today_no).json()["ok"], "다시 점검 단추")

print("§5 마감 · 다시 진행")
r = cl.post("/export/s/%s/close" % today_no, data={"to": "1"})
chk(r.status_code == 303, "마감")
t = cl.get("/export/s/" + today_no).text
chk("↺ 다시 진행" in t, "마감 뒤 = 다시 진행 단추")
t = cl.get("/export").text
chk("이번 달 마감 1건" in t, "보드 = 이번 달 마감 1건")
cl.post("/export/s/%s/close" % today_no, data={"to": "0"})
chk("✔ 마감" in cl.get("/export/s/" + today_no).text, "다시 진행 → 마감 단추 다시")

print("§6 직접 만들기 · 지난 건")
r = cl.post("/export/s/new", data={"invoice_no": "knk-261125-1", "kind": "수책통관"})
chk(r.status_code == 303 and r.headers["location"] == "/export/s/KNK-261125-1", "직접 만들기(대문자로) → 그 건")
chk(cl.post("/export/s/new", data={"invoice_no": "a b"}).headers["location"] == "/export?err=no", "이상한 번호 → 안내")
t = cl.get("/export").text
chk("KNK-261125-1" in t and "모든 선적 건" in t, "직접 만든 건 보드에")
chk("지난 건 1건" in t, "1월 이력 건 = 지난 건(진행 칸에 안 섞임 · 옛 회신 대기 기록이 있어도)")
EB._CFG["go_live"] = "2026-11-19"
t = cl.get("/export").text
chk("지난 건 2건" in t, "시작일(11-19) 전 인보이스 KNK-261118-1 = 적은 것 없으면 지난 건")
chk(today_no in t.split("모든 선적 건")[0], "시작일 뒤 인보이스와 적은 것이 있는 건은 그대로 진행 칸")
EB._CFG["go_live"] = "2026-01-01"

print("§7 권한 · 예전 화면")
CUR["u"] = N
chk(cl.get("/export").status_code == 303 and cl.get("/export").headers["location"] == "/home", "수출 권한 없으면 보드 → /home")
chk(cl.post("/export/s/%s/save" % today_no, json={"old": {}, "new": {"note": "x"}}).status_code == 403, "저장 403")
chk(cl.post("/export/s/%s/file" % today_no, data={"kind": "etc"}, files={"file": ("a.pdf", b"%PDF", "application/pdf")}).status_code == 403, "올리기 403")
chk(cl.get("/export/s/%s/file/%d" % (today_no, fid)).status_code == 303, "받기도 막힘")
CUR["u"] = A
chk(cl.get("/export/old").status_code == 200, "예전 첫 화면 = /export/old 그대로")
chk('href="/export/s/' + today_no in cl.get("/export/hs-fill").text, "자동 채움 기록의 번호 → 선적 건으로 이어짐")
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
chk(src.count('@app.get("/export", ') == 0 and '@app.get("/export/old", ' in src and "_z85eb.register_export_board" in src, "main.py: 예전 첫 화면 → /export/old · 보드 등록")
chk('app.add_api_route("/export", export_home' in src, "보드 등록 실패 시 예전 첫 화면을 /export 에 다시 거는 길")

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
