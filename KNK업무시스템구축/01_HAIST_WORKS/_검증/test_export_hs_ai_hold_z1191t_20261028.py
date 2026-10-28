# -*- coding: utf-8 -*-
"""z1191t 시험 — AI 추정 보류 · 📌 가 「같은 날 두 HS」를 줄 순서로 고르지 않기
   대표 2026-10-28 「그럼 AI확정은 근거가 없으니깐 삭제하고 AI확정 이부분은 앞으로도 기록하지 말고 보류하자.. 지금은 베트남법인에
   내용을 전달하면 법인에서 베트남통관 관련 업체에 품목 확인해서 HS코드 안내받아서 입력하는거라 지금은 이 방법으로 확정한것만 사용하는게
   맞는것 같아...」 → 이해 보고 → 「1로 진행해」(운영 사전 정리는 같은 날 SSH 로 따로 · 이 시험은 코드만)
   + 10-28 실측: KNK-260901-1 안에 HSP0320-35E/B 가 460행 39269099 · 582행 39259000 → 10:38 📌 가 줄 순서(582행)로 골랐다
  §1 원문: 보류 스위치(꺼짐)가 AI 부르기보다 앞 · 저장에서 AI → 확인 대기 · 📌 SQL 같은 날 HS 하나만 · 화면 틀 글
  §2 동작: AI 추정 경로 = 보류 안내(AI 안 부름 · 사전 그대로) · 스위치를 켜면 원래 길 · 한 줄 저장 · HS 사전 화면 AI 칸·고르기 ·
           📌 대상·split·남는 수 · 확정 뒤 그대로 · 자동 채움 화면 안내
"""
import ast
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191t-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  [OK] " + label)
    else:
        FAIL += 1
        print("  [FAIL] " + label + ("   ← %r" % (got,) if got is not None else ""))


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


SRC = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
FN = {n.name: ast.get_source_segment(SRC, n) for n in ast.parse(SRC).body
      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
      and n.name in ("export_hs_ai_suggest", "export_hs_dict_save", "_hs_hist_latest", "_hs_hist_summary")}
T_PREP = open(os.path.join(ROOT, "app", "templates", "export_prep_detail.html"), encoding="utf-8").read()
T_DICT = open(os.path.join(ROOT, "app", "templates", "export_hs_dict.html"), encoding="utf-8").read()
T_FILL = open(os.path.join(ROOT, "app", "templates", "export_hs_fill.html"), encoding="utf-8").read()
print("=" * 78)
print("§1 원문")
print("=" * 78)
f = FN["export_hs_ai_suggest"]
check("1 AI 추정 경로 — 보류 스위치(_HS_AI_SUGGEST_ON = False)를 권한 검사 바로 뒤 · AI 부르기(ai_client)보다 앞에서 본다",
      "\n_HS_AI_SUGGEST_ON = False\n" in SRC and "if not _HS_AI_SUGGEST_ON:" in f
      and f.index("if not _HS_AI_SUGGEST_ON:") < f.index("from . import ai_client") and f.index("_export_guard(req)") < f.index("if not _HS_AI_SUGGEST_ON:")
      and '"hold": True' in f)
s = FN["export_hs_dict_save"]
check("2 한 줄 저장 — 「AI 추정」으로 적지 않는다(AI → 확인 대기) · 그 밖의 값은 전처럼 확정",
      re.search(r'if st == "AI":[^\n]*\n\s+st = "PENDING"\n\s+if st not in \("CONFIRMED", "PENDING"\):\n\s+st = "CONFIRMED"', s) is not None, s[:300])
check("3 📌 대상 SQL — 마지막 수출 날짜의 줄끼리 HS 가 하나일 때만(같은 날 두 값이면 빠짐) · 요약은 그런 규격을 split 으로",
      "COUNT(DISTINCT w.hs_code)" in FN["_hs_hist_latest"] and "IFNULL(w.inv_date,'')=IFNULL(l.inv_date,''))=1" in FN["_hs_hist_latest"]
      and '"split": split[:50], "n_split": len(split)' in FN["_hs_hist_summary"])
check("4 통관 입력표 — 「AI로 추정할까요」 물음 없음 · 신규는 비워 둔다는 보류 안내 · 단추 설명 · 보류 응답은 「실패」라 하지 않음",
      "AI로 추정할까요" not in T_PREP and "AI 추정은 보류 중입니다(대표 10-28)" in T_PREP
      and "AI 추정 보류 — 베트남 법인이 통관 업체에 확인한 HS 를 입력" in T_PREP and "alert(j.hold ? j.error : " in T_PREP)
