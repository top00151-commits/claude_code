# -*- coding: utf-8 -*-
"""z1191z2 시험 — HS 사전에 없는 품목: 사전 확정 줄의 품명 낱말로 HS 를 예측해 주황(확인)으로 채운다
   대표 2026-11-02 「최대한 비슷한걸 넣었으면 좋겠어.. 기존에 입력된 HS사전에서 내용을 확인한 후 품명 및 용도가 비슷하면 자동으로
   채워줘 … "PIN BLOCK" … PUSHER 기구 부품 … 단순 비교만으로 보지말고 예측을하고 분석을 해서」 → 분석·측정 보고 →
   「1. 추천 2. 추천 3. 추천」 = 확신 0.8 이상만 채움 · KNK-P 는 많은 쪽 주황 + 단추 · 품명도 주황
  §1 낱말 뽑기(PUSHER1 → PUSHER · 낱말 쌍 · 코드 앞머리 · KNK·PART 뺌)
  §2 예측 — 부품 종류 낱말(PIN BLOCK · RUBBER)은 무겁게 · 모델 낱말(SM · SUB)은 가볍게 · 확정 줄만 배움
  §3 plan — 확신 ≥0.8 주황 채움(HS · 품명 · mã hàng 새 규격) · 미만 노랑 + 예측 단추 · 낱말 없으면 그대로 · 이미 찾는 줄은 전과 같음
  §4 사전에는 안 넣음(10-28 「확정한것만」) — lookup 그대로 · 고르기 단추로 확정할 때 품명(suggest_vn)
  §5 KNK 묶음 — HS 하나뿐인 묶음도 주황 채움 · 같은 번호 판 우선
  §6 서버 · 화면 글
  §7 경로(임시 DB · TestClient): ① 올림 → 예측 주황 채움 · 예측 단추 → 사전 확정(품명 mã hàng 새 규격 · note) → 다시 만든 파일은 자동
"""
import contextlib
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z2-test-only-not-a-real-key"   # 시험용 가짜 값
import openpyxl                                    # noqa: E402
import app.database as D                           # noqa: E402
from app import hs_fill as H                       # noqa: E402

OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


E = []


def ent(model, hs, vn="", st="CONFIRMED", n=1, key=None):
    E.append({"part_key": key or H.norm_key(model), "model": model, "name_en": "", "vn_name": vn, "hs_code": hs, "status": st,
              "seen_count": n, "last_seen": "2026-09-01"})


# PIN BLOCK = 늘 39269099 (모델은 여러 가지) · RUBBER = 40169390 · SM-F971 / SUB 는 여러 HS 에 흩어짐
for i, m in enumerate(("GROUND PIN BLOCK(SM-F971U SUB TOP PBA)", "PIN BLOCK(SM-A556 MAIN)", "PIN BLOCK(SM-S928 SUB)",
                       "SIGNAL PIN BLOCK(SM-F741 TOP)", "PIN BLOCK(SM-X910 FPCB)")):
    ent(m, "39269099", "Gá cố định vị trí sản phẩm bằng nhựa, mã hàng: %s, hàng mới 100%%" % m, n=2 + i)
for m in ("MIC RUBBER_R4", "KEY RUBBER(SM-A556)", "RUBBER PAD 10*10"):
    ent(m, "40169390", "Miếng đệm cao su, mã hàng: %s" % m)
for m, h in (("SM-F971 SUB CABLE", "85444294"), ("SM-F971 SUB JIG PLATE", "76169990"), ("SM-S928 SUB SOCKET", "85366999"),
             ("SM-A556 SUB SPRING", "73202090")):
    ent(m, h, "x, mã hàng: %s" % m)
