# -*- coding: utf-8 -*-
"""새 메일 기본 양식 · 쓰기 도구(표·그림·정렬·색·크기) 시험 — 가짜 직원·가짜 메일·임시 DB(운영 무접촉 · 실제 메일 없음).
대표 11-26 「새 메일 쓰기를 누르면 아웃룩처럼 기본으로 많이 쓰는 내용이 바로 — 양식에 『기본 양식』을 추가해 그것을 우선으로」 ·
          「아웃룩처럼 글 도구·표 도구·그림 도구 — 어떤 게 들어가면 좋을지 검토해서 추가」
사용: py -3.13 _검증/mail_compose_template_test.py"""
import _mail_ico; _mail_ico.install()  # noqa: E402  11-28 4단계: 화면의 선 아이콘을 [i:이름] 으로 읽음(그림 문자 대신 · 아이콘 이름까지 확인)
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

print("③ 11-26 오후 「전달·회신에도 기본 양식」 — 답장·전체 답장·전달 = 넣음 · 임시 메일·다시 묻기 = 안 넣음")
with _db.db_session() as c:
    mid, _o = ms.store_inbound(c, to_email="t9801@knknara.co.kr", from_email="buyer@partner-demo.example", from_name="가짜 거래처",
                               subject="가짜 문의", text="가짜 본문", html="<p>가짜 본문</p>", owner_id=ME, run_ai=False,
                               message_id="cmptpl-1@test")
    did = ms.save_draft(c, user_id=ME, to_email="a@partner-demo.example", subject="가짜 임시", body="쓰던 글",
                        body_html="<div>쓰던 글</div>") if hasattr(ms, "save_draft") else 0
for q, kind in (("reply=%d" % mid, "reply"), ("replyall=%d" % mid, "reply"), ("forward=%d" % mid, "forward")):
    hh = k.get("/mail/compose?" + q).text
    _d = deftpl(hh)
    check("%s → CMP_DEFTPL 있음(kind=%s) · 원본 인용도 그대로" % (q.split("=")[0], kind), isinstance(_d, dict) and _d.get("kind") == kind and "knk-quote" in hh, _d)
hh = k.get("/mail/compose?reply=%d&ack=2026-11-28" % mid).text
check("확인 답장(ack) = 서버는 주지만 화면이 넣지 않음(확인 글이 따로 들어감)", "!window.CMP_ACK && defPut(" in hh)
check("화면: 내 글 판정에서 인용한 원본 뺌 · 서명이 없으면 원본 위에", ".knk-sig,.knk-quote').forEach" in hh and "ED2.querySelector('.knk-sig')||ED2.querySelector('.knk-quote')" in hh)
check("「양식」 단추 = 남색 채움 · 📑 · 휴대폰도 글자", 'id="cTplBtn"' in hh and "[i:clipboard-list]<span class=\"tl-keep\">" in hh.replace('"', '\"') or ('[i:clipboard-list]<span class="tl-keep">' in hh and "#cTplBtn{" in hh), "")
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
      "[i:mail] 기본</span>" in th and "tpDefSet(0)" in th and "[i:mail] 새 메일 기본으로" in th and "[i:library] 예시 양식" in th, "")
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
check("색·형광펜·정렬 = 인라인 style(styleWithCSS)", "exec('hiliteColor', c, true)" in h and "exec('foreColor', c, true)" in h)
check("글자 크기 = <font> 대신 인라인 style(pt) · 글꼴도 같은 방식", "FSZ_PEND=v+'pt'" in h and "unwrapFont(f, 'fontSize', FSZ_PEND)" in h and "unwrapFont(f, 'fontFamily', FONT_PEND)" in h)
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

print("\n⑩ 2차 도구(11-26 대표 「그림·표 크기를 마우스로 · 글꼴 · 글자색 단색 칸」)")
h = k.get("/mail/compose").text
# 그림
check("그림: 모서리 손잡이 넷(겹 요소 img-ov · data-knk-ui) · pointer 이벤트(터치도)",
      "['nw','ne','sw','se']" in h and "imgOv.className='img-ov'" in h and "imgOv.setAttribute('data-knk-ui','1')" in h
      and "addEventListener('pointerdown', imgDown)" in h and "setPointerCapture" in h and "touch-action:none" in h)
check("그림: 손잡이·테두리는 본문(cBody) 밖 body 에 붙음", "document.body.appendChild(imgOv)" in h and "ED.appendChild(imgOv)" not in h)
check("그림: 크기 = 인라인 width px + height:auto + max-width:100% + width 속성(아웃룩 데스크톱)",
      "img.style.width=w+'px'; img.style.height='auto'; img.style.maxWidth='100%'" in h and "img.setAttribute('width', w)" in h)
