# -*- coding: utf-8 -*-
"""메일 보내기 전 확인 — 신입사원 관점 가 묶음(대표 2026-11-21 「진행해」).
운영 무접촉 · 임시 DB(knk_mpre_*) · 가짜 사람·가짜 거래처·가짜 주소만.

증명할 것
  ① 다른 거래처 이름: 첨부 이름·제목·본문 → 받는 사람에 그 거래처 사람이 없으면 알림 · 있으면 조용
     · 긴 이름이 이김(「삼성전기」 안의 「삼성」은 따로 안 셈) · 영문 별칭(연락처 회사 이름) · 영문은 낱말 경계
     · 사내끼리는 알림 없음 · 우리 회사 이름은 안 찾음 · 쓰지 않는 거래처는 안 찾음 · 거래처 모르는 주소 안내
  ② 처음 보내는 주소: 회사 밖 · 내가 주고받은 적 없음 · 주소록(내가 볼 수 있는 것)·거래처 담당자에 없음 → 알림
     · 오타 회사 주소 / 같은 회사 비슷한 사람 → 「혹시 이 주소인가요?」 + 바꾸기 · 남의 개인 주소록은 안 봄
  입구: 로그인 필요 · 형식 오류 400 · 읽기만(표 안 바뀜) · 화면에 확인·바꾸기 연결 · 파이썬 3.8
"""
import ast
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

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
    _TMP = tempfile.mkdtemp(prefix="knk_mpre_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_precheck as pc
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


with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id IN ('newbie','other')")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(9811,'T9811','시험영업팀',3)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9811,'newbie','시험신입','member',1,'x','newbie@knknara.co.kr',9811)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9812,'other','시험선배','member',1,'x','senior@knknara.co.kr',9811)")
    cust = [(9801, "삼성전기"), (9802, "(주)드림텍"), (9803, "파트론"), (9804, "삼성"), (9805, "옛거래처"), (9806, "KNK VINA"),
            (9807, "가나정밀"), (9808, "다라정밀")]
    for cid, nm in cust:
        c.execute("INSERT INTO customers(id, name) VALUES(?,?)", (cid, nm))
    try:
        c.execute("UPDATE customers SET is_active=0 WHERE id=9805")
        INACTIVE_OK = True
    except Exception:
        INACTIVE_OK = False
    sc = [  # 이름, 주소, 회사, 거래처, 공개, 만든 사람
        ("박구매", "buyer@semco-demo.example", "Samsung Electro-Mechanics Co., Ltd.", 9801, "company", 9812),
        ("한드림", "han@dreamtech-demo.example", "Dreamtech Co., Ltd.", 9802, "company", 9812),
        ("오파트", "oh@partron-demo.example", "파트론", 9803, "company", 9812),
        ("비밀", "secret@hidden-demo.example", "숨은회사", None, "private", 9812),
        ("공용", "share@gana-demo.example", "가나정밀", 9807, "company", 9812),
        ("공용2", "share2@gana-demo.example", "다라정밀", 9808, "company", 9812),   # 같은 회사 주소가 두 거래처 → 회사 주소로는 안 묶음
        ("옛사람", "old@oldcust-demo.example", "옛거래처", 9805, "company", 9812),
    ]
    for nm, em, co, cid, vis, by in sc:
        c.execute("INSERT INTO shared_contacts(name, email, company, customer_id, visibility, created_by) VALUES(?,?,?,?,?,?)", (nm, em, co, cid, vis, by))
    c.execute("INSERT INTO customer_contacts(customer_id, role, name, email) VALUES(9803,'품질','품질담당','qa@partron-demo.example')")
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, received_at) "
              "VALUES(9811,'in','friend@vendor-demo.example','친구','newbie@knknara.co.kr','가짜','가짜',datetime('now','localtime'))")
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, cc, subject, body_text, received_at) "
              "VALUES(9811,'out','newbie@knknara.co.kr','시험신입','\"고객\" <client@client-demo.example>','cc1@client-demo.example','가짜','가짜',datetime('now','localtime'))")
    # 남의 메일함(선배) — 이 주소는 신입에게 「아는 주소」가 아님
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, received_at) "
              "VALUES(9812,'in','seniorfriend@vendor2-demo.example','선배친구','senior@knknara.co.kr','가짜','가짜',datetime('now','localtime'))")