ent("PUSHER HEAD(PENDING ONLY)", "84799090", st="PENDING")          # 확정 아님 — 배우지 않는다
ent("SPRING#&", "73202090", vn="SPRING#&Lò xo cuộn, mã hàng: BUFSP5, hsx: MISUMI")
ent("KNK-G-0374", "85371099", vn="MASTER BOARD#&Bảng mạch điều khiển, mã hàng: KNK-G-0374, hàng mới")
ent("KNK-G-0375", "85371099", vn="Bảng mạch điều khiển, mã hàng: KNK-G-0375")
idx = H.build_index(E)

print("§1 낱말 뽑기")
w = H.pred_words("SM-F971 SUB TOP PBA_PUSHER1(R0.3A-P-C)")
check("PUSHER1 → PUSHER · 낱말 쌍(SUB TOP · PBA PUSHER) · 숫자 섞인 모델 글자(F971 · R0)는 낱말 아님",
      {"PUSHER", "SUB", "TOP", "PBA", "SUB TOP", "PBA PUSHER"} <= w and "F971" not in w and "PUSHER1" not in w, sorted(w))
check("코드 앞머리(HSP0320-35E → #HSP · #HSP0320) · KNK · PART 는 뺌",
      {"#HSP", "#HSP0320"} <= H.pred_words("HSP0320-35E/B") and "KNK" not in H.pred_words("KNK-P-5019 PART")
      and "PART" not in H.pred_words("LATCH PART"))
check("사전 줄 글에 베트남어 품명 앞 영문 이름(SPRING#&Lò xo → SPRING)", "SPRING" in H.pred_words(H._pred_text(E[-3])))

print("§2 예측")
p1 = H.predict(idx, "SM-F971 SUB TOP PBA_PIN BLOCK2(R0.3A)")
check("PIN BLOCK 이 든 새 규격 → 39269099 · 확신 ≥ 0.8 · 근거 낱말에 PIN BLOCK", p1 and p1["hs"] == "39269099" and p1["conf"] >= H.PRED_MIN
      and any(x[0] == "PIN BLOCK" for x in p1["why"]), p1 and (p1["hs"], p1["conf"], p1["why"]))
p2 = H.predict(idx, "MIC SOUND LEAK RUBBER_R6-2(4.9*4*2.4)")
check("RUBBER → 40169390 · 가장 비슷한 사전 품목 = MIC RUBBER_R4(MIC · RUBBER 둘 다 겹침)", p2 and p2["hs"] == "40169390" and p2["ex"] == "MIC RUBBER_R4",
      p2 and (p2["hs"], p2["ex"], p2["conf"]))
p3 = H.predict(idx, "SM-F971 SUB HOLDER")
check("모델 낱말(SM · SUB)만 겹치면 확신이 낮다(< 0.8)", p3 is None or p3["conf"] < H.PRED_MIN, p3 and (p3["hs"], p3["conf"]))
check("확정 아닌 줄(PENDING PUSHER HEAD)은 배우지 않음 · 낱말이 사전에 없으면 None",
      "PUSHER" not in idx["pred"]["cnt"] and H.predict(idx, "ZZTOP UNKNOWNWORD") is None)
check("PRED_MIN = 0.8(대표 「1. 추천」)", H.PRED_MIN == 0.8)


def sc_of(rows):
    return {"sheets": [{"title": "INVOICE", "col_vn": 18, "items": [{"row": 34 + i, "desc": d, "hs_raw": hs, "vn_raw": vn}
                                                                      for i, (d, hs, vn) in enumerate(rows)]}]}


print("§3 plan")
acts = H.plan(sc_of([("SM-F971 SUB TOP PBA_PIN BLOCK2(R0.3A)", "", ""), ("SM-F971 SUB HOLDER", "", ""), ("ZZTOP UNKNOWNWORD", "", ""),
                     ("MIC RUBBER_R4", "", ""), ("SM-F971 SUB TOP PBA_PIN BLOCK3", "", "Đã có tên")]), idx)
