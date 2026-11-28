# -*- coding: utf-8 -*-
"""이음메일 디자인을 코드로(대표 2026-11-28) — 0·1·2·5·6단계 + 7절 새 기능 셋 시험.
사용: py -3.13 _검증/mail_design_code_test.py
  0 서명 로고 = static/img/brand/ 스킬 원본(바이트까지) · 보낼 때 인라인 첨부로 바뀜
  1 메일 색 이름(--mt-* · --md-*) = 별칭만(직접 색 0) · 세 테마가 --knk-* 값을 정함
  2 메일 공용 모양 static/css/knk-mail.css = .m-* 모두 · 색 숫자 0 · --knk-* 정의 0 · 메일 화면이 불러옴
  3 회사 모양(mail_ci) = 꺼짐(전역 False) · 켜는 줄 한 곳
  5 검사기 메일 몫(M-1~M-4) = 지금 코드 통과 · 일부러 어긴 코드는 잡힘(자체 시험)
  7 ① 보내기 전 확인: 개인 메일 섞임 · 첨부 말 ② 대화 흐름 점·선·「내 답장 아직」 ③ 보낸 사람 카드 숫자(주소 경계)
"""
import io
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
H = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(H, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "deploy"))
T = os.path.join(ROOT, "app", "templates", "_v5_partials")
ok_n = bad_n = 0


def check(name, cond, extra=""):
    global ok_n, bad_n
    if cond:
        ok_n += 1
        print("  ✅", name)
    else:
        bad_n += 1
        print("  ❌", name, extra)


def rd(*p):
    return io.open(os.path.join(*p), encoding="utf-8").read()


# ── 0단계 ──
print("0단계 서명 로고")
from app import mail_guide as mg
lg = os.path.join(ROOT, "static", *mg.SIG_LOGO_FILE.split("/"))
src = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "00_스킬규정", "knk-brand", "assets", "logo", "png", os.path.basename(lg))
check("서명 로고 = static/img/brand/ 아래", mg.SIG_LOGO_FILE.startswith("img/brand/") and os.path.isfile(lg))
check("서명 로고 = 스킬 원본과 바이트까지 같음", (not os.path.exists(src)) or open(lg, "rb").read() == open(src, "rb").read())
html = mg.design_html("김가짜 대리\nKim Gajja\n(주)케이엔케이 · 서울", "hq", "ko")
check("서명 HTML 에 로고 그림(data:) · 폭 %d" % mg.SIG_LOGO_W, html.count('src="data:image/png;base64,') >= 1 and ('width="%d"' % mg.SIG_LOGO_W) in html)
from app import mail_send as ms
h2, imgs = ms._inline_data_images(html)
check("보낼 때 로고 = 인라인 첨부(cid · 받는 쪽 메일 프로그램에서도 보임)", "data:image" not in h2 and 'src="cid:' in h2 and len(imgs) >= 1)

# ── 1단계 ──
print("\n1단계 메일 색 이름 = 별칭")
alltxt = ""
for fn in ("mail_theme.html", "mail_design_v2.html", "mail_contrast.html"):
    s = re.sub(r"/\*.*?\*/", "", rd(T, fn), flags=re.S)
    alltxt += s
    bad = [m.group(0)[:60] for m in re.finditer(r"(?<![\w-])--(?:mt|md)-[\w-]+\s*:\s*[^;{}]*(#[0-9a-fA-F]{3,8}|rgba?\()", s)]
    check("%s — --mt-*·--md-* 정의에 직접 색 0" % fn, not bad, bad[:3])
for th in ("clear", "soft", "dark"):
    blk = re.search(r'html\[data-mt="%s"\]\{(.*?)\}' % th, alltxt, re.S)
    body = blk.group(1) if blk else ""
    need = ["--knk-bg-page", "--knk-bg-surface", "--knk-text-primary", "--knk-text-muted", "--knk-border-default", "--knk-bg-selected", "--knk-info"]
    check("테마 %s 가 --knk-* 값을 정함(%d개)" % (th, len(need)), all(n + ":" in body.replace(" ", "") for n in need))
