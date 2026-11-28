# -*- coding: utf-8 -*-
"""이음메일 회사 얼굴 「더 강하게」(대표 11-28 저녁) — 빠지면 걸리는 검사
사용: py -3.13 _검증/mail_brand_strong_test.py
  ① 스위치 한 곳(main.py mail_brand_strong) · 조각은 mail_theme.html 에서 그 스위치로만
  ② 화면 조각 3곳(휴대폰 띠 · 회사 판 · 읽기 창 띠)도 같은 스위치로만 · 회사 판은 메일 앱 화면(mail_app)에서만(웍스 틀엔 테마가 없어 깨짐)
  ③ 조각에 직접 색 0(#… · rgb() · hsl()) — var(--knk-*) · color-mix 만 · 로고·패턴은 static/img/brand/ 원본 파일
  ④ 세 테마(clear·soft·dark) 값이 모두 있음 · 어둡게 빨강 판은 한 단계 낮춤(--knk-brand-hover)
  ⑤ 끈 화면 = 3단계 그대로(조각이 안 들어감) — Jinja 로 실제 그려 확인
  ⑥ 나쁜 예: 조각에 직접 색을 넣은 판은 ③ 이 실제로 잡는지
"""
import io, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
H = os.path.dirname(os.path.abspath(__file__))
R = os.path.normpath(os.path.join(H, ".."))
T = os.path.join(R, "app", "templates")
P = os.path.join(T, "_v5_partials")
ok = bad = 0


def chk(name, cond):
    global ok, bad
    if cond:
        ok += 1
        print("  [OK]", name)
    else:
        bad += 1
        print("  [XX]", name)


def rd(*p):
    return io.open(os.path.join(*p), encoding="utf-8").read()


def no_direct_color(css):
    body = re.sub(r"\{#.*?#\}", "", css, flags=re.S)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    return not re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", body)


main = rd(R, "app", "main.py")
theme = rd(P, "mail_theme.html")
strong = rd(P, "mail_brand_strong.html")
head = rd(P, "mail_app_head.html")
inbox = rd(T, "mail_inbox.html")
win = rd(T, "mail_view_win.html")

print("① 스위치")
chk("main.py 전역 스위치 한 줄", len(re.findall(r'tpl\.env\.globals\["mail_brand_strong"\]\s*=\s*(True|False)', main)) == 1)
chk("mail_theme.html 이 스위치로만 조각을 부름(mail_ci 다음)",
    re.search(r'\{% if mail_brand_strong\|default\(false\) %\}\{% include "_v5_partials/mail_brand_strong.html" %\}\{% endif %\}', theme) is not None
    and theme.find("mail_brand_strong.html") > theme.find("mail_ci.html"))
print("② 화면 조각 3곳")
chk("휴대폰 슬로건 띠 = 스위치로만", re.search(r'\{% if mail_brand_strong\|default\(false\) %\}<div class="mbs-topband" aria-hidden="true">', head) is not None)
chk("회사 판 = 스위치 + 메일 앱 화면에서만", re.search(r'\{% if mail_brand_strong\|default\(false\) and mail_app %\}<div class="mbs-face">', inbox) is not None)
chk("읽기 창 회사 띠 = 스위치로만", re.search(r'\{% if mail_brand_strong\|default\(false\) %\}<div class="mbs-winband">', win) is not None)
chk("단추·링크를 새로 만들지 않음(조각 3곳 안에 <button>·<a> 없음)",
    not re.search(r"<(button|a)\b", "".join(re.findall(r'\{% if mail_brand_strong.*?\{% endif %\}', head + inbox + win, re.S))))
print("③ 직접 색 0 · 원본 로고")
chk("조각에 직접 색 없음", no_direct_color(strong))
chk("화면 글꼴을 따로 적지 않음(대표 11-28 21:4x 화면 글꼴 = Pretendard · NanumSquare·--knk-font 금지)",
    not re.search(r"NanumSquare|--knk-font|font-family", re.sub(r"\{#.*?#\}", "", strong, flags=re.S), re.I))
for f in re.findall(r"/static/img/brand/([\w.-]+)", strong + head + inbox + win):
    chk("로고·패턴 파일 있음 " + f, os.path.isfile(os.path.join(R, "static", "img", "brand", f)))
print("④ 세 테마")
for t in ("", '="soft"', '="dark"'):
    chk("테마 값 묶음 " + (t or "공통(밝게)"), ("html.mb-strong[data-mt%s]{" % t) in strong)
chk("어둡게 빨강 판 = --knk-brand-hover", re.search(r'html\.mb-strong\[data-mt="dark"\]\{\s*--knk-mail-band:var\(--knk-brand-hover\)', strong) is not None)
chk("--mt-* 는 별칭만(M-1)", all(v.strip().startswith("var(--knk-") for v in re.findall(r"--mt-[\w-]+\s*:\s*([^;}]+)", strong)))

print("⑤ 끈 화면 = 조각 없음(Jinja)")
try:
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(T))
    env.globals.update(APP_VERSION="t", mail_design_preview=False, mail_ci=False, mi=lambda *a, **k: "")
    off = env.get_template("_v5_partials/mail_theme.html").render(mail_brand_strong=False)
    on = env.get_template("_v5_partials/mail_theme.html").render(mail_brand_strong=True)
    chk("끄면 mb-strong 없음", "mb-strong" not in off)
    chk("켜면 mb-strong 있음", "classList.add('mb-strong')" in on)
except Exception as e:  # noqa: BLE001
    chk("Jinja 그리기 " + str(e)[:80], False)

print("⑥ 나쁜 예")
chk("직접 색을 넣은 판은 잡힘", not no_direct_color(strong.replace("--knk-mail-band:var(--knk-brand);", "--knk-mail-band:#AE2025;", 1)))
chk("rgba 를 넣은 판도 잡힘", not no_direct_color(strong + "<style>.x{color:rgba(255,255,255,.5)}</style>"))

print("결과: %d/%d %s" % (ok, ok + bad, "✅ 통과" if not bad else "❌ 실패 %d" % bad))
sys.exit(1 if bad else 0)
