# -*- coding: utf-8 -*-
"""z1169 검사기 — 🎤 음성 메모 **정리를 뒤에서 돌리는가**를 옛 코드와 맞대어 잰다.

왜 (대표 신고 2026-10-13 「다시 정리 눌렀는데… 정리하지 못했습니다」)
  z1168 로 정리가 길어지자(원문 27,950자 → 정리 **4,032자**) 한 요청이 **60초를 넘겼고**,
  앞단 웹서버가 먼저 끊었다. **서버는 성공해 저장까지 됐는데** 화면만 실패로 보였다(실측).
  → 받아쓰기와 같은 방식으로 바꾼다: 서버는 **시작만 알리고**, 화면이 상태를 물어본다.

🔵 **가장 센 검사** = 「정리 요청이 **바로 돌아오는가**」.
   바로 돌아오면 앞단이 끊을 수 없다. 가짜 AI 를 **느리게**(기본 5초) 만들어 둘을 견준다.
     · 옛 코드: 요청이 **5초 넘게** 붙잡혀 있다(그래서 60초짜리는 끊긴다)
     · 새 코드: 요청이 **1초 안에** 돌아오고, 정리는 뒤에서 끝난다

재는 것
  ① 🔴 반대 시험 — 옛 코드는 느린 만큼 **붙잡혀 있다** (검사가 헛돌지 않는다는 증거)
  ② 새 코드는 **바로 돌아온다**(started) · ③ 상태가 running → done 으로 간다
  ④ 🔵 **정리 글이 진짜 저장된다**(둘 다 같은 결과 — 바뀐 건 기다리는 방식뿐)
  ⑤ 두 번 눌러도 **한 번만** 일한다(already)
  ⑥ 사람이 바로 알아야 할 것은 **그대로 즉시** — 내용 없음 400 · 남의 메모 404 · 없는 메모 404
  ⑦ 지울 때 정리 상태도 같이 치운다
  ⑧ 500 없음

쓰는 법: py vn_async_check.py <포트_base> <포트_new> [app_base·app_new 가 있는 폴더]
판정: **종료코드**(0=통과).
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
PB = int(sys.argv[1]) if len(sys.argv) > 1 else 8985
PN = int(sys.argv[2]) if len(sys.argv) > 2 else 8986
APPDIR = sys.argv[3] if len(sys.argv) > 3 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_vn3_app.py")
SLOW = 5.0
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
    pr = subprocess.Popen([P313, RUN, os.path.join(APPDIR, app), str(port), str(SLOW)],
                          stdout=log, stderr=subprocess.STDOUT, cwd=APPDIR)
    for _ in range(600):
        time.sleep(0.2)
        try:
            s = io.open(lp, encoding="utf-8").read()
        except Exception:
            s = ""
        if "READY" in s:
            m = re.search(r"READY \d+ me (\d+) mine (\d+) empty (\d+) notmine (\d+)", s)
            return pr, {"me": int(m.group(1)), "mine": int(m.group(2)),
                        "empty": int(m.group(3)), "notmine": int(m.group(4))}
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def call(port, path, uid, method="GET"):
    """(HTTP 코드, 본문dict, 걸린 초)"""
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), method=method)
    req.add_header("Cookie", "tuser=%d" % uid)
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=120)
        code, raw = r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        code, raw = e.code, e.read()
    el = time.time() - t0
    try:
        d = json.loads(raw.decode("utf-8", "replace"))
    except Exception:
        d = {}
    return code, d, el


print("두 벌 띄우는 중… (가짜 AI 가 %.0f초 걸리게 해 둔다)" % SLOW)
pb, ib = boot("app_base", PB)
pn, inn = boot("app_new", PN)
print("  운영그대로 %d · 내변경 %d" % (PB, PN))

try:
    # ── ① 🔴 반대 시험 — 옛 코드는 느린 만큼 붙잡혀 있다 ─────────
    print("\n── ① 🔴 반대 시험: 옛 코드는 요청이 **붙잡혀 있다** ──")
    cb, db_, eb = call(PB, "/api/voice-note/%d/extract" % ib["mine"], ib["me"], "POST")
    chk("옛 코드 200", cb == 200, cb)
    chk("🔴 옛 코드는 %.0f초 넘게 붙잡혀 있다 (잰 값 %.1f초)" % (SLOW, eb), eb >= SLOW - 0.5,
        "%.1f초" % eb)
    chk("옛 코드는 답에 정리 글을 담아 준다", bool(db_.get("summary")), list(db_.keys()))
    chk("옛 코드엔 /extract-status 가 **없다**",
        call(PB, "/api/voice-note/%d/extract-status" % ib["mine"], ib["me"])[0] == 404)

    # ── ② 새 코드는 바로 돌아온다 ───────────────────────────────
    print("\n── ② 🔵 새 코드는 **바로 돌아온다**(앞단이 끊을 수 없다) ──")
    cn, dn, en = call(PN, "/api/voice-note/%d/extract" % inn["mine"], inn["me"], "POST")
    chk("새 코드 200", cn == 200, cn)
    chk("🔵 **1.5초 안에** 돌아온다 (잰 값 %.2f초 · 옛 코드 %.1f초)" % (en, eb), en < 1.5,
        "%.2f초" % en)
    chk("「시작했다」고 알려 준다", dn.get("started") is True, dn)
    chk("🔵 옛 코드보다 **%.1f배 빨리** 돌아온다" % (eb / max(en, 0.001)), en * 2 < eb,
        "새 %.2f초 vs 옛 %.1f초" % (en, eb))

    # ── ⑤ 두 번 눌러도 한 번만 ──────────────────────────────────
    print("\n── ⑤ 두 번 눌러도 한 번만 일한다 ──")
    c2, d2, e2 = call(PN, "/api/voice-note/%d/extract" % inn["mine"], inn["me"], "POST")
    chk("두 번째는 「이미 하고 있다」", d2.get("already") is True, d2)
    chk("두 번째도 바로 돌아온다", e2 < 1.5, "%.2f초" % e2)

    # ── ③ 상태가 running → done ─────────────────────────────────
    print("\n── ③ 상태가 running → done 으로 간다 ──")
    cs, ds, _ = call(PN, "/api/voice-note/%d/extract-status" % inn["mine"], inn["me"])
    chk("상태를 물어볼 수 있다(200)", cs == 200, cs)
    chk("지금은 **running**", ds.get("state") == "running", ds)
    seen_done, waited = False, 0.0
    for _ in range(60):
        time.sleep(0.5)
        waited += 0.5
        _, ds2, _ = call(PN, "/api/voice-note/%d/extract-status" % inn["mine"], inn["me"])
        if ds2.get("state") == "done":
            seen_done = True
            break
        if ds2.get("state") == "error":
            break
    chk("곧 **done** 이 된다 (%.1f초 뒤)" % waited, seen_done, ds2)
    chk("오류가 비어 있다", not ds2.get("error"), ds2.get("error"))

    # ── ④ 🔵 정리 글이 진짜 저장되고, 둘의 결과가 같다 ───────────
    print("\n── ④ 🔵 정리 글이 **진짜 저장**되고 옛 코드와 **같은 결과** ──")
    _, nb, _ = call(PB, "/api/voice-note/%d" % ib["mine"], ib["me"])
    _, nn, _ = call(PN, "/api/voice-note/%d" % inn["mine"], inn["me"])
    sb = (nb.get("note") or {}).get("summary") or ""
    sn = (nn.get("note") or {}).get("summary") or ""
    chk("새 코드: 정리 글이 저장됐다", bool(sn), sn[:40])
    chk("🔵 옛 코드와 **글자 그대로 같다**", sb == sn, "\n       옛:%r\n       새:%r" % (sb[:60], sn[:60]))
    chk("옛 정리 글이 **바뀌었다**(그대로가 아니다)", "옛 정리" not in sn, sn[:40])
    tb = (nb.get("note") or {}).get("title") or ""
    tn = (nn.get("note") or {}).get("title") or ""
    chk("사람이 지은 제목은 **안 건드린다**", tb == tn == "현장 설비 메모", "%r %r" % (tb, tn))

    # ── ⑥ 바로 알아야 할 것은 그대로 즉시 ───────────────────────
    print("\n── ⑥ 사람이 바로 알아야 할 것은 **그대로 즉시** ──")
    for label, nid_b, nid_n, want in [
            ("내용 없는 메모", ib["empty"], inn["empty"], 400),
            ("남의 메모", ib["notmine"], inn["notmine"], 404),
            ("없는 메모", 99999, 99999, 404)]:
        cb2, db2, eb2 = call(PB, "/api/voice-note/%d/extract" % nid_b, ib["me"], "POST")
        cn2, dn2, en2 = call(PN, "/api/voice-note/%d/extract" % nid_n, inn["me"], "POST")
        chk("%s · 옛 %d · 새 %d (같다)" % (label, cb2, cn2), cb2 == cn2 == want,
            "바라는 값 %d" % want)
        chk("%s · 새 코드도 **바로** 답한다 (%.2f초)" % (label, en2), en2 < 1.5, "%.2f초" % en2)
        if want != 404 or label == "남의 메모":
            chk("%s · 까닭을 알려 준다" % label, bool(dn2.get("error")), dn2)

    # ── ⑦ 지울 때 정리 상태도 같이 치운다 ───────────────────────
    print("\n── ⑦ 지우면 정리 상태도 같이 치운다 ──")
    cd, dd, _ = call(PN, "/api/voice-note/%d" % inn["mine"], inn["me"], "DELETE")
    chk("지워진다", cd == 200 and dd.get("ok") is True, (cd, dd))
    cs3, ds3, _ = call(PN, "/api/voice-note/%d/extract-status" % inn["mine"], inn["me"])
    chk("지운 뒤엔 상태도 **404**(기록이 남지 않는다)", cs3 == 404, (cs3, ds3))

    # ── ⑧ 500 없음 ─────────────────────────────────────────────
    print("\n── ⑧ 500 없음 ──")
    for port, lab in ((PB, "운영그대로"), (PN, "내변경")):
        s = io.open(os.path.join(APPDIR, "srv_%d.log" % port), encoding="utf-8").read()
        chk("%s · 기록에 Traceback 없음" % lab, "Traceback" not in s,
            s[-300:] if "Traceback" in s else "")
        chk("%s · 기록에 500 없음" % lab, " 500 " not in s)
finally:
    for pr in (pb, pn):
        try:
            pr.terminate()
        except Exception:
            pass

print("\n" + "=" * 58)
print("통과 %d · 실패 %d" % (OK, FAIL))
print("=" * 58)
sys.exit(1 if FAIL else 0)
