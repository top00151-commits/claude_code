# -*- coding: utf-8 -*-
"""z1191z109 시험 — 영업 기회: 담당 = 기술영업팀 · 취소 상태 · 실주·취소 이유 · 미팅·제안서 참여자 · 결과 비율
(대표 11-22 「영업담당은 본사는 기술영업팀 인원만」 · 「수주 성공한거 수주 성공못한거 취소된거 … 비율」
 · 「초기 미팅 및 제안서 작성에 참여한 부서 및 담당자 기록」 → 취소 새로 · 이유 고르기 · 베트남 칸 빼기 · 참여자 = 전 직원)
  §1 영업 담당 목록 = 기술영업팀만 · 베트남 칸 없음 · 지금 담당이 밖이면 그 이름만 덧붙임
  §2 참여자 고르기(전 직원 · 베트남 포함 · 이름 직책 부서) · 저장 · 빼기 · 없는 번호 버림 · 참여 칸 없는 저장은 그대로
  §3 취소 상태 · 이유(실주·취소일 때만 남음 · 목록 밖 값 버림) · 다음 할 일 「—」
  §4 결과 비율(수주·실주·취소·진행 · 끝난 것 중 % · 단계 흐름 · 제안서 낸 건 수주율 · 담당·사업부·참여 부서·이유별)
  §5 비율 칸 숫자 → 목록 거르기 · 기간(올해·작년·전체) · 목록 참여 칸 · 결과 표시
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
os.environ["KNK_SSO_SERVICE_KEY"] = "z1191z109-test-only-not-a-real-key"   # 시험용 가짜 값

import app.database as D                                   # noqa: E402

TMP = tempfile.mkdtemp(prefix="knk_z1191z109_")
_REAL = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "t.db")
assert D.DB_PATH != _REAL
with contextlib.redirect_stdout(io.StringIO()):
    D.init_db()
from app.migrations.m_z416_sales_opportunity import migrate as _m416   # noqa: E402
from app.migrations.m_z421_opp_dept_request import migrate as _m421    # noqa: E402
_m416(D.DB_PATH)
_m421(D.DB_PATH)
from datetime import date as _d                            # noqa: E402
Y = _d.today().year
with D.db_session() as conn:
    have = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
    for col, typ in [("employee_no", "TEXT"), ("password_version", "INTEGER DEFAULT 1"), ("must_change_pw", "INTEGER DEFAULT 0"),
                     ("entity", "TEXT"), ("rank", "TEXT")]:
        if col not in have:
            conn.execute("ALTER TABLE users ADD COLUMN %s %s" % (col, typ))
    tcols = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
    for tid, code, nm in ((1, "01", "기술영업팀"), (4, "04", "설계팀"), (20, "20", "소프트웨어팀"), (12, "12", "베트남법인"), (15, "15", "총괄")):
        if conn.execute("SELECT 1 FROM teams WHERE id=?", (tid,)).fetchone():
            conn.execute("UPDATE teams SET name=? WHERE id=?", (nm, tid))
        elif "code" in tcols:
            conn.execute("INSERT INTO teams (id, code, name) VALUES (?, ?, ?)", (tid, code, nm))
        else:
            conn.execute("INSERT INTO teams (id, name) VALUES (?, ?)", (tid, nm))

    def user(emp, name, team, ent="KOR", rank="프로", role="member", active=1):
        conn.execute("INSERT INTO users (name, role, employee_no, login_id, password, is_active, password_version, team_id, entity, rank, "
                     "can_view_sales, can_use_sales, can_view_logistics, can_use_logistics) "
                     "VALUES (?, ?, ?, ?, 'sso_only_no_local_password', ?, 1, ?, ?, ?, 1, 1, 1, 1)",
                     (name, role, emp, emp, active, team, ent, rank))
        return conn.execute("SELECT id FROM users WHERE employee_no=?", (emp,)).fetchone()[0]
    S1 = user("Z901", "가상영업하나", 1)
    S2 = user("Z902", "가상영업둘", 1)
    DS = user("Z903", "가상설계", 4, rank="책임")
    VN = user("Z904", "가상베트남", 20, ent="VN", rank="Engineer")
    BOSS = user("Z905", "가상대표", 15, role="ceo", rank="대표")
    OLD = user("Z906", "가상퇴사영업", 1, active=0)
    U = {r[0]: dict(r) for r in []}
    CEO = dict(conn.execute("SELECT * FROM users WHERE id=?", (BOSS,)).fetchone())
    # 기존 영업 기회(담당 = 대표 · 기술영업팀 밖)
    conn.execute("INSERT INTO sales_opportunities (opp_no, title, owner_user_id, stage, status, biz_div) "
                 "VALUES ('OPP-0000-001', '가상 옛 기회', ?, '미팅', 'active', 'T')", (BOSS,))
    OLD_OPP = conn.execute("SELECT id FROM sales_opportunities WHERE opp_no='OPP-0000-001'").fetchone()[0]

import app.main as M                                        # noqa: E402
from fastapi.testclient import TestClient                  # noqa: E402

M.get_user = lambda request: CEO
cl = TestClient(M.app)
OK = FAIL = 0


def check(label, cond, got=None):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", label)
    else:
        FAIL += 1
        print("  ❌", label, "" if got is None else ("→ %r" % (got,))[:500])


def owner_select(h):
    i = h.find('name="owner_user_id"')
    return h[i:h.find("</select>", i)]


def fd(pairs):
    """[(이름, 값)…] → httpx 가 받는 {이름: [값…]}"""
    out = {}
    for k, v in pairs:
        out.setdefault(k, []).append(v)
    return out


def create(title, **kw):
    data = {"title": title, "biz_div": kw.pop("biz", "T"), "owner_user_id": str(kw.pop("owner", S1)), "stage": kw.pop("stage", "미팅"),
            "status": kw.pop("status", "active"), "currency": "KRW", "people_form": "1"}
    for k in ("meeting_done", "proposal_done", "quotation_done"):
        if kw.pop(k, 0):
            data[k] = "1"
    for k in ("close_reason", "close_memo"):
        if k in kw:
            data[k] = kw.pop(k)
    mp, pp = kw.pop("mp", []), kw.pop("pp", [])
    body = list(data.items()) + [("meeting_people", str(x)) for x in mp] + [("proposal_people", str(x)) for x in pp]
    r = cl.post("/sales/opportunities", data=fd(body), follow_redirects=False)
    m = re.search(r"/sales/opportunities/(\d+)", r.headers.get("location", ""))
    return int(m.group(1)) if m else None


def opp(oid):
    with D.db_session() as c:
        return dict(c.execute("SELECT * FROM sales_opportunities WHERE id=?", (oid,)).fetchone())


def people(oid):
    with D.db_session() as c:
        return sorted((r[0], r[1]) for r in c.execute("SELECT step, user_id FROM sales_opp_people WHERE opp_id=?", (oid,)).fetchall())


print("§1 영업 담당 목록")
h = cl.get("/sales/opportunities/new").text
sel = owner_select(h)
check("기술영업팀 재직자 둘만(설계·베트남·대표·퇴사자 없음)", "가상영업하나" in sel and "가상영업둘" in sel and "가상설계" not in sel
      and "가상베트남" not in sel and "가상대표" not in sel and "가상퇴사영업" not in sel, sel[:400])
check("베트남법인 칸 없음 · 기술영업팀 묶음", "베트남법인" not in sel and 'optgroup label="기술영업팀"' in sel)
h = cl.get("/sales/opportunities/%d" % OLD_OPP).text
sel = owner_select(h)
check("지금 담당이 기술영업팀 밖이면 그 이름만 덧붙여 고른 채로", "가상대표 (지금 담당 · 기술영업팀 아님)" in sel and 'value="%d" selected' % BOSS in sel, sel[-300:])

print("§2 참여자")
h = cl.get("/sales/opportunities/new").text
check("미팅·제안서 참여 칸 둘 + 숨은 표시", h.count('class="op-ppl" data-step=') == 2 and 'name="people_form" value="1"' in h)
check("고르기 = 전 직원(베트남 포함) · 법인·부서 묶음 · 이름 직책 부서",
      'optgroup label="베트남 · 소프트웨어팀"' in h and 'optgroup label="본사 · 설계팀"' in h and "가상설계 책임 설계팀" in h
      and "가상베트남" in h and "가상퇴사영업" not in h.split('class="op-padd"')[1])
A = create("가상 A", mp=[S1, DS], pp=[S1, VN, 999999], meeting_done=1, proposal_done=1)
check("저장: 미팅 = 영업하나·설계 · 제안서 = 영업하나·베트남 · 없는 번호 버림",
      people(A) == sorted([("meeting", S1), ("meeting", DS), ("proposal", S1), ("proposal", VN)]), people(A))
h = cl.get("/sales/opportunities/%d" % A).text
check("상세에 칩(이름 직책 부서)", "가상설계 책임 설계팀<input type=\"hidden\" name=\"meeting_people\" value=\"%d\">" % DS in h)
cl.post("/sales/opportunities/%d/edit" % A, data=fd([("title", "가상 A"), ("status", "active"), ("stage", "제안"), ("owner_user_id", str(S1)), ("biz_div", "T"),
                                                  ("people_form", "1"), ("meeting_people", str(S1)), ("proposal_people", str(VN))]))
check("고치기: 뺀 사람은 지워짐", people(A) == sorted([("meeting", S1), ("proposal", VN)]), people(A))
cl.post("/sales/opportunities/%d/edit" % A, data=fd([("title", "가상 A"), ("status", "active"), ("stage", "제안"), ("owner_user_id", str(S1)), ("biz_div", "T")]))
check("참여 칸 없는 저장(people_form 없음)은 그대로", people(A) == sorted([("meeting", S1), ("proposal", VN)]), people(A))

print("§3 취소 상태 · 이유")
h = cl.get("/sales/opportunities/new").text
check("상태에 「취소」 · 이유 칸(처음엔 숨김) · 이유 다섯", '<option value="cancel" >취소</option>' in h and 'id="oppCloseBox" hidden' in h
      and all(">%s</option>" % r in h for r in ("가격", "납기", "경쟁사", "고객 사정", "기타")))
B = create("가상 B", status="cancel", close_reason="고객 사정", close_memo="고객 투자 보류", proposal_done=1)
o = opp(B)
check("취소 + 이유 저장", o["status"] == "cancel" and o["close_reason"] == "고객 사정" and o["close_memo"] == "고객 투자 보류", o)
h = cl.get("/sales/opportunities/%d" % B).text
check("상세: 취소 고른 채 · 이유 칸 보임", "<option value=\"cancel\" selected>취소</option>" in h and 'id="oppCloseBox">' in h and ">고객 사정</option>" in h)
cl.post("/sales/opportunities/%d/edit" % B, data={"title": "가상 B", "owner_user_id": str(S1), "biz_div": "T", "status": "active", "close_reason": "가격"})
check("진행중으로 바꾸면 이유 지움", opp(B)["close_reason"] is None)
cl.post("/sales/opportunities/%d/edit" % B, data={"title": "가상 B", "owner_user_id": str(S1), "biz_div": "T", "status": "lost", "close_reason": "아무말", "proposal_done": "1"})
check("목록 밖 이유 버림(실주 · 이유 없음)", opp(B)["status"] == "lost" and opp(B)["close_reason"] is None)
cl.post("/sales/opportunities/%d/edit" % B, data={"title": "가상 B", "owner_user_id": str(S1), "biz_div": "T", "status": "cancel", "close_reason": "고객 사정", "proposal_done": "1"})
check("다음 할 일 「—」(취소)", M._opp_next_action(opp(B)) == "—")
h = cl.get("/sales/opportunities/%d" % B).text
check("빈 칸(모델명·메모·비고)에 「None」 글자 안 보임(원래부터 있던 것 고침)", 'value="None"' not in h and ">None</textarea>" not in h)

print("§4 결과 비율")
C1 = create("가상 C1", status="won", stage="수주확정", meeting_done=1, proposal_done=1, quotation_done=1, owner=S2, biz="M", mp=[DS])
C2 = create("가상 C2", status="lost", close_reason="가격", meeting_done=1, proposal_done=1, owner=S2, biz="M")
C3 = create("가상 C3", status="hold", meeting_done=1)
C4 = create("가상 C4", stage="실주", meeting_done=1, owner=S2)      # 단계 실주 = 실주(이유 안 적음)
with D.db_session() as c:   # 부서 요청(취소 아님) = 참여 부서 · 구성원
    c.execute("INSERT INTO opp_dept_requests (opp_id, team_id, status) VALUES (?, 20, 'assigned')", (C1,))
    rid = c.execute("SELECT id FROM opp_dept_requests WHERE opp_id=?", (C1,)).fetchone()[0]
    c.execute("INSERT INTO opp_request_members (request_id, user_id, role_in_req) VALUES (?, ?, 'pm')", (rid, VN))
    c.execute("INSERT INTO opp_dept_requests (opp_id, team_id, status) VALUES (?, 4, 'canceled')", (C2,))   # 취소된 요청은 안 셈
    c.execute("UPDATE sales_opportunities SET created_at=? WHERE id=?", ("%d-03-01 10:00:00" % (Y - 1), C4))   # 작년 등록
# 올해: OLD(진행) · A(진행) · B(취소 · 고객 사정) · C1(수주) · C2(실주 · 가격) · C3(보류)   작년: C4(실주)
st = cl.get("/sales/opportunities").text
with D.db_session() as c:
    allr = [dict(r) for r in c.execute("SELECT o.*, u.name AS owner_name FROM sales_opportunities o LEFT JOIN users u ON u.id=o.owner_user_id").fetchall()]
    ppl = M._z109_people_map(c)
z = M._z109_stats(allr, ppl, "y")
k = z["k"]
check("올해 6건: 수주 1 · 실주 1 · 취소 1 · 진행 2 · 보류 1", (k["n"], k["won"], k["lost"], k["cancel"], k["active"], k["hold"]) == (6, 1, 1, 1, 2, 1), k)
check("끝난 3건 중 수주율 33%", k["fin"] == 3 and k["rate"] == 33 and k["won_p"] == 33)
f = z["fun"]
check("단계 흐름: 등록 6 · 미팅 3 · 제안서 3 · 견적 1 · 수주 1(A 는 고치기에서 완료 칸 뺌)", (f["n"], f["meet"], f["prop"], f["quote"], f["won"]) == (6, 3, 3, 1, 1), f)
check("제안서 낸 3건(B·C1·C2): 수주 1 · 실주 1 · 취소 1 → 33%", (z["prop"]["n"], z["prop"]["won"], z["prop"]["lost"], z["prop"]["cancel"], z["prop"]["rate"]) == (3, 1, 1, 1, 33), z["prop"])
ow = {d["label"]: (d["n"], d["won"], d["rate"]) for d in z["owners"]}
check("담당별: 영업둘 2건 수주 1(50%) · 영업하나 3건 · 대표 1건", ow.get("가상영업둘") == (2, 1, 50) and ow.get("가상영업하나", (0,))[0] == 3 and ow.get("가상대표", (0,))[0] == 1, ow)
bz = {d["key"]: (d["n"], d["rate"]) for d in z["bizs"]}
check("사업부별: 자동화 2건 50% · 검사기 4건", bz.get("M") == (2, 50) and bz.get("T", (0,))[0] == 4, bz)
tm = {d["key"]: (d["n"], d["won"]) for d in z["teams"]}
check("참여 부서별: 설계팀 1(C1 · A 는 뺐음) · 소프트웨어팀 2(A 베트남 참여 · C1 부서 요청) · 기술영업팀 따로 안 셈 · 취소된 요청 안 셈 · 없음 4",
      tm.get("설계팀") == (1, 1) and tm.get("소프트웨어팀") == (2, 1) and "기술영업팀" not in tm and tm.get("none", (0,))[0] == 4, tm)
rs = {d["key"]: (d["lost"], d["cancel"]) for d in z["reasons"]}
check("이유별: 가격 실주 1 · 고객 사정 취소 1", rs == {"가격": (1, 0), "고객 사정": (0, 1)}, rs)
check("화면: 결과 비율 칸 · 수주 성공 1건 · 33%", "📊 결과 비율" in st and "수주 성공</div><div class=\"n\">1건 · 33%" in st and "끝난 3건 중 비율" in st)
check("화면: 표 넷(담당·사업부·참여 부서·이유)", all(x in st for x in ("담당별", "사업부별", "참여 부서별", "실주·취소 이유")))
zp = M._z109_stats(allr, ppl, "py")
check("작년 = C4(단계 실주 · 이유 안 적음)", zp["k"]["n"] == 1 and zp["k"]["lost"] == 1 and zp["reasons"][0]["label"] == "이유 안 적음", zp["k"])

print("§5 거르기 · 목록")
h = cl.get("/sales/opportunities?rp=y&res=cancel").text
check("취소만: 가상 B 하나 · 거르기 띠", ">가상 B</a>" in h and ">가상 A</a>" not in h and "결과 = 취소" in h and "✕ 거르기 풀기" in h)
h = cl.get("/sales/opportunities?rp=y&team=" + "소프트웨어팀").text
check("참여 부서 = 소프트웨어팀: A · C1(수주도 보임)", ">가상 A</a>" in h and ">가상 C1</a>" in h and ">가상 B</a>" not in h)
h = cl.get("/sales/opportunities?rp=y&owner=%d" % S2).text
check("담당 = 영업둘(올해): C1·C2 · 작년 C4 안 보임", ">가상 C1</a>" in h and ">가상 C2</a>" in h and ">가상 C4</a>" not in h and "담당 = 가상영업둘" in h)
h = cl.get("/sales/opportunities?rp=y&reason=none").text
check("이유 안 적음(올해) = 없음", ">가상 C" not in h and ">가상 B</a>" not in h)
h = cl.get("/sales/opportunities").text
check("기본 목록: 끝난 것(수주·실주·취소) 숨김 · 진행·보류만", ">가상 A</a>" in h and ">가상 C3</a>" in h and ">가상 B</a>" not in h and ">가상 C2</a>" not in h)
check("목록 참여 칸: A = 설계팀 아님(뺐음) · 소프트웨어팀 · 2명", re.search(r">가상 A</a>.*?<td class=\"op-ppl\">기술영업팀 · 소프트웨어팀 <span class=\"op-muted\">\(2명\)</span>", h, re.S) is not None)
h = cl.get("/sales/opportunities?closed=1").text
check("완료도 보기: 취소 표시 배지", '<span class="op-out cancel">취소</span>' in h)

print("\n결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
