# -*- coding: utf-8 -*-
"""하이웍스에서 옮겨 오기 시험 — 임시 DB · 가짜 메일(eml·mbox·zip 을 시험 안에서 만듦) · 운영·실제 하이웍스·실제 메일 무접촉.
대표 11-27 「최대한 쉽게 설명을 포함해서 만들어 · 직원들이 직접 내용 보고 쉽게 · 자꾸 나한테 질문하게 하지 말고」
확인: ① 붙여넣기 해석(탭·여러 칸 빈칸·한 칸 빈칸·머리줄·「수정 삭제」·쪽 번호·칸마다 줄바꿈·중복·옮길 수 없는 종류)
        · 미리 보기 상태(새로·이미 있음·다른 폴더·위 줄과 같음) · 체크 안 한 것은 저장 안 됨 · 지금부터/지난 메일도 · ↺ 되돌리기
      ③ 파일 해석(zip 폴더 구조·zip 안 mbox·zip 안 zip·eml·mbox(.txt)·윈도 한글 zip 이름·메일 아닌 파일) · 폴더 이름 정하기
        · 이미 있는 메일 옮기기 · 다른 폴더에 둔 것·지운 것 그대로 · 새로 저장(원래 날짜) · 내가 보낸 메일 = 보낸 메일함
        · 두 번 넣어도 한 번 · 멈춤 → 이어 하기 · 너무 큰 메일 · 남의 메일함 안 건드림
      화면·주소: 화면 200 · 입구 · 조각 올리기 → 파일 안 보기 → 넣기 · 다른 사이트 POST 403 · 남의 파일 못 만짐 · 남의 진행 안 보임
사용: py -3.13 _검증/mail_hiworks_move_test.py"""
import io
import json
import os
import sys
import tempfile
import threading
import time
import zipfile
from email.message import EmailMessage

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
    _TMP = tempfile.mkdtemp(prefix="knk_hwm_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_folders as mf
    from app import mail_hiworks_move as hwm
    from app import mail_hiworks_folders as mhw
    from app import mail_import_outlook as mio
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
        print("  [FAIL]", name, "<-", str(extra)[:600])


ME, OTHER = 9701, 9702
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(?,?,?,?,?,?,?)",
              (ME, "t9701", "가짜직원", "member", 1, "x", "hong@knknara.co.kr"))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email) VALUES(?,?,?,?,?,?,?)",
              (OTHER, "t9702", "남직원", "member", 1, "x", "kim@knknara.co.kr"))
_DISK = {"free": 500 * 1024 ** 3, "total": 1000 * 1024 ** 3, "ok": True}
mio.disk_state = lambda path=None: dict(_DISK)


def raw_mail(mid, frm, subj, body="가짜 본문", to="hong@knknara.co.kr", recv="Mon, 02 Nov 2026 09:00:00 +0900"):
    e = EmailMessage()
    if recv:
        e["Received"] = "from mx.example by pop.example; " + recv
    e["From"] = frm
    e["To"] = to
    e["Subject"] = subj
    e["Date"] = "Mon, 02 Nov 2026 08:59:00 +0900"
    if mid:
        e["Message-ID"] = "<%s>" % mid
    e.set_content(body)
    return e.as_bytes()


def mbox(msgs):
    out = b""
    for raw in msgs:
        body = b"\n".join((b">" + ln if ln.startswith(b"From ") else ln) for ln in raw.replace(b"\r\n", b"\n").split(b"\n"))
        out += b"From MAILER-DAEMON Mon Nov  2 09:00:00 2026\n" + body + b"\n\n"
    return out


