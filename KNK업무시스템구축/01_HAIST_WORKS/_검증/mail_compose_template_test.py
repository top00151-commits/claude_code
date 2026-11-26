# -*- coding: utf-8 -*-
"""새 메일 기본 양식 · 쓰기 도구(표·그림·정렬·색·크기) 시험 — 가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 11-26 「새 메일 쓰기를 누르면 아웃룩처럼 기본으로 많이 쓰는 내용이 바로 — 양식에 『기본 양식』을 추가해 그것을 우선으로」 ·
          「아웃룩처럼 글 도구·표 도구·그림 도구 — 어떤 게 들어가면 좋을지 검토해서 추가」
사용: py -3.13 _검증/mail_compose_template_test.py"""
import io
import json
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
    import app.database as _db
    _TMP = tempfile.mkdtemp(prefix="knk_cmptpl_")
    _db.DB_PATH = os.path.join(_TMP, "t.db")
    _db.init_db()
    import app.main as m
    from app import mail_store as ms
    from app import mail_work as mw
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


ME, OTHER, VN = 9801, 9802, 9803
with _db.db_session() as c:
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (ME, "t9801", "가짜나", "member"))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (OTHER, "t9802", "가짜남", "member"))
    c.execute("INSERT INTO users(id, login_id, name, role, is_active, password) VALUES(?,?,?,?,1,'x')", (VN, "VN998", "Gia Thu", "member"))

_U = {"id": ME, "name": "가짜나", "login_id": "t9801"}
m.get_user = lambda req: dict(_U, role="member", team_id=None, team_name="")
k = TestClient(m.app, base_url="http://127.0.0.1:5051", raise_server_exceptions=False, follow_redirects=False)
k.headers.update({"host": "works.knknara.co.kr", "x-forwarded-proto": "https"})


def deftpl(html):
    mm = re.search(r"window\.CMP_DEFTPL = (.*?);</script>", html)
    if not mm:
        return "없음"
    return json.loads(mm.group(1))


print("① 처음 쓰는 사람 = 제안 양식 하나를 내 양식으로 만들고 새 메일에 줌")
h = k.get("/mail/compose").text
d = deftpl(h)
check("새 메일 = CMP_DEFTPL 있음", isinstance(d, dict) and d.get("id"), d)
check("모양 = 안녕하세요 / 케이엔케이 [내 이름] 입니다 / 빈 줄 셋 / 감사합니다",
      isinstance(d, dict) and d["body"] == "안녕하세요.\n케이엔케이 [내 이름] 입니다.\n\n\n\n감사합니다.", d)
check("이름은 코드에 박지 않음([내 이름] → 화면이 로그인한 사람 이름으로) · CMP_ME = 로그인 이름",
      json.loads(re.search(r"window\.CMP_ME = (.*?);", h).group(1)) == "가짜나" and "김정락" not in json.dumps(d, ensure_ascii=False), "")
with _db.db_session() as c:
    rows = c.execute("SELECT id, owner_id, title FROM mail_templates WHERE owner_id=?", (ME,)).fetchall()
    dr = c.execute("SELECT tpl_id FROM mail_tpl_default WHERE user_id=?", (ME,)).fetchone()
check("내 양식 1개(새 메일 기본 양식) · 기본 번호 = 그것", len(rows) == 1 and dr and dr["tpl_id"] == rows[0]["id"], [dict(r) for r in rows])
k.get("/mail/compose")
k.get("/mail/templates")
with _db.db_session() as c:
    n = c.execute("SELECT COUNT(*) FROM mail_templates WHERE owner_id=?", (ME,)).fetchone()[0]
check("여러 번 열어도 한 번만 만듦", n == 1, n)

print("② 화면 — 기본 양식을 넣는 길 · 서명 위 · 커서 · 안내 줄")
check("기본 양식 넣기(defPut) · 서명 위(insertBefore top) · 한 줄씩(div)", "function defPut(t)" in h and "ED2.insertBefore(d, top)" in h and "'<div><br></div>'" in h)
check("이미 쓴 글이 있으면 안 넣음(ownEmpty)", "!ownEmpty()) return false" in h)
check("커서 = 인사말 아래 첫 빈 줄(defCaret)", "function defCaret()" in h)
check("안내 줄: 이번 메일에서 빼기 · 바꾸기·끄기(새 창 · ✕ 닫기 붙는 주소)", "이번 메일에서 빼기" in h and 'href="/mail/templates?from=compose" target="_blank"' in h)
check("기본 양식만 있고 말씀이 없으면 「본문이 비어 있습니다」", "기본 양식(인사말·끝인사)만 들어 있습니다" in h)
check("서명 순서: 서버가 서명(cSigHtml)도 함께 줌", 'id="cSigHtml"' in h)

