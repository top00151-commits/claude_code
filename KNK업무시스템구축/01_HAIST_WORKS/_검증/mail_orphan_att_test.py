# -*- coding: utf-8 -*-
"""어느 메일도 쓰지 않는 첨부 파일 밤 정리 시험 (대표 11-28 「정리」 · 스킬 knk-safe-delete 3절) — 가짜 자료로 만든 임시 DB·임시 폴더만 씀.
· 두 메일이 같은 파일 공유 → 한 통 지워도 남음 · 둘 다 지워지면(밤 정리 뒤) 7일 지난 파일만 · 6일짜리 남음
· 완전 삭제 대기·임시보관·예약·휴지통·차단·떨어진 첨부 줄·옛 방식 경로가 쓰면 남음 · 모르는 모양 안 지움
· 금지 시간 안 돎 · 미리 세기는 아무것도 안 지움(안 씀) · 지우기 직전 다시 셈 · 한 밤 상한 · 이력 · 직원은 관리 화면 못 봄
실행: 프로젝트 루트(01_HAIST_WORKS)에서  PYTHONIOENCODING=utf-8 python _검증/mail_orphan_att_test.py"""
import datetime as dt
import io
import os
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

P, F = [], []


def ck(n, ok, extra=""):
    (P if ok else F).append(n)
    print(("  [OK] " if ok else "  [XX] ") + n + ("" if ok else "  " + str(extra)[:400]))


_so = sys.stdout
sys.stdout = io.StringIO()
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    TMP = tempfile.mkdtemp(prefix="knk_morphan_")
    _db.DB_PATH = os.path.join(TMP, "knk.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
finally:
    sys.stdout = _so

A, ADM, MEM = 9811, 9812, 9813
with _db.db_session() as c:
    for uid, lid, nm, role in ((A, "t_oa_a", "시험갑", "member"), (ADM, "t_oa_adm", "시험관리자", "admin"),
                               (MEM, "t_oa_mem", "시험직원", "member")):
        c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (uid, lid, nm, role))
    ms._ensure_security_cols(c)
    MCOLS = {r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()}

ATT = ms._att_dir()
DAY = 86400
# 화요일 23:40(금지 시간 아님) · 시험 「지금」
T0 = dt.datetime(2026, 12, 1, 23, 40)
assert T0.weekday() == 1


def put(subj, data, *, deleted=0, direction="in", extra=None):
    with _db.db_session() as c:
        cur = c.execute("INSERT INTO mail_messages(user_id, direction, from_email, to_email, subject, body_text, received_at, is_deleted) "
                        "VALUES(?,?,?,?,?,?,datetime('now','localtime'),?)",
                        (A, direction, "fake.sender@example.test", "fake@knk-mailtest.com", subj, "가짜 본문", deleted))
        mid = cur.lastrowid
        for k_, v_ in (extra or {}).items():
            c.execute("UPDATE mail_messages SET %s=? WHERE id=?" % k_, (v_, mid))
        ms._save_attachments(c, mid, [{"filename": "가짜_%d.txt" % mid, "mime": "text/plain", "size": len(data), "data": data}])
    return mid


def fpath(data):
    return ms._content_att_path(ms._att_sha256(data))


def age(p, days):
    t = time.time() - days * DAY
    os.utime(p, (t, t))


def files():
    out = set()
    for d, _s, fs in os.walk(ATT):
        for f in fs:
            out.add(os.path.relpath(os.path.join(d, f), ATT).replace("\\", "/"))
    return out


def seen_rows():
    with _db.db_session() as c:
        if not c.execute("SELECT 1 FROM sqlite_master WHERE name='mail_att_orphan_seen'").fetchone():
            return []
        return sorted(tuple(r) for r in c.execute("SELECT key, first_seen FROM mail_att_orphan_seen").fetchall())


def run(now, **kw):
    so = sys.stdout
    sys.stdout = io.StringIO()
    try:
        return ms.purge_orphan_att_files(_db.db_session, now=now, **kw)
    finally:
        sys.stdout = so


def gone_mail(mid, now):
    """휴지통 → 완전 삭제 대기 → 30일 뒤 밤 정리(줄 지움) — 실제 순서 그대로."""
    with _db.db_session() as c:
        c.execute("UPDATE mail_messages SET is_deleted=1 WHERE id=?", (mid,))
        ms.hard_delete_mail(c, mid, A)
    so = sys.stdout
    sys.stdout = io.StringIO()
    try:
        ms.purge_expired_pending(_db.db_session, now=now + dt.timedelta(days=31))
    finally:
        sys.stdout = so