# ═══ ① 붙여넣기 해석 ═══════════════════════════════════════════
print("[1] 붙여넣기 해석")
PASTE1 = """메일 환경설정
기본 설정\t메일함 관리\t메일 자동분류\t스팸 관리
분류 대상\t분류 조건\t조건 내용\t이동할 메일함\t관리
보낸 사람\t일치\tboss@partner.example\t주간업무\t수정 삭제
보낸 사람\t포함\tbank-x.example\t자금일보\t수정\t삭제
보낸 사람  포함  @steel.example  받은메일함 > 거래처 > 철강  수정  삭제
제목\t포함\t[주간보고]\t주간업무\t수정 삭제
받는 사람\t일치\tsales@knknara.co.kr\t영업\t수정 삭제
보낸 사람\t포함하지 않음\tspam.example\t기타\t수정 삭제
보낸 사람\t포함\tkim\t김씨\t수정 삭제
보낸 사람\t일치\tjunk@ad.example\t휴지통\t수정 삭제
처음 이전 1 2 3 다음 마지막
"""
rows, left = hwm.parse_rules(PASTE1)
check("규칙 8줄 읽음(머리줄·쪽 번호·메뉴 글은 뺌)", len(rows) == 8, [(r["target"], r["cond"], r["value"]) for r in rows])
check("한 칸 띄어쓰기 줄도 읽음", bool(hwm.parse_rules("보낸 사람 일치 one@solo.example 혼자폴더 수정 삭제")[0]))
cellwise = "보낸 사람\n일치\nline@cell.example\n줄바꿈폴더\n수정\n삭제\n보낸 사람\n포함\ncell2.example\n줄바꿈폴더2\n"
r2, _l = hwm.parse_rules(cellwise)
check("칸마다 줄이 바뀐 붙여넣기도 읽음", len(r2) == 2 and r2[0]["value"] == "line@cell.example", r2)
r3, _l = hwm.parse_rules(PASTE1 + "\n" + PASTE1)
check("같은 쪽을 두 번 붙여도 한 번만", len(r3) == 8, len(r3))
nested = [r for r in rows if r["value"].startswith("@steel")][0]
check("「받은메일함 > 거래처 > 철강」 → 거래처 › 철강", nested["dest"] == ["거래처", "철강"], nested)
conv = {r["value"]: hwm.convert(r) for r in rows}
check("보낸 사람 일치 주소 → 사람 규칙", conv["boss@partner.example"][:2] == ("email", "boss@partner.example"), conv["boss@partner.example"])
check("보낸 사람 포함 회사 주소 → 회사 규칙", conv["bank-x.example"][:2] == ("domain", "bank-x.example"), conv["bank-x.example"])
check("@회사 주소도 회사 규칙", conv["@steel.example"][:2] == ("domain", "steel.example"))
check("제목 규칙 = 옮길 수 없음(이유)", conv["[주간보고]"][0] is None and "제목" in conv["[주간보고]"][2])
check("받는 사람 규칙 = 옮길 수 없음", conv["sales@knknara.co.kr"][0] is None and "받는 사람" in conv["sales@knknara.co.kr"][2])
check("포함하지 않음 = 옮길 수 없음", conv["spam.example"][0] is None and "포함하지 않음" in conv["spam.example"][2])
check("주소 일부 글자 = 옮길 수 없음", conv["kim"][0] is None)
check("휴지통으로 = 옮길 수 없음", conv["junk@ad.example"][0] is None and "휴지통" in conv["junk@ad.example"][2])

# ═══ ① 미리 보기 · 저장 · 되돌리기 ═══════════════════════════════
print("[2] 미리 보기·저장·되돌리기")
with _db.db_session() as c:
    mf.ensure(c)
    WK = mf.add_folder(c, ME, "주간업무")
    OTHERF = mf.add_folder(c, ME, "예전자금")
    undo = {"add": [], "del": [], "pins": []}
    mf._put_rule(c, ME, "email", "boss@partner.example", "f%d" % WK, "", undo)          # 이미 있는 규칙
    mf._put_rule(c, ME, "domain", "bank-x.example", "f%d" % OTHERF, "", undo)           # 다른 폴더로 가는 규칙
    A, _ = ms.store_inbound(c, to_email="hong@knknara.co.kr", owner_id=ME, from_email="boss@partner.example",
                            subject="이미 있는 메일 A", text="a", run_ai=False, message_id="a1@x")
    B, _ = ms.store_inbound(c, to_email="hong@knknara.co.kr", owner_id=ME, from_email="boss@partner.example",
                            subject="이미 다른 폴더 B", text="b", run_ai=False, message_id="b1@x")
    C, _ = ms.store_inbound(c, to_email="hong@knknara.co.kr", owner_id=ME, from_email="x@partner.example",
                            subject="지운 메일 C", text="c", run_ai=False, message_id="c1@x")
    S1, _ = ms.store_inbound(c, to_email="hong@knknara.co.kr", owner_id=ME, from_email="a@steel.example",
                             subject="철강 옛 메일", text="s", run_ai=False, message_id="s1@x")
    M1, _ = ms.store_inbound(c, to_email="hong@knknara.co.kr", owner_id=ME, from_email="solo@norule.example",
                             subject="규칙 없는 옛 메일 M", text="m", run_ai=False, message_id="m1@x")
    MYF = mf.add_folder(c, ME, "내가 만든 다른 폴더")
    c.execute("UPDATE mail_messages SET fd_pin=? WHERE id=?", ("f%d" % MYF, B))
    c.execute("UPDATE mail_messages SET is_deleted=1 WHERE id=?", (C,))
    X, _ = ms.store_inbound(c, to_email="kim@knknara.co.kr", owner_id=OTHER, from_email="boss@partner.example",
                            subject="남의 메일", text="o", run_ai=False, message_id="d1@x")
    n_rules0 = c.execute("SELECT COUNT(*) FROM mail_move_rules WHERE user_id=?", (ME,)).fetchone()[0]
    pv = hwm.preview_rules(c, ME, PASTE1)