a0, a1, a2, a3, a4 = acts
check("확신 ≥0.8 → 주황(확인) 채움 · HS · 품명(mã hàng 은 새 규격) · 단추(예측) · 사전 값 칸 = 예측 HS · 까닭에 「예측(확신 …)」",
      a0["status"] == H.CHECK and a0["write_hs"] == "39269099" and a0["color_hs"] == H.ORANGE and a0["color_vn"] == H.ORANGE
      and "mã hàng: SM-F971 SUB TOP PBA_PIN BLOCK2(R0.3A)," in (a0["write_vn"] or "") and a0["choices"][0]["kind"] == "predict"
      and a0["dict_hs"] == "39269099" and "예측(확신" in a0["why"] and "근거 낱말" in a0["why"], (a0["status"], a0["why"], a0["write_vn"]))
check("확신 < 0.8 → 노랑 그대로(채우지 않음) + 예측 단추 · 까닭에 「기준 0.8 미만이라 안 채움」",
      a1["status"] == H.NEED and a1["write_hs"] is None and a1["color_hs"] == H.YELLOW
      and (not a1["choices"] or (a1["choices"][0]["kind"] == "predict" and "기준 0.8 미만이라 안 채움" in a1["why"])), (a1["status"], a1["why"]))
check("낱말이 사전에 없으면 전처럼 「사전에 없음」 노랑 · 단추 없음", a2["status"] == H.NEED and a2["choices"] == [] and a2["why"] == "사전에 없음(새 품목)")
check("사전에 규격 그대로 있으면 전처럼 자동(예측 안 붙음)", a3["status"] == H.AUTO and a3["write_hs"] == "40169390"
      and not any(c.get("kind") == "predict" for c in a3["choices"]))
check("품명이 이미 적혀 있으면 품명은 그대로(HS 만 주황)", a4["status"] == H.CHECK and a4["write_vn"] is None and a4["color_vn"] is None)
cn = H.counts(acts)
check("셈 — 예측 주황 줄은 「확인」(법인 회신 필요)", cn["check"] >= 2 and not cn["no_reply"], cn)

print("§4 사전에는 넣지 않음 · 단추로 확정할 때 품명")
check("lookup 은 그대로 — 모델 글자(SM-F971)가 여러 HS 와 겹치면 ambiguous(📚 · 📌 는 예측을 쓰지 않음) · 예측은 plan 에서만",
      H.lookup(idx, "SM-F971 SUB TOP PBA_PIN BLOCK2(R0.3A)")[0] == "ambiguous" and H.lookup(idx, "MIC SOUND LEAK RUBBER_R6")[0] == "none")
check("모델 글자가 갈린 줄도 예측 — 까닭에 원래 까닭(같은 모델 후보 HS 가 갈림) + 예측",
      a0["why"].startswith("같은 모델 후보 HS 가 갈림") and "예측(확신" in a0["why"], a0["why"])
check("plan 은 사전 entries 를 바꾸지 않는다(줄 수 그대로)", len(idx["exact"]) == len({e["part_key"] for e in E}))
v = H.suggest_vn(idx, "SM-F971 SUB TOP PBA_PIN BLOCK2(R0.3A)", "39269099")
check("suggest_vn(예측) = 가장 비슷한 같은 HS 품명 · mã hàng 새 규격", v.startswith("Gá cố định") and "mã hàng: SM-F971 SUB TOP PBA_PIN BLOCK2(R0.3A)," in v, v)
check("suggest_vn(KNK 묶음) = 묶음 품명 번호 바꿈", "KNK-G-0390" in H.suggest_vn(idx, "KNK-G-0390", "85371099"))
check("예측 품명이 없으면 ''(품명 칸은 노랑)", H.predict_vn(idx, "ZZTOP UNKNOWNWORD", "39269099") == "")