check("5 HS 사전 화면 — 안내 「AI 추정은 보류」 · AI 칸은 남은 줄이 있을 때만 · 상태 고르기에 AI 없음(AI 줄만 지금 값으로)",
      "AI 추정은 보류</b>(대표 10-28)" in T_DICT and "{% if stats.get('AI') or st=='AI' %}" in T_DICT
      and "{% for s in ['CONFIRMED','PENDING'] + (['AI'] if r.status=='AI' else []) %}" in T_DICT
      and "확인 대기·AI 추정 우선" not in T_DICT)
check("6 자동 채움 화면 — 📌 설명에서 AI 추정 뺌 · 같은 날 두 HS 안내(📌 칸 · 다 맞음 줄 두 곳)",
      "사전이 <b>확인 대기</b>이거나" in T_FILL and "AI 추정·확인 대기</b>이거나" not in T_FILL
      and T_FILL.count("같은 날 수출에서 HS 가 둘로 적힌 규격 {{ hist.n_split }}개") == 2)

print()
print("=" * 78)
print("§2 동작")
print("=" * 78)
TMP = tempfile.mkdtemp(prefix="knk_z1191t_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("entity", "TEXT"), ("name_vi", "TEXT"), ("rank", "TEXT"), ("team_id", "INTEGER"),
                     ("password_version", "INTEGER DEFAULT 1")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, "
                 "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) VALUES ('가상M901','member','M901','M901','x',1,1,1,1,0,0)")
    U = dict(conn.execute("SELECT * FROM users WHERE employee_no='M901'").fetchone())
import app.main as M                                        # noqa: E402
import app.ai_client as AI                                  # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M._HS_FILL_DIR = os.path.join(TMP, "hs_fill")
M._HS_HIST_IMG_DIR = os.path.join(TMP, "hs_hist_img")
M.get_user = lambda request, _u=U: _u
cl = TestClient(M.app, follow_redirects=False)
with D.db_session() as c:
    M._hs_dict_ensure(c)
    M._hs_hist_ensure(c)
    for t in ("export_hs_dict", "export_hist_line", "export_hist_inv"):
        c.execute("DELETE FROM %s" % t)
    for k, hs, st, note in (("K-SPLIT", "39259000", "PENDING", "충돌: 기존 39259000 ↔ 신규 39269099 (x.xlsx)"),
                            ("K-SPLIT-CONF", "11111111", "CONFIRMED", ""),
                            ("K-OLD-SPLIT", "44444444", "PENDING", ""),
                            ("K-NORMAL", "88888888", "PENDING", ""),
                            ("K-NOHIST", "99999999", "PENDING", ""),
                            ("K-PLAIN", "12345678", "CONFIRMED", "")):
        c.execute("INSERT INTO export_hs_dict(part_key,model,vn_name,hs_code,status,seen_count,note,updated_at) "
                  "VALUES(?,?,?,?,?,1,?,'2026-07-23 10:00:00')", (k, k + " 모델", "VN " + k, hs, st, note))
    for ino, d, k, hs, row in (("KNK-260901-9", "2026-09-01", "K-SPLIT", "39269099", 460),
                               ("KNK-260901-9", "2026-09-01", "K-SPLIT", "39259000", 582),     # 같은 인보이스 안 두 값(10-28 실물 모양)
                               ("KNK-260801-9", "2026-08-01", "K-SPLIT-CONF", "22222222", 10),
                               ("KNK-260801-8", "2026-08-01", "K-SPLIT-CONF", "33333333", 11),  # 같은 날 다른 인보이스 두 값
                               ("KNK-260101-9", "2026-01-01", "K-OLD-SPLIT", "55555555", 1),
                               ("KNK-260101-9", "2026-01-01", "K-OLD-SPLIT", "66666666", 2),    # 옛날에 갈렸어도 마지막 날은 하나
                               ("KNK-260501-9", "2026-05-01", "K-OLD-SPLIT", "77777777", 3),
                               ("KNK-260401-9", "2026-04-01", "K-NORMAL", "88888888", 4)):
        c.execute("INSERT INTO export_hist_line(invoice_no,inv_date,kind,sheet,row_no,part_key,descr,qty,unit_price,amount,hs_code,vn_name,img) "
                  "VALUES(?,?,'일반통관','INVOICE',?,?,?,1,1,1,?,?,NULL)", (ino, d, row, k, k, hs, "VN " + k + " " + hs))
    for ino, d in (("KNK-260901-9", "2026-09-01"), ("KNK-260801-9", "2026-08-01"), ("KNK-260801-8", "2026-08-01"),
                   ("KNK-260101-9", "2026-01-01"), ("KNK-260501-9", "2026-05-01"), ("KNK-260401-9", "2026-04-01")):
        c.execute("INSERT INTO export_hist_inv(invoice_no,inv_date,kind,file_name,source,n_lines,total_amount,reg_by) "
                  "VALUES(?,?,'일반통관','x.xlsx','register',1,1,?)", (ino, d, U["id"]))
    n_dict0 = c.execute("SELECT COUNT(*) FROM export_hs_dict").fetchone()[0]

