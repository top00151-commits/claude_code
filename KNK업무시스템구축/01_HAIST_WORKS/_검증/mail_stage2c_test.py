# -*- coding: utf-8 -*-
"""메일 2단계(대표 2026-11-20 「다음 진행해」) — 하루 숫자 · 큰 파일 받아 간 시각 · 휴가 → 부재중 제안 · 받는 사람 휴가 · 거래처 진행 상황.
운영 무접촉 · 임시 DB(knk_ms2c_*) · **가짜 이음 명부**(로컬 작은 서버 _검증/fake_eum_directory.py) · 가짜 메일·가짜 사람·가짜 회사·가짜 열쇠.

증명할 것
  ⑥ 받은편지함 위 한 줄: 회신 필요 · 오늘까지 기한 · 답 기다림(기한 지난 것) · 오늘 예약 — 누르면 그 목록 · 0 은 흐리게 · 모두 0 이면 줄 없음
     · 예전 「⏳ 답 안 온 메일」 띠는 이 줄로 합침(따로 안 나옴) · 인쇄 때 숨김
  ⑦ 큰 파일: 받아 갈 때마다 시각 기록(링크 번호·시각만 · 주소/IP 칸 없음) · 보낸 사람 읽기 화면에 「처음 받아 감 · N번 · 마지막」
     · 남이 올린 파일은 안 보임 · 시각 = 보는 사람 소속(본사 +9 · 베트남 +7) · 200줄 넘으면 처음 것·최근 것 남김
  🏖 휴가 → 부재중 제안: 명부에 휴가면 제안 · **저절로 켜지 않음** · 「켜기」= 날짜 채운 설정 화면(저장해야 켜짐) · 이미 켜져 있으면 안 보임
     · 명부는 서버에서만 · 5분 캐시(여러 번 열어도 한 번) · 실패·느림·키 거부 → 화면 정상(띠만 없음) · 실패도 1분 캐시
  받는 사람 휴가: 주소 → 휴가 중인 사내 직원만 「이름 직책 부서 · ~날짜」 · 명부 주소가 달라도 웍스 사번으로 찾음 · 바깥·안 휴가는 없음
  🏢 거래처 진행 상황: 거래처 폴더와 같은 규칙(정확 일치 → 한 거래처만 가리키는 회사 주소) · 둘이면 안 보임 · 진행 중·최근 수주 · 웍스 화면 연결
     · 매출 보기 권한(can_view_sales) 없는 사람에겐 칸·금액 모두 안 보임 · 웍스 표는 바뀌지 않음(읽기만)
  공유키 값은 응답·화면·서버 기록 어디에도 안 나옴
"""
import _mail_ico; _mail_ico.install()  # noqa: E402  11-28 4단계: 화면의 선 아이콘을 [i:이름] 으로 읽음(그림 문자 대신 · 아이콘 이름까지 확인)
import io
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
KEY = "fake-dir-key-" + os.urandom(8).hex()
os.environ["KNK_SSO_SERVICE_KEY"] = KEY
os.environ["KNK_RUN_MAIL_FETCH"] = "0"


class _Tee(object):
    def __init__(self, real, buf):
        self.real, self.buf = real, buf

    def write(self, t):
        self.buf.write(t)
        return self.real.write(t)

    def flush(self):
        self.real.flush()


LOG = io.StringIO()
_so = sys.stdout
sys.stdout = LOG
try:
    from cryptography.fernet import Fernet
    os.environ.setdefault("KNK_MAIL_KEY", Fernet.generate_key().decode())
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_ms2c_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_glance as mg
    from app import mail_work as mw
    from app import sso_client as sso
finally:
    sys.stdout = _Tee(_so, LOG)
import fake_eum_directory as fd  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

P = F = 0


def check(name, cond, extra=""):
    global P, F
    if cond:
        P += 1
        print("  [PASS]", name)
    else:
        F += 1
        print("  [FAIL]", name, "<-", str(extra)[:400])


SRV, BASE = fd.start()
fd.FAKE["key"] = KEY
sso.MESSENGER_INTERNAL_BASE = BASE