by = {r["value"]: r for r in pv["rows"]}
check("이미 있는 규칙 = 이미 있음(체크 안 됨)", by["boss@partner.example"]["status"] == "have" and not by["boss@partner.example"]["checked"])
check("다른 폴더로 가는 규칙 = 기본 체크 해제·이름 보임", by["bank-x.example"]["status"] == "other" and not by["bank-x.example"]["checked"]
      and by["bank-x.example"]["other_folder"] == "예전자금", by["bank-x.example"])
check("새 규칙 = 새로·기본 체크·새로 만듦 표시", by["@steel.example"]["status"] == "new" and by["@steel.example"]["checked"]
      and by["@steel.example"]["folder_new"], by["@steel.example"])
check("지난 메일 수 미리(철강 1통)", by["@steel.example"]["more"] == 1, by["@steel.example"])
check("옮길 수 없는 줄도 이유와 함께 보임", pv["n_no"] == 5 and all(r["why"] for r in pv["rows"] if not r["ok"]), pv["n_no"])
with _db.db_session() as c:
    pvd = hwm.preview_rules(c, ME, "보낸 사람\t일치\tdup@d.example\t가\n보낸 사람\t일치\tdup@d.example\t나\n")
check("같은 보낸 사람 두 줄 = 아래 줄은 「위 줄과 같음」(체크 해제)", [r["status"] for r in pvd["rows"]] == ["new", "dup"], [r["status"] for r in pvd["rows"]])
with _db.db_session() as c:
    out0 = hwm.save_rules(c, ME, PASTE1, [], False)
    n_rules1 = c.execute("SELECT COUNT(*) FROM mail_move_rules WHERE user_id=?", (ME,)).fetchone()[0]
check("체크 없이 저장 = 아무것도 안 바뀜", out0["saved"] == 0 and n_rules1 == n_rules0, (out0, n_rules0, n_rules1))
with _db.db_session() as c:
    nf0 = c.execute("SELECT COUNT(*) FROM mail_folders WHERE user_id=?", (ME,)).fetchone()[0]
    out = hwm.save_rules(c, ME, PASTE1, [by["@steel.example"]["id"], by["boss@partner.example"]["id"], "가짜|번호|x",
                                         by["[주간보고]"]["id"]], False)
    rr = c.execute("SELECT * FROM mail_move_rules WHERE user_id=? AND kind='domain' AND pattern='steel.example'", (ME,)).fetchall()
    nf1 = c.execute("SELECT COUNT(*) FROM mail_folders WHERE user_id=?", (ME,)).fetchone()[0]
    bank = c.execute("SELECT target FROM mail_move_rules WHERE user_id=? AND pattern='bank-x.example'", (ME,)).fetchall()
    st = hwm.rules_state(c, ME)
check("체크한 새 규칙만 저장(이미 있음·옮길 수 없음·가짜 번호는 건너뜀)", out["saved"] == 1 and out["have"] == 1 and out["skipped"] == 2, out)
check("지금부터만 = 언제부터 칸 채움", len(rr) == 1 and rr[0]["since"], [dict(x) for x in rr])
check("없던 폴더 거래처 › 철강 새로 만듦(2개)", nf1 - nf0 == 2 and out["made"] == 2, (nf0, nf1, out))
check("체크 안 한 다른 폴더 규칙은 그대로", [b["target"] for b in bank] == ["f%d" % OTHERF], [dict(b) for b in bank])
check("저장 정보·되돌리기 가능", st.get("n") == 1 and st.get("can_undo"), st)
with _db.db_session() as c:
    u = hwm.undo_rules(c, ME)
    rr = c.execute("SELECT COUNT(*) FROM mail_move_rules WHERE user_id=? AND pattern='steel.example'", (ME,)).fetchone()[0]
    nf2 = c.execute("SELECT COUNT(*) FROM mail_folders WHERE user_id=?", (ME,)).fetchone()[0]
    st2 = hwm.rules_state(c, ME)
    u2 = hwm.undo_rules(c, ME)
