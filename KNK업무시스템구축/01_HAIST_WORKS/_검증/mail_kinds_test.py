# -*- coding: utf-8 -*-
"""🏷 종류 목록 고치기 (대표 2026-11-23 「보고 싶은 걸 내가 지정 · 고치는 메뉴를 팝업에서 바로」) — 운영 무접촉 · 임시 DB · 가짜 사람·메일만.
실행: 프로젝트 루트(01_HAIST_WORKS)에서  python _검증/mail_kinds_test.py"""
import io
import os
import re
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
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_kinds_"), "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_ui_prefs as mup
    from app import mail_store as ms
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


D = "@knknara.co.kr"
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x', email=NULL")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(9930,'t_kd','시험','사원','member',1,'x','kd" + D + "')")
    c.execute("INSERT INTO users(id, login_id, name, rank, role, is_active, password, email) VALUES(9931,'t_kd2','남','사원','member',1,'x','kd2" + D + "')")
    for i, (subj, fe, fn) in enumerate((("[가짜] 제작 요청 — 검사기 2대", "a@cust-demo.example", "가짜고객"),
                                        ("[가짜] 제작요청서 보내드립니다", "b@cust-demo.example", "가짜고객"),
                                        ("[가짜] 견적 부탁드립니다", "c@cust-demo.example", "가짜고객"),
                                        ("[가짜] 안부 인사", "d@vendor-demo.example", "가짜협력사"),
                                        ("[가짜] 회의 일정", "e@vendor-demo.example", "가짜협력사"))):
        c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
                  "VALUES(9930,'in',?,?,'kd" + D + "',?,'가짜',0,0,datetime('now','localtime', ?))", (fe, fn, subj, "-%d minutes" % i))
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
              "VALUES(9931,'in','x@cust-demo.example','남','kd2" + D + "','[가짜] 제작 요청 남의 것','가짜',0,0,datetime('now','localtime'))")

print("① 거르기(clean_kinds)")
d0 = mup.default_kinds()
check("처음 = 견적·발주·세금계산서 셋 · 모두 보임", [x["b"] for x in d0] == ["견적", "발주", "세금계산서"] and all(x["on"] for x in d0))
cl = mup.clean_kinds([{"b": "발주", "on": 0}, {"n": " 제작요청 ", "w": "제작 요청, 제작요청 ,, 제작요청", "i": "🛠", "on": 1},
                      {"n": "나쁜 그림", "w": ["샘플"], "i": "<b>", "on": "1"}, {"n": "", "w": ["x"]}, {"n": "낱말없음", "w": []},
                      {"b": "가짜기본"}, {"n": "<script>alert(1)</script>이름이아주길어서스무자를넘어가는종류", "w": ["50%_off"], "on": 1}, "이상한값"])
check("기본 발주 = 숨김 그대로 · 빠진 기본(견적·세금계산서)은 끝에 숨김으로", cl[0] == {"id": "b:발주", "b": "발주", "i": "🛒", "on": 0}
      and [(x.get("b"), x["on"]) for x in cl if x.get("b")] == [("발주", 0), ("견적", 0), ("세금계산서", 0)], cl)
cu = [x for x in cl if not x.get("b")]
check("내 종류: 이름 다듬음 · 낱말 쉼표로 나눔·겹침 뺌 · 번호 u1·u2·u3", cu[0]["n"] == "제작요청" and cu[0]["w"] == ["제작 요청", "제작요청"] and [x["id"] for x in cu] == ["u1", "u2", "u3"], cu)
check("정해진 그림 밖 = 🏷 · 이름 없음·낱말 없음·모르는 기본·이상한 값 = 버림", cu[1]["i"] == "🏷" and len(cu) == 3, cu)
check("이름 20자로 자름 · 낱말의 % _ 는 뺌(찾기 글자 오작동 막기)", len(cu[2]["n"]) == 20 and cu[2]["w"] == ["50 off"], cu[2])
many = mup.clean_kinds([{"n": "k%d" % i, "w": ["w%d" % i], "on": 1} for i in range(30)])
check("내 종류는 15개까지", len([x for x in many if not x.get("b")]) == 15)
keep = mup.clean_kinds([{"id": "u7", "n": "A", "w": ["a1"], "on": 1}, {"n": "B", "w": ["b1"], "on": 1}, {"id": "u7", "n": "C", "w": ["c1"], "on": 1}])
check("있던 번호는 그대로 · 새것·겹친 번호는 새 번호(u8·u9)", [x["id"] for x in keep if not x.get("b")] == ["u7", "u8", "u9"], keep)