print("③ 답장·전달·임시 메일·다시 묻기 = 안 넣음")
with _db.db_session() as c:
    mid, _o = ms.store_inbound(c, to_email="t9801@knknara.co.kr", from_email="buyer@partner-demo.example", from_name="가짜 거래처",
                               subject="가짜 문의", text="가짜 본문", html="<p>가짜 본문</p>", owner_id=ME, run_ai=False,
                               message_id="cmptpl-1@test")
    did = ms.save_draft(c, user_id=ME, to_email="a@partner-demo.example", subject="가짜 임시", body="쓰던 글",
                        body_html="<div>쓰던 글</div>") if hasattr(ms, "save_draft") else 0
for q in ("reply=%d" % mid, "replyall=%d" % mid, "forward=%d" % mid):
    hh = k.get("/mail/compose?" + q).text
    check("%s → CMP_DEFTPL 없음(null)" % q.split("=")[0], deftpl(hh) is None, deftpl(hh))
if did:
    hh = k.get("/mail/compose?draft=%d" % did).text
    check("임시 메일 열기 → 없음", deftpl(hh) is None, deftpl(hh))
else:
    print("  (임시 저장 함수 이름이 달라 임시 메일 열기는 건너뜀)")
check("새 메일(받는 사람 미리) → 있음", isinstance(deftpl(k.get("/mail/compose?to=buyer@partner-demo.example").text), dict))

print("④ 끄기 · 다시 켜기 · 남의 양식 막기")
tid = d["id"]
r = k.post("/mail/templates/default", data={"id": "0"})
check("끄기 200", r.status_code == 200 and r.json().get("ok"), r.text)
check("끄면 새 메일에 안 넣음", deftpl(k.get("/mail/compose").text) is None)
with _db.db_session() as c:
    n = c.execute("SELECT COUNT(*) FROM mail_templates WHERE owner_id=?", (ME,)).fetchone()[0]
check("끈 뒤 다시 열어도 새로 만들지 않음 · 양식은 그대로", n == 1, n)
with _db.db_session() as c:
    ok, _msg, oid = mw.save_template(c, OTHER, title="남의 양식", body="남의 글")
r = k.post("/mail/templates/default", data={"id": str(oid)})
check("남의 양식은 기본으로 못 정함(400)", r.status_code == 400, r.text)
with _db.db_session() as c:
    ok, _msg, cid = mw.save_template(c, OTHER, title="회사 인사", body="회사 글", company=True, is_admin=True)
r = k.post("/mail/templates/default", data={"id": str(cid)})
check("회사 양식은 기본으로 정할 수 있음", r.status_code == 200, r.text)
check("→ 새 메일에 회사 양식", (deftpl(k.get("/mail/compose").text) or {}).get("body") == "회사 글")
r = k.post("/mail/templates/default", data={"id": str(tid)})
check("내 양식으로 되돌리기", r.status_code == 200 and (deftpl(k.get("/mail/compose").text) or {}).get("id") == tid)
j = k.get("/api/mail/templates").json()
check("양식 목록 API 에 default_id", j.get("default_id") == tid, j.get("default_id"))
th = k.get("/mail/templates").text
check("양식 화면: 「✉ 기본」 표시 · 끄기 단추 · 「✉ 새 메일 기본으로」 · 예시 양식 이름",
      "✉ 기본</span>" in th and "tpDefSet(0)" in th and "✉ 새 메일 기본으로" in th and "📚 예시 양식" in th, "")
th2 = k.get("/mail/templates?from=compose").text
check("양식 화면: 메일 쓰기에서 새 창으로 열면 ✕ 닫기 · 그냥 열면 없음", 'id="tpWinX"' in th2 and "window.close()" in th2 and 'id="tpWinX"' not in th)
with _db.db_session() as c:
    mw.delete_template(c, ME, tid)