check("돌고 도는 이름 없음(--knk-text-*:var(--mt-*) 옛 줄 빠짐)", "--knk-text-primary:var(--mt-text)" not in alltxt)
check("주석 안에 「*/」가 끼어 CSS 가 끊기지 않음", "*/--" not in rd(T, "mail_theme.html") and "*/--" not in rd(T, "mail_design_v2.html"))

# ── 2단계 ──
print("\n2단계 메일 공용 모양")
css = rd(ROOT, "static", "css", "knk-mail.css")
cssn = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
want = ["m-ic", "m-app", "m-top", "m-brand", "m-body", "m-side", "m-list", "m-read", "m-f", "m-u", "m-n", "m-side-h", "m-today", "m-chip",
        "m-filter", "m-row", "m-dot", "m-from", "m-subj", "m-snip", "m-time", "m-tags", "m-star", "m-read-in", "m-tool", "m-subject", "m-av",
        "m-person", "m-meta", "m-bodytext", "m-att", "m-menu"]
miss = [w for w in want if not re.search(r"\." + re.escape(w) + r"(?![\w-])", cssn)]
check("knk-mail.css 에 .m-* %d가지" % len(want), not miss, miss)
check("knk-mail.css 색 숫자 0", not re.search(r"#[0-9a-fA-F]{3,8}\b", cssn))
check("knk-mail.css 가 --knk-* 를 정하지 않음(쓰기만)", not re.search(r"(?<![\w(-])--knk-[\w-]+\s*:", cssn))
check("메일 테마가 knk-mail.css 를 불러옴", "/static/css/knk-mail.css" in rd(T, "mail_theme.html"))

# ── 3단계 꺼짐 ──
print("\n3단계 회사 모양 = 꺼짐(대표 「올려」 전)")
main_src = rd(ROOT, "app", "main.py")
check("전역 mail_ci = False", re.search(r'(?m)^tpl\.env\.globals\["mail_ci"\] = False', main_src) is not None)
mt = rd(T, "mail_theme.html")
check("mail_ci.html 은 mail_ci(또는 견본 미리보기)일 때만 들어옴", re.search(r"\{%\s*if\s*mail_ci\b[^%]*%\}\s*\{%\s*include\s*\"_v5_partials/mail_ci.html\"", mt) is not None)

# ── 5단계 검사기 ──
print("\n5단계 검사기 메일 몫")
import check_standards as cs
b, e = cs.check_mail_design()
new, old = cs.split_by_path(e, cs.MAIL_EMOJI_BASE)
check("지금 메일 코드: M-1·M-3·M-4 위반 0", not b, b[:3])
check("지금 메일 코드: 새 그림 문자 단추 0 (면제 %d)" % old, not new, new[:3])
st = cs.mail_design_selftest()
check("일부러 어긴 코드(직접 색 · 그림 문자 단추 · 다른 회사 색 · 원본 아닌 로고)를 모두 잡음", not st, st[:3])

# ── 7절 ① 보내기 전에 확인 ──
print("\n7 ① 보내기 전에 확인")
cmp = rd(ROOT, "app", "templates", "mail_compose.html")
check("개인 메일 주소 목록을 서버 한 곳에서 받음(mail_free_domains)", "mail_free_domains" in cmp and "mail_free_domains" in main_src)
check("개인 메일 섞임 알림 있음 · 「그래도 보내기」 그대로", "회사 밖 개인 메일" in cmp and "그래도 보내기" in cmp)
check("회신·전달 제목의 「첨부」는 첨부 잊음으로 안 봄(원래 메일 말)", "subjOwn" in cmp)

# ── 7절 ② 대화 흐름 ──
print("\n7 ② 대화 흐름")
from app import mail_thread as mth
items = [{"id": 1, "out": False, "cur": False, "at": "11-01 09:00", "who": "가"}, {"id": 2, "out": True, "cur": False, "at": "11-01 10:00", "who": "→ 가"},
         {"id": 3, "out": False, "cur": True, "at": "11-02 09:00", "who": "가"}]