print("§5 KNK 묶음")
k = H.plan(sc_of([("KNK-G-0390", "", "")]), idx)[0]
check("HS 하나뿐인 묶음(KNK-G) → 주황 채움 · 단추 1 · 품명 번호 바꿈", k["status"] == H.CHECK and k["write_hs"] == "85371099"
      and len(k["choices"]) == 1 and "KNK-G-0390" in (k["write_vn"] or "") and "KNK-G-037" not in (k["write_vn"] or ""), (k["why"], k["write_vn"]))
k2 = H.plan(sc_of([("KNK-G-0374-2", "", "")]), idx)[0]
check("같은 번호 판(KNK-G-0374-2 ↔ 0374) → 「같은 번호」로 채움", "같은 번호 85371099" in k2["why"], k2["why"])

print("§6 서버 · 화면 글")
main = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
html = io.open(os.path.join(ROOT, "app", "templates", "export_hs_fill.html"), encoding="utf-8").read()
check("확정: 예측 단추도 같은 길(suggest_vn) · note 에 「예측 값(확신 · 비슷한 …)」",
      'ch.get("kind") in ("family", "predict") and ch.get("hs") == hs' in main and 'vn = _hf.suggest_vn(_idx, a["desc"], hs)' in main
      and 'note += " · 예측 값(확신 %s · 비슷한 %s)"' in main)
check("확정: 고를 수 있는 값 검사는 그대로", 'if hs not in [ch.get("hs") for ch in (a.get("choices") or [])]:' in main)
check("화면: 예측 단추 글(확신 · 비슷한 품목) · 초록", "if(c.kind === 'predict') lab = '✓ 예측 ' + c.hs + ' 확정 (확신 ' + c.conf" in html
      and "(c.kind === 'family' || c.kind === 'predict' ? ' fam' : '')" in html)

print("§7 경로 — 임시 DB · TestClient")