check("↺ 되돌리기 = 규칙·새 폴더 지움", u["ok"] and rr == 0 and nf2 == nf0, (u, rr, nf2, nf0))
check("두 번 되돌리기 = 거절", st2.get("undone") and not st2.get("can_undo") and not u2["ok"], (st2, u2))
with _db.db_session() as c:
    out = hwm.save_rules(c, ME, PASTE1, [by["@steel.example"]["id"]], True)
    rr = c.execute("SELECT since FROM mail_move_rules WHERE user_id=? AND pattern='steel.example'", (ME,)).fetchall()
    res = mf.classify(c, ME)
    sk = mf.mail_where(res, dict(c.execute("SELECT * FROM mail_messages WHERE id=?", (S1,)).fetchone())) if hasattr(mf, "mail_where") else {}
    mf.set_rule(c, ME, WK, "zzz@other.example", when="new")   # 그 뒤 다른 옮기기
    st3 = hwm.rules_state(c, ME)
check("지난 메일도 = 언제부터 빈칸(처음부터)", len(rr) == 1 and rr[0]["since"] == "", [dict(x) for x in rr])
check("그 뒤 다른 옮기기를 하면 여기서 되돌리기 안 됨(안내)", not st3.get("can_undo"), st3)

# ═══ ③ 파일 해석 ════════════════════════════════════════════════
print("[3] 파일 해석·폴더 이름")
W = os.path.join(_TMP, "files")
os.makedirs(W, exist_ok=True)


class _FakeInfo:
    def __init__(self, name):
        self.filename = name.encode("cp949").decode("cp437")
        self.flag_bits = 0


check("윈도 한글 zip 이름(cp949) 바르게", hwm._zname(_FakeInfo("주간업무/메일.eml")) == "주간업무/메일.eml", hwm._zname(_FakeInfo("주간업무/메일.eml")))
MY_SENT = raw_mail("sent1@x", "hong@knknara.co.kr", "내가 보낸 회신", to="boss@partner.example")
Z1 = os.path.join(W, "hong@knknara.co.kr_메일백업_20261127.zip")
with zipfile.ZipFile(Z1, "w") as z:
    z.writestr("hong@knknara.co.kr/받은메일함/주간업무/0001.eml", raw_mail("a1@x", "boss@partner.example", "이미 있는 메일 A", "a"))
    z.writestr("hong@knknara.co.kr/받은메일함/주간업무/0002.eml", raw_mail("b1@x", "boss@partner.example", "이미 다른 폴더 B", "b"))
    z.writestr("hong@knknara.co.kr/받은메일함/주간업무/0003.eml", raw_mail("c1@x", "x@partner.example", "지운 메일 C", "c"))
    z.writestr("hong@knknara.co.kr/받은메일함/주간업무/0004.eml", raw_mail("d1@x", "boss@partner.example", "새 메일 D1",
                                                                       "From 으로 시작하는 줄\n본문"))
    z.writestr("hong@knknara.co.kr/받은메일함/주간업무/0005.eml", raw_mail("", "boss@partner.example", "번호 없는 새 메일"))
    z.writestr("hong@knknara.co.kr/받은메일함/주간업무/0006.eml", MY_SENT)
    z.writestr("hong@knknara.co.kr/받은메일함/주간업무/0007.eml", raw_mail("m1@x", "solo@norule.example", "규칙 없는 옛 메일 M", "m"))
    z.writestr("hong@knknara.co.kr/받은메일함/자금일보.mbox", mbox([raw_mail("f%d@x" % i, "fin@bank-x.example", "자금일보 %d" % i,
                                                                         "본문 %d\nFrom 은행 알림" % i) for i in range(3)]))
    z.writestr("hong@knknara.co.kr/받은메일함/읽어보세요.pdf", b"%PDF-1.4 fake")
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as zi:
        zi.writestr("홍길동/g1.eml", raw_mail("g1@x", "gil@free.example", "홍길동 메일"))
    z.writestr("hong@knknara.co.kr/받은메일함/사람별.zip", inner.getvalue())
ents, bad = hwm.entries(Z1, os.path.basename(Z1))
gids = sorted({e[0] for e in ents})
check("zip 안 폴더·mbox·zip 안 zip 모두 찾음", any(g.endswith("주간업무") for g in gids) and any(g.endswith("자금일보") for g in gids)
      and any("홍길동" in g for g in gids), gids)