check("기본 양식을 지우면 = 꺼진 것(새로 만들지 않음)", deftpl(k.get("/mail/compose").text) is None)
with _db.db_session() as c:
    n = c.execute("SELECT COUNT(*) FROM mail_templates WHERE owner_id=?", (ME,)).fetchone()[0]
check("지운 뒤 다시 안 만듦", n == 0, n)

print("⑤ 베트남 사람 = 베트남어 제안")
_U.update(id=VN, name="Gia Thu", login_id="VN998")
dv = deftpl(k.get("/mail/compose").text)
check("VN 로그인 → 베트남어 인사 · [tên tôi]", isinstance(dv, dict) and "Kính gửi" in dv["body"] and "[tên tôi]" in dv["body"], dv)
_U.update(id=ME, name="가짜나", login_id="t9801")

print("⑥ 도구 — 표·그림·정렬·색·크기·형광펜·번호 목록·들여쓰기·가로줄·되돌리기 · ✕ 닫기")
h = k.get("/mail/compose").text
for nm, s in (("되돌리기", 'data-cmd="undo"'), ("다시 하기", 'data-cmd="redo"'), ("글자 크기", 'id="cFsz"'), ("형광펜", 'id="cHlBtn"'),
              ("가운데 정렬", 'data-cmd="justifyCenter"'), ("번호 목록", 'data-cmd="insertOrderedList"'), ("표", 'id="cTblBtn"'),
              ("그림", 'id="cImgBtn"'), ("들여쓰기", 'data-cmd="indent"'), ("내어쓰기", 'data-cmd="outdent"'), ("가로줄", 'id="cHrBtn"'),
              ("더 보기", 'id="cMoreBtn"'), ("서식 지우기", 'id="cClear"'), ("글자색", 'id="cColor"')):
    check("도구 있음: " + nm, s in h)
check("작은 창 셋(형광펜·표·더 보기)마다 ✕ 닫기", all(('data-close="%s"' % x) in h for x in ("cHlPop", "cTblPop", "cMorePop")))
check("색·형광펜·정렬 = 인라인 style(styleWithCSS)", "exec('hiliteColor', hl, true)" in h and "exec('foreColor', col.value, true)" in h)
check("글자 크기 = <font> 대신 px 인라인 style", "sp.style.fontSize=FSZ_PX+'px'" in h)
check("그림 = 큰 사진 줄여 넣기(폭 1280)", "IMG_MAX_W=1280" in h)
check("가운데 폭·휴대폰 = 덜 쓰는 것 「더 보기」 안으로", "@media(max-width:1000px)" in h and "mob-only" in h)
check("Jinja 주석 꼴 '{' + '#' 이 CSS·JS 에 없음", "{#" not in re.sub(r"(?s)<!--.*?-->", "", h))

print("⑦ 보낼 때 위생 처리 — 새 도구가 만든 HTML 이 남고 스크립트는 지워짐")
TD = "border:1px solid #b9b9b9;padding:4px 8px;font-size:13px"
made = ('<div class="knk-tpl knk-tpl-def"><div>안녕하세요.</div><div>케이엔케이 가짜나 입니다.</div><div><br></div></div>'
        '<div style="text-align: center;">가운데 글</div><div style="text-align: right;">오른쪽 글</div>'
        '<span style="color: rgb(192, 57, 43);">빨강</span> <span style="background-color: rgb(254, 240, 138);">형광펜</span> '
        '<span style="font-size:24px">아주 크게</span> <strike>취소선</strike>'
        '<ol><li>하나</li><li>둘</li></ol><blockquote style="margin: 0 0 0 40px; border: none; padding: 0px;">들여쓰기</blockquote>'
        '<hr style="border:0;border-top:1px solid #c8c8c8;margin:10px 0">'
        '<table style="border-collapse:collapse;width:100%;margin:6px 0"><tr><td style="' + TD + '" colspan="2">가</td></tr>'
        '<tr><td style="' + TD + '">나</td><td style="' + TD + ';background-color:#fff7d6">다</td></tr></table>'
        '<img src="data:image/png;base64,iVBORw0KGgo=" alt="" style="max-width:100%;width:300px;height:auto">'
        '<script>alert(1)</script><img src=x onerror="alert(2)"><a href="javascript:alert(3)">나쁜 링크</a>')