def make_form(items, ino="KNK-261199-9"):
    """수책통관 최종 양식 모양(HS=S · Tên hàng=T) — items=[규격]"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "INVOICE"
    ws["A1"] = "COMMERCIAL  INVOICE"
    ws["G4"] = ino
    for col, v in {"A": "12) Marks and Number of PKGS", "D": "13) Description of Goods", "F": " 14) Q'ty /Unit", "H": "15) Unit Price",
                   "I": "16) Amount", "K": "COMPANY", "L": "관리코드", "M": "MODEL", "N": "품명", "O": "Q'TY", "P": "ORIGIN",
                   "Q": "SUPPLIER", "R": "CATEGORY", "S": "HS CODE", "T": "Tên hàng", "U": "SHIPPING DATE"}.items():
        ws[col + "31"] = v
    r = 34
    for d in items:
        ws["D%d" % r], ws["F%d" % r], ws["H%d" % r], ws["I%d" % r] = d, 2, 3.5, "=F%d*H%d" % (r, r)
        r += 1
    ws["A%d" % (r + 1)] = "TOTAL"
    wb.create_sheet("PACKING LIST")["A1"] = "PACKING LIST"
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


TMP = tempfile.mkdtemp(prefix="knk_z1191z2_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("name_vi", "TEXT"), ("dept_code", "TEXT"), ("rank", "TEXT"),
                     ("team_id", "INTEGER"), ("password_version", "INTEGER DEFAULT 1")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    if "entity" not in {r[1] for r in conn.execute("PRAGMA table_info(teams)")}:
        conn.execute("ALTER TABLE teams ADD COLUMN entity TEXT")
    conn.execute("INSERT INTO teams (name, entity, code, display_order) VALUES ('가상기술영업팀','KOR','ZPHQ',1)")
    TM = conn.execute("SELECT MAX(id) FROM teams").fetchone()[0]
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, rank, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) VALUES ('가상P901','member','P901','P901','x',1,1,?,'프로',1,1,0,0)",
                 (TM,))
    UP = dict(conn.execute("SELECT * FROM users WHERE employee_no='P901'").fetchone())

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M._HS_FILL_DIR = os.path.join(TMP, "hs_fill")
M._HS_HIST_IMG_DIR = os.path.join(TMP, "hs_hist_img")
M.get_user = lambda request, _u=UP: _u
cl = TestClient(M.app, follow_redirects=False)
with D.db_session() as c:
    M._hs_dict_ensure(c)
    c.execute("DELETE FROM export_hs_dict")
    for e in E:
        c.execute("INSERT INTO export_hs_dict(part_key,model,name_en,hs_code,vn_name,status,seen_count,last_seen,source_file) VALUES(?,?,?,?,?,?,?,?,'시험')",
                  (e["part_key"], e["model"], e["name_en"], e["hs_code"], e["vn_name"], e["status"], e["seen_count"], e["last_seen"]))


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def dict_row(key):
    with D.db_session() as c:
        r = c.execute("SELECT * FROM export_hs_dict WHERE part_key=?", (key,)).fetchone()
        return dict(r) if r else None


D1, D2 = "SM-F971 SUB TOP PBA_PIN BLOCK2(R0.3A)", "SM-F971 SUB HOLDER"
j = quiet(cl.post, "/export/hs-fill", files={"file": ("Invoice&packinglist_VN(261199-9).xlsx", make_form([D1, D2]))}).json()
at = {a["row"]: a for a in j.get("attention", [])}
check("① 올림 → 34줄 예측 주황(확인) · 예측 단추 · 35줄 노랑 + 예측 단추(안 채움) · 법인 회신 필요",
      j.get("ok") and at.get(34, {}).get("st") == "CHECK" and [c["kind"] for c in at[34]["choices"]] == ["predict"]
      and at.get(35, {}).get("st") == "NEED" and (not at[35]["choices"] or at[35]["choices"][0]["kind"] == "predict")
      and j["no_reply"] is False, (j.get("summary"), {r: (a["st"], a["choices"]) for r, a in at.items()}, j.get("error")))
wb = openpyxl.load_workbook(io.BytesIO(quiet(cl.get, j["download_url"]).content))
s34, t34 = wb["INVOICE"]["S34"], wb["INVOICE"]["T34"]
check("내려받은 파일 34줄 HS 39269099 · 품명(mã hàng 새 규격) · 둘 다 주황",
      str(s34.value) == "39269099" and ("mã hàng: " + D1) in str(t34.value or "") and s34.fill.fgColor.rgb == H.ORANGE
      and t34.fill.fgColor.rgb == H.ORANGE, (s34.value, t34.value, s34.fill.fgColor.rgb))
check("올리기만으로는 사전에 안 들어감(10-28 「확정한것만」)", dict_row(H.norm_key(D1)) is None)
r1 = quiet(cl.post, "/export/hs-fill/%d/confirm" % j["log_id"], json={"sheet": "INVOICE", "row": 34, "hs": "39269099"})
d1 = dict_row(H.norm_key(D1))
check("예측 단추 확정 → 사전 확정 · 품명 = 비슷한 사전 품명(mã hàng 새 규격) · note 에 「예측 값(확신」",
      r1.status_code == 200 and d1 and d1["status"] == "CONFIRMED" and d1["hs_code"] == "39269099"
      and ("mã hàng: " + D1) in (d1["vn_name"] or "") and "예측 값(확신" in (d1["note"] or ""), (r1.status_code, r1.text[:200], d1))
j2 = r1.json()
a34 = next((a for a in j2.get("attention", []) if a["row"] == 34), None)
check("다시 만든 파일 — 34줄은 자동(볼 줄에서 빠짐)", a34 is None and j2.get("ok"), (a34, j2.get("summary")))
bad = quiet(cl.post, "/export/hs-fill/%d/confirm" % j["log_id"], json={"sheet": "INVOICE", "row": 35, "hs": "12345678"})
check("단추에 없는 값은 막힘(409)", bad.status_code == 409, (bad.status_code, bad.text[:120]))

print()
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