print("② 저장 · 글자 크기와 같은 칸 · 사람마다")
with _db.db_session() as c:
    mup.save_fs(c, 9930, {"knkmail.fs": 2, "t": 5})
    mup.save_kinds(c, 9930, [{"n": "제작요청", "w": ["제작 요청", "제작요청"], "i": "🛠", "on": 1}, {"b": "견적", "on": 1}, {"b": "발주", "on": 0}, {"b": "세금계산서", "on": 1}])
    g = mup.get_kinds(c, 9930)
    check("저장한 순서·보이기 그대로", [(x.get("b") or x.get("n"), x["on"]) for x in g] == [("제작요청", 1), ("견적", 1), ("발주", 0), ("세금계산서", 1)], g)
    check("글자 크기 기억은 안 지워짐(같은 칸 다른 열쇠)", (mup.get_fs(c, 9930) or {}).get("knkmail.fs") == 2)
    mup.save_fs(c, 9930, {"knkmail.fs": 1, "t": 9})
    check("글자 크기를 다시 저장해도 종류 목록은 그대로", len(mup.get_kinds(c, 9930)) == 4)
    check("남은 기본 셋(고른 적 없음)", [x.get("b") for x in mup.get_kinds(c, 9931)] == ["견적", "발주", "세금계산서"])

print("③ 받은편지함 모아 보기(kind_words)")
with _db.db_session() as c:
    r = ms.list_inbox(c, 9930, kind_words=["제작 요청", "제작요청"])
    check("제목에 「제작 요청」·「제작요청」 = 2통 · 남의 메일 안 섞임", sorted(x["subject"] for x in r) == ["[가짜] 제작 요청 — 검사기 2대", "[가짜] 제작요청서 보내드립니다"], [x["subject"] for x in r])
    check("보낸 사람 이름으로도(가짜협력사 = 2통)", ms.list_inbox(c, 9930, count_only=True, kind_words=["가짜협력사"]) == 2)
    check("보낸 주소로도(@cust-demo = 3통)", ms.list_inbox(c, 9930, count_only=True, kind_words=["cust-demo"]) == 3)
    check("낱말 없음 = 거르지 않음(5통)", ms.list_inbox(c, 9930, count_only=True, kind_words=[]) == 5)

ME = {"id": 9930, "role": "member", "name": "시험", "rank": "사원", "login_id": "t_kd", "email": "kd" + D, "lang": "ko"}
m.get_user = lambda req: ME
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})


def NM(h):
    return len(set(re.findall(r'data-mail-id="(\d+)"', h)))


def T(r):
    return r.text.replace("\r\n", "\n")


print("④ 받은편지함 「🏷 종류 ▾」 펼침 상자")
h = T(k.get("/mail/inbox?app=1"))
menu = h[h.find('<span class="mbx-kindmenu">'):h.find('</span></span>', h.find('<span class="mbx-kindmenu">'))]
check("내 순서대로: 🛠 제작요청 → 💲 견적 → 🧾 세금계산서 · 숨긴 발주 없음",
      menu.find("🛠 제작요청") < menu.find("💲 견적") < menu.find("🧾 세금계산서") and "🛠 제작요청" in menu and "🛒 발주" not in menu, menu[:600])
