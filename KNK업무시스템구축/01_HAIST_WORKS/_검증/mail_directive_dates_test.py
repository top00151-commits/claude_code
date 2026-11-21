# -*- coding: utf-8 -*-
"""메일 「나」 묶음 — 사내 지시 말투(3-1) · 본문 날짜 → 🚩 기한(2-1) (대표 2026-11-21 「다음 진행해」).
운영 무접촉 · 임시 DB(knk_mdd_*) · 가짜 사람·가짜 문장만.

증명할 것
  ① 지시 말투: 지난 점검에서 놓친 사내 지시 7문장 포함 12문장 모두 「회신 필요」
     · 사내에서 한 일을 알리는 말(보고 드립니다·진행 중입니다·처리했습니다…)·인사말(좋은 하루 보내세요)은 안 잡음
     · 바깥(광고) 「신청하세요」는 지시 규칙을 안 씀 · 「내일 9시까지」도 급함
  ② 본문 날짜: 받은 날 기준(내일·다음 주 화요일·금요일·25일·11/25(화)·11월 28일·2026.12.03·Nov 30·by Friday·기한: 12/5)
     · 기한 말(까지·마감·by…)이 붙은 것을 먼저 · 적힌 요일이 달력과 다르면 알림 · 지난 날짜·인사말·분수·버전 빼기 · 최대 3개
     · 12월 메일의 「1/5」 = 다음 해
  ③ 메일 보기: 📅 띠 · 「🚩 기한으로」 → 기존 🚩 기한 길로 저장 → 「✓ 🚩 기한」 · 보낸 메일·인용(옛 글)은 안 봄 · 남의 메일은 404
  ④ 파이썬 3.8 문법
"""
import ast
import io
import os
import sys
import tempfile
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
os.environ["KNK_RUN_MAIL_FETCH"] = "0"

_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mdd_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_reply as R
    from app import mail_dates as D
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:500])


print("① 사내 지시 말투")
BOSS = "boss@knknara.co.kr"
POS = ["금요일까지 견적 자료 정리해서 제출 바랍니다.", "다음 주 월요일 회의 전까지 준비하세요.", "이 건 진행 바랍니다.",
       "고객사 방문 일정 잡아 보고할 것.", "내일 오전까지 보고해 주세요.", "첨부 도면 검토 후 의견 주세요.",
       "샘플 일정 다음 주 화요일 가능합니다. 확인 부탁드립니다.", "11/25까지 회신 부탁드립니다.",
       "김 사원, 이거 오늘 중으로 처리해.", "자료 챙겨서 내일 오전 9시까지 가져와요.", "확인했으면 답장 주세요",
       "좋은 하루 보내세요. 견적은 내일까지 보내 주세요."]
miss = [s for s in POS if not R.assess(subject="업무 지시", body=s, from_email=BOSS)[0]]
check("지시 12문장 모두 회신 필요(지난번 7개 놓침)", not miss, miss)
lv, why = R.assess(subject="업무", body="이 건 진행 바랍니다.", from_email=BOSS)
check("이유에 「사내 지시」 표시", lv == 1 and why and why[0].startswith("사내 지시"), why)
lv, why = R.assess(subject="업무", body="자료 챙겨서 내일 오전 9시까지 가져와요.", from_email=BOSS)
check("「내일 오전 9시까지」 = 급함(높음)", lv == 2 and any("급함" in x for x in why), why)
NEG = ["주간 업무 보고 드립니다.", "A건은 현재 진행 중입니다.", "어제 요청하신 건 처리했습니다.", "견적서 작성 완료하였습니다.",
       "준비 완료되었습니다.", "검토 결과 공유합니다.", "오늘 출장 다녀오겠습니다.", "회의록 정리해서 올렸습니다.",
       "감사합니다. 수고하세요.", "좋은 하루 보내세요.", "즐거운 주말 보내세요~", "감기 조심하시고 건강 챙기세요."]
bad = [s for s in NEG if R.assess(subject="업무", body=s, from_email="kim@knknara.co.kr")[0]]
check("사내 알림·인사말 12문장은 안 잡음", not bad, bad)
bad = [s for s in ("지금 바로 신청하세요!", "무료 체험 등록하세요", "이번 기회를 놓치지 마세요. 확인하세요")
       if R.assess(subject="안내", body=s, from_email="news@shop-demo.example")[0]]