# ─── AI 추정 경로 = 보류 ───
called = []
_av, _ch = AI.ai_available, AI.ai_chat
AI.ai_available = lambda *a, **k: called.append("available") or True
AI.ai_chat = lambda *a, **k: called.append("chat") or (True, "[]")
r = quiet(cl.post, "/export/prep/1/hs-ai-suggest")
with D.db_session() as c:
    n_dict1 = c.execute("SELECT COUNT(*) FROM export_hs_dict").fetchone()[0]
check("7 AI 추정 경로 — 200 · ok False · hold True · 보류 안내 글 · AI 를 부르지 않음 · 사전 줄 수 그대로",
      r.status_code == 200 and r.json() == {"ok": False, "hold": True, "error": M._HS_AI_HOLD_MSG} and called == [] and n_dict1 == n_dict0
      and "베트남 법인이 통관 업체에 확인한 값" in M._HS_AI_HOLD_MSG, (r.status_code, r.text[:200], called, n_dict0, n_dict1))
M._HS_AI_SUGGEST_ON = True
AI.ai_available = lambda *a, **k: called.append("available") or False
r2 = quiet(cl.post, "/export/prep/1/hs-ai-suggest")
M._HS_AI_SUGGEST_ON = False
AI.ai_available, AI.ai_chat = _av, _ch
check("8 스위치 — 켜면 원래 길(여기선 「AI 미설정」 안내)로 간다 = 끄기는 스위치 하나 · 다시 끔",
      r2.json().get("error", "").startswith("AI 미설정") and called == ["available"] and M._HS_AI_SUGGEST_ON is False, (r2.text[:200], called))

# ─── 한 줄 저장 ───
with D.db_session() as c:
    pid = c.execute("SELECT id FROM export_hs_dict WHERE part_key='K-PLAIN'").fetchone()[0]
got = []
for want in ("AI", "CONFIRMED", "PENDING", ""):          # 마지막은 확정으로 끝낸다(아래 📌 남는 수에 안 섞이게)
    rr = quiet(cl.post, "/export/hs-dict/%d/save" % pid, data={"hs_code": "12345678", "vn_name": "VN K-PLAIN", "origin": "", "status": want})
    with D.db_session() as c:
        got.append((rr.json().get("ok"), c.execute("SELECT status FROM export_hs_dict WHERE id=?", (pid,)).fetchone()[0]))
check("9 한 줄 저장 — AI 로 보내면 확인 대기 · 확정은 확정 · 확인 대기는 확인 대기 · 빈 값은 전처럼 확정",
      got == [(True, "PENDING"), (True, "CONFIRMED"), (True, "PENDING"), (True, "CONFIRMED")], got)

# ─── HS 사전 화면 ───
pg = quiet(cl.get, "/export/hs-dict").text
check("10 HS 사전 화면(AI 줄 없음) — 안내 「AI 추정은 보류」 · AI 칸 없음 · 고르기에 AI 없음 · 확인 대기 칸은 그대로",
      "AI 추정은 보류</b>(대표 10-28)" in pg and 'href="/export/hs-dict?status=AI' not in pg and '<option value="AI"' not in pg
      and 'href="/export/hs-dict?status=PENDING' in pg, [x for x in ('status=AI', '<option value="AI"') if x in pg])
with D.db_session() as c:
    c.execute("INSERT INTO export_hs_dict(part_key,model,vn_name,hs_code,status,seen_count,note) VALUES('K-LEGACY-AI','옛 AI','x','85365099','AI',0,'AI 추정 — 검토 필요')")