with _db.db_session() as c:
    try:
        c.execute("ALTER TABLE users ADD COLUMN employee_no TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN can_view_sales INTEGER DEFAULT 0")
    except Exception:
        pass
    c.execute("UPDATE users SET login_id=login_id||'_x' WHERE login_id IN ('kjr')")
    c.execute("INSERT INTO teams(id, code, name, display_order, entity) VALUES(9801,'T9801','시험품질팀',3,'KOR')")
    c.execute("INSERT INTO teams(id, code, name, display_order, entity) VALUES(9802,'V9802','시험구매팀',60,'VN')")
    ppl = [(9801, "kjr", "시험대표", "ceo", "5", 9801, "", 0), (9802, "t1102", "조민혁", "member", "1102", 9801, "과장", 0),
           (9803, "tvn201", "쩐 티 하", "member", "VN201", 9802, "", 0), (9804, "t777", "영업담당", "member", "777", 9801, "대리", 1),
           (9805, "t888", "다른사람", "member", "888", 9801, "", 0)]
    for uid, lid, nm, role, emp, team, rank, cvs in ppl:
        c.execute("INSERT INTO users(id, login_id, name, role, is_active, password, email, team_id, rank, employee_no, can_view_sales) "
                  "VALUES(?,?,?,?,1,'x',?,?,?,?,?)", (uid, lid, nm, role, lid + "@knknara.co.kr", team, rank, emp, cvs))
U = {k: {"id": uid, "role": role, "name": nm, "team_id": team, "team_name": "", "employee_no": emp, "rank": rank,
         "login_id": lid, "email": lid + "@knknara.co.kr", "can_view_sales": cvs}
     for k, (uid, lid, nm, role, emp, team, rank, cvs) in zip(("ceo", "jo", "vn", "sales", "other"), ppl)}
_U = {"v": dict(U["ceo"])}
m.get_user = lambda req: _U["v"]
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})
RESP_TEXT = []


def as_(key):
    _U["v"] = dict(U[key])


def get(path):
    r = k.get(path)
    RESP_TEXT.append(r.text)
    return r


_SEQ = [0]


def put_in(subject, frm="hong@cust-a.example", owner=9801, text="안녕하세요"):
    _SEQ[0] += 1
    with _db.db_session() as c:
        mid, _o = ms.store_inbound(c, to_email="t@knknara.co.kr", from_email=frm, from_name="홍길동", subject=subject, text=text,
                                   owner_id=owner, run_ai=False, message_id="s2c-%d@t" % _SEQ[0])
    return mid


def put_out(subject, body, owner=9801, to="buyer@cust-a.example"):
    with _db.db_session() as c:
        return ms.store_outbound(c, user_id=owner, from_email="kjr@knknara.co.kr", to_email=to, subject=subject, body=body)


def kst_today():
    return (datetime.now(timezone.utc) + timedelta(hours=9)).date()


# ═══════════════════════ ⑥ 메일 하루 숫자 ═══════════════════════
print("\n⑥ 받은편지함 위 메일 하루 숫자")
as_("ceo")
hi = get("/mail/inbox").text
check("숫자가 모두 0 이면 줄 자체가 없음", 'id="mbxDay"' not in hi and "/api/mail/vacation/me" in hi, hi[:100])
today = m._mail_local_today(9)
M1 = put_in("11월 공지 안내", text="참고만 하시면 됩니다.")
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET flag_due=? WHERE id=?", (today, M1))
O1 = put_out("[KNK] 장비 견적서 송부", "견적서 보내 드립니다.")
with _db.db_session() as c:
    mw.ensure(c)
    ok, _msg = mw.set_wait(c, 9801, O1, (kst_today() + timedelta(days=3)).isoformat())
    c.execute("UPDATE mail_messages SET wait_until=? WHERE id=?", ((kst_today() - timedelta(days=1)).isoformat(), O1))
    c.execute("UPDATE mail_messages SET received_at=datetime('now','localtime','-2 day') WHERE id=?", (O1,))
_now9 = m._mail_now_local(9)
_soon = _now9 + timedelta(minutes=2) if _now9.hour < 23 or _now9.minute < 50 else _now9
with _db.db_session() as c:
    S1 = ms.create_scheduled(c, user_id=9801, to_email="a@cust-a.example", cc="", bcc="", subject="오늘 예약", body="x", body_html="",
                             sched_at=m._mail_local_to_server(_soon, 9))
    S2 = ms.create_scheduled(c, user_id=9801, to_email="a@cust-a.example", cc="", bcc="", subject="모레 예약", body="x", body_html="",
                             sched_at=m._mail_local_to_server(_now9 + timedelta(days=2), 9))