print("① 두 메일이 같은 파일을 함께 씀")
LIVE = put("가짜살아있는메일", b"fake living mail att")   # 늘 살아 있는 메일 하나(받은편지함)
SH = b"fake shared content A"
m1 = put("가짜공유1", SH)
m2 = put("가짜공유2", SH)
ps = fpath(SH)
ck("(준비) 같은 내용 = 파일 하나", os.path.exists(ps) and len([f for f in files() if f.startswith("sha256/")]) == 2, files())
age(ps, 30)
gone_mail(m1, T0)
ck("(준비) 한 통은 줄까지 지워짐", ms is not None and _db.get_db().execute("SELECT COUNT(*) FROM mail_messages WHERE id=?", (m1,)).fetchone()[0] == 0)
run(T0)
run(T0 + dt.timedelta(days=10))
ck("한 통 지워도 다른 메일이 쓰면 파일 남음(10일 뒤에도)", os.path.exists(ps))
ck("받은편지함 메일 첨부 파일 남음", os.path.exists(fpath(b"fake living mail att")))

print("② 둘 다 지워진 뒤 — 7일 지난 파일만 · 처음 본 날부터 7일 뒤")
Y6 = b"fake young orphan 6 days"
m3 = put("가짜6일", Y6)
py6 = fpath(Y6)
gone_mail(m2, T0)
gone_mail(m3, T0)
age(ps, 30)
age(py6, 6)
r1 = run(T0)
ck("처음 본 밤에는 안 지움(처음 본 날부터 7일 여유)", os.path.exists(ps) and r1["deleted"] == 0, r1)
ck("처음 본 날 기록됨", any(k == os.path.relpath(ps, ATT).replace("\\", "/") for k, _ in seen_rows()), seen_rows())
r2 = run(T0 + dt.timedelta(days=8))
ck("8일 뒤 = 수정 30일 지난 파일 지움", not os.path.exists(ps), r2)
ck("수정 6일짜리 파일은 남음", os.path.exists(py6))
ck("지운 수 = 1", r2["deleted"] == 1, r2)

print("③ 쓰는 곳이 있으면 남김 — 대기·임시보관·예약·휴지통·차단·떨어진 줄·옛 경로")
keepers = {}
keepers["완전 삭제 대기"] = put("가짜대기", b"fake k pending")
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET is_deleted=1 WHERE id=?", (keepers["완전 삭제 대기"],))
    ms.hard_delete_mail(c, keepers["완전 삭제 대기"], A)
keepers["임시보관"] = put("가짜임시", b"fake k draft", direction="draft")
keepers["예약"] = put("가짜예약", b"fake k sched", direction="sched", extra={"sched_state": "wait"})
keepers["휴지통"] = put("가짜휴지통", b"fake k trash", deleted=1)
keepers["보낸"] = put("가짜보낸", b"fake k sent", direction="out")
if "is_blocked" in MCOLS:
    keepers["차단함"] = put("가짜차단", b"fake k blocked", extra={"is_blocked": 1})
keepers["스팸"] = put("가짜스팸", b"fake k spam", extra={"category": "스팸"})
# 떨어진 첨부 줄(메일 줄 없음) — 웍스 쪽 등 다른 곳이 줄만 남긴 경우도 「쓰는 곳」
DG = b"fake k dangling row"
ms._write_content_file(fpath(DG), DG)
with _db.db_session() as c:
    c.execute("INSERT INTO mail_attachments(mail_id, filename, size, path, sha256) VALUES(NULL,'가짜떨어짐.txt',?,?,?)",
              (len(DG), fpath(DG), ms._att_sha256(DG)))
# 옛 방식 경로(메일 번호 폴더) — 쓰는 줄 있음 / 없음
mo = put("가짜옛경로", b"x")
old_keep = os.path.join(ATT, str(mo), "1_old.txt")
os.makedirs(os.path.dirname(old_keep), exist_ok=True)
open(old_keep, "wb").write(b"fake old style keep")
with _db.db_session() as c:
    # 서버 폴더 이름이 달라졌어도(다른 앞부분) 같은 파일로 봄
    c.execute("INSERT INTO mail_attachments(mail_id, filename, size, path) VALUES(?,?,?,?)",
              (mo, "old.txt", 19, "/opt/knk_haist/data/mail_att/%d/1_old.txt" % mo))
