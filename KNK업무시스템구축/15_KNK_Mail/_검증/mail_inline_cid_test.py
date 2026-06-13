# -*- coding: utf-8 -*-
"""
KNK Mail 인라인 CID 변환 검증 —
본문에 박힌 <img src="data:image/...;base64,..."> 를 발송 직전 인라인 첨부(Content-ID)로
바꿔 보내는지 실제 _smtp_send/send_system 코드를 가짜 SMTP 로 호출해 MIME 구조까지 확인.
(저장 body_html 은 data: 유지 → 보낸함 표시 / 발송 MIME 만 cid: → 수신측 안정 표시)
"""
import os, sys, sqlite3, base64

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "01_HAIST_WORKS")))
from cryptography.fernet import Fernet
os.environ["KNK_MAIL_KEY"] = Fernet.generate_key().decode()

from app import database as DB
from app import mail_send as SEND

PASS, FAIL = 0, 0
def check(n, c, e=""):
    global PASS, FAIL
    if c: PASS += 1; print(f"  [PASS] {n}" + (f"  ({e})" if e else ""))
    else: FAIL += 1; print(f"  [FAIL] {n}" + (f"  ({e})" if e else ""))
def section(t): print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60)

# 1x1 PNG (유효 base64 + 유효 PNG 바이트)
PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
PNG_BYTES = base64.b64decode(PNG_B64)

con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.executescript(DB.SCHEMA)
SEND.save_send_config(con, "smtp.mx.cloudflare.net", "465", "api_token", "tok_secret")
con.commit()

captured = {}
class FakeSMTP:
    def __init__(self, *a, **k): pass
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def login(self, u, p): pass
    def send_message(self, msg): captured["msg"] = msg
SEND.smtplib.SMTP_SSL = FakeSMTP

def parts_of(m):
    return list(m.walk()) if m else []
def by_type(m, ctype):
    return [p for p in parts_of(m) if p.get_content_type() == ctype]
def images(m):
    return [p for p in parts_of(m) if p.get_content_maintype() == "image"]
def html_text(m):
    hs = by_type(m, "text/html")
    if not hs: return ""
    try: return hs[0].get_content()
    except Exception:
        return (hs[0].get_payload(decode=True) or b"").decode("utf-8", "replace")

# ── 1. 헬퍼 단위 ──────────────────────────────────────────────
section("1. _inline_data_images 헬퍼")
html_in = f'<p>안녕하세요</p><img src="data:image/png;base64,{PNG_B64}"><p>끝</p>'
new_html, parts = SEND._inline_data_images(html_in)
check("data: 1개 → 추출 1개", len(parts) == 1, f"parts={len(parts)}")
check("HTML 에 data: 제거됨", "data:image" not in new_html)
check("HTML 에 cid: 삽입됨", "cid:" in new_html)
if parts:
    cid_full, subtype, raw = parts[0]
    check("cid 가 <...@...> 형식", cid_full.startswith("<") and cid_full.endswith(">") and "@" in cid_full, cid_full)
    check("subtype=png", subtype == "png", subtype)
    check("디코드 바이트 == 원본 PNG", raw == PNG_BYTES)
    check("HTML cid 값이 첨부 cid 와 일치", f"cid:{cid_full[1:-1]}" in new_html)
# jpg → jpeg 정규화
_, p2 = SEND._inline_data_images(f'<img src="data:image/jpg;base64,{PNG_B64}">')
check("jpg subtype → jpeg 정규화", p2 and p2[0][1] == "jpeg", p2[0][1] if p2 else "")
# 깨진 base64 는 원본 유지(손실 방지)
bad_html = '<img src="data:image/png;base64,@@@notbase64@@@">'
nb, pb = SEND._inline_data_images(bad_html)
check("깨진 base64 → 원본 유지(변환 안 함)", len(pb) == 0 and "data:image" in nb)

# ── 2. data: 이미지만 (파일첨부 없음) ────────────────────────
section("2. 발송 MIME — data: 이미지 1개 (첨부 없음)")
captured.clear()
ok, msg = SEND.send_system(con, from_email="me@knknara.co.kr", to_email="t@y.com",
                           subject="인라인 이미지", body="텍스트 대체",
                           from_name="김정락", html=html_in)