hi = get("/mail/inbox").text
seg = hi[hi.find('id="mbxDay"'):hi.find("</nav>", hi.find('id="mbxDay"'))]
check("한 줄이 나옴 · 「오늘 챙길 메일」", 'id="mbxDay"' in hi and "오늘 챙길 메일" in seg, seg[:200])
check("🚩 오늘까지 기한 1 → /mail/inbox?flag=1 (빨강)", 'href="/mail/inbox?flag=1" class="mbx-day-i red"' in seg and "오늘까지 기한 <b>1</b>" in seg, seg)
check("⏳ 답 기다림 1 · 기한 지남 → 주황 · 「답 안 온 메일 1통」 · /mail/waiting · id=mbxWaitBar(합친 칸)",
      'href="/mail/waiting" class="mbx-day-i warn" id="mbxWaitBar"' in seg and "답 기다림 <b>1</b>" in seg and "답 안 온 메일 1통" in seg, seg)
check("⏱ 오늘 예약 1(모레 것은 안 셈) → /mail/sent", 'href="/mail/sent"' in seg and "오늘 예약 <b>1</b>" in seg, seg)
check("0 인 칸(회신 필요 0)은 흐리게", 'href="/mail/inbox?reply=1" class="mbx-day-i zero"' in seg, seg)
check("예전 따로 띠(「바깥 거래처에 보낸 메일 중 정한 날까지」)는 안 나옴 · 줄은 하나", "정한 날까지 답이 없는 것" not in hi and hi.count('id="mbxWaitBar"') == 1)
check("인쇄 때 숨김 · 휴대폰 폭 규칙", "@media print{.mbx-day,.mbx-vac{display:none !important}}" in hi and "@media(max-width:640px){.mbx-day{" in hi)
with _db.db_session() as c:
    c.execute("UPDATE mail_messages SET sched_state='fail', sched_err='시험' WHERE id=?", (S2,))
seg2 = get("/mail/inbox").text
seg2 = seg2[seg2.find('id="mbxDay"'):]
check("못 보낸 예약은 「⚠ 못 보냄 1」 빨강", "[i:triangle-alert] 못 보냄 1" in seg2[:3000] and 'href="/mail/sent" class="mbx-day-i red"' in seg2[:3000])
j = get("/api/mail/counts").json()
check("숫자 입구(/api/mail/counts)에도 오늘 예약", j.get("sched_today") == 1, j)
with _db.db_session() as c:
    end_kr = m._mail_local_to_server(datetime.combine(m._mail_now_local(9).date() + timedelta(days=1), datetime.min.time()), 9)
    end_vn = m._mail_local_to_server(datetime.combine(m._mail_now_local(7).date() + timedelta(days=1), datetime.min.time()), 7)
    d_kr = datetime.strptime(end_kr, "%Y-%m-%d %H:%M:%S")
    d_vn = datetime.strptime(end_vn, "%Y-%m-%d %H:%M:%S")
check("오늘 끝 = 그 사람 소속 자정(베트남은 본사보다 2시간 늦음 · 날짜가 같을 때)",
      (d_vn - d_kr) in (timedelta(hours=2), timedelta(hours=2) - timedelta(days=1), timedelta(hours=2) + timedelta(days=1)), (end_kr, end_vn))
as_("other")
check("다른 사람에게는 내 숫자가 안 섞임(모두 0 → 줄 없음)", 'id="mbxDay"' not in get("/mail/inbox").text)

# ═══════════════════════ ⑦ 큰 파일 받아 간 시각 ═══════════════════════
print("\n⑦ 큰 파일 받아 간 시각")
as_("ceo")
TK = ms.new_large_token()
TK2 = ms.new_large_token()
os.makedirs(ms.large_file_dir(TK), exist_ok=True)
FP = os.path.join(ms.large_file_dir(TK), "drawing.zip")
open(FP, "wb").write(b"PK fake zip")
with _db.db_session() as c:
    ms.register_large_file(c, token=TK, user_id=9801, filename="도면_묶음.zip", mime="application/zip", path=FP, size=123456789)
    ms.register_large_file(c, token=TK2, user_id=9805, filename="남의파일.zip", mime="application/zip", path=FP, size=10)