check("메일 아닌 파일 = 건너뜀 목록", any(b.endswith(".pdf") for b in bad), bad)
mails = list(hwm.iter_mail(ents))
check("모든 메일 한 통씩(eml 7 + mbox 3 + zip 안 1 = 11)", len(mails) == 11, len(mails))
mb = [r for g, r in mails if g.endswith("자금일보")]
check("mbox 안 「>From 」 되살림", all(b"\nFrom " in r for r in mb), mb[0][-80:] if mb else "")
sg = hwm.suggest(sorted({e[0] for e in ents}), os.path.basename(Z1))
names = {g: "/".join(p) for g, (p, n) in sg.items()}
check("zip 안 zip 메일함 경로 = 바깥 폴더 + zip 이름 + 안 폴더", any(g.endswith("받은메일함/사람별/홍길동") for g in gids), gids)
check("폴더 이름: 계정·받은메일함 떼고 주간업무·자금일보·사람별/홍길동",
      sorted(names.values()) == sorted(["주간업무", "자금일보", "사람별/홍길동"]), names)
E1 = os.path.join(W, "주간업무_백업_20261127.eml")
open(E1, "wb").write(raw_mail("e1@x", "boss@partner.example", "eml 하나"))
ents_e, _b = hwm.entries(E1, os.path.basename(E1))
check(".eml 하나 = 한 통 · 이름에서 「주간업무」", len(list(hwm.iter_mail(ents_e))) == 1
      and hwm.suggest([""], os.path.basename(E1))[""][0] == ["주간업무"], hwm.suggest([""], os.path.basename(E1)))
T1 = os.path.join(W, "mailbox_export.txt")
open(T1, "wb").write(mbox([raw_mail("t%d@x" % i, "t@txt.example", "txt %d" % i) for i in range(2)]))
ents_t, _b = hwm.entries(T1, os.path.basename(T1))
check(".txt 로 된 mbox = 두 통 · 이름이 비면 「하이웍스 옛 메일」", len(list(hwm.iter_mail(ents_t))) == 2
      and hwm.suggest([""], "mailbox_export.txt")[""][0] == ["하이웍스 옛 메일"], hwm.suggest([""], "mailbox_export.txt"))
N1 = os.path.join(W, "그림.png")
open(N1, "wb").write(b"\x89PNG\r\n\x1a\nfake")
check("메일이 아닌 파일 = 읽을 것 없음", hwm.entries(N1, "그림.png")[0] == [])


# ═══ ③ 넣기 ═════════════════════════════════════════════════════
print("[4] 넣기")


def upload_file(c_uid, path, name=None):
    with _db.db_session() as c:
        b = hwm.begin(c, c_uid, name or os.path.basename(path), os.path.getsize(path))
    assert b["ok"], b
    with open(path, "rb") as src, open(hwm._tmp_path(c_uid, b["id"]), "wb") as dst:
        dst.write(src.read())
    with _db.db_session() as c:
        hwm.chunk_done(c, c_uid, b["id"], os.path.getsize(path))
    return b["id"]


fid = upload_file(ME, Z1)
sc = hwm.scan(_db.db_session, ME, fid)
G = {g["label"].split("/")[-1]: g for g in sc["file"]["groups"]}
check("파일 안 보기 = 메일함 셋 · 통수", sc["ok"] and G.get("주간업무", {}).get("n") == 7 and G.get("자금일보", {}).get("n") == 3
      and G.get("홍길동", {}).get("n") == 1, sc)
with _db.db_session() as c:
    cnt_other0 = c.execute("SELECT COUNT(*), MAX(COALESCE(fd_pin,'')) FROM mail_messages WHERE user_id=?", (OTHER,)).fetchone()
plan = {G["주간업무"]["gid"]: "주간업무", G["자금일보"]["gid"]: "자금일보", G["홍길동"]["gid"]: None}
ok, why = hwm.start(_db.db_session, ME, fid, plan, wait=True)
with _db.db_session() as c:
    f = hwm.public(hwm._row(c, ME, fid))
    def pin(mid_):
        return c.execute("SELECT COALESCE(fd_pin,'') AS p FROM mail_messages WHERE id=?", (mid_,)).fetchone()["p"]
    pA, pB, pC, pM = pin(A), pin(B), pin(C), pin(M1)
    d1 = c.execute("SELECT * FROM mail_messages WHERE user_id=? AND subject='새 메일 D1'", (ME,)).fetchone()
    sent = c.execute("SELECT * FROM mail_messages WHERE user_id=? AND subject='내가 보낸 회신'", (ME,)).fetchall()
    fin = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND subject LIKE '자금일보 %' AND fd_pin<>''", (ME,)).fetchone()[0]
    gil = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND subject='홍길동 메일'", (ME,)).fetchone()[0]
    cnt_other1 = c.execute("SELECT COUNT(*), MAX(COALESCE(fd_pin,'')) FROM mail_messages WHERE user_id=?", (OTHER,)).fetchone()
    nmail1 = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=?", (ME,)).fetchone()[0]
