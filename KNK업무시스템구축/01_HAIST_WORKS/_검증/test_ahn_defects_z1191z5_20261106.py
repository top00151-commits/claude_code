# -*- coding: utf-8 -*-
"""z1191z5 시험 — 안지연 프로 오류 신고(2026-11-06) 중 결함 ②③⑤ 고치기
   (대표 2026-11-06 「② 1·2·3 진행 / ③ 1·2 진행·3 안 채움 / ⑤ 1」)

  ② 추가·개조 발주 때 적은 모델명·장비명이 **그 수주에** 저장된다(간편 등록 완제품·제품·상품 · 엑셀 일괄은 인자만) ·
     상세 카드 「📦 모델/장비」가 항상 보이고 ✏️ 수정 때 그 수주만 고쳐진다(수주 머리 수정 입구) · 정보 수정 화면에 대표값 안내
  ③ 상품 양식 올리기의 PO유형은 **올린 그 수주에만**(프로젝트 PO유형 불변) ·
     프로젝트 PO유형이 바뀌는 길(정보 수정 · 상세 머리 칸 · 작업일정표 칸)에서 자기 값 없는 수주를 옛 값으로 먼저 굳힌다 ·
     값이 같으면 굳히지 않는다 · so_oid 있는 칸 수정은 그 수주만(기존)
  ⑤ 작업일정표: 프로젝트 비고 대신 보이기는 첫 수주 줄에만 — 추가·개조 수주 줄은 자기 비고(없으면 빈칸) · 엑셀 내보내기도 같음
  임시 DB · TestClient · 운영 아님
"""
import contextlib
import io
import os
import re
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z5-test-only-not-a-real-key"   # 시험용 가짜 값

import openpyxl                                              # noqa: E402
import app.database as D                                     # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z5_")
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
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                 "VALUES ('가상관리자', 'admin', 'T905', 'T905', 'sso_only_no_local_password', 1, 1, 1, 1, 1, 1)")
    ADMIN = dict(conn.execute("SELECT * FROM users WHERE employee_no='T905'").fetchone())
    conn.execute("INSERT INTO customers (name) VALUES ('가상고객')")

import app.main as M                                         # noqa: E402
from fastapi.testclient import TestClient                   # noqa: E402

M.get_user = lambda request: ADMIN
cl = TestClient(M.app, follow_redirects=False)
OK = FAIL = 0


def check(cond, msg):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", msg)
    else:
        FAIL += 1
        print("  ❌", msg)