body = "도면 보내 드립니다.\n" + "\n📎 대용량 첨부파일\n• 도면_묶음.zip\n  https://works.knknara.co.kr/dl/%s\n  https://works.knknara.co.kr/dl/%s\n" % (TK, TK2)
O2 = put_out("[KNK] 도면 송부", body)
hv = get("/mail/%d" % O2).text
check("아직 안 받아 감 → 「아직 받아 가지 않음」 · 남이 올린 파일은 안 보임",
      "📦 큰 파일 받아 간 기록" in hv and "도면_묶음.zip" in hv and "아직 받아 가지 않음" in hv and "남의파일.zip" not in hv[hv.find('id="mvLgf"'):], hv[:200])
r1 = k.get("/dl/%s" % TK)
r2 = k.get("/dl/%s" % TK)
check("받아 가기 두 번(파일 그대로 내려 줌)", r1.status_code == 200 and r1.content == b"PK fake zip" and r2.status_code == 200, r1.status_code)
with _db.db_session() as c:
    cols = [x[1] for x in c.execute("PRAGMA table_info(mail_large_dl)").fetchall()]
    n = c.execute("SELECT COUNT(*) FROM mail_large_dl WHERE token=?", (TK,)).fetchone()[0]
    cnt = c.execute("SELECT download_count FROM mail_large_files WHERE token=?", (TK,)).fetchone()[0]
check("시각 기록 표 = 번호·링크·시각만(받아 간 사람 주소·IP 칸 없음) · 2줄 · 횟수 2", cols == ["id", "token", "at"] and n == 2 and cnt == 2, (cols, n, cnt))
with _db.db_session() as c:
    ids = [x[0] for x in c.execute("SELECT id FROM mail_large_dl WHERE token=? ORDER BY id", (TK,)).fetchall()]
    c.execute("UPDATE mail_large_dl SET at='2026-11-20 14:03:00' WHERE id=?", (ids[0],))
    c.execute("UPDATE mail_large_dl SET at='2026-11-21 09:10:00' WHERE id=?", (ids[1],))
lab_kr = m._mail_local_label("2026-11-20 14:03:00", 9)
lab_vn = m._mail_local_label("2026-11-20 14:03:00", 7)
hv = get("/mail/%d" % O2).text
seg = hv[hv.find('id="mvLgf"'):]
check("보낸 사람 화면 「✅ 처음 받아 감 (본사 시각) · 2번 · 마지막 …」", ("처음 받아 감 %s · 2번 · 마지막 %s" % (lab_kr, m._mail_local_label("2026-11-21 09:10:00", 9))) in seg, seg[:600])
hp = get("/mail/%d/pane" % O2).text
check("읽기 창(목록 오른쪽)에도 같은 기록", "처음 받아 감 %s" % lab_kr in hp)
as_("vn")
with _db.db_session() as c:
    lgf = mg.large_info_for_mail(c, 9801, {"body_text": body}, lambda s: m._mail_local_label(s, m._mail_off(c, U["vn"])))
check("시각 = 보는 사람 소속(베트남 +7 은 본사보다 2시간 이름)", lgf and lgf[0]["first"] == lab_vn and lab_kr != lab_vn
      and int(lab_kr.split()[1][:2]) - int(lab_vn.split()[1][:2]) in (2, -22), (lab_kr, lab_vn, lgf))
as_("other")
O3 = put_out("전달", body, owner=9805)
hv = get("/mail/%d" % O3).text
seg = hv[hv.find('id="mvLgf"'):hv.find('class="mv-body"', hv.find('id="mvLgf"'))] if 'id="mvLgf"' in hv else ""
check("다른 사람 메일엔 그 사람이 올린 파일만(내 파일 기록은 안 보임)", "남의파일.zip" in seg and "도면_묶음.zip" not in seg, seg[:300])
as_("ceo")
_keep = ms.LARGE_DL_KEEP
ms.LARGE_DL_KEEP = 3
with _db.db_session() as c:
    for _ in range(4):
        ms.bump_large_download(c, TK)
    rows = [x[0] for x in c.execute("SELECT at FROM mail_large_dl WHERE token=? ORDER BY id", (TK,)).fetchall()]
    cnt = c.execute("SELECT download_count FROM mail_large_files WHERE token=?", (TK,)).fetchone()[0]
ms.LARGE_DL_KEEP = _keep
check("기록 줄 한도 넘으면 처음 것은 남기고 그 사이 오래된 것부터 지움 · 횟수는 다 셈", len(rows) == 3 and rows[0] == "2026-11-20 14:03:00" and cnt == 6, (rows, cnt))
check("받아 간 사람 정보(주소·IP)는 서버 기록에도 안 찍음", "testclient" not in LOG.getvalue().lower())