check("발송 성공", ok is True, msg)
m = captured.get("msg")
check("multipart/related 존재", any(p.get_content_type() == "multipart/related" for p in parts_of(m)))
check("text/html 파트 존재", len(by_type(m, "text/html")) == 1)
check("text/plain 파트 존재", len(by_type(m, "text/plain")) == 1)
imgs = images(m)
check("인라인 이미지 파트 1개", len(imgs) == 1, f"imgs={len(imgs)}")
if imgs:
    check("이미지에 Content-ID 헤더", bool(imgs[0]["Content-ID"]), imgs[0]["Content-ID"] or "")
    check("이미지 Content-Disposition=inline", imgs[0].get_content_disposition() == "inline", str(imgs[0].get_content_disposition()))
    cidv = (imgs[0]["Content-ID"] or "")[1:-1]
    check("HTML 본문이 이 cid 를 참조", f"cid:{cidv}" in html_text(m), cidv)
    check("이미지 바이트 보존", imgs[0].get_payload(decode=True) == PNG_BYTES)
check("발송 HTML 에 data: 없음(전부 cid 치환)", "data:image" not in html_text(m))

# ── 3. data: 이미지 + 파일첨부 공존 ──────────────────────────
section("3. 발송 MIME — 인라인 이미지 + 파일첨부 공존")
captured.clear()
ok, msg = SEND.send_system(con, from_email="me@knknara.co.kr", to_email="t@y.com",
                           subject="이미지+첨부", body="텍스트", from_name="김정락",
                           html=html_in,
                           attachments=[("문서.pdf", b"%PDF-1.4 fake", "application/pdf")])
check("발송 성공", ok is True, msg)
m = captured.get("msg")
check("루트 multipart/mixed", m and m.get_content_type() == "multipart/mixed", m.get_content_type() if m else "")
check("multipart/related 존재", any(p.get_content_type() == "multipart/related" for p in parts_of(m)))
check("인라인 이미지 1개", len(images(m)) == 1)
pdfs = [p for p in parts_of(m) if p.get_content_type() == "application/pdf"]
check("PDF 첨부 파트 존재", len(pdfs) == 1)
check("PDF 는 attachment disposition", pdfs and pdfs[0].get_content_disposition() == "attachment")
check("이미지는 inline disposition(첨부와 구분)", images(m) and images(m)[0].get_content_disposition() == "inline")

# ── 4. 이미지 2개 + 서로 다른 CID ────────────────────────────
section("4. data: 이미지 2개 → 서로 다른 CID")
captured.clear()
html2 = (f'<img src="data:image/png;base64,{PNG_B64}">'
         f'<img src="data:image/jpeg;base64,{PNG_B64}">')
ok, msg = SEND.send_system(con, from_email="me@knknara.co.kr", to_email="t@y.com",
                           subject="두장", body="x", from_name="김정락", html=html2)
m = captured.get("msg")
imgs = images(m)
check("인라인 이미지 2개", len(imgs) == 2, f"imgs={len(imgs)}")
cids = [(p["Content-ID"] or "") for p in imgs]
check("두 이미지 CID 가 서로 다름", len(set(cids)) == 2, str(cids))
itypes = sorted([p.get_content_type() for p in imgs])
check("subtype png/jpeg 각각", itypes == ["image/jpeg", "image/png"], str(itypes))

# ── 5. data: 없는 일반 HTML → 기존 동작(관련파트 없음) ───────
section("5. data: 없는 HTML → 회귀 없음")
captured.clear()
ok, msg = SEND.send_system(con, from_email="me@knknara.co.kr", to_email="t@y.com",
                           subject="평범", body="x", from_name="김정락",
                           html="<p>그냥 <b>서식</b> 본문</p>")
m = captured.get("msg")
check("multipart/related 없음(불필요한 변환 안 함)",
      not any(p.get_content_type() == "multipart/related" for p in parts_of(m)))
check("이미지 파트 없음", len(images(m)) == 0)
check("text/html 정상 포함", len(by_type(m, "text/html")) == 1)

print("\n" + "=" * 60)
print(f"결과: PASS={PASS}  FAIL={FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