out = ms.sanitize_html_for_view(made, 0, [])
for nm, s in (("가운데 정렬", 'style="text-align: center;"'), ("오른쪽 정렬", 'style="text-align: right;"'),
              ("글자색", "color: rgb(192, 57, 43)"), ("형광펜", "background-color: rgb(254, 240, 138)"), ("글자 크기 px", "font-size:24px"),
              ("번호 목록", "<ol><li>하나</li>"), ("들여쓰기", "<blockquote style=\"margin: 0 0 0 40px"), ("가로줄", "<hr style="),
              ("표 테두리", 'border-collapse:collapse'), ("표 칸 style", TD), ("칸 합치기 colspan", 'colspan="2"'), ("칸 채움색", "background-color:#fff7d6"),
              ("본문 그림(data:) · 크기 style", 'src="data:image/png;base64,iVBORw0KGgo="'), ("그림 폭", "width:300px"),
              ("기본 양식 줄", "케이엔케이 가짜나 입니다.")):
    check("위생 처리 뒤에도 남음: " + nm, s in out, out[:300])
check("스크립트 지워짐", "<script" not in out.lower() and "alert(1)" not in out)
check("이벤트 속성 지워짐(onerror)", "onerror" not in out.lower())
check("javascript: 링크 무력화", "javascript:" not in out.lower())
try:
    from app import mail_send as _msend
    nh, parts = _msend._inline_data_images(out)
    check("보낼 때 본문 그림 → 인라인 첨부(cid)로 바뀜", len(parts) == 1 and 'src="cid:' in nh, nh[:200])
except Exception as e:
    check("보낼 때 본문 그림 → 인라인 첨부(cid)", False, e)

print("⑧ 화면 스크립트 문법(node --check)")
node = shutil.which("node")
if not node:
    print("  (node 없음 — 건너뜀)")
else:
    for path in ("/mail/compose", "/mail/templates"):
        hh = k.get(path).text
        scripts = re.findall(r"(?is)<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", hh)
        bad = []
        for i, sc in enumerate(scripts):
            fn = os.path.join(_TMP, "s%d.js" % i)
            with open(fn, "w", encoding="utf-8") as f:
                f.write(sc)
            rr = subprocess.run([node, "--check", fn], capture_output=True, text=True, encoding="utf-8")
            if rr.returncode != 0:
                bad.append((i, rr.stderr[:300]))
        check("%s 스크립트 %d개 문법 맞음" % (path, len(scripts)), not bad, bad)

print("\n⑨ 큰 본문(그림 넣은 메일) — 운영 Starlette 1.2 의 폼 칸 1MB 한도에 안 걸리게(11-26 · 로컬 0.38 엔 한도 없음)")
import re as _re  # noqa: E402
_src = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
for _path in ("/mail/send", "/mail/draft/save", "/mail/schedule", "/mail/signature", "/mail/templates/save"):
    _i = _src.find('@app.post("%s")' % _path)
    _body = _src[_i:_src.find("\n@app.", _i + 5)] if _i >= 0 else ""
    check("%s = 칸 한도 넓힌 _mail_form 사용(req.form() 그대로 아님)" % _path,
          "await _mail_form(req)" in _body and "await req.form()" not in _body, _path)
check("_mail_form = max_part_size 넘기고 옛 판은 그냥 form()",
      bool(_re.search(r"req\.form\(max_part_size=MAIL_FORM_PART_MAX\)[\s\S]{0,80}except TypeError", _src)))
_r = k.post("/mail/draft/save", data={"to": "", "subject": "큰 본문", "body": "x",
                                      "body_html": "<p>" + "가" * 700000 + "</p>"}, files={"files": ("a.txt", b"x", "text/plain")})
check("2MB 본문 임시저장 = 거절 안 됨(400 아님)", _r.status_code != 400, (_r.status_code, _r.text[:120]))

print("\n결과: %d 통과 / %d 실패" % (P, F))
shutil.rmtree(_TMP, ignore_errors=True)
sys.exit(1 if F else 0)