check("넣기 끝", ok and f["state"] == "done", (ok, why, f))
check("이미 있던 A = 내 규칙이 이미 주간업무로 보냄 → 그대로(이미 그 폴더)", pA == "" and f["already"] == 1, (pA, WK, f))
check("이미 있던 M(규칙 없음) = 주간업무 폴더로 옮김", pM == "f%d" % WK and f["moved"] == 1, (pM, WK, f))
check("내가 다른 폴더에 둔 B = 그대로", pB == "f%d" % MYF and f["kept"] == 1, (pB, f))
check("지운 C = 그대로(지운 채)", pC == "" and f["other"] == 1, (pC, f))
check("새 메일 D1 = 저장 · 주간업무 · 읽음 · 원래 날짜", d1 is not None and d1["fd_pin"] == "f%d" % WK and d1["is_read"] == 1
      and (d1["received_at"] or "").startswith("2026-11-02"), dict(d1) if d1 else None)
check("내가 보낸 메일 = 보낸 메일함", len(sent) == 1 and sent[0]["direction"] == "out" and f["sent"] == 1, (f, [dict(s) for s in sent]))
check("mbox 자금일보 3통 = 자금일보 폴더", fin == 3, fin)
check("넣지 않기로 한 메일함(홍길동) = 안 들어감", gil == 0, gil)
check("수 맞음(처리 = 전체 10)", f["done"] == 10 and f["total"] == 10, f)
check("남의 메일함 그대로", cnt_other0[0] == cnt_other1[0] and cnt_other0[1] == cnt_other1[1], (cnt_other0, cnt_other1))
check("끝나면 임시 파일 지움", not os.path.exists(hwm._tmp_path(ME, fid)), hwm._tmp_path(ME, fid))
with _db.db_session() as c:
    cands = mhw.rule_candidates(c, ME)
check("올린 폴더로 규칙 후보(자금일보 = bank-x.example)", any(x["pattern"] == "bank-x.example" for x in cands), cands)

fid2 = upload_file(ME, Z1)
sc2 = hwm.scan(_db.db_session, ME, fid2)
G2 = {g["label"].split("/")[-1]: g for g in sc2["file"]["groups"]}
ok, why = hwm.start(_db.db_session, ME, fid2, {G2["주간업무"]["gid"]: "주간업무", G2["자금일보"]["gid"]: "자금일보"}, wait=True)
with _db.db_session() as c:
    f2 = hwm.public(hwm._row(c, ME, fid2))
    nmail2 = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=?", (ME,)).fetchone()[0]
check("같은 파일 두 번 = 새로 들어간 메일 0", ok and f2["saved"] == 0 and nmail2 == nmail1, (f2, nmail1, nmail2))

# 멈춤 → 이어 하기
Z2 = os.path.join(W, "큰폴더.zip")
with zipfile.ZipFile(Z2, "w") as z:
    for i in range(8):
        z.writestr("큰폴더/%03d.eml" % i, raw_mail("big%d@x" % i, "many@lot.example", "많은 메일 %d" % i))
    z.writestr("큰폴더/999.eml", raw_mail("huge@x", "many@lot.example", "너무 큰 메일", "가" * 3000))
fid3 = upload_file(ME, Z2)
sc3 = hwm.scan(_db.db_session, ME, fid3)
g3 = sc3["file"]["groups"][0]
_real_parse = ms.parse_raw_email
_calls = {"n": 0}


def _stop_after_3(raw):
    _calls["n"] += 1
    if _calls["n"] == 3:
        with hwm._RUN_LOCK:
            ev = hwm._RUNNING.get(ME)
        if ev:
            ev.set()
    return _real_parse(raw)


_old_max = hwm.MAX_MSG_BYTES
hwm.MAX_MSG_BYTES = 4000
ms.parse_raw_email = _stop_after_3
ok, why = hwm.start(_db.db_session, ME, fid3, {g3["gid"]: g3["folder"]}, wait=True)
ms.parse_raw_email = _real_parse
with _db.db_session() as c:
    f3 = hwm.public(hwm._row(c, ME, fid3))