def q(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


BASE = {"quick": "1", "customer_name": "가상고객", "biz_div": "M", "project_type": "NEW_EQUIP",
        "po_type": "신규", "status": "진행중", "confirm_now": "1", "order_date": "2026-11-04",
        "due_date": "2026-11-20", "currency": "KRW", "equip_name": "가상장비", "unit_qty": "1"}


def post_new(**kw):
    f = dict(BASE); f.update(kw)
    r = q(cl.post, "/projects/new", data=f)
    return r.status_code


def proj(name):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM projects WHERE name=? ORDER BY id DESC", (name,)).fetchone()
        return dict(r) if r else None


def orders_of(pid):
    with D.db_session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM orders WHERE project_id=? ORDER BY id", (pid,))]


def set_so_po_null(oid):
    with D.db_session() as c:
        c.execute("UPDATE orders SET po_type=NULL WHERE id=?", (oid,))


def board_rows():
    h = q(cl.get, "/sales/schedule?ym=2026-11").text
    out = {}
    for m in re.finditer(r'<tr[^>]*data-sono="([^"]*)"[^>]*>(.*?)</tr>', h, re.S):
        cells = dict(re.findall(r'data-col="([a-z_0-9]+)"[^>]*>(.*?)</td>', m.group(2), re.S))
        out[m.group(1)] = {k: re.sub(r"<[^>]+>", "", v).strip() for k, v in cells.items()}
    return out


def so_card(pid, sono, soid):
    h = q(cl.get, "/project/%d?so=%s" % (pid, sono)).text
    m = re.search(r'<div class="so-card[^"]*" data-soid="%d".*?(?=<div class="so-card[ "]|$)' % soid, h, re.S)
    return (m.group(0) if m else ""), h


# ───────────── ② 추가·개조 발주 모델명·장비명 저장 ─────────────
print("§1 ② 추가·개조 발주 모델명·장비명이 그 수주에 저장")
post_new(name="A-완제품", model="M1-처음", equip_name="E1-처음", shipment_form="ASSEMBLY", unit_price="1000", order_amount="1000", note="첫 등록 비고")
PA = proj("A-완제품")
post_new(name="A-완제품", po_type="추가", mgmt_code=PA["mgmt_code"], model="M2-추가", equip_name="E2-추가", shipment_form="ASSEMBLY",
         unit_price="2000", order_amount="2000", note="")
post_new(name="A-완제품", po_type="개조", mgmt_code=PA["mgmt_code"], model="M3-개조", equip_name="E3-개조", shipment_form="ASSEMBLY",
         unit_price="3000", order_amount="3000", note="")
post_new(name="A-완제품", po_type="추가", mgmt_code=PA["mgmt_code"], model="MP-상품", equip_name="EP-상품", shipment_form="PARTS",
         unit_price="", order_amount="0", parts_units="", note="",
         **{"pk_name[]": ["볼트"], "pk_model[]": ["B-1"], "pk_qty[]": ["4"], "pk_price[]": ["10"]})
post_new(name="A-완제품", po_type="추가", mgmt_code=PA["mgmt_code"], model="MS-제품", equip_name="ES-제품", shipment_form="SEMI",
         unit_price="", order_amount="0", note="",
         **{"it_name[]": ["소켓"], "it_spec[]": ["S-1"], "it_qty[]": ["2"], "it_price[]": ["100"]})
OA = orders_of(PA["id"])
PA = proj("A-완제품")
check(len(OA) == 5, "A 프로젝트 수주 5건(신규·추가·개조·상품 추가·제품 추가) — 실제 %d" % len(OA))
check(PA["model_name"] == "M1-처음" and PA["equip_name"] == "E1-처음", "프로젝트 대표값은 첫 등록(M1-처음·E1-처음) 그대로")
check((OA[0].get("model_name") or "") in ("", "M1-처음"), "첫 수주 모델명 = 비움 또는 첫 등록값(기존 동작) — %r" % OA[0].get("model_name"))
check(OA[1].get("model_name") == "M2-추가" and OA[1].get("equip_name") == "E2-추가", "추가 발주(완제품) 수주에 M2-추가·E2-추가 저장")
check(OA[2].get("model_name") == "M3-개조" and OA[2].get("equip_name") == "E3-개조", "개조 발주(완제품) 수주에 M3-개조·E3-개조 저장")
check(OA[3].get("model_name") == "MP-상품" and OA[3].get("equip_name") == "EP-상품", "상품 추가 발주 수주에 MP-상품·EP-상품 저장")
check(OA[4].get("model_name") == "MS-제품" and OA[4].get("equip_name") == "ES-제품", "제품 추가 발주 수주에 MS-제품·ES-제품 저장")
check(OA[1].get("po_type") == "추가" and OA[2].get("po_type") == "개조", "추가·개조 수주 PO유형은 종전처럼 자기 값")

# 추가 발주 함수 직접: 비우면 안 적음(NULL)
with D.db_session() as c:
    import app.project_workflow as PWF
    r0 = q(PWF.add_followup_order, c, PA["id"], order_date="2026-11-05", total_amount=10, due_date="2026-11-30",
           created_by=ADMIN["id"], note="", qty=1, model_name="  ", equip_name=None)
    so_blank = dict(c.execute("SELECT * FROM orders WHERE id=?", (r0["order_id"],)).fetchone())
check(so_blank.get("model_name") is None and so_blank.get("equip_name") is None, "모델·장비를 비우면 수주에 적지 않음(NULL = 프로젝트 대표값)")

print("§2 ② 상세 카드 📦 모델/장비 — 항상 보이고 ✏️ 수정 때 그 수주만")
card2, html2 = so_card(PA["id"], OA[1]["order_no"], OA[1]["id"])
check("📦 모델/장비" in card2 and "M2-추가" in card2 and "E2-추가" in card2, "추가 수주 카드에 📦 모델/장비 = M2-추가 · E2-추가")
check('data-field="model_name"' in card2 and 'value="M2-추가"' in card2 and 'data-field="equip_name"' in card2, "✏️ 수정 입력칸(model_name·equip_name) 있음 · 값 채워짐")
check("(기본값)" not in card2.split("🏢 발주처")[0], "자기 값 있는 수주엔 (기본값) 표시 없음")
card_blank, _ = so_card(PA["id"], so_blank["order_no"], so_blank["id"])
check("📦 모델/장비" in card_blank and "M1-처음" in card_blank and "(기본값)" in card_blank, "자기 값 없는 수주 카드는 프로젝트 값 M1-처음 + (기본값)")
# z1191z16 (대표 「1,2,3 진행해」 2026-11-10): ?so= 로 열면 위쪽은 그 수주 값((수주)) · 그냥 열면 대표값((대표값))
check("(대표값)" in q(cl.get, "/project/%d" % PA["id"]).text and "(수주)" in html2, "프로젝트 정보 칸 모델명·장비명: 그냥 열면 (대표값) · ?so= 면 (수주)(z1191z16)")
r = q(cl.post, "/sales/orders/%d/quick-edit" % OA[1]["id"], data={"model_name": "M2-고침", "equip_name": "E2-고침"})
o1 = orders_of(PA["id"])[1]
check(r.status_code == 200 and r.json().get("ok") and o1.get("model_name") == "M2-고침" and o1.get("equip_name") == "E2-고침", "수주 머리 수정 입구로 모델·장비 저장 → 그 수주만 바뀜")
check(proj("A-완제품")["model_name"] == "M1-처음", "프로젝트 대표값은 그대로(M1-처음)")
r = q(cl.post, "/sales/orders/%d/quick-edit" % OA[1]["id"], data={"model_name": "", "equip_name": ""})
o1 = orders_of(PA["id"])[1]
check(r.status_code == 200 and o1.get("model_name") is None, "비우면 NULL → 프로젝트 대표값을 따름")
q(cl.post, "/sales/orders/%d/quick-edit" % OA[1]["id"], data={"model_name": "M2-추가", "equip_name": "E2-추가"})
hq = q(cl.get, "/projects/%d/quick-edit" % PA["id"]).text
check("프로젝트 대표값" in hq and "📦 모델/장비" in hq, "프로젝트 정보 수정 화면에 「대표값 · 수주 카드에서」 안내")
hn = q(cl.get, "/projects/new").text
check("프로젝트 대표값" not in hn, "신규 등록 화면엔 그 안내 없음(수정 모드만)")

# ───────────── ③ PO유형 ─────────────
print("§3 ③ 상품 양식 올리기의 PO유형은 올린 그 수주에만")
post_new(name="B-상품", model="MB", shipment_form="PARTS", unit_price="", order_amount="0", parts_units="",
         **{"pk_name[]": ["부품1"], "pk_model[]": ["PB-1"], "pk_qty[]": ["2"], "pk_price[]": ["100"]})
PB = proj("B-상품")
post_new(name="B-상품", po_type="추가", mgmt_code=PB["mgmt_code"], model="MB2", shipment_form="PARTS", unit_price="", order_amount="0", parts_units="",
         **{"pk_name[]": ["부품2"], "pk_model[]": ["PB-2"], "pk_qty[]": ["1"], "pk_price[]": ["50"]})
OB = orders_of(PB["id"])
set_so_po_null(OB[0]["id"])      # 옛 데이터 모양(z1033 이전): 첫 수주는 자기 값 없음
xr = q(cl.get, "/projects/import-product-template?so_id=%d" % OB[1]["id"])
wb = openpyxl.load_workbook(io.BytesIO(xr.content)); ws = wb.active
found = None
for row in ws.iter_rows():
    for cell in row:
        if str(cell.value or "").strip() == "PO유형":
            found = cell; break
    if found:
        break
labels_in_row = sum(1 for cc in ws[found.row] if isinstance(cc.value, str) and cc.value.strip())
tgt = ws.cell(found.row + 1, found.column) if labels_in_row >= 4 else ws.cell(found.row, found.column + 1)
tgt.value = "개조"
# 모델명 칸도 바꿔 본다(② 올리기 경로)
fm = None
for row in ws.iter_rows():
    for cell in row:
        if str(cell.value or "").strip() == "모델명":
            fm = cell; break
    if fm:
        break
if fm:
    lr = sum(1 for cc in ws[fm.row] if isinstance(cc.value, str) and cc.value.strip())
    tm = ws.cell(fm.row + 1, fm.column) if lr >= 4 else ws.cell(fm.row, fm.column + 1)
    tm.value = "MB2-양식"
buf = io.BytesIO(); wb.save(buf)
ur = q(cl.post, "/sales/orders/%d/overwrite-product" % OB[1]["id"],
       files={"xlsx": ("상품양식.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}, data={"mode": "add"})
check(ur.status_code == 200 and (ur.json() or {}).get("ok"), "상품 양식 올리기(부품 추가·PO유형=개조) 응답 ok — %s" % ur.text[:100])
PB = proj("B-상품"); OB = orders_of(PB["id"])
check(PB["po_type"] == "신규", "프로젝트 PO유형은 그대로 '신규'(덮지 않음) — 실제 %r" % PB["po_type"])
check(OB[1].get("po_type") == "개조", "올린 수주의 PO유형 = 개조 — 실제 %r" % OB[1].get("po_type"))
check(OB[0].get("po_type") is None, "첫 수주(자기 값 없음)는 그대로 NULL(올리기는 프로젝트를 안 건드리니 굳힐 일도 없음)")
check(OB[1].get("model_name") == "MB2-양식" if fm else True, "올린 수주의 모델명 = 양식값(MB2-양식)")
br = board_rows()
check(br.get(OB[0]["order_no"], {}).get("po") == "신규" and br.get(OB[1]["order_no"], {}).get("po") == "개조",
      "작업일정표: 첫 수주 '신규' · 올린 수주 '개조' — %r / %r" % (br.get(OB[0]["order_no"], {}).get("po"), br.get(OB[1]["order_no"], {}).get("po")))

print("§4 ③ 프로젝트 PO유형이 바뀌는 길마다 자기 값 없는 수주를 옛 값으로 먼저 굳힘")


def make_two(name, first_null=True):
    post_new(name=name, model="MX", equip_name="EX", shipment_form="ASSEMBLY", unit_price="100", order_amount="100", note="")
    p = proj(name)
    post_new(name=name, po_type="추가", mgmt_code=p["mgmt_code"], model="MX2", equip_name="EX2", shipment_form="ASSEMBLY", unit_price="100", order_amount="100", note="")
    o = orders_of(p["id"])
    if first_null:
        set_so_po_null(o[0]["id"])
    return proj(name), orders_of(p["id"])


# (가) 프로젝트 정보 수정(빠른 폼 수정 모드 → POST /projects/{pid}/edit)
PC, OC = make_two("C-정보수정")
f = {"quick": "1", "unlock_verified": "1", "name": "C-정보수정", "customer_name": "가상고객", "biz_div": "M", "project_type": "NEW_EQUIP",
     "model": "MX", "equip_name": "EX", "po_type": "개조", "status": "진행중", "currency": "KRW", "is_export": "0",
     "order_date": "2026-11-04", "due_date": "2026-11-20", "shipment_form": "ASSEMBLY", "unit_qty": "1", "unit_price": "100", "order_amount": "100"}
r = q(cl.post, "/projects/%d/edit" % PC["id"], data=f)
PC2 = proj("C-정보수정"); OC2 = orders_of(PC["id"])
check(r.status_code in (200, 303) and "error=" not in (r.headers.get("location") or ""), "정보 수정 POST 통과 — %s %s" % (r.status_code, r.headers.get("location", "")[:60]))
check(PC2["po_type"] == "개조", "프로젝트 PO유형 → 개조")
check(OC2[0].get("po_type") == "신규", "자기 값 없던 첫 수주는 옛 값 '신규'로 굳어짐(따라 바뀌지 않음) — 실제 %r" % OC2[0].get("po_type"))
check(OC2[1].get("po_type") == "추가", "자기 값 있던 추가 수주는 '추가' 그대로")
with D.db_session() as c:
    hist = [dict(x) for x in c.execute("SELECT field, new_value FROM project_history WHERE project_id=? ORDER BY id", (PC["id"],))]
check(any("기존 수주 유지" in (h.get("field") or "") and "1건" in (h.get("new_value") or "") for h in hist), "변경 이력에 「PO유형(기존 수주 유지) … 1건」 남음")
br = board_rows()
check(br.get(OC2[0]["order_no"], {}).get("po") == "신규" and br.get(OC2[1]["order_no"], {}).get("po") == "추가", "작업일정표 줄도 신규 / 추가 그대로")
# 같은 값으로 다시 저장 → 굳히지 않음
PC3, OC3 = make_two("C2-같은값")
f2 = dict(f); f2["name"] = "C2-같은값"; f2["po_type"] = "신규"
q(cl.post, "/projects/%d/edit" % PC3["id"], data=f2)
check(orders_of(PC3["id"])[0].get("po_type") is None, "PO유형이 안 바뀌는 저장은 수주를 굳히지 않음(NULL 그대로)")

# (나) 상세 머리 칸 수정(header-edit)
PD, OD = make_two("D-머리칸")
r = q(cl.post, "/projects/%d/header-edit" % PD["id"], data={"field": "po_type", "value": "수리"})
OD2 = orders_of(PD["id"])
check(r.status_code == 200 and r.json().get("ok") and proj("D-머리칸")["po_type"] == "수리", "머리 칸 수정: 프로젝트 → 수리")
check(OD2[0].get("po_type") == "신규" and OD2[1].get("po_type") == "추가", "첫 수주 '신규'로 굳음 · 추가 수주 '추가' 그대로 — %r / %r" % (OD2[0].get("po_type"), OD2[1].get("po_type")))
with D.db_session() as c:
    hist = [dict(x) for x in c.execute("SELECT note FROM project_history WHERE project_id=? ORDER BY id DESC LIMIT 1", (PD["id"],))]
check(hist and "유지(z1191z5)" in (hist[0].get("note") or ""), "머리 칸 이력에 「… 1건은 '신규'로 유지」 — %r" % ((hist or [{}])[0].get("note") or "")[:80])

# (다) 작업일정표 칸 수정 — so_oid 없이(프로젝트) / so_oid 있이(그 수주만)
PE, OE = make_two("E-일정표칸")
r = q(cl.post, "/sales/schedule/cell", json={"kind": "project", "ref_id": PE["id"], "field": "po_type", "value": "기타"})
OE2 = orders_of(PE["id"])
check(r.status_code == 200 and r.json().get("ok") and proj("E-일정표칸")["po_type"] == "기타", "일정표 칸(프로젝트): 프로젝트 → 기타")
check(OE2[0].get("po_type") == "신규" and OE2[1].get("po_type") == "추가", "첫 수주 '신규'로 굳음 · 추가 수주 그대로")
PF, OF = make_two("F-수주칸")
r = q(cl.post, "/sales/schedule/cell", json={"kind": "project", "ref_id": PF["id"], "field": "po_type", "value": "개조", "so_oid": str(OF[1]["id"])})
OF2 = orders_of(PF["id"])
check(r.status_code == 200 and r.json().get("ok") and OF2[1].get("po_type") == "개조" and OF2[0].get("po_type") is None and proj("F-수주칸")["po_type"] == "신규",
      "so_oid 있는 칸 수정은 그 수주만(기존 z1033) — 프로젝트·첫 수주 불변")
# 일괄 수정(bulk) 프로젝트 대상
PG, OG = make_two("G-일괄")
r = q(cl.post, "/sales/schedule/bulk-cell", json={"field": "po_type", "value": "수리", "targets": [{"kind": "project", "ref_id": PG["id"]}]})
OG2 = orders_of(PG["id"])
check(r.status_code == 200 and proj("G-일괄")["po_type"] == "수리" and OG2[0].get("po_type") == "신규", "일괄 수정(프로젝트)도 첫 수주 '신규'로 굳음 — %s" % r.text[:80])

# ───────────── ⑤ 작업일정표 비고 ─────────────
print("§5 ⑤ 작업일정표 프로젝트 비고 대신 보이기는 첫 수주 줄에만")
br = board_rows()
a1, a2, a3 = OA[0]["order_no"], OA[1]["order_no"], OA[2]["order_no"]
check(br.get(a1, {}).get("note") == "첫 등록 비고", "첫 수주 줄 기타사항 = 프로젝트 비고 '첫 등록 비고'(기존 폴백 유지) — %r" % br.get(a1, {}).get("note"))
_BLANK = ("", "＋")   # 빈칸은 수정 가능 칸이라 「＋」(누르면 적기)로 그려진다
check(br.get(a2, {}).get("note") in _BLANK and br.get(a3, {}).get("note") in _BLANK, "추가·개조 수주 줄(비고 안 적음) = 빈칸 — %r / %r" % (br.get(a2, {}).get("note"), br.get(a3, {}).get("note")))
post_new(name="A-완제품", po_type="추가", mgmt_code=PA["mgmt_code"], model="M6", equip_name="E6", shipment_form="ASSEMBLY",
         unit_price="100", order_amount="100", note="추가 비고 적음")
a6 = orders_of(PA["id"])[-1]["order_no"]
br = board_rows()
check(br.get(a6, {}).get("note") == "추가 비고 적음", "비고를 적은 추가 수주 줄은 자기 비고 — %r" % br.get(a6, {}).get("note"))
# 작업일정표에서 비고를 적은 추가 수주 줄의 비고를 지우면 ''(z983) → 빈칸, 프로젝트 비고 그대로(첫 줄은 여전히 프로젝트 비고)
#   (작업일정표 JS startSoTextEdit 는 수주 줄 기타사항을 수주 머리 수정 입구 line_note 로 보낸다 — 같은 요청으로)
o6 = orders_of(PA["id"])[-1]
r = q(cl.post, "/sales/orders/%d/quick-edit" % o6["id"], data={"line_note": ""})
br = board_rows()
check(r.status_code == 200 and br.get(a6, {}).get("note") in _BLANK and br.get(a1, {}).get("note") == "첫 등록 비고" and proj("A-완제품")["logi_note"] == "첫 등록 비고",
      "추가 수주 줄 비고를 지우면 빈칸(z983) · 첫 줄·프로젝트 비고는 그대로 — %s / %r" % (r.text[:60], br.get(a6, {}).get("note")))
q(cl.post, "/sales/orders/%d/quick-edit" % o6["id"], data={"line_note": "추가 비고 적음"})
# 엑셀 내보내기도 같은 줄 자료
xr = q(cl.get, "/sales/schedule/export.xlsx?ym=2026-11")
check(xr.status_code == 200, "작업일정표 엑셀 내보내기 200")
if xr.status_code == 200:
    wb = openpyxl.load_workbook(io.BytesIO(xr.content)); ws = wb.active
    hdr = [str(c.value or "").strip() for c in ws[1]]
    ci_so = next((i for i, h in enumerate(hdr) if h in ("수주번호", "SO")), None)
    ci_note = next((i for i, h in enumerate(hdr) if "기타" in h or h == "비고"), None)
    notes = {}
    if ci_so is not None and ci_note is not None:
        for row in ws.iter_rows(min_row=2, values_only=True):
            notes[str(row[ci_so] or "").strip()] = str(row[ci_note] or "").strip()
    check(notes.get(a2, None) == "" and notes.get(a6) == "추가 비고 적음", "엑셀: 추가 수주 줄 비고 빈칸 · 적은 줄은 자기 비고 — %r / %r" % (notes.get(a2), notes.get(a6)))

print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
