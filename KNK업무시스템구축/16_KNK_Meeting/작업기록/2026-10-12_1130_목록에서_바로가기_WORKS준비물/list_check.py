# -*- coding: utf-8 -*-
"""z1166 — 회의록 목록의 「✏ 수정 · 📄 양식」 바로가기를 **앱 두 벌을 실제로 띄워** 잰다.

  ① 🔵 가장 센 검사: **한국어 화면이 운영과 글자 그대로 같다** — 달라진 줄은 내가 넣은 것뿐,
     **지워진 줄은 없어야** 한다.
  ② 🔴 `<a>` 안에 `<a>` 가 **없어야** 한다 — 전에는 줄 전체가 링크였다(구조를 나눈 까닭).
  ③ 고칠 수 있는 회의 = ✏ 가 **링크** · 못 고치는 회의 = ✏ 가 **흐린 글자**(안 눌림)
  ④ 📄 는 둘 다 `/meetings/<id>/doc` 로 간다
  ⑤ 베트남어 화면도 같고, 그 칸에 한국어가 0
  ⑥ 500 없음

쓰는 법: py list_check.py [app_base·app_new 가 있는 폴더]
"""
import difflib
import io
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_list_app.py")
PORT_BASE, PORT_NEW = 8975, 8976
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


#  변하는 값(서버가 뜬 초로 정해짐)은 지우고 비교한다 — 안 그러면 「전부 다름」 거짓경보
_VOLATILE = [
    (re.compile(r"\?v=t[0-9]{6,}"), "?v=X"),
    (re.compile(r'"t[0-9]{9,}"'), '"tX"'),
    (re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"), "DATETIME"),
]
for _r, _s in _VOLATILE:
    assert "\x08" not in _r.pattern, "정규식에 제어 글자"


def nocache(s):
    for r, sub in _VOLATILE:
        s = r.sub(sub, s)
    return s


assert nocache("a.css?v=t1791727973") == "a.css?v=X", "정규식이 안 듣는다"


def boot(app, port):
    lp = os.path.join(APPDIR, "srv_%d.log" % port)
    log = io.open(lp, "w", encoding="utf-8")
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port)],
                          stdout=log, stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(600):
        time.sleep(0.2)
        try:
            s = io.open(lp, encoding="utf-8").read()
        except Exception:
            s = ""
        if "READY" in s:
            m = re.search(r"READY \d+ ko (\d+) vi (\d+) ok (\d+) no (\d+)", s)
            return pr, {"ko": int(m.group(1)), "vi": int(m.group(2)),
                        "ok": int(m.group(3)), "no": int(m.group(4))}
        if pr.poll() is not None:
            print(s[-3000:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def get(port, path, uid):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
    req.add_header("Cookie", "tuser=%d" % uid)
    return nocache(urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace"))


ADDED = ['mtg-row', 'mtg-acts', 'mtg-act', 'mt_act', '수정', '양식', '/doc"',
         'aria-disabled', 'aria-label', '✏', '📄', '</div>', '</a>',
         '줄에서 바로 들어가기', '본문 링크', '겉모습', '안 눌린다', '뜨는 느낌',
         'Sửa', 'Biểu mẫu', 'biên bản', 'không sửa được',
         '{% if m.can_edit %}', '{% else %}', '{% endif %}',
         'display:flex', 'border-radius:999px', '이름과 href 를 그대로', '꺾쇠 태그를 적지 말 것',
         '시험 4곳이 깨진다', 'ui_share', 'not-allowed', 'opacity', 'max-width: 560px', 'z1166',
         'transition: all .12s', 'color: var(--qv-ink-2);',
         'border:1px solid var(--qv-line); border-radius', 'padding:14px 18px', 'align-items:center',
         'flex:1; min-width:0; text-decoration:none']
#  겉모습을 바깥 칸으로 옮기며 지워진 CSS 두 줄 · 들여쓰기만 바뀐 닫는 태그
REMOVED_OK = ['.mtg-card { display:block;', '.mtg-card:hover {', '</a>']

print("두 벌 띄우는 중…")
pb, ib = boot("app_base", PORT_BASE)
pn, inn = boot("app_new", PORT_NEW)
print("  운영그대로 %d · 내변경 %d (고칠수있는회의 %d · 못고치는회의 %d)"
      % (PORT_BASE, PORT_NEW, inn["ok"], inn["no"]))

try:
    print("\n── ① 🔵 한국어 화면이 운영과 글자 그대로 같은가 (내가 넣은 것만 빼고) ──")
    a = get(PORT_BASE, "/meetings", ib["ko"]).splitlines()
    b = get(PORT_NEW, "/meetings", inn["ko"]).splitlines()
    gone, came = [], []
    for ln in difflib.unified_diff(a, b, n=0, lineterm=""):
        if ln[:3] in ("---", "+++", "@@ "):
            continue
        if ln.startswith("-"):
            gone.append(ln[1:])
        elif ln.startswith("+"):
            came.append(ln[1:])

    def shape_only(s):
        return s.strip() != "" and all(ch in " \t{}();,<>/" for ch in s)

    bad_gone = [g for g in gone if g.strip() and not shape_only(g)
                and not any(m in g for m in REMOVED_OK)]
    bad_came = [c for c in came if c.strip() and not shape_only(c)
                and not any(m in c for m in ADDED)]
    chk("지워진 줄 0 (실제 %d · 설명 안 되는 것 %d)" % (len(gone), len(bad_gone)),
        not bad_gone, bad_gone[:3])
    chk("새 줄은 모두 내가 넣은 것 (%d줄)" % len(came), not bad_came, bad_came[:3])

    print("\n── ② 🔴 링크 안에 링크가 없나 (전에는 줄 전체가 링크였다) ──")
    ko_new = get(PORT_NEW, "/meetings", inn["ko"])
    #  🔴 이 정규식은 **주석에 적힌 글자도** 잡는다 — 바깥 틀 JS 주석에 원래 3개가 있다.
    #     그래서 「0개」로 보지 말고 **운영 그대로와 견줘 늘지 않았나**로 본다.
    #     그리고 **줄 토막 안쪽**은 따로 엄격히 본다(거기가 내가 고친 곳이다).
    NEST = re.compile(r"<a\b[^>]*>(?:(?!</a>).)*?<a\b", re.S)
    ko_base_h = get(PORT_BASE, "/meetings", ib["ko"])
    nb, nn = len(NEST.findall(ko_base_h)), len(NEST.findall(ko_new))
    chk("링크 안 링크: 운영 %d개 → 내 변경 %d개 (늘지 않음)" % (nb, nn), nn <= nb, (nb, nn))
    _rows = re.findall(r'<div class="mtg-row">.*?</div>\s*</div>', ko_new, re.S)
    chk("🔴 줄 토막 안에는 링크 안 링크 0개 (줄 %d개 검사)" % len(_rows),
        len(_rows) >= 2 and all(not NEST.search(r) for r in _rows), len(_rows))
    chk("줄을 감싸는 칸이 생겼다(.mtg-row)", '<div class="mtg-row">' in ko_new)

    print("\n── ②-B 🔴 줄을 글자로 찾는 **다른 시험 4곳**이 그대로 도나 ──")
    #  ui_share.py:52 · ui_back.py:101 · ui_back_z1130.py:111 · verify_cards.py:207 이
    #  a.mtg-card[href^="/meetings/"] 로 줄을 찾는다. 이름을 바꾸면 그 넷이 조용히 깨진다
    #  (z1166 에서 실제로 깨뜨려 봤다 → 그래서 이름을 그대로 두는 쪽으로 다시 만들었다).
    chk("🔵 a.mtg-card[href^=/meetings/] 모양이 살아 있다",
        re.search(r'<a class="mtg-card" href="/meetings/\d+">', ko_new) is not None)
    chk("🔵 verify_cards 의 정규식이 줄을 센다",
        len(re.findall(r'<a class="mtg-card" href="/meetings/\d+">', ko_new)) >= 2,
        len(re.findall(r'<a class="mtg-card" href="/meetings/\d+">', ko_new)))
    chk("🔵 카드 탭엔 그 줄이 없다(verify_cards A7 과 같은 검사)",
        'class="mtg-card"' not in get(PORT_NEW, "/meetings?tab=cards", inn["ko"]))

    print("\n── ③ 고칠 수 있나에 따라 ✏ 가 달라지나 ──")
    def row(html, mid):
        i = html.find('href="/meetings/%d"' % mid)
        if i < 0:
            return ""
        s = html.rfind('<div class="mtg-row">', 0, i)
        e = html.find('<div class="mtg-row">', i)
        return html[s:(e if e > 0 else i + 3000)]
    r_ok, r_no = row(ko_new, inn["ok"]), row(ko_new, inn["no"])
    chk("두 회의 줄을 다 찾았다", bool(r_ok) and bool(r_no))
    chk("고칠 수 있는 회의: ✏ 가 **링크**", '<a class="mtg-act" href="/meetings/%d"' % inn["ok"] in r_ok)
    chk("고칠 수 있는 회의: 흐린 표시 없음", "mtg-act off" not in r_ok)
    chk("🔴 못 고치는 회의: ✏ 가 **흐린 글자**(링크 아님)", "mtg-act off" in r_no)
    chk("🔴 못 고치는 회의: 수정 링크가 아예 없다",
        ('<a class="mtg-act" href="/meetings/%d"' % inn["no"]) not in r_no)
    chk("못 고치는 까닭을 알려 준다", "고칠 수 없습니다" in r_no)

    print("\n── ④ 📄 양식은 둘 다 /doc 로 ──")
    for nm, mid, rr in (("고칠 수 있는", inn["ok"], r_ok), ("못 고치는", inn["no"], r_no)):
        chk("%s 회의 → /meetings/%d/doc" % (nm, mid), '/meetings/%d/doc"' % mid in rr)
    chk("양식 주소가 정말 열린다(200)",
        urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:%d/meetings/%d/doc" % (PORT_NEW, inn["ok"]),
            headers={"Cookie": "tuser=%d" % inn["ko"]}), timeout=60).status == 200)

    print("\n── ⑤ 베트남어 쓰는 분 화면 (권한은 한국어 쪽과 똑같게 맞춰 둠) ──")
    vi_new = get(PORT_NEW, "/meetings", inn["vi"])
    for s in ("Sửa", "Biểu mẫu", "Sửa biên bản", "Xem theo biểu mẫu biên bản"):
        chk("베트남어 「%s」" % s, s in vi_new)
    v_ok, v_no = row(vi_new, inn["ok"]), row(vi_new, inn["no"])
    chk("베트남어도: 고칠 수 있는 회의 = 링크", '<a class="mtg-act" href="/meetings/%d"' % inn["ok"] in v_ok)
    chk("베트남어도: 못 고치는 회의 = 흐림", "mtg-act off" in v_no)
    m = re.search(r'<div class="mtg-acts">.*?</div>', v_ok, re.S)
    chk("그 칸을 찾았다", bool(m))
    if m:
        kor = re.findall(r"[가-힣]+", m.group(0))
        chk("베트남어 화면의 그 칸에 한국어 0개", not kor, kor[:5])

    print("\n── ⑥ 500 없나 ──")
    for who, uid in (("한국어", inn["ko"]), ("베트남어", inn["vi"])):
        for path in ("/meetings", "/meetings?tab=cards", "/meetings/%d" % inn["ok"],
                     "/meetings/%d/doc" % inn["ok"]):
            try:
                h = get(PORT_NEW, path, uid)
                chk("%-4s %-28s 그려짐" % (who, path), len(h) > 1500)
            except Exception as e:
                chk("%-4s %-28s 그려짐" % (who, path), False, str(e)[:80])
finally:
    for pr in (pb, pn):
        try:
            pr.terminate()
        except Exception:
            pass

print("\n합계 %d검사 · 실패 %d" % (OK + FAIL, FAIL))
sys.exit(1 if FAIL else 0)