# ═══════════════════════ 🏖 휴가 → 부재중 제안 ═══════════════════════
print("\n🏖 휴가 → 부재중 자동 응답 제안")
until_utc = datetime.now(timezone.utc).replace(hour=14, minute=59, second=59, microsecond=0) + timedelta(days=4)
until_iso = until_utc.isoformat()
exp_until = (until_utc + timedelta(hours=9)).date().isoformat()
fd.USERS[:] = [
    {"employee_no": "5", "name_kr": "시험대표", "dept": "경영", "position": "대표", "entity": "KOR", "email": "ceo-other@knknara.co.kr",
     "phone": "010-0000-0000", "active": True, "status": "vacation", "status_label": "🌴 휴가", "status_until": until_iso, "online": False},
    {"employee_no": "1102", "name_kr": "조민혁(이음)", "dept": "품질", "position": "과장", "email": "jo.other@knknara.co.kr",
     "active": True, "status": "vacation", "status_until": until_iso},
    {"employee_no": "VN201", "name_kr": "쩐 티 하", "dept": "구매", "email": "tvn201@knknara.co.kr", "active": True, "status": "working", "status_until": None},
    {"employee_no": "777", "name_kr": "영업담당", "email": "t777@knknara.co.kr", "active": True, "status": "overseas", "status_until": until_iso},
    {"employee_no": "999", "name_kr": "퇴사자", "email": "gone@knknara.co.kr", "active": False, "status": "vacation", "status_until": until_iso},
]
mg.dir_reset()
fd.CALLS.clear()
as_("ceo")
hi = get("/mail/inbox").text
check("받은편지함을 그릴 때는 이음을 부르지 않음(화면이 따로 물음 · 느려도 목록은 바로)", fd.CALLS == [] and 'id="mbxVac" hidden' in hi, fd.CALLS)
j = get("/api/mail/vacation/me").json()
check("내가 휴가(사번 5) → 제안 · 끝 날짜 = 본사 날짜 · 「켜기」= 날짜 채운 설정 화면",
      j.get("show") and j.get("until") == exp_until and j.get("label") == "~" + mg.md_label(exp_until) and j.get("href") == "/mail/autoreply?vac=" + exp_until, j)
for _ in range(4):
    get("/api/mail/vacation/me")
check("여러 번 열어도 이음은 한 번만 부름(5분 캐시) · 키는 머리글로", len(fd.CALLS) == 1 and fd.CALLS[0][1], fd.CALLS)
with _db.db_session() as c:
    st = ms.get_autoreply(c, 9801)
check("제안만 — 부재중 자동 응답은 저절로 켜지지 않음", not st.get("enabled"), st)
ha = get("/mail/autoreply?vac=" + exp_until).text
check("「켜기」 화면: 기간 채움(오늘 ~ 휴가 끝) · 켜기 칸 체크 · 「저장을 눌러야 켜집니다」",
      'id="arVacFill"' in ha and ('value="%s"' % exp_until) in ha and ('id="arStart" value="%s"' % today) in ha
      and 'id="arOn" checked' in ha and "저장」</b>을 눌러야 켜집니다" in ha, ha[ha.find("ar-card"):][:300])
with _db.db_session() as c:
    st = ms.get_autoreply(c, 9801)
check("설정 화면을 열기만 해서는 여전히 꺼짐", not st.get("enabled"), st)
ha = get("/mail/autoreply?vac=1999-01-01").text
check("지난 날짜·엉터리 날짜는 끝 날짜를 채우지 않음", 'id="arEnd" value=""' in ha and "끝나는 날을 몰라" in ha)
r = k.post("/mail/autoreply", data={"enabled": "1", "start_date": today, "end_date": exp_until, "subject": "", "body": "휴가 중입니다", "only_known": "1"})
check("저장을 누르면 켜짐", r.json().get("ok"), r.text[:200])
j = get("/api/mail/vacation/me").json()
check("이미 부재중이 켜져 있으면 제안 안 보임", j.get("ok") and not j.get("show"), j)
ha = get("/mail/autoreply?vac=" + exp_until).text
check("이미 켜져 있으면 설정 화면도 채워 넣지 않음(저장된 값 그대로)", 'id="arVacFill"' not in ha)
k.post("/mail/autoreply", data={"enabled": "0", "start_date": "", "end_date": "", "body": ""})
as_("vn")
j = get("/api/mail/vacation/me").json()
check("휴가 아닌 사람(근무 중) → 제안 없음", j.get("ok") and not j.get("show"), j)
as_("sales")
check("출장(overseas)은 휴가 아님 → 제안 없음(2단계는 휴가만)", not get("/api/mail/vacation/me").json().get("show"))
# 시간대 — 이음 휴가 끝은 UTC ISO
check("휴가 끝 시간대: 11-24 16:30Z → 본사 11/25 · 베트남 11/24", mg.until_local("2026-11-24T16:30:00+00:00", 9) == "2026-11-25"
      and mg.until_local("2026-11-24T16:30:00+00:00", 7) == "2026-11-24")