check("멈추기 = 멈춤 · 임시 파일 남김(이어 하기용)", f3["state"] == "stopped" and 0 < f3["done"] < 9
      and os.path.exists(hwm._tmp_path(ME, fid3)), f3)
ok, why = hwm.start(_db.db_session, ME, fid3, {g3["gid"]: g3["folder"]}, wait=True)
hwm.MAX_MSG_BYTES = _old_max
with _db.db_session() as c:
    f3b = hwm.public(hwm._row(c, ME, fid3))
    n_many = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND from_email='many@lot.example'", (ME,)).fetchone()[0]
check("이어 하기 = 끝 · 처음부터 다시 세지 않음(9)", f3b["state"] == "done" and f3b["done"] == 9 and f3b["total"] == 9, f3b)
check("너무 큰 메일 = 넣지 않고 수만", f3b["big"] == 1 and n_many == 8, (f3b, n_many))
check("폴더 이름 「큰폴더」 새로 만듦", g3["folder"] == "큰폴더", g3)

# ═══ 화면·주소 ═════════════════════════════════════════════════
print("[5] 화면·주소")
_U = {"id": ME}
m.get_user = lambda req: dict(_U, role="member", name="가짜", team_id=None, team_name="", login_id="t%d" % _U["id"],
                              email="hong@knknara.co.kr" if _U["id"] == ME else "kim@knknara.co.kr")
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
r = k.get("/mail/hiworks-move")
check("화면 열림 200", r.status_code == 200, r.status_code)
check("화면: 단계 줄·지금 하실 일·닫기·하이웍스 설명·이유", all(s in r.text for s in ("규칙 옮기기", "하이웍스 규칙 지우기", "옛 메일 올리기",
      "hmMsg", "✕ 닫기", "메일 자동분류", "메일 백업", "이걸 안 하면")), r.text[:300])
r = k.get("/mail/tools")
check("메일 도구에 입구 있음 · 옛 하이웍스 폴더(IMAP) 입구는 그대로 숨김", r.status_code == 200 and "/mail/hiworks-move" in r.text
      and "/mail/hiworks-folders" not in r.text, r.status_code)
r = k.post("/mail/hiworks-move/rules/preview", data={"text": PASTE1})
j = r.json()
check("미리 보기 주소", r.status_code == 200 and j.get("ok") and j.get("n_rows") == 8, r.text[:300])
r = k.post("/mail/hiworks-move/rules/preview", data={"text": PASTE1}, headers={"origin": "https://evil.example"})
check("다른 사이트에서 온 미리 보기 = 막음(403)", r.status_code == 403, r.status_code)
r = k.post("/mail/hiworks-move/rules/save", data={"text": PASTE1, "picked": "[]"})
check("체크 없이 저장 = 거절", r.status_code == 400, r.text[:200])
newid = [x["id"] for x in j["rows"] if x["value"] == "bank-x.example"][0]
r = k.post("/mail/hiworks-move/rules/save", data={"text": PASTE1, "picked": json.dumps([newid]), "past": "0"},
           headers={"origin": "https://evil.example"})
check("다른 사이트에서 온 저장 = 막음(403)", r.status_code == 403, r.status_code)
r = k.post("/mail/hiworks-move/rules/save", data={"text": PASTE1, "picked": json.dumps([newid]), "past": "0"},
           headers={"origin": "https://works.knknara.co.kr"})
check("우리 화면에서 저장 = 됨(다른 폴더 규칙을 체크해 바꿈)", r.status_code == 200 and r.json().get("saved") == 1, r.text[:300])
# 조각 올리기
Z3 = os.path.join(W, "화면시험.zip")
with zipfile.ZipFile(Z3, "w", zipfile.ZIP_STORED) as z:
    for i in range(3):
        z.writestr("화면폴더/%d.eml" % i, raw_mail("ui%d@x" % i, "ui@screen.example", "화면 메일 %d" % i, "x" * 20000))
data = open(Z3, "rb").read()
r = k.post("/mail/hiworks-move/up/begin", data={"name": "화면시험.zip", "size": str(len(data))})
b = r.json()
check("올리기 시작", r.status_code == 200 and b.get("id") and b.get("received") == 0, r.text[:200])
half = len(data) // 2
r = k.post("/mail/hiworks-move/up/chunk?id=%d&off=0" % b["id"], content=data[:half], headers={"content-type": "application/octet-stream"})
check("첫 조각", r.status_code == 200 and r.json().get("received") == half, r.text[:200])
r = k.post("/mail/hiworks-move/up/chunk?id=%d&off=0" % b["id"], content=data[:half], headers={"content-type": "application/octet-stream"})
check("위치가 틀린 조각 = 받은 크기만 알려 줌(두 번 붙지 않음)", r.json().get("where") and r.json().get("received") == half, r.text[:200])
r = k.post("/mail/hiworks-move/up/chunk?id=%d&off=%d" % (b["id"], half), content=data[half:],
           headers={"content-type": "application/octet-stream", "origin": "https://evil.example"})