ME = {"id": 9811, "role": "member", "name": "시험신입", "team_id": 9811, "team_name": "시험영업팀", "login_id": "newbie",
      "email": "newbie@knknara.co.kr", "lang": "ko"}


def run(**kw):
    with _db.db_session() as c:
        return pc.run(c, ME, **kw)


def kinds(ws, k):
    return [w for w in ws if w.get("kind") == k]


def snap():
    with _db.db_session() as c:
        out = {}
        for t in ("customers", "shared_contacts", "customer_contacts", "mail_messages", "users"):
            out[t] = [dict(r) for r in c.execute("SELECT * FROM %s ORDER BY id" % t).fetchall()]
        return json.dumps(out, ensure_ascii=False, default=str)


S0 = snap()

print("\n도움 함수")
check("회사 꾸밈말 빼기: (주)드림텍 → 드림텍", pc.norm_company("(주)드림텍") == "드림텍", pc.norm_company("(주)드림텍"))
check("회사 꾸밈말 빼기: Dreamtech Co., Ltd. → dreamtech", pc.norm_company("Dreamtech Co., Ltd.") == "dreamtech", pc.norm_company("Dreamtech Co., Ltd."))
check("회사 꾸밈말 빼기: 주식회사 삼성전기 → 삼성전기", pc.norm_company("주식회사 삼성전기") == "삼성전기")
check("편집 거리", pc.lev("dreamtech", "dreamtek") == 2 and pc.lev("han", "hon") == 1 and pc.lev("abc", "abc") == 0)
check("주소 뽑기: 이름 <주소> · 쉼표 · 중복 · 소문자", pc.parse_addrs('"가" <A@x-demo.example>, a@x-demo.example; b@y-demo.example') == ["a@x-demo.example", "b@y-demo.example"])
with _db.db_session() as c:
    CU = pc.customers(c)
check("거래처 별칭: 드림텍 + 연락처 회사 영문 이름 dreamtech", set(CU[9802]["aliases"]) == {"드림텍", "dreamtech"}, CU.get(9802))
check("우리 회사 이름(KNK VINA)은 찾지 않음", CU.get(9806, {}).get("aliases") == [], CU.get(9806))
if INACTIVE_OK:
    check("쓰지 않는 거래처는 빼기", 9805 not in CU, list(CU))

print("\n① 다른 거래처 이름")
w = run(to="newbie@knknara.co.kr, senior@knknara.co.kr", subject="삼성전기 견적 검토", own="삼성전기 견적 봐 주세요", att_names=["삼성전기_견적.xlsx"])
check("사내끼리 = 알림 없음(거래처 이야기는 정상)", w == [], w)
w = run(to="오파트 <oh@partron-demo.example>", subject="견적서 송부", own="견적서 보내드립니다.", att_names=["삼성전기_견적.xlsx"])
oc = kinds(w, "other_cust")
check("파트론에 「삼성전기_견적.xlsx」 → 알림 1건", len(oc) == 1 and "삼성전기" in oc[0]["t"], w)
check("찾은 곳 = 파일 이름 · 받는 회사 = 파트론", oc and any("파일 이름: 삼성전기_견적.xlsx" in x for x in oc[0]["who"]) and any("받는 회사: 파트론" in x for x in oc[0]["who"]), oc)
check("아는 주소라 「처음 보내는 주소」 없음", not kinds(w, "first"), w)
w = run(to="buyer@semco-demo.example", subject="[삼성전기] 11월 발주 확인", own="삼성전기 발주 건 확인했습니다.")
check("삼성전기 사람에게 삼성전기 이야기 = 조용 · 「삼성」(긴 이름 안)도 안 셈", w == [], w)
w = run(to="buyer@semco-demo.example", subject="확인", own="삼성 계열 일정과 함께 보겠습니다.")
check("「삼성」만 따로 쓰면 「삼성」 거래처로 알림", len(kinds(w, "other_cust")) == 1 and "삼성" in kinds(w, "other_cust")[0]["t"], w)
w = run(to="oh@partron-demo.example", subject="도면", own="도면입니다", att_names=["Dreamtech_drawing_rev2.pdf"])
oc = kinds(w, "other_cust")
check("영문 별칭: 「Dreamtech_drawing」 → (주)드림텍 알림", len(oc) == 1 and "(주)드림텍" in oc[0]["t"], w)
w = run(to="oh@partron-demo.example", subject="dreamtechnology 소개", own="")
check("영문은 낱말 경계(dreamtechnology 는 아님)", not kinds(w, "other_cust"), w)
w = run(to="qa@partron-demo.example", subject="파트론 품질", own="파트론 건")
check("거래처 담당자 표(customer_contacts) 주소도 그 거래처로 = 조용", w == [], w)
w = run(to="new@unknown-demo.example", subject="파트론 납기 회신", own="")
oc = kinds(w, "other_cust")
check("거래처 모르는 주소에 파트론 이야기 → 알림 + 「거래처를 모르는 주소」", len(oc) == 1 and any("거래처를 모르는 주소: new@unknown-demo.example" in x for x in oc[0]["who"]), w)
w = run(to="oh@partron-demo.example", subject="KNK VINA 출하", own="KNK VINA 로 갑니다")
check("우리 회사 이름은 알림 없음", not kinds(w, "other_cust"), w)
w = run(to="oh@partron-demo.example", subject="옛거래처 정리", own="")
if INACTIVE_OK:
    check("쓰지 않는 거래처 이름은 알림 없음", not kinds(w, "other_cust"), w)