check("자정 딱 끝(본사 11/25 00:00)은 「~11/24 까지」 · Z 꼴 · 날짜만 · 빈 값", mg.until_local("2026-11-24T15:00:00Z", 9) == "2026-11-24"
      and mg.until_local("2026-11-24", 9) == "2026-11-24" and mg.until_local("", 9) == "" and mg.until_local("엉터리", 9) == "")

print("\n  명부 실패·느림")
as_("ceo")
for mode, why in (("500", "이음 오류(500)"), ("404", "입구 없음(404)"), ("badjson", "JSON 아님")):
    mg.dir_reset()
    fd.FAKE["mode"] = mode
    fd.CALLS.clear()
    j = get("/api/mail/vacation/me").json()
    hi_r = k.get("/mail/inbox")
    check("%s → 띠 없음 · 받은편지함 정상" % why, j.get("ok") and not j.get("show") and hi_r.status_code == 200 and 'id="mbxVac" hidden' in hi_r.text, j)
    get("/api/mail/vacation/me")
    check("%s → 1분 동안 다시 안 부름" % why, len(fd.CALLS) == 1, fd.CALLS)
mg.dir_reset()
fd.FAKE["mode"] = "ok"
fd.FAKE["key"] = "wrong-key"
j = get("/api/mail/vacation/me").json()
check("공유키 거부(403) → 띠 없음", j.get("ok") and not j.get("show"), j)
fd.FAKE["key"] = KEY
mg.dir_reset()
fd.FAKE["mode"] = "slow"
fd.FAKE["slow"] = mg.DIR_TIMEOUT + 2
t0 = time.time()
j = get("/api/mail/vacation/me").json()
dt = time.time() - t0
check("느림 → 정한 시간(%.0f초)쯤에서 끊고 띠 없음" % mg.DIR_TIMEOUT, not j.get("show") and dt < mg.DIR_TIMEOUT + 1.5, dt)
t0 = time.time()
hi_r = k.get("/mail/inbox")
check("느린 동안에도 받은편지함은 바로 열림", hi_r.status_code == 200 and time.time() - t0 < 3, time.time() - t0)
fd.FAKE["mode"] = "ok"
mg.dir_reset()
fd.CALLS.clear()
get("/api/mail/vacation/me")
_DIR_OK = mg._DIR["ok_at"]
mg._DIR["ok_at"] = time.time() - mg.DIR_TTL - 1
fd.FAKE["mode"] = "500"
j = get("/api/mail/vacation/me").json()
check("5분 지나 다시 부르다 실패하면 15분 안의 명부를 그대로 씀", j.get("show") and len(fd.CALLS) == 2, (j, fd.CALLS))
fd.FAKE["mode"] = "ok"
mg.dir_reset()
sso_key_saved = os.environ.pop("KNK_SSO_SERVICE_KEY")
fd.CALLS.clear()
j = get("/api/mail/vacation/me").json()
os.environ["KNK_SSO_SERVICE_KEY"] = sso_key_saved
check("공유키가 없으면 부르지도 않음 · 띠 없음", not j.get("show") and fd.CALLS == [], (j, fd.CALLS))

# ═══════════════════════ 받는 사람 휴가 표시 ═══════════════════════
print("\n받는 사람이 휴가면 쓰기 화면에 표시")
mg.dir_reset()
fd.CALLS.clear()
as_("vn")
j = get("/api/mail/vacation/addrs?a=" + ",".join(["t1102@knknara.co.kr", "tvn201@knknara.co.kr", "buyer@cust-a.example", "t777@knknara.co.kr", "gone@knknara.co.kr", "nobody"])).json()
info = j.get("info") or {}
exp_vn = (until_utc + timedelta(hours=7)).date().isoformat()
check("휴가 중인 사내 직원만(근무·출장·퇴사·바깥은 없음)", set(info) == {"t1102@knknara.co.kr"}, info)
x = info.get("t1102@knknara.co.kr") or {}
check("명부 주소가 달라도 웍스 사번으로 찾음 · 이름 = 「이름 직책 부서」(웍스) · 날짜 = 보는 사람(베트남) 소속",
      x.get("disp") == "조민혁 과장 시험품질팀" and x.get("until") == exp_vn and x.get("label") == "~" + mg.md_label(exp_vn), x)