pg = quiet(cl.get, "/export/hs-dict").text
check("11 남은 AI 줄이 있으면 — AI 칸(1)이 보이고 그 줄만 고르기에 「AI 추정」(지금 값으로 선택됨) · 다른 줄엔 없음",
      'href="/export/hs-dict?status=AI">' in pg and re.search(r'AI 추정 <b>1</b>', pg) is not None
      and pg.count('<option value="AI"') == 1 and '<option value="AI" selected>' in pg, pg.count('<option value="AI"'))
with D.db_session() as c:
    c.execute("DELETE FROM export_hs_dict WHERE part_key='K-LEGACY-AI'")

# ─── 📌 대상 · split ───
with D.db_session() as c:
    sm = M._hs_hist_summary(c)
lt = {x["part_key"]: x for x in sm["latest"]}
check("12 📌 대상 — 같은 날 두 HS(같은 인보이스 · 다른 인보이스) 2개 빠짐 · 옛날에만 갈린 것은 마지막 값으로 들어감 · 남는 확인 대기 1(이력 없음)",
      sorted(lt) == ["K-NORMAL", "K-OLD-SPLIT"] and lt["K-OLD-SPLIT"]["hs"] == "77777777" and lt["K-OLD-SPLIT"]["hs_change"]
      and not lt["K-NORMAL"]["hs_change"] and sm["n_split"] == 2 and sorted(x["part_key"] for x in sm["split"]) == ["K-SPLIT", "K-SPLIT-CONF"]
      and (sm["n_latest"], sm["n_latest_hs"], sm["rest_ai"], sm["rest_pending"]) == (2, 1, 0, 1),
      (sorted(lt), sm["n_split"], [x["part_key"] for x in sm["split"]], sm["n_latest"], sm["n_latest_hs"], sm["rest_ai"], sm["rest_pending"]))
pg = quiet(cl.get, "/export/hs-fill").text
check("13 자동 채움 화면(📌 2개) — 같은 날 두 HS 안내 2개 · 그 규격으로 가는 고리 · AI 추정 고리 없음 · 이력 없는 확인 대기 1",
      "📌 HS 사전을 최근 수출 값으로 맞출 규격 2개" in pg and "⚠ 같은 날 수출에서 HS 가 둘로 적힌 규격 2개는 이 단추가 고르지 않습니다" in pg
      and 'href="/export/hs-dict?q=K-SPLIT">K-SPLIT 모델</a>' in pg and 'href="/export/hs-dict?q=K-SPLIT-CONF">K-SPLIT-CONF 모델</a>' in pg
      and 'status=AI">AI 추정' not in pg and '이력이 없는 <a href="/export/hs-dict?status=PENDING">확인 대기 1</a>개는 이 단추로 정하지 못합니다' in pg,
      [x for x in ("맞출 규격 2개", "HS 가 둘로 적힌 규격 2개", "q=K-SPLIT", "확인 대기 1</a>") if x not in pg])
ap = quiet(cl.post, "/export/hs-fill/hist/apply-latest", json={"expect": 2}).json()
with D.db_session() as c:
    st = {r[0]: (r[1], r[2]) for r in c.execute("SELECT part_key, hs_code, status FROM export_hs_dict")}
check("14 확정 — 2개만(HS 바뀜 1 · 확정만 1) · 같은 날 두 HS 2개는 그대로(확인 대기 39259000 · 확정 11111111)",
      ap.get("ok") and (ap.get("applied"), ap.get("hs_changed"), ap.get("status_only")) == (2, 1, 1)
      and st["K-OLD-SPLIT"] == ("77777777", "CONFIRMED") and st["K-NORMAL"] == ("88888888", "CONFIRMED")
      and st["K-SPLIT"] == ("39259000", "PENDING") and st["K-SPLIT-CONF"] == ("11111111", "CONFIRMED"), (ap, st))
pg = quiet(cl.get, "/export/hs-fill").text
check("15 확정 뒤 화면 — 「아래 ⚠ 2개 말고 모두 … 확정돼 있습니다」 · 그 2개 안내 · 📌 칸 없음",
      "✅ HS 사전에서 지난 수출 이력이 있는 규격은 아래 ⚠ 2개 말고 모두 최근 수출 값으로 확정돼 있습니다" in pg
      and "⚠ 같은 날 수출에서 HS 가 둘로 적힌 규격 2개는 「최근 수출 값으로 확정」이 고르지 않습니다" in pg
      and 'id="hfLatest"' not in pg, [x for x in ("아래 ⚠ 2개 말고", "「최근 수출 값으로 확정」이 고르지") if x not in pg])

print()
print("결과: %d개 중 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
