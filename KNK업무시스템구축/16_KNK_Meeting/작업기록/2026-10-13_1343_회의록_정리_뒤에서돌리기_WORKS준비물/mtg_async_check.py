# -*- coding: utf-8 -*-
"""z1170 검사기 — 🗓 회의록 **AI 정리를 뒤에서 돌리는가**를 옛 코드와 맞대어 잰다.

대표 지시 2026-10-13 「**회의록도 같은 방식으로 변경해**」
  (음성 메모에서 z1168→z1169 로 겪은 일 — 정리가 길어지자 앞단 기다림 한도 60초를 넘겨
   연결이 먼저 끊겼고, **서버는 성공해 저장까지 했는데** 화면엔 실패만 떴다.)
  🔵 받아쓰기는 2026-08-24(z1090)에 이미 같은 까닭으로 뒤로 보냈다 — **정리만 안 옮겨져 있었다.**

🔵 **가장 센 검사** = 「정리 요청이 **바로 돌아오는가**」 + 「**결과가 옛 코드와 똑같은가**」.
   가짜 AI 를 **느리게**(기본 5초) 만들어 둘을 견준다.

재는 것
  ① 🔴 반대 시험 — 옛 코드는 느린 만큼 **붙잡혀 있고**, /extract-status 가 **없다**
  ② 새 코드는 **바로 돌아온다**(started) · ③ 상태가 running → done
  ④ 🔵 **결과가 옛 코드와 글자 그대로 같다** — 요약·제목·결정·할 일 전부
  ⑤ 🔴 **사람이 손으로 적은 결정·할 일은 안 지운다**(옛 코드와 같은 규칙)
  ⑥ 두 번 눌러도 **한 번만** 일한다(already)
  ⑦ 바로 알아야 할 것은 **그대로 즉시** — 내용 없음 400 · 남의 회의 403 · 없는 회의 404
     (상태 입구도 **같은 권한 판정**을 쓴다 — 남의 회의 상태는 못 본다)
  ⑧ 500 없음

쓰는 법: py mtg_async_check.py <포트_base> <포트_new> [app_base·app_new 가 있는 폴더]
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
PB = int(sys.argv[1]) if len(sys.argv) > 1 else 8991
PN = int(sys.argv[2]) if len(sys.argv) > 2 else 8992
APPDIR = sys.argv[3] if len(sys.argv) > 3 else HERE
P313 = "C:/Users/top00/AppData/Local/Programs/Python/Python313/python.exe"
RUN = os.path.join(HERE, "run_mtg3_app.py")
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
            m = re.search(r"READY \d+ me (\d+) other (\d+) mine (\d+) empty (\d+) notmine (\d+)", s)
            return pr, {"me": int(m.group(1)), "other": int(m.group(2)), "mine": int(m.group(3)),
                        "empty": int(m.group(4)), "notmine": int(m.group(5))}
        if pr.poll() is not None:
            print(s[-2500:])
            raise SystemExit("!! %s(%d) 가 떴다 죽었다" % (app, port))
    raise SystemExit("!! %s(%d) 가 안 떴다" % (app, port))


def call(port, path, uid, method="GET"):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), method=method)
    req.add_header("Cookie", "tuser=%d" % uid)
    if method == "POST":
        req.add_header("Content-Type", "application/json")
        req.data = b"{}"
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


def shape(d):
    """견줄 알맹이만 뽑는다 — 줄 번호(id)·시각처럼 돌릴 때마다 달라지는 값은 뺀다."""
    def rows(xs, keys):
        return [{k: (r.get(k) if isinstance(r, dict) else None) for k in keys} for r in (xs or [])]
    return {
        "summary": d.get("summary"),
        "title": d.get("title"),
        "decisions": rows(d.get("decisions"), ("who", "what", "due", "source")),
        "actions": rows(d.get("actions"), ("assignee_name", "task", "due_date", "source")),
        "has_ts": bool(d.get("updated_at")),
    }


print("두 벌 띄우는 중… (가짜 AI %.0f초)" % SLOW)
pb, ib = boot("app_base", PB)
pn, inn = boot("app_new", PN)

try:
    # ── ① 🔴 반대 시험 ─────────────────────────────────────────
    print("\n── ① 🔴 반대 시험: 옛 코드는 요청이 **붙잡혀 있다** ──")
    cb, db_, eb = call(PB, "/api/meeting/%d/extract" % ib["mine"], ib["me"], "POST")
    chk("옛 코드 200", cb == 200, (cb, db_.get("error")))
    chk("🔴 옛 코드는 %.0f초 넘게 붙잡혀 있다 (잰 값 %.1f초)" % (SLOW, eb), eb >= SLOW - 0.5,
        "%.1f초" % eb)
    chk("옛 코드는 답에 정리 결과를 담아 준다", bool(db_.get("summary")), list(db_.keys()))
    chk("옛 코드엔 /extract-status 가 **없다**",
        call(PB, "/api/meeting/%d/extract-status" % ib["mine"], ib["me"])[0] == 404)

    # ── ② 새 코드는 바로 돌아온다 ───────────────────────────────
    print("\n── ② 🔵 새 코드는 **바로 돌아온다**(앞단이 끊을 수 없다) ──")
    cn, dn, en = call(PN, "/api/meeting/%d/extract" % inn["mine"], inn["me"], "POST")
    chk("새 코드 200", cn == 200, (cn, dn.get("error")))
    chk("🔵 **1.5초 안에** 돌아온다 (잰 값 %.2f초 · 옛 코드 %.1f초)" % (en, eb), en < 1.5,
        "%.2f초" % en)
    chk("「시작했다」고 알려 준다", dn.get("started") is True, dn)
    chk("🔵 옛 코드보다 **%.0f배 빨리** 돌아온다" % (eb / max(en, 0.001)), en * 2 < eb,
        "새 %.2f초 vs 옛 %.1f초" % (en, eb))

    # ── ⑥ 두 번 눌러도 한 번만 ──────────────────────────────────
    print("\n── ⑥ 두 번 눌러도 한 번만 일한다 ──")
    c2, d2, e2 = call(PN, "/api/meeting/%d/extract" % inn["mine"], inn["me"], "POST")
    chk("두 번째는 「이미 하고 있다」", d2.get("already") is True, d2)
    chk("두 번째도 바로 돌아온다", e2 < 1.5, "%.2f초" % e2)

    # ── ③ 상태가 running → done ─────────────────────────────────
    print("\n── ③ 상태가 running → done 으로 간다 ──")
    cs, ds, _ = call(PN, "/api/meeting/%d/extract-status" % inn["mine"], inn["me"])
    chk("상태를 물어볼 수 있다(200)", cs == 200, cs)
    chk("지금은 **running**", ds.get("state") == "running", ds)
    chk("아직 결과는 안 담겨 있다", not ds.get("summary"), ds.get("summary"))
    seen, waited, ds2 = False, 0.0, {}
    for _ in range(60):
        time.sleep(0.5)
        waited += 0.5
        _, ds2, _ = call(PN, "/api/meeting/%d/extract-status" % inn["mine"], inn["me"])
        if ds2.get("state") in ("done", "error"):
            seen = ds2.get("state") == "done"
            break
    chk("곧 **done** 이 된다 (%.1f초 뒤)" % waited, seen, ds2.get("state"))
    chk("오류가 비어 있다", not ds2.get("error"), ds2.get("error"))

    # ── ④ 🔵 결과가 옛 코드와 같다 ──────────────────────────────
    print("\n── ④ 🔵 결과가 옛 코드와 **글자 그대로 같다** ──")
    sb, sn = shape(db_), shape(ds2)
    chk("요약이 같다", sb["summary"] == sn["summary"], "\n       옛:%r\n       새:%r"
        % (sb["summary"], sn["summary"]))
    chk("AI 제안 제목이 같다", sb["title"] == sn["title"], "%r vs %r" % (sb["title"], sn["title"]))
    chk("결정사항이 같다", sb["decisions"] == sn["decisions"],
        "\n       옛:%s\n       새:%s" % (sb["decisions"], sn["decisions"]))
    chk("할 일이 같다", sb["actions"] == sn["actions"],
        "\n       옛:%s\n       새:%s" % (sb["actions"], sn["actions"]))
    chk("저장 시각(updated_at)을 돌려준다", sb["has_ts"] and sn["has_ts"],
        "%s %s" % (sb["has_ts"], sn["has_ts"]))

    # ── ⑤ 🔴 사람이 적은 것은 안 지운다 ─────────────────────────
    print("\n── ⑤ 🔴 사람이 손으로 적은 결정·할 일은 **안 지운다** ──")
    for lab, s in (("옛 코드", sb), ("새 코드", sn)):
        man_d = [r for r in s["decisions"] if r.get("source") == "manual"]
        man_a = [r for r in s["actions"] if r.get("source") == "manual"]
        ai_d = [r for r in s["decisions"] if r.get("source") == "ai"]
        chk("%s · 사람이 적은 결정이 남아 있다" % lab, len(man_d) == 1, s["decisions"])
        chk("%s · 사람이 적은 할 일이 남아 있다" % lab, len(man_a) == 1, s["actions"])
        chk("%s · AI 가 적은 결정도 들어왔다" % lab, len(ai_d) == 1, s["decisions"])

    # ── ⑦ 바로 알아야 할 것은 그대로 즉시 ───────────────────────
    print("\n── ⑦ 바로 알아야 할 것은 **그대로 즉시** ──")
    for label, key, want in (("내용 없는 회의", "empty", 400),
                             ("남의 회의", "notmine", 403),
                             ("없는 회의", None, 404)):
        nb = 99999 if key is None else ib[key]
        nn = 99999 if key is None else inn[key]
        cb2, db2, _ = call(PB, "/api/meeting/%d/extract" % nb, ib["me"], "POST")
        cn2, dn2, en2 = call(PN, "/api/meeting/%d/extract" % nn, inn["me"], "POST")
        chk("%s · 옛 %d · 새 %d (같다 · 바라는 값 %d)" % (label, cb2, cn2, want),
            cb2 == cn2 == want)
        chk("%s · 새 코드도 **바로** 답한다 (%.2f초)" % (label, en2), en2 < 1.5, "%.2f초" % en2)
        chk("%s · 까닭을 알려 준다" % label, bool(dn2.get("error")), dn2)
    #  상태 입구도 같은 권한 판정
    cs2, _, _ = call(PN, "/api/meeting/%d/extract-status" % inn["notmine"], inn["me"])
    chk("🔴 남의 회의는 **상태도 못 본다**(403)", cs2 == 403, cs2)
    cs3, _, _ = call(PN, "/api/meeting/99999/extract-status", inn["me"])
    chk("없는 회의 상태는 404", cs3 == 404, cs3)

    # ── ⑧ 500 없음 ─────────────────────────────────────────────
    print("\n── ⑧ 500 없음 ──")
    for port, lab in ((PB, "운영그대로"), (PN, "내변경")):
        s = io.open(os.path.join(APPDIR, "srv_%d.log" % port), encoding="utf-8").read()
        chk("%s · Traceback 없음" % lab, "Traceback" not in s, s[-300:] if "Traceback" in s else "")
        chk("%s · 500 없음" % lab, " 500 " not in s)
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