old_orphan = os.path.join(ATT, "777", "5_old_orphan.txt")
os.makedirs(os.path.dirname(old_orphan), exist_ok=True)
open(old_orphan, "wb").write(b"fake old orphan")
unknown = os.path.join(ATT, "readme_unknown.txt")
open(unknown, "wb").write(b"fake unknown shape")
tmpf = os.path.join(os.path.dirname(py6), ".tmp_fake_left")
open(tmpf, "wb").write(b"fake temp left")
kp = {k_: fpath(b"fake k " + {"완전 삭제 대기": b"pending", "임시보관": b"draft", "예약": b"sched", "휴지통": b"trash",
                               "보낸": b"sent", "차단함": b"blocked", "스팸": b"spam"}[k_]) for k_ in keepers}
kp["떨어진 첨부 줄"] = fpath(DG)
kp["옛 방식 경로"] = old_keep
for p_ in list(kp.values()) + [old_orphan, unknown, tmpf]:
    age(p_, 40)

print("④ 미리 세기 = 아무것도 안 지움 · 안 씀")
before_f, before_s = files(), seen_rows()
cnt = ms.count_orphan_att_files(_db.db_session, now=T0 + dt.timedelta(days=9))
ck("미리 세기 뒤 파일 그대로", files() == before_f)
ck("미리 세기 뒤 처음 본 날 기록 그대로(안 씀)", seen_rows() == before_s, (len(before_s), len(seen_rows())))
ck("미리 세기 수 = 아무도 안 씀(6일짜리·옛 고아·임시 = 3)", cnt["n"] == 3, cnt)
ck("미리 세기 크기 = 그 셋 합", cnt["bytes"] == len(Y6) + len(b"fake old orphan") + len(b"fake temp left"), cnt)
ck("모르는 모양 1개는 따로 셈(안 지움 쪽)", cnt["unknown"] == 1, cnt)

print("⑤ 금지 시간에는 안 돎")
for nm, qt in (("출근 08:50~09:30(평일)", dt.datetime(2026, 12, 2, 9, 0)), ("출근 시간(주말)", dt.datetime(2026, 12, 5, 9, 10)),
               ("월 NAS 백업 02:00~07:30", dt.datetime(2026, 11, 30, 3, 0))):
    b_ = files()
    rq = run(qt)
    ck("금지 시간 안 돎 — " + nm, rq["skip"] and files() == b_, rq)

print("⑥ 밤 정리(처음 본 날 기록 → 8일 뒤)")
run(T0 + dt.timedelta(days=9))        # 새 고아들 처음 봄
r3 = run(T0 + dt.timedelta(days=18))
for k_, p_ in kp.items():
    ck("쓰는 곳 있으면 남음 — " + k_, os.path.exists(p_))
ck("모르는 모양 파일 안 지움", os.path.exists(unknown))
ck("옛 방식 고아 파일 지움 + 빈 폴더 치움", not os.path.exists(old_orphan) and not os.path.isdir(os.path.dirname(old_orphan)), r3)
ck("오래 남은 저장 중 임시 파일 지움", not os.path.exists(tmpf), r3)
with _db.db_session() as c:
    lg = c.execute("SELECT action, n, actor_id, user_id, note FROM mail_purge_log WHERE action='night_att_files' ORDER BY id DESC LIMIT 1").fetchone()
ck("이력 = 밤 정리 · 누른 사람 NULL(시스템) · 지운 수 · 크기·까닭 글", lg and lg[0] == "night_att_files" and lg[1] == r3["deleted"] and lg[2] is None
   and "지움" in (lg[4] or "") and "기다림" in (lg[4] or ""), tuple(lg) if lg else None)

print("⑦ 지우기 바로 전에 그 파일 하나를 다시 셈(훑은 뒤 새 메일이 같은 내용을 씀)")
RC = b"fake recheck content"
mr = put("가짜재확인", RC)
prc = fpath(RC)
gone_mail(mr, T0)
age(prc, 30)
run(T0 + dt.timedelta(days=20))
_orig_refs = ms._att_refs


def _refs_then_new_row(c):
    out = _orig_refs(c)            # 쓰는 곳을 센 뒤에 …
    with _db.db_session() as c2:   # … 새 메일 줄이 같은 파일을 가리키게 됨(파일은 건드리지 않음)
        cur = c2.execute("INSERT INTO mail_messages(user_id, direction, subject, is_deleted) VALUES(?,?,?,0)", (A, "in", "가짜새메일"))
        c2.execute("INSERT INTO mail_attachments(mail_id, filename, size, path, sha256) VALUES(?,?,?,?,?)",
                   (cur.lastrowid, "새.txt", len(RC), prc, ms._att_sha256(RC)))
    return out


ms._att_refs = _refs_then_new_row
try:
    r4 = run(T0 + dt.timedelta(days=30))
finally:
    ms._att_refs = _orig_refs