check("맨 아래 「✏ 종류 고치기」 → /mail/kinds", menu.rstrip().endswith('✏ 종류 고치기</a>') and 'href="/mail/kinds" class="mbx-chip mbx-kedit"' in menu)
check("제작요청 링크 = kd=u1", "&amp;kd=u1" in menu or "&kd=u1" in menu, menu[:400])
hk = T(k.get("/mail/inbox?app=1&kd=u1"))
check("kd=u1 → 2통 · 단추 이름 「🏷 제작요청 ▾」 · 그 줄 ✕(다시 누르면 풂)", "🏷 제작요청 ▾" in hk and "🛠 제작요청 ✕" in hk and NM(hk) == 2, NM(hk))
hx = T(k.get("/mail/inbox?app=1&kd=u99"))
check("모르는 kd = 거르지 않음(5통)", NM(hx) == 5, NM(hx))
hc = T(k.get("/mail/inbox?app=1&cat=" + "견적" + "&kd=u1"))
mc = hc[hc.find('<span class="mbx-kindmenu">'):]
check("종류를 바꾸면 다른 종류 조건은 빠짐(견적 링크에 kd 없음)", "kd=u1&amp;cat=견적" not in mc and "kd=u1&cat=견적" not in mc)

print("④-2 거르기 줄 「📂 분류 안 됨」 · 화살표 크게(11-23)")
src = open(os.path.join(ROOT, "app", "templates", "mail_inbox.html"), encoding="utf-8").read()
cs = src[src.find('<div class="mbx-chips">'):src.find('id="mbxKindDd"')]
check("「📂 분류 안 됨」 = 대화로 묶기 다음·종류 앞 · fd=gen(폴더 쓰는 사람만 · 시험 사람은 폴더 없음 → 시연 서버에서 확인)",
      cs.find("💬 대화로 묶기") < cs.find("📂 분류안됨") and "'/mail/inbox?fd=gen'" in cs and "{% if mf %}" in cs)
check("고른 뒤 = 켜짐 · ✕ · 다시 누르면 전체(/mail/inbox) · 통수", "'/mail/inbox' if cur_fd|default('') == 'gen'" in cs and "{{ ' ✕' if cur_fd|default('') == 'gen' else '' }}" in cs and "mf.gen.n" in cs)
check("화살표: 폴더 칸 ▾ 15px · 칸 18px · 대화 묶음 ▸ 16px", ".mbx-side .mf-tg{width:18px;font-size:15px !important" in h and 'html[data-md="v2"] .mbx-side .mf-tg{font-size:15px !important' in h and ".mbx-twist{font-size:16px" in h)

print("⑤ 고치기 화면 · 저장 · 세기")
r = k.get("/mail/kinds?app=1")
pg = T(r)
check("/mail/kinds 200 · 목록·추천·저장 단추", r.status_code == 200 and 'id="kdList"' in pg and "kdSave()" in pg and "제작요청" in pg and "↺ 처음 목록으로" in pg, r.status_code)
check("기본 셋 낱말 보여 줌(읽기만)", "AI 분류 + 제목 낱말" in pg and "quotation" in pg)
r = k.post("/mail/kinds/count", json={"w": ["제작 요청", "제작요청"]})
check("세기: 2통", r.json().get("n") == 2, r.text)
check("세기: 빈 낱말 = 0", k.post("/mail/kinds/count", json={"w": []}).json().get("n") == 0)
r = k.post("/mail/kinds", json={"kinds": [{"b": "세금계산서", "on": 1}, {"id": "u1", "n": "제작", "w": "제작", "i": "🔧", "on": 1}]})
j = r.json()
check("저장: 순서 · 이름 바뀜 · 빠진 기본은 숨김으로", j["ok"] and [(x.get("b") or x.get("n"), x["on"]) for x in j["kinds"]] == [("세금계산서", 1), ("제작", 1), ("견적", 0), ("발주", 0)], j)
r = k.post("/mail/kinds", json={"reset": 1})
check("처음 목록으로 = 기본 셋", [x.get("b") for x in r.json()["kinds"]] == ["견적", "발주", "세금계산서"])
t = T(k.get("/mail/tools?app=1"))
check("⚙ 설정·정리에도 「🏷 종류 목록 고치기」", 'href="/mail/kinds"' in t)
m.get_user = lambda req: None
check("로그인 안 하면 저장 안 됨", k.post("/mail/kinds", json={"reset": 1}).status_code == 401)
m.get_user = lambda req: ME

print("⑥ 광고·알림 내가 지정 · 다른 폴더로 목록 굴려도 안 닫힘(11-23)")
from app import mail_cleanup as mcl  # noqa: E402
from app import mail_find as mfi  # noqa: E402
with _db.db_session() as c:
    c.execute("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, is_read, is_deleted, received_at) "
              "VALUES(9930,'in','noreply@shop-demo.example','가짜쇼핑','kd" + D + "','[가짜] 주문 안내','가짜',1,0,datetime('now','localtime'))")
    kinds0 = {g["addr"]: g["kind"] for g in mcl.sender_groups(c, 9930)["groups"]}
