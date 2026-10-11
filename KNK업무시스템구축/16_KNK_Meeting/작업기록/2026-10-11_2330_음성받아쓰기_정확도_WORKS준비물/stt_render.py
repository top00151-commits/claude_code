# -*- coding: utf-8 -*-
"""z1165 화면 대조 — 앱 두 벌(운영 그대로 / 내 변경)을 **실제로 띄워** 맞춰 본다.

  ① 🔵 가장 센 검사: **한국어 쓰는 분 화면이 운영과 글자 그대로 같다** —
     달라진 줄은 내가 **일부러 넣은 것뿐**이어야 하고, **지워진 줄은 없어야** 한다.
  ② 베트남어 화면에 내가 적은 베트남어가 다 나온다.
  ③ 베트남어 화면의 그 칸에 한국어가 0.
  ④ 기본값이 「자동 감지」(언어를 안 보냄 = z1165 이전과 같은 동작).
  ⑤ 음성 메모 화면에도 그 칸이 있고 **파일 단추보다 위**에 있다.
"""
import io
import os
import re
import subprocess
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

#  쓰는 법: py stt_render.py [앱두벌이있는폴더]
#     그 폴더에 app_base(지금 운영 그대로)·app_new(내 변경)가 있어야 한다.
HERE = os.path.dirname(os.path.abspath(__file__))
APPDIR = sys.argv[1] if len(sys.argv) > 1 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_stt_app.py")
PORT_BASE, PORT_NEW = 8971, 8972
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


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
            m = re.search(r"READY \d+ mid (\d+) ko (\d+) vi (\d+)", s)
            return pr, {"mid": int(m.group(1)), "ko": int(m.group(2)), "vi": int(m.group(3))}
        if pr.poll() is not None:
            print(s[-3000:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


#  🔴 캐시 번호(`?v=t1791727973`)는 **서버가 뜬 초**로 정해진다 — 두 벌이 다른 초에 떴으니
#     그대로 비교하면 「8쪽 전부 다름」이라는 거짓경보가 난다(z1159 에서 겪음).
#  🔴 이 정규식은 반드시 편집 도구로 직접 쓴다 — heredoc 이 \d 를 **진짜 백스페이스(0x08)** 로
#     바꿔 넣어 정규식이 조용히 죽은 적이 있다(z1163 · 20분 헤맴). 아래에서 그걸 확인한다.
#     ⚠ 캐시 번호 말고도 **서버가 뜬 초**로 정해지는 값이 둘 더 있다 —
#        `var LOADED = "t1791727973"` 와 회의가 만들어진 시각 `base_ts: "2026-10-11 23:23:09"`.
_VOLATILE = [
    (re.compile(r"\?v=t[0-9]{6,}"), "?v=X"),
    (re.compile(r'"t[0-9]{9,}"'), '"tX"'),
    (re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}"), "DATETIME"),
]
for _re_, _sub_ in _VOLATILE:
    assert "\x08" not in _re_.pattern, "정규식에 보이지 않는 제어 글자가 들어갔다"


def nocache(s):
    for r, sub in _VOLATILE:
        s = r.sub(sub, s)
    return s


# 🔴 정규식이 실제로 듣는지 확인한다(z1163: 조용히 죽은 정규식에 20분을 썼다)
assert nocache('a.css?v=t1791727973') == "a.css?v=X", "캐시 번호 정규식이 안 듣는다"
assert nocache('var L = "t1791727973";') == 'var L = "tX";', "버전 정규식이 안 듣는다"
assert nocache('base_ts: "2026-10-11 23:23:09",') == 'base_ts: "DATETIME",', "시각 정규식이 안 듣는다"


def get(port, path, uid):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
    req.add_header("Cookie", "tuser=%d" % uid)
    return nocache(urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace"))


print("두 벌 띄우는 중…")
pb, ib = boot("app_base", PORT_BASE)
pn, inn = boot("app_new", PORT_NEW)
print("  운영그대로 %d · 내변경 %d (회의 %d)" % (PORT_BASE, PORT_NEW, inn["mid"]))

# 내가 **일부러 넣은** 줄 (이것 말고 달라지면 안 된다)
ADDED_MARKS = ['id="sttLang"', 'id="sttLangRedo"', "sttLangPick", 'id="vnLang"',
               'id="vnLangWrap"', "<option value=",
               "회의에서 쓰는 말", "쓰는 말", "자동 감지", "한국어", "베트남어",
               "골라 주면 받아쓰기가", "function sttLang()", "lang: sttLang()",
               "JSON.stringify({ lang:", "Content-Type", "/transcribe',",
               "mf-fld", "mf-hint", "vn-fld", "label for=", "</select>", "</div>",
               "구간마다 나눠 변환", "본문(.main) 안이라",
               # 두 자리에 놓고 값이 든 칸을 찾아 쓰는 토막 · 주소로 말을 이어 넘기는 토막
               # ⚠ 여기에 "}" 처럼 흔한 토막을 넣으면 **아무 줄이나 통과해** 검사가 죽는다.
               "두 자리", "값이 든 칸", "querySelectorAll", "es[i]", "for (var i = 0",
               "return '';", "URLSearchParams", "sttlang", "encodeURIComponent",
               "var _sl=sttLang()", "afterAudioSaved", "ko·vi 만 받는다",
               "(function(){ try{", "v !== 'ko'", "}catch(_){} })();",
               "안 넘기면 사람이 고른 말이",
               "Ngôn ngữ", "Tự động", "Tiếng", "Chọn đúng"]
REMOVED_OK = ["transcribe', {})", "20분씩 나눠 변환", "/transcribe', { method:'POST' })",
              "?auto=1'; return;"]

try:
    print("\n── ① 🔵 한국어 화면이 운영과 글자 그대로 같은가 (내가 넣은 칸만 빼고) ──")
    PAGES = [("/meetings/new", "새 회의록"), ("/meetings/%d" % inn["mid"], "회의록 상세"),
             ("/voice-notes/new", "음성 메모")]
    for path, nm in PAGES:
        a = get(PORT_BASE, path, ib["ko"]).splitlines()
        b = get(PORT_NEW, path, inn["ko"]).splitlines()
        import difflib
        gone, came = [], []
        for ln in difflib.unified_diff(a, b, n=0, lineterm=""):
            if ln.startswith("---") or ln.startswith("+++") or ln.startswith("@@"):
                continue
            if ln.startswith("-"):
                gone.append(ln[1:])
            elif ln.startswith("+"):
                came.append(ln[1:])
        # 들여쓰기만 있는 줄, 그리고 **글자가 없는 구조 줄**(괄호·세미콜론만)은 설명된 것으로 본다.
        #   ⚠ 허용 목록에 "}" 같은 흔한 토막을 넣으면 **아무 줄이나 통과해** 검사가 죽는다 →
        #      대신 「알맹이가 없는 줄」만 봐준다. 글자가 한 자라도 있으면 반드시 설명돼야 한다.
        def _empty_shape(s):
            return s.strip() != "" and all(ch in " \t{}();," for ch in s)

        bad_gone = [g for g in gone
                    if g.strip() and not _empty_shape(g) and not any(m in g for m in REMOVED_OK)]
        bad_came = [c for c in came
                    if c.strip() and not _empty_shape(c) and not any(m in c for m in ADDED_MARKS)]
        chk("%-10s 지워진 줄 0 (실제 %d · 설명 안 되는 것 %d)" % (nm, len(gone), len(bad_gone)),
            not bad_gone, bad_gone[:3])
        chk("%-10s 새 줄은 모두 내가 넣은 것 (%d줄)" % (nm, len(came)), not bad_came, bad_came[:3])

    print("\n── ② 베트남어 화면에 그 칸이 베트남어로 나오나 ──")
    vi_new = get(PORT_NEW, "/meetings/%d" % inn["mid"], inn["vi"])
    for s in ["Ngôn ngữ dùng trong cuộc họp", "Tự động nhận biết (mặc định)",
              "Tiếng Hàn", "Tiếng Việt", "Chọn đúng thì việc ghi lại"]:
        chk("베트남어 「%s」" % s[:34], s in vi_new)

    print("\n── ③ 그 칸에 한국어가 남아 있지 않나 ──")
    m = re.search(r'<div class="mf-fld"[^>]*>\s*<label for="sttLang">.*?</div>\s*</div>',
                  vi_new, re.S)
    chk("그 칸을 찾았다", bool(m))
    if m:
        blk = m.group(0)
        kо = re.findall(r"[가-힣]+", blk)
        chk("베트남어 화면의 그 칸에 한국어 0개", not kо, kо[:6])

    print("\n── ④ 🔴 기본값이 「자동 감지」 = 언어를 안 보낸다(옛 동작 보존) ──")
    ko_new = get(PORT_NEW, "/meetings/%d" % inn["mid"], inn["ko"])
    sel = re.search(r'<select id="sttLang"[^>]*>(.*?)</select>', ko_new, re.S)
    chk("고르는 칸이 있다", bool(sel))
    if sel:
        opts = re.findall(r'<option value="([^"]*)"', sel.group(1))
        chk("첫 보기가 빈 값(자동)", opts and opts[0] == "", opts)
        chk("보기는 자동·ko·vi 셋", opts == ["", "ko", "vi"], opts)
        chk("아무것도 미리 골라 두지 않았다", "selected" not in sel.group(1))
    chk("🔴 칸이 **두 자리**에 있다(큰 올리기 · 접힌 다시 하기)",
        ko_new.count('class="sttLangPick"') == 2, ko_new.count('class="sttLangPick"'))
    chk("요청에 그 값을 실어 보낸다", "lang: sttLang()" in ko_new)
    chk("부를 때마다 칸을 찾는다(쥐고 있지 않다)",
        "document.querySelectorAll('select.sttLangPick')" in ko_new)
    chk("새 회의에서 고른 말을 주소로 이어 넘긴다",
        "&sttlang='+encodeURIComponent(_sl)" in ko_new)
    chk("옛 빈 몸통 호출이 사라졌다", "transcribe', {})" not in ko_new)

    print("\n── ⑤ 음성 메모 화면 ──")
    vn = get(PORT_NEW, "/voice-notes/new", inn["ko"])
    chk("그 칸이 있다", 'id="vnLang"' in vn)
    chk("🔴 파일 단추보다 **위**에 있다(고르면 바로 변환이 시작된다)",
        vn.find('id="vnLang"') < vn.find('id="vnFile"'),
        "%d vs %d" % (vn.find('id="vnLang"'), vn.find('id="vnFile"')))
    chk("요청에 그 값을 실어 보낸다", "JSON.stringify({ lang:" in vn)
    chk("기본이 자동", re.search(r'<select id="vnLang">\s*<option value="">', vn) is not None)

    print("\n── ⑥ 500 없나 (여덟 번 그려 본다) ──")
    for path, nm in PAGES:
        for who, uid in (("한국어", inn["ko"]), ("베트남어", inn["vi"])):
            try:
                h = get(PORT_NEW, path, uid)
                chk("%-10s %-4s 그려짐 (%d자)" % (nm, who, len(h)), len(h) > 2000)
            except Exception as e:
                chk("%-10s %-4s 그려짐" % (nm, who), False, str(e)[:90])
finally:
    for pr in (pb, pn):
        try:
            pr.terminate()
        except Exception:
            pass

print("\n합계 %d검사 · 실패 %d" % (OK + FAIL, FAIL))   # 「합계」 = 회귀 묶음이 읽는 말투
sys.exit(1 if FAIL else 0)