j2 = get("/api/mail/vacation/addrs?a=ceo-other@knknara.co.kr").json()
check("웍스에 없는 주소라도 명부 주소가 맞으면 명부 이름으로", (j2.get("info") or {}).get("ceo-other@knknara.co.kr", {}).get("disp") == "시험대표 대표 경영", j2)
check("주소 묻기도 같은 캐시(명부 한 번)", len(fd.CALLS) == 1, fd.CALLS)
check("빈 주소 → 빈 답 · 명부 안 부름", get("/api/mail/vacation/addrs?a=").json() == {"ok": True, "info": {}})
hc = get("/mail/compose").text
check("쓰기 화면: 받는 사람 칸 아래 자리 · 받는 사람·참조 칸을 볼 때마다 확인 · 인쇄 때 숨김",
      'id="cVacInfo" hidden' in hc and "window.cmpVacCheck" in hc and "/api/mail/vacation/addrs?a=" in hc and "@media print{.cmp-grp{display:none !important}}" in hc)
check("이음에 글을 보내는 길 없음(명부 읽기만)", "/api/works/notify" not in open(os.path.join(ROOT, "app", "mail_glance.py"), encoding="utf-8").read())

# ═══════════════════════ 🏢 거래처 진행 상황 ═══════════════════════
print("\n🏢 거래처 메일 옆 진행 상황(웍스 읽기만 · 권한)")
with _db.db_session() as c:
    c.execute("INSERT INTO customers(id, name) VALUES(9901, '시험고객A')")
    c.execute("INSERT INTO customers(id, name) VALUES(9902, '시험고객B')")
    c.execute("INSERT INTO shared_contacts(name, email, customer_id) VALUES('홍길동','hong@cust-a.example',9901)")
    c.execute("INSERT INTO shared_contacts(name, email, customer_id) VALUES('박구매','park@cust-a.example',9901)")
    c.execute("INSERT INTO shared_contacts(name, email, customer_id) VALUES('양다리','both@shared.example',9901)")
    c.execute("INSERT INTO shared_contacts(name, email, customer_id) VALUES('양다리','both@shared.example',9902)")
    pj = [("검사기 1호", "진행중", "2026-11-01", 12345678, "KRW", "M-2611-01"), ("치구 개조", "진행중", "", 0, "KRW", "M-2611-02"),
          ("끝난 장비", "완료", "2026-10-01", 5000, "USD", "M-2610-01"), ("취소 건", "취소", "2026-11-10", 999, "KRW", "M-2611-03")]
    for nm, stt, od, amt, ccy, code in pj:
        c.execute("INSERT INTO projects(name, customer_id, status, order_date, order_amount, currency, mgmt_code, due_date) VALUES(?,?,?,?,?,?,?,?)",
                  (nm, 9901, stt, od, amt, ccy, code, "2026-12-15"))
    snap = json.dumps([dict(r) for r in c.execute("SELECT * FROM projects ORDER BY id").fetchall()]
                      + [dict(r) for r in c.execute("SELECT * FROM customers WHERE id IN (9901,9902)").fetchall()]
                      + [dict(r) for r in c.execute("SELECT * FROM shared_contacts ORDER BY id").fetchall()], ensure_ascii=False, default=str)
MC = put_in("[발주] 검사기 추가 발주", frm="hong@cust-a.example")
as_("ceo")
hv = get("/mail/%d" % MC).text
seg = hv[hv.find('id="mvCust"'):hv.find("</details>", hv.find('id="mvCust"'))] if 'id="mvCust"' in hv else ""
check("대표(매출 보기 권한) → 「🏢 시험고객A 진행 상황」 접는 칸 · 진행 중 2건", "<details class=\"mv-cust\"" in hv and "시험고객A</b> 진행 상황" in seg and "진행 중 2건" in seg, seg[:300])
check("진행 중 프로젝트(완료·취소 빼고) · 웍스 프로젝트 화면 연결", "검사기 1호" in seg and "치구 개조" in seg and "/project/" in seg and "M-2611-01" in seg
      and seg.count("취소 건") == 0, seg[:800])