check("그림 띠: 25·50·75·100%(원래) · 왼쪽·가운데·오른쪽 · 지우기 · ✕ 닫기",
      "[25,50,75,100].forEach" in h and "'100% 원래'" in h and "'◧ 왼쪽'" in h and "'▣ 가운데'" in h and "'◨ 오른쪽'" in h
      and "'🗑 지우기'" in h and "mk('✕ 닫기',clearImgSel" in h)
check("그림: Delete 키로 지우기 · Esc 로 닫기", "e.key==='Delete' || e.key==='Backspace'" in h and "if(selImg){ clearImgSel(); return true; }" in h)
check("그림: 넣을 때도 width 속성 · 붙여 넣은 그림도 줄여 넣기(putImages)",
      "im.setAttribute('width', w)" in h and "e.preventDefault(); saveRange(); putImages(fs)" in h)
# 표
check("표: 열 경계(cb)·줄 경계(rb)·오른쪽 아래(tc) 손잡이 = 겹 요소(tbl-ov · data-knk-ui)",
      'class="cb" data-col=' in h and 'class="rb" data-row=' in h and 'class="tc" data-corner="1"' in h
      and "tblOv.setAttribute('data-knk-ui','1')" in h and "document.body.appendChild(tblOv)" in h)
check("표: 결과 = td width style·속성 + table width style·속성(아웃룩)",
      "x.td.style.width=Math.max(8, Math.round(inner))+'px'; x.td.setAttribute('width', s)" in h
      and "t.style.width=tot+'px'; t.setAttribute('width', tot)" in h)
check("표: 합친 칸(colspan·rowspan)을 고려한 열 계산(tblGrid)", "function tblGrid(t)" in h and "occ[r+a][c+b]=1" in h)
check("표 띠: 칸 색 · 선(굵기·모양·색) · 가운데 · 폭 맞춤 · 표 지우기 · ✕ 닫기 · 행·열·합치기 그대로",
      "'🎨 칸 색 ▾'" in h and "'▦ 선 ▾'" in h and "mk('가운데',toggleCenter" in h and "mk('폭 맞춤',fitWidth" in h
      and "'🗑 표 지우기'" in h and "mk('✕ 닫기',clearTbl" in h and "mk('합치기',mergeSel" in h and "mk('＋아래'" in h)
check("표 작은 창(칸 색·선) = ✕ 닫기 · Esc", 'data-subx="1"' in h and "if(tblSub){ tblSub.remove(); tblSub=null; return true; }" in h)
check("표 가운데 = align 속성 + margin auto(아웃룩·지메일)", "t.setAttribute('align','center'); t.style.marginLeft='auto'" in h)
check("머리줄 = 칸 너비·선을 지우지 않음(배경·굵기만)", "c.style.backgroundColor = on ? '' : '#f3f4f6'" in h and "c.setAttribute('style', TD_STYLE + (on" not in h)
# 글꼴
for f in ("맑은 고딕", "굴림", "돋움", "바탕", "나눔고딕", "Arial", "Times New Roman", "Verdana", "Tahoma"):
    check("글꼴 목록: " + f, ("['%s'," % f) in h)
check("글꼴 = 대체 글꼴 목록 붙임(예: 맑은 고딕 → Malgun Gothic · sans-serif)", "\"'맑은 고딕','Malgun Gothic','Apple SD Gothic Neo',sans-serif\"" in h)
check("글꼴 목록 = 각 글꼴로 보임(b.style.fontFamily)", "b.style.fontFamily=f[1]" in h)
check("글꼴 창 ✕ 닫기", 'data-close="cFontPop"' in h)
# 색
check("글자색: 단추 본체 = 마지막 색 바로(data-paint) · ▾ = 바둑판", 'id="cColor" class="sp-main" data-paint="fore"' in h and 'id="cColorDd"' in h and 'id="cColorPop"' in h)
check("형광펜도 같은 방식", 'id="cHlBtn" class="sp-main" data-paint="hl"' in h and 'id="cHlDd"' in h)
check("색 바둑판: 기본 10색 · 밝게 3줄 · 어둡게 2줄 · 자동(검정) · 최근 쓴 색 · 다른 색",
      "PAL_BASE=['#000000','#c00000','#ff0000','#ff8c00','#ffc000','#00b050','#00b0f0','#0070c0','#002060','#7030a0']" in h
      and "[0.8,0.6,0.4]" in h and "[0.25,0.5]" in h and "자동(검정)" in h and "최근 쓴 색" in h and "다른 색 고르기" in h)
