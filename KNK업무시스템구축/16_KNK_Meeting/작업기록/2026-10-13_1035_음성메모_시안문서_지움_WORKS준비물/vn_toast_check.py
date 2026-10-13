# -*- coding: utf-8 -*-
"""z1167 — 🎤 음성 메모 화면에 섞여 나오던 **디자인 시안 문서**를 지운 것을 잰다.

무엇이 잘못돼 있었나
  `voice_note_form.html` 과 `voice_notes.html` 이 맨 끝에서
  `{% include "_v5_partials/toasts.html" %}` 를 불렀는데, 그 파일은 **부품이 아니라**
  「토스트·알림 5종 · v5 H5」라는 **완성된 웹페이지 한 장**(디자인 제안서)이다.
  그래서 음성 메모 화면 아래에 제안서가 통째로 찍혔다(대표 2026-10-13 신고).

  🔵 그 제안서 스스로 「현재 시스템에 토스트 시스템 **미구현** → 신규 적용 **권고**」라고 적고 있다.
     즉 **만들자는 글**이지 돌아가는 부품이 아니다. 음성 메모 화면은 토스트를 **부르지 않는다**.

재는 것 (앱 두 벌을 실제로 띄워 세 화면을 받아 본다)
  ① 🔵 **가장 센 검사** — 운영 화면에서 **시안 글자만 뺀 것**이 내 화면과 **글자 그대로 같다**
       (base 화면에서 시안 원문을 빼면 new 화면과 완전 일치 → 내가 **그것만** 뺐다는 증거)
  ② 들어온 줄 **0** · 빠진 줄은 **한 덩어리** · 그 덩어리는 `<!DOCTYPE html>` 로 시작해 `</html>` 로 끝난다
  ③ 🔴 **반대 시험** — 운영 화면에는 그 흔적이 **있다**(없으면 검사기가 헛것을 보고 있는 것)
  ④ 내 화면엔 흔적 **0** — `toast-stage`(그 파일에만 있는 이름) · `victor.toast` · `T-01` · 「토스트·알림 5종」
  ⑤ **문서가 한 장** — `<!DOCTYPE`·`<html`·`</html>` 가 각 1개(전에는 2개였다)
  ⑥ 바깥 주소 사라짐 — `jsdelivr`(바깥 폰트) · `ZZ_표준토큰.css`(**없는 파일 → 404**)
  ⑦ `body { … padding …}` 덮어쓰기 사라짐 — 음성 메모 화면 여백·바탕색이 제 것으로 돌아온다
  ⑧ 음성 메모 알맹이는 **그대로** — 받아쓴 원문 토글 · 정리 칸 · 고치기/다시 정리 · 목록 줄
  ⑨ 세 화면 모두 **200** (500 없음)

쓰는 법: py vn_toast_check.py [app_base·app_new 가 있는 폴더]
판정: **종료코드**(0=통과) — 요약 줄은 참고용. (세션 01 방식 · z1165 에서 빈 요약에 속은 적 있음)
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
RUN = os.path.join(HERE, "run_vn2_app.py")
PORT_BASE, PORT_NEW = 8981, 8982
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


#  서버가 뜬 초로 정해지는 값은 지우고 비교한다 — 안 그러면 「전부 다름」 거짓경보
_VOLATILE = [
    (re.compile(r"\?v=t[0-9]{6,}"), "?v=X"),
    (re.compile(r'"t[0-9]{9,}"'), '"tX"'),
    #  🔴 초가 **없는** 시각도 지워야 한다 — 화면은 created_at[:16] 이라 「2026-10-13 14:05」처럼
    #     분까지만 찍는다. 두 시험 서버가 1분 걸쳐 뜨면 14:05 / 14:06 으로 갈려 **거짓 실패**가 난다
    #     (2026-10-13 reg70 에서 실제로 났다). z1168 검사기엔 이미 이 꼴로 넣어 뒀었다.
    (re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}(:[0-9]{2})?"), "DATETIME"),
]
assert re.sub(_VOLATILE[-1][0], "DATETIME", "a 2026-10-13 14:05 b") == "a DATETIME b", \
    "분까지만 있는 시각을 못 지운다"


def nocache(s):
    #  🔴 이 화면틀 파일들은 저장소에 **CRLF 로 들어 있다**(원본 덩어리로 확인함).
    #     줄끝을 안 맞추면 「전부 다름」 거짓경보가 난다.
    s = s.replace("\r\n", "\n")
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
            m = re.search(r"READY \d+ me (\d+) done (\d+) todo (\d+)", s)
            return pr, {"me": int(m.group(1)), "done": int(m.group(2)),
                        "todo": int(m.group(3))}
        if pr.poll() is not None:
            print(s[-3000:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def get(port, path, uid):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path))
    req.add_header("Cookie", "tuser=%d" % uid)
    r = urllib.request.urlopen(req, timeout=60)
    return r.getcode(), nocache(r.read().decode("utf-8", "replace"))


#  그 시안 파일에만 있는 표식(저장소 전체를 훑어 확인함 — toast-stage 는 그 파일에만 있다)
MARKS = ["toast-stage", "victor.toast", "T-01", "토스트·알림 5종", "toast-spec", "gallery-head"]
OUTSIDE = ["jsdelivr", "ZZ_표준토큰.css"]

print("두 벌 띄우는 중…")
pb, ib = boot("app_base", PORT_BASE)
pn, inn = boot("app_new", PORT_NEW)
print("  운영그대로 %d · 내변경 %d (메모 %d·%d)" % (PORT_BASE, PORT_NEW, inn["done"], inn["todo"]))

#  운영 사본에 들어 있는 시안 원문 — 이것과 글자 단위로 맞춘다
SRC = io.open(os.path.join(APPDIR, "app_base", "app", "templates",
                           "_v5_partials", "toasts.html"), encoding="utf-8").read()
SRC_LF = SRC.replace("\r\n", "\n").rstrip("\n")     # Jinja 는 끝 줄바꿈을 떼고 넣는다
print("  시안 원문 %d줄" % len(SRC_LF.splitlines()))

PAGES = [("음성메모 목록", "/voice-notes"),
         ("음성메모 상세(정리 끝)", "/voice-notes/%d" % inn["done"]),
         ("새 음성메모", "/voice-notes/new")]

try:
    for title, path in PAGES:
        print("\n── 【%s】 %s ──" % (title, path))
        cb, a = get(PORT_BASE, path, ib["me"])
        cn, b = get(PORT_NEW, path, inn["me"])

        # ⑨ 두 벌 모두 200
        chk("%s · 운영 200" % title, cb == 200, "→ %s" % cb)
        chk("%s · 내변경 200" % title, cn == 200, "→ %s" % cn)

        # ③ 🔴 반대 시험 — 운영에는 흔적이 **있어야** 한다
        miss_base = [m for m in MARKS if m not in a]
        chk("%s · 운영엔 시안 흔적이 있다(검사기가 헛것을 보는지 확인)" % title,
            not miss_base, "운영에서 못 찾음: %s" % miss_base)

        # ④ 내 화면엔 흔적 0
        left = [m for m in MARKS if m in b]
        chk("%s · 내 화면엔 시안 흔적 0" % title, not left, "남음: %s" % left)

        # ① 🔵 가장 센 검사 — 운영에서 시안 원문만 빼면 내 화면과 글자 그대로 같다
        chk("%s · 운영 화면이 시안 원문을 통째로 품고 있다" % title, SRC_LF in a,
            "들어 있지 않다(표식만으론 「그것만 뺐다」를 증명 못 한다)")
        cut = a.replace(SRC_LF, "", 1)
        same = cut == b
        if not same:
            # 끝 줄바꿈 한 개 차이는 봐준다
            same = cut.replace("\n\n", "\n") == b.replace("\n\n", "\n")
        chk("%s · 🔵 시안만 뺀 운영 == 내 화면 (글자 그대로)" % title, same,
            "아직 다르다 — 시안 말고 다른 것도 바뀌었다")

        # ② 들어온 줄 0 · 빠진 줄은 한 덩어리
        la, lb = a.splitlines(), b.splitlines()
        came, gone, gone_idx = [], [], []
        i = 0
        for ln in difflib.unified_diff(la, lb, n=0, lineterm=""):
            if ln[:3] in ("---", "+++") or ln.startswith("@@"):
                continue
            if ln.startswith("+"):
                came.append(ln[1:])
            elif ln.startswith("-"):
                gone.append(ln[1:])
        chk("%s · 새로 들어온 줄 0" % title, not came, "들어옴: %s" % came[:3])
        chk("%s · 빠진 줄이 있다" % title, len(gone) > 0, "하나도 안 빠졌다")
        if gone:
            chk("%s · 빠진 덩어리가 <!DOCTYPE html> 로 시작" % title,
                gone[0].strip().lower().startswith("<!doctype html"), "→ %r" % gone[0][:60])
            chk("%s · 빠진 덩어리가 </html> 로 끝남" % title,
                gone[-1].strip().lower() == "</html>", "→ %r" % gone[-1][:60])
            chk("%s · 빠진 덩어리 안에 toast-stage 가 있다" % title,
                any("toast-stage" in g for g in gone))

        # ⑤ 문서가 한 장
        for tag, pat in (("<!DOCTYPE", r"(?i)<!doctype"), ("<html", r"(?i)<html[ >]"),
                         ("</html>", r"(?i)</html>")):
            nb, nn = len(re.findall(pat, a)), len(re.findall(pat, b))
            chk("%s · %s 가 한 개 (운영 %d → 내변경 %d)" % (title, tag, nb, nn), nn == 1,
                "아직 %d 개" % nn)

        # ⑥ 바깥 주소 사라짐
        for o in OUTSIDE:
            nb, nn = a.count(o), b.count(o)
            chk("%s · 바깥 주소 %s 0회 (운영 %d회)" % (title, o, nb), nn == 0, "아직 %d회" % nn)

        # ⑦ body 덮어쓰기 사라짐
        chk("%s · body 여백 덮어쓰기 사라짐" % title,
            "body { background: var(--paper-2); padding:" not in b)

        # ⑧ 음성 메모 알맹이는 그대로
        need = ["음성", "voice-note"]
        if path != "/voice-notes":
            need += ["받아쓴 원문", "📌 정리", "다시 정리", "vnBody", "vnSumBox"]
        lost = [s for s in need if s in a and s not in b]
        chk("%s · 음성 메모 알맹이 그대로" % title, not lost, "사라짐: %s" % lost)

finally:
    for p in (pb, pn):
        try:
            p.terminate()
        except Exception:
            pass

print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