check("다른 사이트에서 온 조각 = 막음(403)", r.status_code == 403, r.status_code)
r = k.post("/mail/hiworks-move/up/begin", data={"name": "화면시험.zip", "size": str(len(data))})
check("같은 파일 다시 고르면 이어 올리기(받은 크기부터)", r.json().get("id") == b["id"] and r.json().get("received") == half, r.text[:200])
_U["id"] = OTHER
r = k.post("/mail/hiworks-move/up/chunk?id=%d&off=%d" % (b["id"], half), content=data[half:], headers={"content-type": "application/octet-stream"})
check("남의 파일 번호로 조각 = 거절", r.status_code == 400, r.text[:200])
r = k.get("/mail/hiworks-move/status")
check("다른 직원에겐 내 파일 안 보임", r.status_code == 200 and not r.json().get("files"), r.text[:200])
r = k.post("/mail/hiworks-move/scan", data={"id": str(fid)})
check("남의 파일 안 보기 = 거절", r.status_code == 400, r.text[:200])
_U["id"] = ME
r = k.post("/mail/hiworks-move/up/chunk?id=%d&off=%d" % (b["id"], half), content=data[half:], headers={"content-type": "application/octet-stream"})
check("마지막 조각 = 다 올라감", r.status_code == 200 and r.json().get("full"), r.text[:200])
r = k.post("/mail/hiworks-move/scan", data={"id": str(b["id"])})
sj = r.json()
check("파일 안 보기 = 화면폴더 3통", r.status_code == 200 and sj["file"]["groups"][0]["n"] == 3 and sj["file"]["groups"][0]["folder"] == "화면폴더",
      r.text[:300])
check("화면에 서버 경로 안 나감", "tmp" not in sj["file"] and _TMP not in r.text, r.text[:200])
gid = sj["file"]["groups"][0]["gid"]
r = k.post("/mail/hiworks-move/start", data={"id": str(b["id"]), "plan": json.dumps({gid: "화면 폴더/작은"})})
check("넣기 시작(뒤에서)", r.status_code == 200 and r.json().get("ok"), r.text[:300])
t0, fs = time.time(), {}
while time.time() - t0 < 20:
    fs = [x for x in k.get("/mail/hiworks-move/status").json().get("files") if x["id"] == b["id"]][0]
    if fs["state"] != "running":
        break
    time.sleep(0.2)
check("뒤에서 끝남 · 3통 새로", fs.get("state") == "done" and fs.get("saved") == 3, fs)
with _db.db_session() as c:
    sub = c.execute("SELECT f.name, p.name AS pn FROM mail_folders f JOIN mail_folders p ON p.id=f.parent_id WHERE f.user_id=? AND f.name='작은'",
                    (ME,)).fetchone()
check("「화면 폴더/작은」 = 아래 폴더로 만듦", sub is not None and sub["pn"] == "화면 폴더", dict(sub) if sub else None)
r = k.post("/mail/hiworks-move/up/begin", data={"name": "huge.zip", "size": str(hwm.MAX_FILE + 1)})
check("너무 큰 파일 = 거절(안내)", r.status_code == 400 and "GB" in r.json().get("message", ""), r.text[:200])
r = k.post("/mail/hiworks-move/up/begin", data={"name": "outlook.pst", "size": "100"})
check("아웃룩 .pst = 거절(아웃룩 가져오기 안내)", r.status_code == 400 and "아웃룩" in r.json().get("message", ""), r.text[:200])
_DISK.update(ok=False)
r = k.post("/mail/hiworks-move/up/begin", data={"name": "a.zip", "size": "100"})
_DISK.update(ok=True)
check("서버 공간 모자라면 거절", r.status_code == 400 and "공간" in r.json().get("message", ""), r.text[:200])
r = k.post("/mail/hiworks-move/rules/undo", data={})
check("화면 ↺ 되돌리기", r.status_code == 200 and r.json().get("ok"), r.text[:200])

print("\n결과: %d 통과 · %d 실패" % (P, F))
sys.exit(1 if F else 0)