check("최근 수주(취소 빼고 · 날짜 순) · 금액 = 웍스 통화 표시", "₩12,345,678" in seg and "$5,000.00" in seg and seg.find("검사기 1호", seg.find("최근 수주")) < seg.find("끝난 장비", seg.find("최근 수주")), seg[seg.find("최근 수주"):][:500])
check("고객사 화면 연결 · 인쇄 때 숨김", "/customer/9901" in seg and "@media print{ .mv-cust, .mv-lgf{display:none !important} }" in hv)
hp = get("/mail/%d/pane" % MC).text
check("읽기 창에도 같은 칸", 'id="mvCust"' in hp and "₩12,345,678" in hp)
as_("other")
MCo = put_in("[발주] 검사기 추가 발주", frm="hong@cust-a.example", owner=9805)
hv = get("/mail/%d" % MCo).text
check("매출 보기 권한 없는 직원 → 칸·금액 모두 안 보임", 'id="mvCust"' not in hv and "₩12,345,678" not in hv and "검사기 1호" not in hv)
as_("sales")
MCs = put_in("[발주] 검사기 추가 발주", frm="hong@cust-a.example", owner=9804)
hv = get("/mail/%d" % MCs).text
check("권한 체크 받은 직원(can_view_sales=1) → 보임", 'id="mvCust"' in hv and "₩12,345,678" in hv)
as_("ceo")
M_dom = put_in("문의", frm="newguy@cust-a.example")
check("연락처에 없는 같은 회사 주소 → 한 거래처만 가리키면 그 거래처(거래처 폴더와 같은 규칙)", "시험고객A</b> 진행 상황" in get("/mail/%d" % M_dom).text)
M_amb = put_in("문의", frm="both@shared.example")
check("한 주소가 두 거래처에 걸리면 안 보임(추측 안 함)", 'id="mvCust"' not in get("/mail/%d" % M_amb).text)
M_unk = put_in("문의", frm="who@unknown.example")
check("모르는 회사 → 안 보임", 'id="mvCust"' not in get("/mail/%d" % M_unk).text)
M_int = put_in("사내", frm="t1102@knknara.co.kr")
check("사내 직원이 보낸 메일 → 안 보임", 'id="mvCust"' not in get("/mail/%d" % M_int).text)
check("내가 보낸 메일 → 안 보임", 'id="mvCust"' not in get("/mail/%d" % O1).text)
with _db.db_session() as c:
    check("함수 직접: 정확 일치 · 회사 주소 · 둘이면 None", mg.customer_of(c, "HONG@cust-a.example") == 9901 and mg.customer_of(c, "x@cust-a.example") == 9901
          and mg.customer_of(c, "both@shared.example") is None and mg.customer_of(c, "") is None)
    pg = mg.customer_progress(c, 9901, with_money=False)
check("금액 없이 부르면 금액 칸 자체가 없음", pg and all("amount" not in p for p in pg["live"] + pg["orders"]), pg)
with _db.db_session() as c:
    snap2 = json.dumps([dict(r) for r in c.execute("SELECT * FROM projects ORDER BY id").fetchall()]
                       + [dict(r) for r in c.execute("SELECT * FROM customers WHERE id IN (9901,9902)").fetchall()]
                       + [dict(r) for r in c.execute("SELECT * FROM shared_contacts ORDER BY id").fetchall()], ensure_ascii=False, default=str)
check("웍스 고객사·프로젝트·연락처 표는 그대로(읽기만)", snap == snap2)

# ═══════════════════════ 공유키 ═══════════════════════
print("\n공유키 값이 어디에도 안 나옴")
leak = [i for i, t in enumerate(RESP_TEXT) if KEY in t]
check("응답·화면 %d개에 공유키 값 없음" % len(RESP_TEXT), not leak, leak[:3])
check("서버 기록(print)에 공유키 값 없음 · 실패 기록은 찍힘", KEY not in LOG.getvalue() and "[MAIL-VAC] 이음 명부 응답 500" in LOG.getvalue())
check("명부 캐시에는 휴가인 사람만 · 전화번호 같은 다른 칸은 안 남김", "010-0000-0000" not in json.dumps(mg._DIR.get("data") or {}, ensure_ascii=False))

SRV.shutdown()
print("\n결과: %d 통과 / %d 실패" % (P, F))
sys.exit(1 if F else 0)