w = run(to="oh@partron-demo.example", cc="buyer@semco-demo.example", subject="삼성전기·파트론 공동 일정", own="")
check("참조에 삼성전기 사람이 있으면 조용(받는사람·참조·숨은참조 모두 봄)", not kinds(w, "other_cust"), w)
w = run(to="oh@partron-demo.example", bcc="buyer@semco-demo.example", subject="삼성전기 건", own="")
check("숨은참조에 있어도 조용", not kinds(w, "other_cust"), w)
w = run(to="share@gana-demo.example", subject="가나정밀 견적", own="")
check("연락처 주소 정확 일치는 회사 주소가 두 거래처여도 그 거래처", not kinds(w, "other_cust"), w)
w = run(to="third@gana-demo.example", subject="가나정밀 견적", own="")
oc = kinds(w, "other_cust")
check("회사 주소가 두 거래처를 가리키면 추측 안 함 → 모르는 주소로 안내", len(oc) == 1 and any("거래처를 모르는 주소" in x for x in oc[0]["who"]), w)

print("\n② 처음 보내는 주소")
w = run(to="friend@vendor-demo.example", subject="가짜", own="")
check("내가 받은 메일 보낸 사람 = 아는 주소", not kinds(w, "first"), w)
w = run(to="client@client-demo.example", cc="CC1@client-demo.example", subject="가짜", own="")
check("내가 보낸 메일 받는사람·참조 = 아는 주소(크고 작은 글자 무시)", not kinds(w, "first"), w)
w = run(to="secret@hidden-demo.example", subject="가짜", own="")
check("남의 개인 주소록 주소는 모름 → 처음 주소 알림", len(kinds(w, "first")) == 1, w)
w = run(to="seniorfriend@vendor2-demo.example", subject="가짜", own="")
check("남의 메일함 주소는 모름(남의 메일함 안 봄) → 처음 주소 알림", len(kinds(w, "first")) == 1, w)
w = run(to="한드림 <han@dreamtek-demo.example>", subject="가짜", own="")
fi = kinds(w, "first")
check("오타 회사 주소 → 처음 주소 + 「혹시 han@dreamtech-demo.example (드림텍)」",
      len(fi) == 1 and any("han@dreamtech-demo.example" in x and "(주)드림텍" in x for x in fi[0]["who"]), w)
check("바꾸기 짝 = dreamtek → dreamtech", fi and {"from": "han@dreamtek-demo.example", "to": "han@dreamtech-demo.example"} in fi[0]["fix"], fi)
w = run(to="hon@dreamtech-demo.example", subject="가짜", own="")
fi = kinds(w, "first")
check("같은 회사 비슷한 사람(hon → han) 추천", fi and {"from": "hon@dreamtech-demo.example", "to": "han@dreamtech-demo.example"} in fi[0]["fix"], w)
w = run(to="zzz@totally-new-demo.example", subject="가짜", own="")
fi = kinds(w, "first")
check("비슷한 것 없으면 추천 없이 알림만", len(fi) == 1 and fi[0]["fix"] == [] and fi[0]["who"] == [], w)
w = run(to="newbie2@knknara.co.kr", subject="가짜", own="")
check("사내 주소는 처음이어도 알림 없음", w == [], w)
w = run(to=",".join("n%d@new%d-demo.example" % (i, i) for i in range(9)), subject="가짜", own="")
check("처음 주소 알림은 5건까지", len(kinds(w, "first")) == 5, len(w))