fd = mth.flow_dots(items, True)
check("점 3 · 선 2 · 받은 메일은 아래 · 보낸 메일은 위(사선)", len(fd["dots"]) == 3 and len(fd["lines"]) == 2 and fd["dots"][0]["y"] > fd["dots"][1]["y"])
check("마지막이 받은 메일 → 「내 답장 아직」 회색 자리", fd["wait"] is not None and fd["wait"]["x"] > fd["dots"][-1]["x"])
fd2 = mth.flow_dots(items[:2], False)
check("마지막이 내 답장 → 회색 자리 없음", fd2["wait"] is None)
many = [{"id": i, "out": i % 2 == 0, "cur": i == 30, "at": "", "who": ""} for i in range(1, 41)]
fd3 = mth.flow_dots(many, False)
check("40통이면 %d통만 그리고 지금 메일이 들어 있음" % mth.FLOW_MAX, len(fd3["dots"]) == mth.FLOW_MAX and any(d["cur"] for d in fd3["dots"]) and fd3["more"] > 0)

# ── 7절 ③ 보낸 사람 카드 숫자 ──
print("\n7 ③ 보낸 사람 카드")
from app import mail_people as mp
c = sqlite3.connect(":memory:")
c.execute("CREATE TABLE mail_messages(id INTEGER PRIMARY KEY, user_id INT, direction TEXT, from_email TEXT, to_email TEXT, cc TEXT, "
          "is_deleted INT DEFAULT 0, is_blocked INT DEFAULT 0, received_at TEXT, created_at TEXT, sent_at TEXT)")
rows = [(1, "in", "han@acme.co.kr", "me@knknara.co.kr", "", 0, 0, "2026-11-01 09:00:00"),
        (1, "in", "han@acme.co.kr", "me@knknara.co.kr", "", 0, 0, "2026-11-03 09:00:00"),
        (1, "in", "han@acme.co.kr", "me@knknara.co.kr", "", 1, 0, "2026-11-04 09:00:00"),     # 지운 메일 — 안 셈
        (1, "in", "han@acme.co.kr", "me@knknara.co.kr", "", 0, 1, "2026-11-05 09:00:00"),     # 스팸함 — 안 셈
        (1, "in", "kim@acme.co.kr", "me@knknara.co.kr", "", 0, 0, "2026-11-02 09:00:00"),
        (1, "out", "me@knknara.co.kr", "khan@acme.co.kr", "", 0, 0, "2026-11-02 10:00:00"),  # khan 은 han 아님
        (1, "out", "me@knknara.co.kr", "Han <han@acme.co.kr>", "boss@knknara.co.kr", 0, 0, "2026-11-06 10:00:00"),
        (1, "out", "me@knknara.co.kr", "x@other.com", "han@acme.co.kr", 0, 0, "2026-11-07 10:00:00"),
        (2, "in", "han@acme.co.kr", "other@knknara.co.kr", "", 0, 0, "2026-11-01 09:00:00")]   # 남의 메일함 — 안 셈
for r in rows:
    c.execute("INSERT INTO mail_messages(user_id,direction,from_email,to_email,cc,is_deleted,is_blocked,received_at,sent_at) VALUES(?,?,?,?,?,?,?,?,?)",
              r + (r[7],))
n = mp.who_counts(c, 1, "han@acme.co.kr", "acme.co.kr", True)
check("이 사람에게서 받은 메일 2통(지운·스팸·남의 메일 뺌)", n["p_in"] == 2, n)
check("내가 이 사람에게 보낸 메일 2통(khan@ 은 안 셈 · 참조 포함)", n["p_out"] == 2, n)
check("이 회사(@acme.co.kr)에서 받은 3통 · 내가 보낸 3통", n["d_in"] == 3 and n["d_out"] == 3, n)
check("마지막 받은 날·보낸 날", n["p_last_in"] == "2026-11-03" and n["p_last_out"] == "2026-11-07", n)
n2 = mp.who_counts(c, 1, "x@gmail.com", "gmail.com", False)
check("개인 메일 주소면 회사 숫자 안 셈(None)", n2["d_in"] is None and n2["d_out"] is None)
vb = rd(T, "mail_view_body.html")
check("읽기 화면: 보낸 사람 카드는 누를 때 숫자를 부름(메일 여는 속도에 안 얹음)", "/who-card" in vb and "mvWhoCard" in vb)
check("읽기 화면: 대화 흐름 그림 · 「내 답장 아직」", "mv-flow" in vb and "내 답장 아직" in vb)

print("\n결과: %d/%d 통과" % (ok_n, ok_n + bad_n))
sys.exit(1 if bad_n else 0)