check("바깥 메일엔 지시 규칙 안 씀(광고 「~하세요」)", not bad, bad)
check("사내 주소 구분", R._is_internal("A@KNKNARA.CO.KR") and not R._is_internal("a@knknara.co.kr.evil-demo.example")
      and not R._is_internal(""), "")
check("인용(옛 글) 속 지시는 안 봄", not R.assess(subject="RE: 업무", body="네 알겠습니다.\n\n-----Original Message-----\nFrom: 팀장\n제출 바랍니다.",
                                           from_email="kim@knknara.co.kr")[0])

print("\n② 본문 날짜")
B = date(2026, 11, 21)   # 토요일


def one(t, base=B, today=None):
    r = D.find(t, base, today)
    return r[0] if r else {}


cases = [
    ("다음 주 화요일까지 견적 부탁드립니다.", "2026-11-24", True),
    ("금요일까지 보내 주세요", "2026-11-27", True),
    ("25일까지 제출 바랍니다", "2026-11-25", True),
    ("내일 오전까지 보고해 주세요", "2026-11-22", True),
    ("내일 9시까지 가져와요", "2026-11-22", True),
    ("오늘 중으로 처리해", "2026-11-21", True),
    ("11/25(수)까지", "2026-11-25", True),
    ("11월 28일 납품 예정입니다", "2026-11-28", False),
    ("2026.12.03 출하 예정", "2026-12-03", False),
    ("2026-11-27(금)까지", "2026-11-27", True),
    ("Delivery: Nov 30th", "2026-11-30", False),
    ("Please confirm by Friday.", "2026-11-27", True),
    ("기한: 12/5", "2026-12-05", True),
    ("납기 12.05 확정", "2026-12-05", True),
    ("다음 주 중으로 처리 바랍니다", "2026-11-27", True),
]
for t, want, dl in cases:
    r = one(t)
    check("%s → %s%s" % (t, want, " (기한)" if dl else ""), r.get("date") == want and r.get("dl") == dl, r)
r = one("11/25(화) 오전까지 회신 바랍니다")
check("적힌 요일이 달력과 다르면 알림(11/25 는 수요일)", r.get("date") == "2026-11-25" and r.get("wd_bad") == "화" and r.get("label") == "11/25(수)", r)
check("요일이 맞으면 알림 없음", one("11/25(수)까지").get("wd_bad") == "")
for t in ("오늘도 좋은 하루 되세요", "버전 1.2 / 수량 1/2 / 2.5mm", "도면 rev 3.1 참고", "가격 12/5 할인 아님 비율 3/4", "Sent: Mon, 17 Nov 2026",
          "매일 수고 많으십니다"):
    rr = D.find(t, B)
    check("안 잡음: %s" % t, rr == [] or (t.startswith("가격") and all(x["date"] != "2026-03-04" for x in rr)), rr)
check("지난 날짜는 뺌(오늘 기준)", D.find("11/20(금)까지 보내 주세요", B, date(2026, 11, 21)) == [])
check("「내일」은 받은 날 기준(11/18 받은 메일 → 11/19)", one("내일 오전까지 회신 바랍니다", date(2026, 11, 18), date(2026, 11, 18)).get("date") == "2026-11-19")
check("12월 메일의 「1/5(화)까지」 = 다음 해", one("1/5(화)까지 보내 주세요", date(2026, 12, 28), date(2026, 12, 28)).get("date") == "2027-01-05")
many = D.find("다음 주 화요일까지 견적, 11월 28일 납품, 12/3(목) 출하, 12월 10일 회의, 12월 11일 점검", B)
check("최대 3개 · 기한 말 붙은 것이 먼저", len(many) == 3 and many[0]["date"] == "2026-11-24" and many[0]["dl"], many)
check("같은 날짜 두 번은 한 번만", len(D.find("11/25(수)까지, 다시 말해 11월 25일", B)) == 1)
check("빈 글·이상한 값에도 죽지 않음", D.find("", B) == [] and D.find(None, B) == [] and D.find("13/45(화)까지 2026-02-30", B) == [])

