# -*- coding: utf-8 -*-
"""메일 끌어서 옮기기 시험 — 목록 줄을 끌어 왼쪽 폴더·⭐ 중요·📦 보관함·🗑 휴지통·(보관함에서) 받은편지함에 놓기.
가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음). 대표 지시 2026-11-18 「메일을 끌어다 폴더에 옮기는거」 → 「진행해」.
실제 끌기(마우스)는 시험 서버에서 브라우저로 확인 · 여기서는 화면에 놓을 곳 표시·서버 길(되돌리기 포함)을 확인.
사용: py -3.13 _검증/mail_dnd_test.py"""
import io
import os
import re
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
_so = sys.stdout
sys.stdout = io.StringIO()
try:
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_mdnd_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
finally:
    sys.stdout = _so
from starlette.testclient import TestClient  # noqa: E402

P = F = 0
_SEQ = [0]


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:600])


OWN, OTHER = 9001, 9002
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("INSERT INTO teams(id, code, name, display_order) VALUES(981,'81','시험영업팀',81)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9001,'kjr','시험대표','ceo',1,'x','boss@knknara.co.kr',981)")
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id) VALUES(9002,'t9002','시험이','member',1,'x','staff2@knknara.co.kr',981)")
    c.execute("INSERT INTO customers(id, name) VALUES(701,'삼성전기㈜')")
    c.execute("INSERT INTO customer_contacts(customer_id, role, name, email) VALUES(701,'구매','박구매','p@semco.example')")


def put(frm, subject, text="내용", owner=OWN, name="보낸이", ago="-1 hours", read=False, star=False):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="boss@knknara.co.kr", from_email=frm, from_name=name, subject=subject,
                                   text=text, owner_id=owner, run_ai=False, message_id="dnd-%d@test" % _SEQ[0])
        c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime', ?), is_read=?, is_starred=? WHERE id=?",
                  (ago, 1 if read else 0, 1 if star else 0, mid))
    return mid


ids = {}
ids["s1"] = put("p@semco.example", "발주서 송부", "발주서 송부드립니다.", name="박구매", ago="-10 minutes")
ids["s2"] = put("p@semco.example", "샘플 일정 문의", "샘플 가능할까요?", name="박구매", ago="-20 minutes")
ids["x1"] = put("hello@unknownco.example", "처음 보는 곳", "안녕하세요", name="모르는곳", ago="-30 minutes")
ids["k1"] = put("staff2@knknara.co.kr", "사내 보고", "보고드립니다", name="시험이", ago="-40 minutes")
ids["other"] = put("p@semco.example", "남의 메일", "x", owner=OTHER)

_U = {"v": {"id": OWN, "role": "ceo", "name": "시험대표", "team_id": 981, "team_name": "시험영업팀"}}
_keep = m.get_user
m.get_user = lambda req: _U["v"]


def client(port=5051, host="works.knknara.co.kr"):
    k = TestClient(m.app, base_url="http://127.0.0.1:%d" % port, raise_server_exceptions=False, follow_redirects=False)
    k.headers.update({"host": host, "x-forwarded-proto": "https"})
    return k


def row_attrs(h, mid):
    mm = re.search(r'<a href="/mail/%d"[^>]*data-mail-id="%d"[^>]*>' % (mid, mid), h)
    return mm.group(0) if mm else ""


def side(h):
    a = h.find('<nav class="mbx-side"')
    return h[a:h.find("</nav>", a)] if a >= 0 else ""


def mrow(mid):
    with _db.db_session() as c:
        return dict(c.execute("SELECT is_deleted, is_archived, is_starred, is_read, fd_pin FROM mail_messages WHERE id=?", (mid,)).fetchone())


