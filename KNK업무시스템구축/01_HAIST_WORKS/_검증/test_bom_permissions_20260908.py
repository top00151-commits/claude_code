#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""WP-04 BOM 권한 분리 시험 14항목 (대표 지시 2026-09-08 · 검토 정정 A~D 반영)

⛔ 운영 DB 를 열지 않는다. 임시 DB + 임시 보관함 + 비식별 시험계정으로만 한다.
   인증(get_user)만 대체하고 인가·저장·다운로드는 실코드를 그대로 누른다.

무엇을 지키는가
  · 설계 BOM 작업(draft·master)은 지금 그대로 — 8개 공용 경로가 함께 막히면 안 된다
  · 구매 작업(price·rfq·po·**revise**)은 구매 실행권한자만
  · 파일은 **담긴 정보**로 판정 — 작업 이름으로 등급을 정하지 않는다(정정 A)
  · 읽기에 실행권한을 요구하지 않는다 — 조회 전용 사용자 보존(정정 B)
  · 법인 계정의 역할 기반 권한을 새로 뺏지 않는다(정정 D)

실행:  python _검증/test_bom_permissions_20260908.py   → "실패 0" 이어야 통과
"""
import io
import os
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

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_bomperm_")
_REAL_DB = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "test.db")
assert D.DB_PATH != _REAL_DB
D.init_db()

import app.main as appmain                                 # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402
from openpyxl import Workbook, load_workbook               # noqa: E402

appmain._BT_STORE = os.path.join(TMP, "store")
os.makedirs(appmain._BT_STORE, exist_ok=True)

CUR = {"u": None}
appmain.get_user = lambda request: CUR["u"]
cl = TestClient(appmain.app, follow_redirects=False)
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# ── 비식별 시험계정 (운영 실측 조합을 그대로 본뜸) ──
DESIGN = {"id": 901, "name": "시험설계", "role": "member", "team_id": 4,     # 팀4: BOM O·구매 X·단가 O·구매처 X
          "can_use_logistics": 0, "can_view_logistics": 1}
SW = {"id": 902, "name": "시험SW", "role": "member", "team_id": 5,           # 팀5: BOM O·구매 X·단가 X·구매처 X
      "can_use_logistics": 0, "can_view_logistics": 1}
BUYER = {"id": 903, "name": "시험구매", "role": "member", "team_id": 10,      # 구매팀: 전권
         "can_use_logistics": 1, "can_view_logistics": 1}
VIEWONLY = {"id": 904, "name": "시험영업", "role": "member", "team_id": 1,    # 팀1: BOM X·조회 O·단가 O·구매처 O
            "can_use_logistics": 0, "can_view_logistics": 1}
VN_ADMIN = {"id": 905, "name": "시험법인관리", "role": "admin", "team_id": 18,  # 법인 팀 + 역할 admin
            "can_use_logistics": 0, "can_view_logistics": 0}

with D.db_session() as conn:
    for uu in (DESIGN, SW, BUYER, VIEWONLY, VN_ADMIN):
        conn.execute("INSERT INTO users(id, name, login_id, password, role) VALUES(?,?,?,'x',?)",
                     (uu["id"], uu["name"], f"P{uu['id']}", uu["role"]))
    # 운영과 같은 민감정보 정책 (실측: purchase_price=1,2,4,10,11,15 · supplier_info=1,10,11,15)
    conn.execute("DELETE FROM field_access_policy")
    for cat, teams in (("purchase_price", (1, 2, 4, 10, 11, 15)),
                       ("supplier_info", (1, 10, 11, 15))):
        for t in teams:
            conn.execute("INSERT INTO field_access_policy(category, team_id) VALUES(?,?)", (cat, t))

FAIL, CNT = [], 0


def check(name, ok, detail=""):
    global CNT
    CNT += 1
    print(("  ✅" if ok else "  ❌") + f" {CNT:02d} {name}" + ("" if ok else f" — {detail}"))
    if not ok:
        FAIL.append(name)


def last_run():
    with D.db_session() as c:
        r = c.execute("SELECT * FROM bom_tool_runs ORDER BY id DESC LIMIT 1").fetchone()
    return dict(r) if r else None


def mk_unified(path, vendor=None, price=None):
    """통일판 모양의 작은 파일 — H(8)=협력사 · P(16)/T(20)=단가 자리."""
    wb = Workbook(); ws = wb.active
    ws.cell(7, 2, "NO."); ws.cell(8, 2, "")
    ws.cell(9, 5, "시험품"); ws.cell(9, 6, "TEST-SPEC")
    if vendor:
        ws.cell(9, 8, vendor)
    if price:
        ws.cell(9, 16, price)
    wb.save(path)
    return path


def fpart(field, path):
    with open(path, "rb") as fh:
        return (field, (os.path.basename(path), fh.read(), XLSX))


def seed_run(step, vendor=None, price=None, report="보고 — 품목 3줄 · 제외 1줄"):
    """실행 기록 한 줄을 직접 심는다(등급 판정 함수를 그대로 통과시켜서)."""
    p = mk_unified(os.path.join(appmain._BT_STORE, f"seed_{step}_{vendor}_{price}.xlsx"), vendor, price)
    hp, hv = appmain._bt_grade_file(p)
    hp, hv = appmain._bt_grade_report(report, hp, hv)
    if step in appmain._BT_PURCHASE_STEPS:
        hp = 1 if hp is None else max(hp, 1)
        hv = 1 if hv is None else max(hv, 1)
    with D.db_session() as c:
        c.execute("INSERT INTO bom_tool_runs(mgmt_code, step, title, inputs, output_name, output_path,"
                  " report, created_by, has_price, has_vendor) VALUES(?,?,?,?,?,?,?,?,?,?)",
                  ("A999X9999", step, "시험", "[]", os.path.basename(p), p,
                   report, BUYER["id"], hp, hv))
        rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    return rid


print("=" * 72)
print("  WP-04 BOM 권한 분리 시험 (비식별 시험계정 · 임시 DB)")
print("=" * 72)

# ══ 1·2 설계 작업은 되고, 구매 작업 직접 호출은 거부 ══
CUR["u"] = DESIGN
KIT = os.path.normpath(os.path.join(ROOT, "..", "참고자료", "설계팀",
                                    "BOM 업무 자동화_2026.08.04", "1. BUDS 단차 검사기", "INVENTOR DOWN"))
r = cl.post("/bom/tools/run/draft", data={"code": "A999X9999", "name": "시험", "author": "시험"},
            files=[fpart("files", os.path.join(KIT, "AA00.xlsx"))])
check("01 설계 전용 사용자가 설계자료를 만든다 (draft)", r.status_code == 303 and "msg=" in (r.headers.get("location") or ""),
      (r.headers.get("location") or "")[:70])
_draft_run = last_run()

m = mk_unified(os.path.join(TMP, "m.xlsx"), "가나상사", 1000)
for st in ("price", "rfq", "po", "revise"):
    data = {"vendor": "가나상사", "due": "2026-09-30", "code": "A999X9999", "name": "시험"}
    fl = [fpart("files", m)] + ([fpart("ledger", m)] if st == "price" else []) \
        + ([fpart("master", m)] if st == "revise" else [])
    rr = cl.post(f"/bom/tools/run/{st}", data=data, files=fl)
    loc = rr.headers.get("location") or ""
    ok = rr.status_code == 303 and "err=" in loc and "%EA%B5%AC%EB%A7%A4" in loc  # '구매'
    if not ok:
        break
check("02 같은 사용자가 구매 작업 URL 을 직접 호출하면 거부 (price·rfq·po·revise)", ok, f"{st} → {loc[:70]}")

# ══ 13 revise 실행은 구매권한 · 조회는 별도 관문 ══
CUR["u"] = BUYER
rr = cl.post("/bom/tools/run/revise", data={"code": "A999X9999"},
             files=[fpart("master", m), fpart("files", os.path.join(KIT, "AA00.xlsx"))])
check("13 revise 실행은 구매 실행권한자에게 허용", rr.status_code == 303, str(rr.status_code))

# ══ 등급 판정 (정정 A) ══
CUR["u"] = BUYER
rid_plain = seed_run("draft")                       # 협력사·단가 없음
rid_vendor = seed_run("draft", vendor="가나상사")     # 🔴 설계 작업인데 협력사 있음
rid_both = seed_run("price", vendor="가나상사", price=5000)
rid_reponly = seed_run("draft", report="보고 — 타매입처로 채운 1줄: r10 SPEC=7,777원(출처 다른업체)")
with D.db_session() as c:
    g_plain = dict(c.execute("SELECT has_price,has_vendor FROM bom_tool_runs WHERE id=?", (rid_plain,)).fetchone())
    g_vendor = dict(c.execute("SELECT has_price,has_vendor FROM bom_tool_runs WHERE id=?", (rid_vendor,)).fetchone())
check("09 협력사가 든 입력으로 만든 draft 결과를 「구매정보 없음」으로 분류하지 않음",
      g_vendor["has_vendor"] == 1, str(g_vendor))
check("10 협력사 없는 설계 결과에는 구매 권한을 요구하지 않음",
      g_plain["has_vendor"] == 0 and g_plain["has_price"] == 0, str(g_plain))

# ══ 3·4·12 단가/구매처 조합별 우회 차단 ══
CUR["u"] = SW          # 단가 X · 구매처 X
check("03 단가 불허 사용자는 단가 포함 파일을 받지 못함",
      cl.get(f"/bom/tools/download/{rid_both}?f=out").status_code == 303)
check("04 구매정보가 남은 결과를 「설계 산출물」이라는 이유로 허용하지 않음",
      cl.get(f"/bom/tools/download/{rid_vendor}?f=out").status_code == 303)
CUR["u"] = DESIGN      # 단가 O · 구매처 X
check("12 단가만 허용된 사용자가 협력사 포함 파일을 우회하지 못함",
      cl.get(f"/bom/tools/download/{rid_vendor}?f=out").status_code == 303)
check("12b 같은 사용자도 순수 설계자료는 받을 수 있음",
      cl.get(f"/bom/tools/download/{rid_plain}?f=out").status_code == 200)

# ══ 5 보고문·입력·직접 URL 우회 ══
CUR["u"] = SW
page = cl.get("/bom/tools")
check("05 보고문에 단가·업체명이 그대로 노출되지 않음",
      "7,777" not in page.text and "열람 권한 필요" in page.text,
      f"status={page.status_code} · 7,777노출={'7,777' in page.text} · "
      f"자물쇠문구={'열람 권한 필요' in page.text}")
check("05b 파일엔 단가가 없어도 **보고문에만** 있으면 등급이 올라간다",
      cl.get(f"/bom/tools/download/{rid_reponly}?f=out").status_code == 303,
      "보고문 검사(_bt_grade_report)가 빠지면 여기서 샌다")

# ══ 11 조회 전용 사용자 (정정 B) ══
CUR["u"] = VIEWONLY
p2 = cl.get("/bom/tools")
check("11 조회 전용 사용자가 화면을 보고 허용 파일을 받을 수 있음",
      p2.status_code == 200 and cl.get(f"/bom/tools/download/{rid_both}?f=out").status_code == 200)
rr = cl.post("/bom/tools/run/draft", data={"code": "A999X9999", "name": "x"},
             files=[fpart("files", os.path.join(KIT, "AA00.xlsx"))])
check("11b 조회 전용 사용자는 실행하지 못함",
      rr.status_code == 303 and "err=" in (rr.headers.get("location") or ""))

# ══ 6 관리번호로 권한이 늘지 않음 ══
CUR["u"] = SW
check("06 관리번호를 같게 해도 권한이 늘지 않음",
      cl.get(f"/bom/tools/download/{rid_both}?f=out").status_code == 303)

# ══ 14 법인 역할 기반 권한 보존 (정정 D) ══
CUR["u"] = VN_ADMIN
check("14 법인 팀이라도 역할(admin) 기반 기존 권한은 사라지지 않음",
      cl.get("/bom/tools").status_code == 200
      and cl.get(f"/bom/tools/download/{rid_both}?f=out").status_code == 200)

# ══ 7 인계 — 남이 만든 설계자료를 다음 담당자가 열 수 있음 ══
CUR["u"] = SW
check("07 남이 만든 설계자료를 다음 담당자가 열 수 있음(본인 것만이 아님)",
      cl.get(f"/bom/tools/download/{rid_plain}?f=out").status_code == 200)

# ══ 8 설계 업로드 8경로가 함께 막히지 않음 ══
CUR["u"] = DESIGN
check("08 설계 BOM 업로드 경로가 함께 막히지 않음 (_bom_can_upload 무접촉)",
      cl.get("/bom/upload").status_code == 200)

# ══ 불명(과거 행)은 제한 ══
with D.db_session() as c:
    c.execute("INSERT INTO bom_tool_runs(mgmt_code, step, title, inputs, output_name, output_path,"
              " report, created_by) VALUES('A999X9999','draft','옛것','[]','old.xlsx',?,'x',?)",
              (os.path.join(appmain._BT_STORE, "seed_draft_None_None.xlsx"), BUYER["id"]))
    rid_old = c.execute("SELECT last_insert_rowid()").fetchone()[0]
CUR["u"] = BUYER
check("15 등급 불명(과거 행)은 구매권한자라도 제한된다",
      cl.get(f"/bom/tools/download/{rid_old}?f=out").status_code == 303)


# ══ 보수 1·2·3 (2026-09-08 검토 지적) ══
# 보수 1 — 실제 회사 빈 양식의 머리글(H7 "VENDOR/외주사")을 협력사로 오인하면 안 된다
_f_draft = os.path.join(ROOT, "app", "bom_tools", "양식", "양식_간이판.xlsx")
_f_master = os.path.join(ROOT, "app", "bom_tools", "양식", "양식_통일판_구매품PARTLIST.xlsx")
check("19 빈 간이판 양식: 머리글을 협력사로 오인하지 않음",
      appmain._bt_grade_file(_f_draft) == (0, 0), str(appmain._bt_grade_file(_f_draft)))
check("20 빈 통일판 양식: 머리글을 협력사로 오인하지 않음",
      appmain._bt_grade_file(_f_master) == (0, 0), str(appmain._bt_grade_file(_f_master)))

# 보수 1 — 실제 draft 생성 → 설계 권한으로 **내려받기까지** (양식 제목 오차단 회귀)
CUR["u"] = DESIGN
rr = cl.post("/bom/tools/run/draft", data={"code": "A999X9998", "name": "양식시험", "author": "시험"},
             files=[fpart("files", os.path.join(KIT, "AA00.xlsx"))])
_made = last_run()
check("21 설계자가 만든 간이판을 **본인이 내려받을 수 있다** (오차단 회귀)",
      rr.status_code == 303 and _made is not None
      and cl.get(f"/bom/tools/download/{_made['id']}?f=out").status_code == 200,
      f"등급={_made and (_made.get('has_price'), _made.get('has_vendor'))}")

# 보수 2 — 제목에 협력사명이 남지 않는다
CUR["u"] = BUYER
rr = cl.post("/bom/tools/run/rfq", data={"vendor": "파익스시험", "due": "2026-09-30"},
             files=[fpart("files", m)])
_rfq = last_run()
CUR["u"] = SW
_pg = cl.get("/bom/tools")
check("22 권한 없으면 실행기록 **제목의 협력사명**도 가려진다",
      "파익스시험" not in _pg.text and "내용 비공개" in _pg.text,
      f"제목노출={'파익스시험' in _pg.text}")

# 보수 3 — 산출물은 깨끗해도 **입력 원본**에 단가가 있으면 원본은 막는다
CUR["u"] = BUYER
_src = mk_unified(os.path.join(TMP, "원본_단가있음.xlsx"), None, 9999)   # 원본엔 단가
rr = cl.post("/bom/tools/run/draft", data={"code": "A999X9997", "name": "원본시험", "author": "시험"},
             files=[fpart("files", os.path.join(KIT, "AA00.xlsx")), fpart("files", _src)])
_mix = last_run()
CUR["u"] = SW
check("23 산출물은 볼 수 있어도 **단가가 든 입력 원본**은 따로 막힌다",
      cl.get(f"/bom/tools/download/{_mix['id']}?f=in1").status_code == 303,
      f"산출물등급={(_mix.get('has_price'), _mix.get('has_vendor'))}")

print("-" * 72)
print(f"  시험 {CNT}건 · 실패 {len(FAIL)}건" + ("" if not FAIL else " → " + ", ".join(FAIL)))
sys.exit(1 if FAIL else 0)