print("\n③ 메일 보기")
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id IN ('newbie','other')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9821,'newbie','시험신입','member',1,'x','newbie@knknara.co.kr')")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(9822,'other','시험선배','member',1,'x','senior@knknara.co.kr')")

    def put(uid, direction, frm, subj, body):
        c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_deleted, received_at) "
                  "VALUES(?,?,?,?,?,?,?,0,datetime('now','localtime'))", (uid, direction, frm, "가짜", "newbie@knknara.co.kr", subj, body))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]
    M_IN = put(9821, "in", BOSS, "견적 자료", "자료는 다음 주 화요일까지 정리해서 제출 바랍니다.\n수고하세요.")
    M_Q = put(9821, "in", "kim@knknara.co.kr", "RE: 견적", "네 알겠습니다.\n\n-----Original Message-----\nFrom: 팀장\n다음 주 화요일까지 제출 바랍니다.")
    M_OUT = put(9821, "out", "newbie@knknara.co.kr", "보고", "다음 주 화요일까지 보내 드리겠습니다.")
    M_OTHER = put(9822, "in", BOSS, "선배 메일", "다음 주 화요일까지 제출 바랍니다.")

ME = {"id": 9821, "role": "member", "name": "시험신입", "login_id": "newbie", "email": "newbie@knknara.co.kr", "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
off = 9
today = m._mail_local_today(off)
with _db.db_session() as c:
    mm = dict(c.execute("SELECT * FROM mail_messages WHERE id=?", (M_IN,)).fetchone())
want = D.find("자료는 다음 주 화요일까지", date.fromisoformat(today), date.fromisoformat(today))
want_date = want[0]["date"] if want else ""
for path in ("/mail/%d" % M_IN, "/mail/%d/pane" % M_IN):
    r = k.get(path)
    check("%s 📅 띠 · 「🚩 기한으로」 단추" % path, r.status_code == 200 and 'id="mvDates"' in r.text and ("mvFollow('flag','%s')" % want_date) in r.text,
          (r.status_code, r.text[:200]))
r = k.get("/mail/%d/pane" % M_IN)
check("회신 필요 띠에 「사내 지시」", "사내 지시" in r.text, "")
r = k.get("/mail/%d/pane" % M_Q)
check("인용(옛 글)의 날짜는 안 띄움", r.status_code == 200 and 'id="mvDates"' not in r.text, r.status_code)
r = k.get("/mail/%d/pane" % M_OUT)
check("보낸 메일엔 안 띄움", r.status_code == 200 and 'id="mvDates"' not in r.text, r.status_code)
r = k.get("/mail/%d/pane" % M_OTHER)
check("남의 메일은 404(그대로)", r.status_code == 404, r.status_code)
r = k.post("/mail/flag", data={"ids": str(M_IN), "due": want_date})
check("「🚩 기한으로」 = 기존 기한 길로 저장", r.status_code == 200 and r.json().get("due") == want_date, r.text[:200])
r = k.get("/mail/%d/pane" % M_IN)
check("저장 뒤 「✓ 🚩 기한」 표시", "✓ 🚩 기한" in r.text and ("mvFollow('flag','%s')" % want_date) not in r.text, "")
info = m._mail_follow_info(None, ME, {"direction": "in", "received_at": "깨진 값", "body_text": "내일까지 보내 주세요", "subject": ""})
check("받은 시각이 깨져도 메일 보기는 그대로(빈 목록 또는 오늘 기준)", isinstance(info.get("dates"), list), info)

print("\n④ 문법·화면")
body = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_view_body.html"), encoding="utf-8").read()
check("화면 조각 한 곳(전체·창·옆 칸 같이)", body.count('id="mvDates"') == 1 and "d.wd_bad" in body)
sty = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_view_styles.html"), encoding="utf-8").read()
thm = io.open(os.path.join(ROOT, "app", "templates", "_v5_partials", "mail_theme.html"), encoding="utf-8").read()
check("꾸밈 · 어두운 화면 · 인쇄 때 숨김", ".mv-dates{" in sty and "@media print{.mv-dates{display:none}}" in sty and '.mv-dates{ background' in thm)
for p in ("app/mail_dates.py", "app/mail_reply.py", "app/main.py"):
    try:
        ast.parse(io.open(os.path.join(ROOT, p), encoding="utf-8").read(), feature_version=(3, 8))
        ok = True
    except SyntaxError as e:
        ok = e
    check("파이썬 3.8 문법: %s" % p, ok is True, ok)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