try:
    k = client()
    h = k.get("/mail/inbox").text
    with _db.db_session() as c:
        res = mf.classify(c, OWN)
        ok_ids = {f["id"] for f in mf.assignable_list(res)}
        srv_ok = {f["id"] for f in mf.assignable(c, OWN)}
        staff_ids = [int(g["key"][1:]) for g in res["nodes"] if g.get("kind") == "staff"]
    sd = side(h)

    print("== 1. 왼쪽: 놓을 수 있는 곳 · 없는 곳 ==")
    check("⭐ 중요 · 📦 보관함 · 🗑 휴지통에 놓을 곳 표시",
          'data-drop="star"' in sd and 'data-drop="archive"' in sd and 'data-drop="delete"' in sd)
    check("받은편지함(그냥 보기)에서는 「📥 받은편지함」에 놓을 곳 없음(같은 곳)", 'data-drop="unarchive"' not in sd)
    fids = [int(x) for x in re.findall(r'data-drop="pin" data-fid="(\d+)"', sd)]
    check("폴더에 놓을 곳이 있고 모두 「📁 폴더로」 고를 수 있는 폴더(여러 통 띠와 같은 목록)", fids and set(fids) <= ok_ids and set(fids) == ok_ids, (fids, ok_ids))
    check("서버도 그 폴더들을 받아 줌(옮길 수 없는 폴더 아님)", set(fids) <= srv_ok, set(fids) - srv_ok)
    check("6.케이엔케이(부서 자동)·그 아래 부서는 놓을 수 없음 + 이유", staff_ids and all(s not in fids for s in staff_ids)
          and sd.count('data-drop="no"') >= 2 and "보낸 직원의 부서로 저절로 나뉘는 폴더" in sd, staff_ids)
    check("「일반」은 놓을 수 없음 + 이유", re.search(r'href="/mail/inbox\?fd=gen"[^>]*data-drop="no"[^>]*data-why="「일반」', sd) is not None)
    check("보낸편지함·쓰다 만 메일·회신 필요에는 놓을 곳 없음",
          all(not re.search(r'href="%s"[^>]*data-drop' % re.escape(u), sd) for u in ("/mail/sent", "/mail/drafts", "/mail/inbox?reply=1")))

    print("== 2. 목록 줄: 끌 때 쓰는 표시 ==")
    a1 = row_attrs(h, ids["s1"])
    check("줄에 지금 폴더·이 메일만 옮긴 폴더·보낸 주소·받은/보낸 표시", all(x in a1 for x in ('data-pin=""', 'data-fd="', 'data-from="p@semco.example"', 'data-dir="in"')), a1)
    fdk = re.search(r'data-fd="([^"]*)"', a1).group(1)
    check("폴더 열쇠 = 왼쪽 폴더 열쇠(같은 폴더에 놓으면 「이미 그 폴더」 안내)", fdk and ('data-fkey="%s"' % fdk) in sd, fdk)
    ax = row_attrs(h, ids["x1"])
    check("어느 폴더에도 안 걸린 메일 = 「일반」(gen)", 'data-fd="gen"' in ax, ax)

    print("== 3. 끌기 코드(화면) ==")
    check("끌기 시작·놓기·끝 처리 + 손가락 화면 제외", all(x in h for x in ("addEventListener('dragstart'", "addEventListener('drop'", "addEventListener('dragend'", "(pointer:fine)")))
    check("고른 줄을 끌면 고른 것 모두 · 아니면 그 줄(대화=그 대화)", "(ck && ck.checked) ? mbxPicked()" in h)
    check("놓은 뒤 안내 + ↺ 되돌리기 + 같은 회사면 「이 회사 메일 모두」", "↺ 되돌리기" in h and "메일 모두 이 폴더로" in h and "mbxSideRefresh()" in h)
    check("빈 읽기 칸에 사용법 한 줄", "끌어서</b> 왼쪽 폴더" in h)
    check("접힌 폴더 묶음·「메일 없는 N곳」 위에 머물면 펼침", "mf-zero-more" in h and "showzero" in h and "650" in h)

    print("== 3b. 보기 방식(11-18 대표 「작은 모니터에서 세 칸은 못 본다」) ==")
    check("「🗔 보기」 메뉴: 읽기 칸 자동·오른쪽·아래·끄기 + 폴더 칸 자동·보이기·접기", all(('name="mbxv" value="%s"' % v) in h for v in ("auto", "right", "bottom", "list")) and all(('name="mbxf" value="%s"' % v) in h for v in ("auto", "show", "hide")))
    check("「☰ 폴더」 서랍 단추 + 끌다가 올려 두면 열림", 'class="mbx-foldbtn"' in h and "closest('.mbx-foldbtn')" in h)
    check("자동 = 칸 폭 1250 이상 세 칸 · 1000~1250 폴더 접기 · 1000 미만 목록만", "W>=1000 ? 'right' : 'list'" in h and "W>=1250 ? 'show' : 'hide'" in h)
    check("목록만 모드: 누르면 그 자리에서 크게 + 「← 목록으로」 + Esc", "mbx-readback" in h and "mbxBackToList()" in h and "e.key!=='Escape'" in h)
    check("자리 이름 배치(아래 모드 3줄 · 끄기 모드는 같은 칸에 겹침)", '"side g1 list" "side g1 g2" "side g1 read"' in h and ".mbx-split.v-list>.mbx-readpane{grid-area:list" in h)
    check("이 컴퓨터에 기억(knkmail.view · knkmail.fold · 아래 모드 높이)", "knkmail.view" in h and "knkmail.fold" in h and "knkmail.r1" in h)
    hs0 = k.get("/mail/sent").text
    check("보낸편지함 등 다른 메일함: 「보기」 메뉴 없음 · 폴더 접기 단추는 있음", 'name="mbxv"' not in hs0 and 'class="mbx-foldbtn"' in hs0)

    print("== 4. 서버 길(놓기 · 되돌리기) ==")
    f1 = sorted(ok_ids)[0]
    j = k.post("/mail/bulk", data={"op": "pin", "ids": "%d,%d" % (ids["s1"], ids["other"]), "folder_id": f1}).json()
    check("폴더에 놓기 = 이 메일만 그 폴더로 · 남의 메일은 조용히 뺌", j.get("ok") and j.get("n") == 1 and mrow(ids["s1"])["fd_pin"] == "f%d" % f1 and mrow(ids["other"])["fd_pin"] in ("", None), j)
    h2 = k.get("/mail/inbox").text
    check("옮긴 뒤 줄 표시도 옮긴 폴더(data-pin·data-fd)", ('data-pin="f%d"' % f1) in row_attrs(h2, ids["s1"]) and ('data-fd="f%d"' % f1) in row_attrs(h2, ids["s1"]), row_attrs(h2, ids["s1"]))
    j = k.post("/mail/bulk", data={"op": "pin", "ids": str(ids["s1"]), "folder_id": "0"}).json()
    check("↺ 되돌리기(폴더) = 자동 분류로", j.get("ok") and mrow(ids["s1"])["fd_pin"] == "", j)
    if staff_ids:
        j = k.post("/mail/bulk", data={"op": "pin", "ids": str(ids["s1"]), "folder_id": staff_ids[0]}).json()
        check("6.케이엔케이 묶음에는 서버도 안 받음", not j.get("ok"), j)
    j = k.post("/mail/bulk", data={"op": "delete", "ids": str(ids["s2"])}).json()
    check("🗑 휴지통에 놓기", j.get("ok") and mrow(ids["s2"])["is_deleted"] == 1, j)
    j = k.post("/mail/bulk", data={"op": "restore", "ids": "%d,%d,abc" % (ids["s2"], ids["other"])}).json()
    check("↺ 되돌리기(휴지통) = 되살림(새 길 restore) · 내 메일만", j.get("ok") and j.get("n") == 1 and mrow(ids["s2"])["is_deleted"] == 0, j)
    k.post("/mail/bulk", data={"op": "delete", "ids": str(ids["other"])})  # 내 것이 아니라 아무 일 없음
    with _db.db_session() as c:
        c.execute("UPDATE mail_messages SET is_deleted=1 WHERE id=?", (ids["other"],))
    j = k.post("/mail/bulk", data={"op": "restore", "ids": str(ids["other"])}).json()
    check("남의 지운 메일은 되살리지 못함", j.get("ok") and j.get("n") == 0 and mrow(ids["other"])["is_deleted"] == 1, j)
    j = k.post("/mail/bulk", data={"op": "archive", "ids": str(ids["x1"])}).json()
    check("📦 보관함에 놓기 → 받은편지함에서 빠짐", j.get("ok") and mrow(ids["x1"])["is_archived"] == 1 and row_attrs(k.get("/mail/inbox").text, ids["x1"]) == "", j)
    ha = k.get("/mail/inbox?arc=1").text
    sa = side(ha)
    check("보관함 보기: 「📥 받은편지함」에 놓을 곳 · 보관함 자신엔 없음", 'data-drop="unarchive"' in sa and not re.search(r'href="/mail/inbox\?arc=1"[^>]*data-drop', sa))
    k.post("/mail/bulk", data={"op": "unarchive", "ids": str(ids["x1"])})
    k.post("/mail/bulk", data={"op": "unread", "ids": str(ids["x1"])})
    check("↺ 되돌리기(보관) = 받은편지함으로 + 안 읽음 그대로", mrow(ids["x1"])["is_archived"] == 0 and mrow(ids["x1"])["is_read"] == 0)
    j = k.post("/mail/bulk", data={"op": "star", "ids": str(ids["s1"])}).json()
    k.post("/mail/bulk", data={"op": "unstar", "ids": str(ids["s1"])})
    check("⭐ 중요에 놓기 · 되돌리기", j.get("ok") and mrow(ids["s1"])["is_starred"] == 0)

    print("== 5. 다른 메일함 · kmail ==")
    hs = k.get("/mail/sent").text
    check("보낸편지함 화면에는 놓을 곳 없음(끌기 꺼짐)", "data-drop=" not in side(hs) and "window._mbxBox = 'sent'" in hs)
    km = client(port=5053, host="kmail.knknara.co.kr")
    hk = km.get("/mail/inbox").text
    check("kmail 받은편지함도 같은 끌기", "addEventListener('dragstart'" in hk and 'data-drop="pin"' in hk)
    _U["v"] = None
    check("로그인 안 하면 되살리기 401", k.post("/mail/bulk", data={"op": "restore", "ids": "1"}).status_code == 401)
finally:
    m.get_user = _keep

print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
