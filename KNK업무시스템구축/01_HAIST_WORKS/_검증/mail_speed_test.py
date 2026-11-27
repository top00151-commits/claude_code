# -*- coding: utf-8 -*-
"""메일 「페이지가 열릴 때 느려」(대표 2026-11-27) — 받은편지함·폴더 화면 빠르게 한 것의 시험.
운영 무접촉 · 임시 DB(knk_mspeed_*) · 가짜 직원·가짜 메일만(약 6천 통 · 큰 본문 섞음).

증명할 것
  ① 폴더 목록(fd_keys) = 예전 질의와 **같은 메일·같은 순서**(폴더마다 · 첫 쪽·다음 쪽 · 안 읽음·첨부·기한 거르기)
     · 고르는 질의는 덮는 색인만 봄(본문 안 읽음) · 시간 한도
  ② 새 메일 뒤 폴더 나누기 질의 = 덮는 색인(idx_mail_cov_d2 · 받은 때 부서 fd_team 포함)만 봄 · 옛 idx_mail_cov_d 는 지움
  ③ 거래처 폴더 셈 total_only = 전체 셈과 통수 같음
  ④ 화면 공용 ctx 의 그룹웨어 주소 = 예전 규칙(새 키 → 옛 hiworks 키 → 빈 값)
  ⑤ 받은편지함 화면: 분류별 숫자(category_counts) 안 셈 · 목록 = list_inbox 와 같음 · 촘촘한 줄 스크립트가 목록 앞에 · 폴더 화면 200
"""
import io
import os
import random
import re
import sys
import tempfile
import time

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
    _TMP = tempfile.mkdtemp(prefix="knk_mspeed_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
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
        print("  [FAIL]", name, ("· " + str(extra)[:300]) if extra != "" else "")


random.seed(5)
OWN = 9300
with _db.db_session() as c:
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id='kjr'")
    c.execute("UPDATE users SET is_active=0")
    tids = []
    for i, nm in enumerate(["00_총괄", "11_제조기술1팀", "12_제조기술2팀", "08_품질팀", "VN01_생산팀"]):
        tids.append(c.execute("INSERT INTO teams(code, name, display_order) VALUES(?,?,?)", ("SP%02d" % i, nm, 700 + i)).lastrowid)
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, team_id, email) "
              "VALUES(?, 'kjr','가짜대표','ceo',1,'x',?, 'ceo@knknara.co.kr')", (OWN, tids[0]))
    staff = []
    for i in range(20):
        em = "sp%02d@knknara.co.kr" % i
        c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, team_id, email) VALUES(?,?,?,?,1,'x',?,?)",
                  (9400 + i, "sp%d" % i, "가짜직원%02d" % i, "member", tids[i % len(tids)], em))
        staff.append(em)
    ms._ensure_security_cols(c)
    mf.ensure(c)
    for i in range(40):
        c.execute("INSERT INTO customers(name) VALUES(?)", ("가짜고객%02d" % i,))
    cids = [r[0] for r in c.execute("SELECT id FROM customers WHERE name LIKE '가짜고객%'").fetchall()]
    for i in range(120):
        c.execute("INSERT INTO shared_contacts(name, company, email, customer_id) VALUES(?,?,?,?)",
                  ("연락처%d" % i, "가짜", "p%d@cust%02d.example" % (i, i % 40), random.choice(cids)))
    senders = ["p%d@cust%02d.example" % (i, i % 40) for i in range(120)] + ["x%d@free%d.example" % (i, i % 7) for i in range(80)] + staff * 3
    big = "<p>" + ("가짜 본문 " * 400) + "</p>"
    rows = []
    for i in range(6000):
        d = random.uniform(0, 900)
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - d * 86400 - (i % 60)))
        rows.append((OWN, "in", random.choice(senders), "보낸이", "ceo@knknara.co.kr", "가짜 제목 %d" % (i % 900),
                     "본문 %d" % i, (big * 20) if random.random() < 0.08 else big, 0 if random.random() < 0.05 else 1,
                     ts, ts, (time.strftime("%Y-%m-%d", time.localtime(time.time() + random.randint(-5, 5) * 86400)) if random.random() < 0.02 else None)))
    rows.sort(key=lambda r: r[9])
    c.executemany("INSERT INTO mail_messages(user_id, direction, from_email, from_name, to_email, subject, body_text, body_html, is_read, "
                  "received_at, created_at, flag_due) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    ids = [r[0] for r in c.execute("SELECT id FROM mail_messages WHERE user_id=?", (OWN,)).fetchall()]
    c.executemany("INSERT INTO mail_attachments(mail_id, filename, mime, size, path, is_inline) VALUES(?,?,?,?,?,0)",
                  [(x, "f%d.pdf" % x, "application/pdf", 1000, "/fake/%d" % x) for x in ids if x % 4 == 0])
    # 옛 판에서 올라온 것처럼 — 11-26 색인(cov_d)이 이미 있는 DB
    c.execute("CREATE INDEX IF NOT EXISTS idx_mail_cov_d ON mail_messages(user_id, direction, is_deleted, " + mf._COVER_COLS + ")")
with _db.db_session() as c:
    mf.seed_if_owner(c, OWN)
    fl = [r[0] for r in c.execute("SELECT id FROM mail_folders WHERE user_id=?", (OWN,)).fetchall()]
    for i in range(12):   # 옮긴 규칙
        c.execute("INSERT INTO mail_move_rules(user_id, kind, pattern, target, since) VALUES(?,?,?,?,?)",
                  (OWN, "domain", "cust%02d.example" % i, "f%d" % random.choice(fl), "" if i % 3 else "2026-01-01 00:00:00"))
    for x in random.sample(ids, 60):   # 이 메일만
        c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=?", ("f%d" % random.choice(fl), x))

print("\n② 폴더 나누기 · 색인")
with _db.db_session() as c:
    mf._COUNT_IDX_OK.clear(); mf._OLD_TRY[0] = 0
    res = mf.classify(c, OWN)
with _db.db_session() as c:
    mf._OLD_TRY[0] = 0
    mf.ensure_count_indexes(c)
    ix = sorted(r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_mail_cov%'").fetchall())
    pl = " / ".join(r[3] for r in c.execute(
        "EXPLAIN QUERY PLAN SELECT id, lower(from_email) AS e, COALESCE(received_at,'') AS ts, COALESCE(fd_pin,'') AS pin, "
        "fd_team, COALESCE(fd_key,'') AS fk, is_read, substr(COALESCE(subject,''),1,200) AS sj FROM mail_messages "
        "WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0", (OWN,)).fetchall())
check("색인 = cov_d2 · cov_x (옛 cov_d 는 지움)", ix == ["idx_mail_cov_d2", "idx_mail_cov_x"], ix)
check("폴더 나누기(메일마다) 질의 = 덮는 색인 cov_d2 만", "COVERING INDEX idx_mail_cov_d2" in pl, pl)
keys = [k for k in res["keys_of"] if res["keys_of"][k]]
check("폴더 열쇠 여럿(팀·폴더·일반)", len(keys) >= 10 and any(k.startswith("t") for k in keys) and "gen" in keys, len(keys))

print("\n① 폴더 목록 = 예전 질의와 같은 메일·같은 순서")
OLD_BASE = ("user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0 "
            "AND (COALESCE(snooze_until,'')='' OR snooze_until <= datetime('now','localtime')) AND direction='in' "
            "AND COALESCE(fd_key,'') IN (%s)")


def old_ids(c, fkeys, extra="", limit=200, offset=0, order="received_at DESC, id DESC"):
    fk = sorted({k for k in fkeys if k})
    q = "SELECT id FROM mail_messages WHERE " + (OLD_BASE % ",".join("?" * len(fk))) + extra + " ORDER BY " + order + " LIMIT ? OFFSET ?"
    return [r[0] for r in c.execute(q, (OWN, *fk, limit, offset)).fetchall()]


n_cmp = n_same = 0
worst = 0.0
with _db.db_session() as c:
    for k in keys:
        fk = res["keys_of"][k]
        for kw, extra, order in (({}, "", None),
                                 ({"unread": True}, " AND is_read=0", None),
                                 ({"has_att": True}, " AND EXISTS(SELECT 1 FROM mail_attachments a WHERE a.mail_id=mail_messages.id AND COALESCE(a.is_inline,0)=0)", None),
                                 ({"flagged": True}, "", "flag_due ASC, received_at DESC, id DESC")):
            for off in (0, 200):
                t0 = time.perf_counter()
                got = ms.list_inbox(c, OWN, fd_keys=sorted(fk), senders=mf.senders_in(res, k), limit=200, offset=off, **kw)
                worst = max(worst, time.perf_counter() - t0)
                ex = extra
                if kw.get("flagged"):
                    ex = " AND COALESCE(flag_due,'')<>''"
                    # 예전 길: 기한 보기는 「다시 알림」 숨김 조건이 없음
                    fk2 = sorted({x for x in fk if x})
                    q = ("SELECT id FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 AND COALESCE(is_blocked,0)=0"
                         " AND COALESCE(flag_due,'')<>'' AND direction='in' AND COALESCE(fd_key,'') IN (%s) ORDER BY %s LIMIT 200 OFFSET ?"
                         % (",".join("?" * len(fk2)), order))
                    want = [r[0] for r in c.execute(q, (OWN, *fk2, off)).fetchall()]
                else:
                    want = old_ids(c, fk, ex, 200, off)
                n_cmp += 1
                n_same += int([g["id"] for g in got] == want)
                if [g["id"] for g in got] != want:
                    print("     다름:", k, kw, off, len(got), len(want))
    cols_fd = set(ms.list_inbox(c, OWN, fd_keys=["gen"], limit=1)[0].keys())
    cols_in = set(ms.list_inbox(c, OWN, limit=1)[0].keys())
    cnt_ok = all(ms.list_inbox(c, OWN, fd_keys=sorted(res["keys_of"][k]), count_only=True) == len(old_ids(c, res["keys_of"][k], "", -1, 0)) for k in keys)
    plan = " / ".join(r[3] for r in c.execute(
        "EXPLAIN QUERY PLAN SELECT id FROM mail_messages WHERE id IN (SELECT id FROM mail_messages WHERE " + (OLD_BASE % "?")
        + " ORDER BY received_at DESC, id DESC LIMIT 200 OFFSET 0)", (OWN, "gen")).fetchall())
check("폴더 %d개 × 거르기 4가지 × 쪽 2개 = %d번 모두 같은 메일·같은 순서" % (len(keys), n_cmp), n_cmp == n_same and n_cmp >= 80, (n_same, n_cmp))
check("폴더 목록 칸 = 받은편지함 목록 칸과 같음", cols_fd == cols_in, cols_fd ^ cols_in)
check("폴더 통수(count_only) = 예전 질의 통수", cnt_ok)
check("메일 고르는 질의 = 덮는 색인만(본문 안 읽음)", "COVERING INDEX idx_mail_cov" in plan, plan)
check("폴더 목록 한 번 = 0.5초 안(6천 통 · 가장 느린 것 %.0fms)" % (worst * 1000), worst < 0.5, worst)

print("\n③ 거래처 폴더 셈 total_only")
with _db.db_session() as c:
    a = ms.customer_folder_counts(c, OWN)
    b = ms.customer_folder_counts(c, OWN, total_only=True)
check("전체 통수·안 읽음 같음 · 거래처 줄 없음", a["total"] == b["total"] and a["total_unread"] == b["total_unread"] and b["customers"] == [] and a["total"] > 5000, (a["total"], b["total"]))

print("\n④ ctx 그룹웨어 주소 규칙")


def setv(k, v):
    with _db.db_session() as c:
        c.execute("DELETE FROM app_settings WHERE key=?", (k,))
        if v is not None:
            c.execute("INSERT INTO app_settings(key, value) VALUES(?,?)", (k, v))


def old_rule(a, b):
    return (_db.get_setting(a, "") or _db.get_setting(b, "") or "").strip()


cases = [("https://gw.new.example ", "https://old.example"), ("", "https://old.example"), (None, " https://old2.example "), (None, None), ("x", None)]
ok = True
for nv, ov in cases:
    for nk in ("approval_url", "mail_url", "domain"):
        setv("groupware_" + nk, nv); setv("hiworks_" + nk, ov)
    g = m._ctx_groupware_settings()
    for nk in ("approval_url", "mail_url", "domain"):
        if g[nk] != old_rule("groupware_" + nk, "hiworks_" + nk):
            ok = False; print("     다름", nk, nv, ov, g[nk])
check("새 키 → 옛 키 → 빈 값 · 앞뒤 빈칸 지움 = get_setting 두 번 부르던 예전과 같음(5가지)", ok)

print("\n⑤ 받은편지함 화면")
m.get_user = lambda req: {"id": OWN, "role": "ceo", "name": "가짜대표", "team_id": tids[0], "team_name": "", "login_id": "kjr", "rank": "대표"}
_called = []
_orig_cc = ms.category_counts
ms.category_counts = lambda *a, **k: (_called.append(1), _orig_cc(*a, **k))[1]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=True, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
r = k.get("/mail/inbox?thread=0")
check("받은편지함 200", r.status_code == 200, r.status_code)
check("분류별 숫자 안 셈(화면에 안 쓰임)", not _called, len(_called))
with _db.db_session() as c:
    from app import mail_find as _mfind
    want = [x["id"] for x in ms.list_inbox(c, OWN, limit=200, noad=_mfind.bulk_map(c, OWN))]
got = [int(x) for x in re.findall(r'data-mail-id="(\d+)"', r.text)]
check("목록 = list_inbox 첫 200통(같은 순서)", got[:len(want)] == want[:len(got)] and len(got) >= 150, (len(got), len(want)))
i_dense = r.text.find("knkmail.dense')||''")
i_row = r.text.find('class="mbx-row"')
check("촘촘한 줄 스크립트가 목록 줄보다 앞", 0 < i_dense < i_row, (i_dense, i_row))
fk_t = next(x for x in keys if x.startswith("t"))
t0 = time.perf_counter()
r2 = k.get("/mail/inbox?thread=0&fd=" + fk_t)
dt = time.perf_counter() - t0
with _db.db_session() as c:
    want2 = old_ids(c, res["keys_of"][fk_t])
got2 = [int(x) for x in re.findall(r'data-mail-id="(\d+)"', r2.text)]
check("부서 폴더 화면 200 · 목록 = 예전 질의(같은 순서)", r2.status_code == 200 and got2 == want2, (len(got2), len(want2)))
check("부서 폴더 화면 2초 안(%.0fms)" % (dt * 1000), dt < 2.0, dt)
ms.category_counts = _orig_cc

print("\n결과: 통과 %d · 실패 %d" % (P, F))
sys.exit(1 if F else 0)