check("색 창 ✕ 닫기 · 바깥 누르기·Esc 목록에 들어 있음", 'data-close="cColorPop"' in h and "var MINIS=['cHlPop','cTblPop','cMorePop','cColorPop','cFontPop']" in h)
check("최근 색·마지막 색 = 이 기기에만(localStorage · try/catch)", "function lsGet(k, d){ try{" in h and "function lsSet(k, v){ try{" in h)
# 그 밖
check("굵게·기울임·밑줄 단추 = 지금 서식이면 눌린 모양(queryCommandState)", "document.queryCommandState(c)" in h and "aria-pressed" in h)
check("글자 크기 숫자 9~36pt", all(('<option value="%s">' % v) in h for v in ("9", "10.5", "12", "14", "24", "36")))
check("링크 고치기·풀기", "링크 주소 고치기" in h and 'id="cUnlink"' in h and "function unwrapA(a)" in h)
check("저장·보내기 HTML 에서 화면 표시 뺌(임시저장 · 보내기)",
      "cmpStripUi(ed.cloneNode(true)).innerHTML" in h and "if(window.cmpStripUi) cmpStripUi(t);" in h)
check("휴대폰(640 이하) = 글꼴·크기 칸 좁게", ".cmp-fontbtn .fl{max-width:58px}" in h)
# 브라우저로 끌어 보며 찾은 것(11-26)
check("줄 높이 = 끈 높이 그대로(칸 height 는 안쪽 여백 포함으로 그려짐 — 빼면 줄이 덜 늘어남)",
      "td.style.height=Math.max(18, h)+'px'; td.setAttribute('height', h)" in h)
check("휴대폰 = 그림·표 띠를 화면 아래에(위 글 도구 줄을 덮지 않게)", ".img-tb,.tbl-tb{position:fixed;left:8px !important" in h)
check("손잡이·띠가 위에 붙은 보내기 단추 줄을 덮지 않음(clipUnder · visTop)", "function visTop()" in h and "clipUnder(imgOv, r, vt)" in h and "clipUnder(tblOv, r, visTop())" in h)
check("그림 % 단추 = 본문 폭에 막혀 같은 크기면 하나만 눌린 모양", "var hit=false;" in h)

print("⑪ 2차 도구가 만든 HTML 이 보내기 위생 처리 뒤에도 남음 · 위험한 것은 여전히 지워짐")
made2 = ('<span style="font-family: &quot;맑은 고딕&quot;, &quot;Malgun Gothic&quot;, &quot;Apple SD Gothic Neo&quot;, sans-serif;">맑은 고딕 글</span>'
         '<span style="font-family:\'Times New Roman\',Times,serif">Times</span>'
         '<span style="font-size: 14pt;">14pt</span><span style="color: rgb(0, 112, 192);">파랑</span>'
         '<span style="background-color: rgb(255, 255, 0);">형광</span>'
         '<img src="data:image/png;base64,iVBORw0KGgo=" alt="" style="width: 321px; height: auto; max-width: 100%;" width="321">'
         '<table style="border-collapse:collapse;margin:6px auto;width: 412px;" width="412" align="center"><tbody><tr>'
         '<td style="border: 2px dashed rgb(0, 112, 192); padding: 4px 8px; width: 150px; height: 40px; background-color: rgb(255, 242, 204);" width="167" height="49">가</td>'
         '<td style="border:1px solid #b9b9b9;padding:4px 8px;width:228px">나</td></tr></tbody></table>'
         '<p onclick="alert(9)" style="color:red">x</p><a href=" javascript:alert(8)">링크</a><script>alert(7)</script>')
out2 = ms.sanitize_html_for_view(made2, 0, [])
for nm, s_ in (("글꼴(대체 목록)", "font-family: &quot;맑은 고딕&quot;, &quot;Malgun Gothic&quot;"), ("영문 글꼴", "font-family:'Times New Roman',Times,serif"),
               ("글자 크기 pt", "font-size: 14pt"), ("글자색", "color: rgb(0, 112, 192)"), ("형광펜", "background-color: rgb(255, 255, 0)"),
               ("그림 폭 style", "width: 321px; height: auto; max-width: 100%"), ("그림 width 속성", 'width="321"'),
               ("표 폭 style·속성", 'width: 412px;" width="412"'), ("표 가운데 align", 'align="center"'),
               ("칸 너비·높이", "width: 150px; height: 40px"), ("칸 width·height 속성", 'width="167" height="49"'),
               ("칸 선 굵기·모양·색", "border: 2px dashed rgb(0, 112, 192)"), ("칸 배경색", "background-color: rgb(255, 242, 204)")):
    check("위생 처리 뒤에도 남음: " + nm, s_ in out2, out2[:400])
check("2차: 스크립트·onclick·javascript: 여전히 지워짐", "<script" not in out2.lower() and "onclick" not in out2.lower() and "javascript:" not in out2.lower(), out2[-200:])
check("2차: 손잡이·띠(겹 요소 이름)가 본문에 없음", "img-ov" not in out2 and "tbl-ov" not in out2 and "data-knk-ui" not in out2)

print("\n결과: %d 통과 / %d 실패" % (P, F))
shutil.rmtree(_TMP, ignore_errors=True)
sys.exit(1 if F else 0)