print("\n입구")
_U = {"v": dict(ME)}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
r = k.post("/api/mail/precheck", json={"to": "oh@partron-demo.example", "subject": "견적", "own": "", "att": ["삼성전기_견적.xlsx"]})
j = r.json() if r.status_code == 200 else {}
check("입구 200 · 알림 돌려줌", r.status_code == 200 and j.get("ok") and kinds(j.get("warns") or [], "other_cust"), (r.status_code, r.text[:300]))
r = k.post("/api/mail/precheck", content=b"not json", headers={"Content-Type": "application/json"})
check("형식 오류 400", r.status_code == 400, r.status_code)
r = k.post("/api/mail/precheck", json=["x"])
check("목록 모양도 400", r.status_code == 400, r.status_code)
r = k.post("/api/mail/precheck", json={"to": 123, "att": "x"})
check("칸 모양이 이상해도 죽지 않음(200 · 알림 없음)", r.status_code == 200 and r.json().get("warns") == [], r.text[:200])
_U["v"] = None
r = k.post("/api/mail/precheck", json={"to": "a@b-demo.example"})
check("로그인 안 하면 401", r.status_code == 401, r.status_code)
_U["v"] = dict(ME)
check("읽기만 — 거래처·주소록·메일·직원 표 그대로", snap() == S0)

print("\n화면")
html = io.open(os.path.join(ROOT, "app", "templates", "mail_compose.html"), encoding="utf-8").read()
check("보내기·예약 둘 다 서버 확인을 거침", html.count("cmpPre(r0, function(r){") == 2)
check("서버 확인 입구 · 4초 넘으면 건너뜀(막지 않음)", "/api/mail/precheck" in html and "}, 4000);" in html)
check("확인 창 그리기 한 곳(scItems) · 바꾸기 단추", html.count("scItems(r.warns)") == 2 and "cmpFixAddr(" in html)
check("대용량 링크 파일 이름도 넘김", "LARGE_NAMES[j.token]=file.name" in html and "LARGE_NAMES[t]" in html)
r = k.get("/mail/compose")
check("쓰기 화면 200", r.status_code == 200, r.status_code)

# 화면 스크립트 — 주소 바꾸기(swapAddr)를 실제로 돌려 봄(node 가 있을 때)
node = shutil.which("node")
if node:
    i0 = html.index("function swapAddr(")
    i1 = html.index("window.cmpFixAddr=")
    js = html[i0:i1] + r"""
var t=[
 [swapAddr('한드림 <HAN@dreamtek-demo.example>, khan@dreamtek-demo.example', 'han@dreamtek-demo.example', 'han@dreamtech-demo.example'), '한드림 <han@dreamtech-demo.example>, khan@dreamtek-demo.example', 1],
 [swapAddr('a@x-demo.example.kr', 'a@x-demo.example', 'b@x-demo.example'), 'a@x-demo.example.kr', 0],
 [swapAddr('a@x-demo.example;a@x-demo.example', 'a@x-demo.example', 'b@x-demo.example'), 'b@x-demo.example;b@x-demo.example', 2]
];
var ok=t.every(function(x){ return x[0].v===x[1] && x[0].n===x[2]; });
console.log(ok?'OK':'BAD '+JSON.stringify(t));
"""
    jp = os.path.join(_TMP, "swap.js")
    io.open(jp, "w", encoding="utf-8").write(js)
    out = subprocess.run([node, jp], capture_output=True, text=True, encoding="utf-8").stdout.strip()
    check("주소 바꾸기: 통째로 같은 주소만 · 크고 작은 글자 무시 · 여러 번", out == "OK", out)
else:
    print("  (node 없음 — 주소 바꾸기 스크립트 실행 시험 건너뜀)")

for p in ("app/mail_precheck.py", "app/main.py"):
    try:
        ast.parse(io.open(os.path.join(ROOT, p), encoding="utf-8").read(), feature_version=(3, 8))
        ok = True
    except SyntaxError as e:
        ok = e
    check("파이썬 3.8 문법: %s" % p, ok is True, ok)

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
