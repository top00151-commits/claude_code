# -*- coding: utf-8 -*-
"""
KNK Mail — 원본처럼 보이기(HTML 렌더 + 인라인 이미지 + 첨부 저장) 검증 (z393)
====================================================================
아웃룩식 메일(multipart/mixed > related > alternative + 인라인 cid 이미지 + PDF 첨부)을
파싱→저장→조회→안전HTML 정리까지 운영 코드로 검증. 실메일·운영DB 무접촉.
"""
import os, sys, sqlite3, base64

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
APP_PARENT = os.path.abspath(os.path.join(HERE, "..", "..", "01_HAIST_WORKS"))
sys.path.insert(0, APP_PARENT)

from app import database as DB
from app import mail_store as MS

PASS, FAIL = 0, 0
def check(name, cond, extra=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  [PASS] {name}" + (f"  ({extra})" if extra else ""))
    else: FAIL += 1; print(f"  [FAIL] {name}" + (f"  ({extra})" if extra else ""))

def section(t): print("\n" + "=" * 64 + f"\n{t}\n" + "=" * 64)

# 1x1 PNG
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
PDF = b"%PDF-1.4 fake quote body"

con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.execute("PRAGMA foreign_keys = ON")
con.executescript(DB.SCHEMA)
con.execute("INSERT INTO users(id,name,login_id,password,role,is_active) VALUES(1,'김정락','kjr','x','ceo',1)")
con.execute("INSERT INTO users(id,name,login_id,password,role,is_active) VALUES(2,'다른직원','emp','x','member',1)")
con.commit()

# ── 마이그레이션 확인(구 스키마 → ALTER ADD COLUMN) ──────────────────
section("DB 마이그레이션 — mail_attachments 신규 컬럼")
mig = sqlite3.connect(":memory:")
mig.execute("CREATE TABLE mail_attachments(id INTEGER PRIMARY KEY, mail_id INTEGER, filename TEXT, mime TEXT, size INTEGER, path TEXT, created_at TEXT)")
macols = [r[1] for r in mig.execute("PRAGMA table_info(mail_attachments)").fetchall()]
for col, ddl in [("content_id","ALTER TABLE mail_attachments ADD COLUMN content_id TEXT"),
                 ("is_inline","ALTER TABLE mail_attachments ADD COLUMN is_inline INTEGER DEFAULT 0"),
                 ("data","ALTER TABLE mail_attachments ADD COLUMN data BLOB")]:
    if col not in macols:
        mig.execute(ddl)
macols2 = [r[1] for r in mig.execute("PRAGMA table_info(mail_attachments)").fetchall()]
check("구 DB에 content_id/is_inline/data 추가됨", all(x in macols2 for x in ("content_id","is_inline","data")), str(macols2))
check("신 SCHEMA에도 컬럼 존재", all(x in [r[1] for r in con.execute("PRAGMA table_info(mail_attachments)").fetchall()] for x in ("content_id","is_inline","data")))

# ── 아웃룩식 메일 원문 구성 ──────────────────────────────────────────
section("받기 — 아웃룩식(인라인 서명로고 + PDF 첨부) 파싱")
cid = "image001.png@01DABCDE.KNK"
img_b64 = base64.b64encode(PNG).decode()
pdf_b64 = base64.b64encode(PDF).decode()
from email.header import Header as H
subj = H("견적서 송부드립니다", "utf-8").encode()
raw = (
    f"From: \"{H('김정락','utf-8').encode()}\" <top0015@knknara.co.kr>\r\n"
    "To: test@knk-mailtest.com\r\n"
    f"Subject: {subj}\r\nMIME-Version: 1.0\r\n"
    "Content-Type: multipart/mixed; boundary=MIX\r\n\r\n"
    "--MIX\r\nContent-Type: multipart/related; boundary=REL\r\n\r\n"
    "--REL\r\nContent-Type: multipart/alternative; boundary=ALT\r\n\r\n"
    "--ALT\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
    "안녕하세요. 케이엔케이 김정락 입니다. 견적서 첨부드립니다. 감사합니다.\r\n"
    "--ALT\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
    "<html><body><p>안녕하세요. <b>케이엔케이</b> 김정락 입니다.</p>"
    f"<p><img src=\"cid:{cid}\" alt=\"logo\"></p>"
    "<p>견적서 첨부드립니다. 감사합니다.</p>"
    "<script>alert('xss')</script><img src=x onerror=\"alert(1)\">"
    "</body></html>\r\n"
    "--ALT--\r\n"
    f"--REL\r\nContent-Type: image/png; name=\"image001.png\"\r\n"
    f"Content-Transfer-Encoding: base64\r\nContent-ID: <{cid}>\r\n"
    "Content-Disposition: inline; filename=\"image001.png\"\r\n\r\n"
    f"{img_b64}\r\n--REL--\r\n"
    f"--MIX\r\nContent-Type: application/pdf; name=\"{H('견적서.pdf','utf-8').encode()}\"\r\n"
    "Content-Transfer-Encoding: base64\r\n"
    f"Content-Disposition: attachment; filename=\"{H('견적서.pdf','utf-8').encode()}\"\r\n\r\n"
    f"{pdf_b64}\r\n--MIX--\r\n"
)

p = MS.parse_raw_email(raw)
check("제목(한글) 디코드", p.get("subject") == "견적서 송부드립니다", p.get("subject"))
check("본문 한글 정상", "케이엔케이 김정락" in (p.get("text") or ""))
check("HTML 원문 보존(cid 포함)", "cid:" in (p.get("html") or ""))
atts = p.get("attachments") or []
check("첨부 2개 추출(인라인1+파일1)", len(atts) == 2, f"n={len(atts)}")
inline = [a for a in atts if a.get("inline")]
files = [a for a in atts if not a.get("inline")]
check("인라인 이미지 1개(서명로고)", len(inline) == 1 and inline[0]["mime"] == "image/png", str([(a['filename'],a['mime']) for a in inline]))
check("인라인 content_id 보존", inline and inline[0]["content_id"] == cid, inline[0]["content_id"] if inline else "")
check("인라인 이미지 바이트=원본 PNG", inline and inline[0]["data"] == PNG)
check("일반 첨부 1개(PDF, 한글파일명)", len(files) == 1 and files[0]["filename"] == "견적서.pdf", str([a['filename'] for a in files]))
check("PDF 바이트=원본", files and files[0]["data"] == PDF)
check("텍스트 본문 끝 '[첨부]'엔 인라인 제외", "[첨부 1개: 견적서.pdf]" in (p.get("text") or ""), repr((p.get("text") or "")[-30:]))

# ── 저장 + 조회 ──────────────────────────────────────────────────────
section("저장/조회 — 첨부 저장·소유권·인라인필터")
mid, owner = MS.store_inbound(con, to_email=p["to_email"], from_email=p["from_email"],
                              from_name=p["from_name"], subject=p["subject"],
                              text=p["text"], html=p["html"], run_ai=False,
                              attachments=atts)
check("메일 저장(owner=대표)", bool(mid) and owner == 1, f"id={mid} owner={owner}")
all_a = MS.list_attachments(con, mid)
check("첨부 2건 저장됨", len(all_a) == 2, f"n={len(all_a)}")
in_a = MS.list_attachments(con, mid, inline=True)
fl_a = MS.list_attachments(con, mid, inline=False)
check("인라인/일반 분리 조회", len(in_a) == 1 and len(fl_a) == 1)
aid = in_a[0]["id"]
got = MS.get_attachment(con, aid, 1)
check("첨부 바이트 조회(소유자)", got and got["data"] == PNG and got["mime"] == "image/png")
check("소유권 차단(타인은 None)", MS.get_attachment(con, aid, 2) is None)

# ── 안전 HTML 정리 ───────────────────────────────────────────────────
section("안전 HTML — 스크립트 제거·cid 치환·서식 보존")
safe = MS.sanitize_html_for_view(p["html"], mid, in_a)
check("<script> 제거", "<script" not in safe.lower(), "")
check("onerror= 이벤트 제거", "onerror" not in safe.lower())
check("cid: → 우리 서버 URL 치환", f"/mail/{mid}/att/{aid}" in safe, "")
check("원본 cid: 흔적 없음", "cid:" not in safe)
check("서식(<b>)·이미지(<img>) 보존", "<b>" in safe and "<img" in safe.lower())

# 스타일 보존(줄간격) + @import 제거 + 파일명 기반 cid 매칭
section("안전 HTML — <style> 보존·@import 제거·파일명 cid 매칭(아웃룩 서명)")
html2 = ("<html><head><style>@import url('http://evil/x.css');"
         "p.MsoNormal{margin:0}</style></head><body>"
         "<p class=MsoNormal>줄1</p><p class=MsoNormal>줄2</p>"
         "<img src=\"cid:image001.png\">"   # content_id 없이 파일명으로만 참조
         "<img src=\"cid:image001.png@01DABCDE.KNK\"></body></html>")
safe2 = MS.sanitize_html_for_view(html2, mid, in_a)
check("<style> 규칙(MsoNormal margin:0) 보존 → 간격 유지", "MsoNormal{margin:0}" in safe2.replace(" ", ""))
check("@import(원격 CSS) 제거", "@import" not in safe2.lower())
check("파일명만으로도 cid 매칭(content_id 없는 참조)", f"/mail/{mid}/att/{aid}" in safe2)
check("content_id 정식 참조도 매칭", safe2.count(f"/mail/{mid}/att/{aid}") >= 2,
      f"matches={safe2.count(f'/mail/{mid}/att/{aid}')}")

print("\n" + "=" * 64)
print(f"결과: PASS={PASS}  FAIL={FAIL}")
print("=" * 64)
sys.exit(1 if FAIL else 0)
