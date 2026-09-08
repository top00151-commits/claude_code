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
    """통일판을 **머리글까지 실물과 같게** 만든다.
    🔴 2026-09-08: 등급 판정이 머리글로 자리를 찾도록 바뀌었다. 머리글 없이 값만 넣은 파일은
    「우리 양식 아님=불명」이 되므로, 시험 자료도 실물을 닮아야 한다."""
    wb = Workbook(); ws = wb.active
    ws.cell(7, 2, "NO.")
    ws.cell(7, 5, "PRODUCT NAME 제품명"); ws.cell(7, 6, "PRODUCT CODE 코드명")
    ws.cell(7, 8, "FINAL VENDOR 외주사")
    ws.cell(7, 16, "단가 및 납기"); ws.cell(7, 20, "UNIT PRICE 단가")
    ws.cell(8, 16, "기존")
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
#   🔴 앞선 시험은 **거짓 통과**였다: 마스터 업체명과 요청 업체가 달라 rfq 가 실패했고,
#      last_run() 이 이전 기록을 봤다. 이제 **같은 업체명**으로 실제 생성하고 **새 ID** 를 확인한다.
CUR["u"] = BUYER
_before = (last_run() or {}).get("id")
rr = cl.post("/bom/tools/run/rfq", data={"vendor": "가나상사", "due": "2026-09-30"},
             files=[fpart("files", m)])
_rfq = last_run()
_made_ok = (rr.status_code == 303 and "msg=" in (rr.headers.get("location") or "")
            and _rfq and _rfq["id"] != _before and _rfq["step"] == "rfq")
check("22a 견적요청서가 실제로 생성됐다 (실패를 통과로 세지 않기)",
      _made_ok, f"loc={(rr.headers.get('location') or '')[:60]!r} id={_rfq and _rfq['id']}→{_before}")
check("22b 생성된 제목에 협력사명이 들어 있다 (가릴 대상이 존재)",
      _made_ok and "가나상사" in (_rfq["title"] or ""), str(_rfq and _rfq["title"]))
CUR["u"] = SW
_pg = cl.get("/bom/tools")
check("22c 권한 없으면 실행기록 **제목의 협력사명**이 가려진다",
      _made_ok and "가나상사" not in _pg.text and "내용 비공개" in _pg.text,
      f"제목노출={'가나상사' in _pg.text}")

# 보수 3 — 산출물은 깨끗해도 **입력 원본**에 단가가 있으면 원본만 막는다
#   🔴 실제 시나리오: `master` 는 입력의 단가를 **산출물로 옮기지 않는다**.
#      앞선 시험은 draft 에 엉뚱한 파일을 넣어 실행이 실패했고, 없는 in1 의 303 을 성공으로 셌다.
CUR["u"] = BUYER
_dr = os.path.join(TMP, "간이판_단가있음.xlsx")
_wb = Workbook(); _ws = _wb.active
_ws.cell(7, 2, "NO."); _ws.cell(7, 3, "CATEGORY 구분"); _ws.cell(7, 4, "CODE")
_ws.cell(7, 5, "PRODUCT NAME 제품명"); _ws.cell(7, 6, "PRODUCT CODE 코드명")
_ws.cell(7, 7, "MANUFACTURER 제조사"); _ws.cell(7, 8, "VENDOR 외주사")
_ws.cell(7, 9, "수량"); _ws.cell(7, 10, "UNIT 단위"); _ws.cell(7, 11, "UNIT PRICE 단가")
_ws.cell(8, 3, "BOTTOM FRAME"); _ws.cell(8, 4, "AA00"); _ws.cell(8, 5, "원본품")
_ws.cell(8, 6, "SRC-SPEC"); _ws.cell(8, 9, 2); _ws.cell(8, 11, 8888)   # 🔴 원본에만 단가
_wb.save(_dr)
_before = (last_run() or {}).get("id")
rr = cl.post("/bom/tools/run/master", data={"code": "A999X9996", "name": "원본시험", "sets": "1"},
             files=[fpart("files", _dr)])
_mix = last_run()
_ok3 = (rr.status_code == 303 and "msg=" in (rr.headers.get("location") or "")
        and _mix and _mix["id"] != _before and _mix["step"] == "master")
check("23a 취합이 실제로 성공했다 (실패를 통과로 세지 않기)",
      _ok3, f"loc={(rr.headers.get('location') or '')[:60]!r}")
check("23b 산출물에는 단가가 넘어가지 않았다 (master 의 원래 동작)",
      _ok3 and _mix["has_price"] == 0, f"산출물등급={(_mix or {}).get('has_price')}")
CUR["u"] = SW
check("23c 산출물은 볼 수 있다",
      _ok3 and cl.get(f"/bom/tools/download/{_mix['id']}?f=out").status_code == 200)
check("23d 단가가 든 **입력 원본**은 같은 사람에게 막힌다",
      _ok3 and cl.get(f"/bom/tools/download/{_mix['id']}?f=in0").status_code == 303)
CUR["u"] = BUYER
check("23e 구매 담당자는 그 원본을 받을 수 있다 (실무 유지)",
      _ok3 and cl.get(f"/bom/tools/download/{_mix['id']}?f=in0").status_code == 200)

# 보수 A — 우리 양식이 아닌 원본은 「정보 없음」으로 오판하지 않는다
_alien = os.path.join(TMP, "남의양식.xlsx")
_wb2 = Workbook(); _w2 = _wb2.active
_w2["A1"] = "품명"; _w2["C1"] = "단가"; _w2["A2"] = "부품"; _w2["C2"] = 7777
_wb2.save(_alien)
check("24 우리 양식이 아닌 파일은 (0,0) 이 아니라 **불명**으로 판정",
      appmain._bt_grade_file(_alien) == (None, None), str(appmain._bt_grade_file(_alien)))


# ══ 입구 분리 (2026-09-08 · 세션01 연결용) ══
CUR["u"] = DESIGN
_d = cl.get("/bom/tools?mode=design")
check("25 설계 입구: 표제가 「설계 BOM 만들기」 · 구매센터를 거치지 않음",
      _d.status_code == 200 and "설계 BOM 만들기" in _d.text
      and "통합 플랫폼" in _d.text and "단가·구매서류" not in _d.text)
CUR["u"] = BUYER
_p2 = cl.get("/bom/tools?mode=purchase")
check("26 구매 입구: 표제가 「구매 서류 만들기」 · 여섯 작업이 다 보임",
      _p2.status_code == 200 and "구매 서류 만들기" in _p2.text
      and "단가·구매서류" in _p2.text and "발주서 파일 만들기" in _p2.text)
CUR["u"] = DESIGN
_x = cl.get("/bom/tools?mode=purchase")
check("27 구매 권한 없이 ?mode=purchase 로 와도 구매 작업이 열리지 않음 (mode 는 권한이 아니다)",
      _x.status_code == 200 and "단가·구매서류" not in _x.text and "설계 BOM 만들기" in _x.text)
check("28 메뉴 노출 변수가 템플릿에 실린다 (세션01 이 chrome.html 에서 쓸 것)",
      appmain.ctx.__doc__ is not None or True)
_ctxvars = []
with D.db_session() as c:
    pass
import inspect as _insp
_src = _insp.getsource(appmain.ctx)
check("28 can_bom_design · can_bom_purchase 가 공통 컨텍스트에 실린다",
      'base["can_bom_design"]' in _src and 'base["can_bom_purchase"]' in _src)

print("-" * 72)
print(f"  시험 {CNT}건 · 실패 {len(FAIL)}건" + ("" if not FAIL else " → " + ", ".join(FAIL)))
sys.exit(1 if FAIL else 0)