check("자동 판단: noreply 주소 = 광고·알림 · 일반 거래처 = 아님", kinds0.get("noreply@shop-demo.example") == "bulk" and kinds0.get("a@cust-demo.example") == "normal", kinds0)
r1 = k.post("/mail/ad-mark", data={"addr": "noreply@shop-demo.example", "mode": "off"})
r2 = k.post("/mail/ad-mark", data={"addr": "A@cust-demo.example", "mode": "on"})
with _db.db_session() as c:
    gg = {g["addr"]: (g["kind"], g["reasons"]) for g in mcl.sender_groups(c, 9930)["groups"]}
    bs = mfi.bulk_senders(c, 9930)
check("「광고·알림 아님」 → 자동 판단보다 먼저(까닭 = 내가 표시)", r1.json().get("mode") == "off" and gg["noreply@shop-demo.example"] == ("normal", ["내가 「광고·알림 아님」으로 표시"]), gg.get("noreply@shop-demo.example"))
check("「광고·알림으로 표시」(대문자 주소도) → 광고·알림 · 받은편지함 표시에도 바로", r2.json().get("mode") == "on" and gg["a@cust-demo.example"][0] == "bulk"
      and "a@cust-demo.example" in bs and "noreply@shop-demo.example" not in bs, (gg.get("a@cust-demo.example"), bs))
hr_ = T(k.get("/mail/inbox?app=1&noad=1"))
check("「광고·알림 빼기」 = 내가 표시한 사람 메일(1통)만 빠지고 「아님」 표시한 noreply 는 남음(6→5)", NM(hr_) == 5 and "주문 안내" in hr_ and "제작 요청 — 검사기" not in hr_, NM(hr_))
with _db.db_session() as c:
    on_, off_ = mup.get_ad_marks(c, 9930)
    mup.set_ad_mark(c, 9930, "a@cust-demo.example", "")
    on2, off2 = mup.get_ad_marks(c, 9930)
    fs_keep = mup.get_fs(c, 9930)
check("표시 풀기('') = 자동 판단으로 · 다른 기억(글자 크기)은 그대로", on_ == {"a@cust-demo.example"} and off_ == {"noreply@shop-demo.example"} and on2 == set() and (fs_keep or {}).get("knkmail.fs") == 1, (on_, off_, on2))
check("회사 안 주소·빈 주소는 거절", not k.post("/mail/ad-mark", data={"addr": "x" + D, "mode": "on"}).json()["ok"] and not k.post("/mail/ad-mark", data={"addr": "", "mode": "on"}).json()["ok"])
check("오른쪽 클릭 메뉴: 📢 광고·알림으로 표시 / 아님(이 사람)", "📢 광고·알림으로 표시(이 사람)" in h and "📢 광고·알림 아님(이 사람)" in h and "fetch('/mail/ad-mark'" in h)
check("다른 폴더로 ▸ 긴 목록: 메뉴 안에서 굴린 것은 안 닫힘 · 끝에서 뒤 목록으로 안 번짐",
      "if(t && t.nodeType===1 && menu.contains(t)) return; closeMenu();" in h and "overscroll-behavior:contain" in h[h.find(".mbx-ctx{"):h.find(".mbx-ctx{") + 200])

node = shutil.which("node")
if node:
    bad = 0
    for nm, src in (("고치기 화면", pg), ("받은편지함", h)):
        for s in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.S):
            if not s.strip():
                continue
            fd, p = tempfile.mkstemp(suffix=".js")
            os.write(fd, s.encode("utf-8"))
            os.close(fd)
            rr = subprocess.run([node, "--check", p], capture_output=True, text=True, encoding="utf-8", stdin=subprocess.DEVNULL)
            if rr.returncode:
                bad += 1
                print(nm, rr.stderr[:300])
            os.remove(p)
    check("스크립트 문법(node) — 고치기 화면·받은편지함", bad == 0, bad)

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