ck("다시 셈에서 쓰는 곳 → 안 지움", os.path.exists(prc), r4)
ck("떼어 낸 임시 이름이 남지 않음", not any(f.endswith(ms._ORPHAN_SFX) for f in files()), files())

print("⑧ 다시 쓰인 옛 파일 = 수정 시각 새로(저장 중 보호)")
RU = b"fake reuse content"
mu = put("가짜재사용1", RU)
pru = fpath(RU)
gone_mail(mu, T0)
age(pru, 30)
put("가짜재사용2", RU)
ck("같은 내용 다시 저장 → 수정 시각 지금", time.time() - os.path.getmtime(pru) < 60)

print("⑨ 한 밤 상한")
lim = []
for i in range(3):
    d_ = ("fake limit %d" % i).encode()
    mm = put("가짜상한%d" % i, d_)
    gone_mail(mm, T0)
    age(fpath(d_), 30)
    lim.append(fpath(d_))
run(T0 + dt.timedelta(days=40))
r5 = run(T0 + dt.timedelta(days=50), max_files=1)
ck("상한 1 → 1개만 지움 · 멈춤 까닭", r5["deleted"] == 1 and sum(1 for p_ in lim if os.path.exists(p_)) == 2 and "상한" in r5["stop"], r5)
r6 = run(T0 + dt.timedelta(days=51))
ck("다음 밤에 이어서", sum(1 for p_ in lim if os.path.exists(p_)) == 0, r6)

print("⑩ 안전 멈춤 — 첨부 줄이 하나도 없는 DB 인데 파일만 있으면 안 지움")
_keep_path = _db.DB_PATH
so = sys.stdout
sys.stdout = io.StringIO()
try:
    _db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_morphan2_"), "knk.db")
    _db.init_db()
finally:
    sys.stdout = so
lone = os.path.join(ms._att_dir(), "sha256", "ab", "ab" + "0" * 62)
os.makedirs(os.path.dirname(lone), exist_ok=True)
open(lone, "wb").write(b"fake lone")
age(lone, 40)
run(T0)
r7 = run(T0 + dt.timedelta(days=10))
ck("줄 0 · 파일만 → 멈춤 · 파일 그대로", os.path.exists(lone) and r7["stop"] and r7["deleted"] == 0, r7)
_db.DB_PATH = _keep_path

print("⑪ 관리 화면 — admin·ceo 만 · 미리 세기 줄")
from starlette.testclient import TestClient  # noqa: E402
_who = {"u": None}
m.get_user = lambda req: _who["u"]
k = TestClient(m.app, base_url="http://127.0.0.1:5096", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
_who["u"] = {"id": MEM, "role": "member", "name": "시험", "login_id": "t_oa_mem", "lang": "ko"}
r = k.get("/admin/mail-purge")
ck("직원 → 관리 화면 못 봄(303)", r.status_code == 303, r.status_code)
r = k.get("/admin/mail-purge/orphan-files")
ck("직원 → 미리 세기 403", r.status_code == 403, r.status_code)
_who["u"] = {"id": ADM, "role": "admin", "name": "시험", "login_id": "t_oa_adm", "lang": "ko"}
b_ = files()
r = k.get("/admin/mail-purge")
ck("관리자 → 화면에 안 쓰는 첨부 줄 · 마지막 밤 정리 결과", r.status_code == 200 and "아무 메일도 쓰지 않는 첨부 파일" in r.text
   and "마지막 밤 정리" in r.text and "✅ 완료 — 지움" in r.text, r.status_code)
ck("관리 화면에 지우는 단추 없음(밤 자동만)", "orphan-files/run" not in r.text and "purge_orphan" not in r.text)
r = k.get("/admin/mail-purge/orphan-files")
j = r.json() if r.status_code == 200 else {}
ck("관리자 → 미리 세기 JSON(수·크기·하실 일 없음 판단 재료)", j.get("ok") and "n" in j and "size_txt" in j, j)
ck("미리 세기 화면 뒤 파일 그대로", files() == b_)

print("⑫ 밤 23:30 틀 — 완전 삭제 대기 정리 바로 뒤 · 줄이기 전")
src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
tick = src[src.index("def _mail_vacuum_tick"):src.index("def _start_mail_vacuum_scheduler")]
ck("순서 = 대기 정리 → 안 쓰는 첨부 → 줄이기", "purge_orphan_att_files" in tick and
   tick.index("purge_expired_pending") < tick.index("purge_orphan_att_files") < tick.index("_mail_vacuum_busy_and_run()"))

print("\n결과: %d/%d" % (len(P), len(P) + len(F)))
sys.exit(1 if F else 0)
