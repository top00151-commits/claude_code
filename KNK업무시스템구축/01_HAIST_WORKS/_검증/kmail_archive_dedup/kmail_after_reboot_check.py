# -*- coding: utf-8 -*-
# kmail 재부팅 뒤 확인 — 읽기 전용(바깥에서 주소만 불러 본다 · 로그인 없음 · 서버 접속 없음).
import collections, json, sys, time, urllib.error, urllib.request
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
W = "https://works.knknara.co.kr"
K = "https://kmail.knknara.co.kr"


class NoRedir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


op = urllib.request.build_opener(NoRedir)


def get(url):
    try:
        r = op.open(url, timeout=8)
        return r.status, {k.title(): v for k, v in r.headers.items()}, r.read(400)
    except urllib.error.HTTPError as e:
        return e.code, {k.title(): v for k, v in e.headers.items()}, e.read(400)
    except Exception as e:
        return 0, {}, ("ERR " + type(e).__name__).encode()


def kind_health(s, b):
    if s == 200 and b"KNK Eum MAIL" in b:
        return "OLD"
    if s == 404:
        return "WORKS"
    return "DOWN(%s)" % s


def kind_ver(s, b):
    if s == 200 and b.strip().startswith(b'{"v":"'):
        return "WORKS"
    if b"knk-mail" in b:
        return "OLD"
    return "DOWN(%s)" % s


def sample(n=30):
    c = collections.Counter()
    for i in range(n):
        s, h, b = get(K + "/healthz?t=%f" % time.time())
        c["healthz:" + kind_health(s, b)] += 1
        s, h, b = get(K + "/api/version?t=%f" % time.time())
        c["version:" + kind_ver(s, b)] += 1
        time.sleep(0.2)
    return c


print("시각", time.strftime("%Y-%m-%d %H:%M:%S"))
ROUNDS = 5
for rnd in range(1, ROUNDS + 1):
    sw, hw, bw = get(W + "/api/version?t=%f" % time.time())
    c = sample()
    print("[%d회차 %s] works /api/version: %s %s" % (rnd, time.strftime("%H:%M:%S"), sw, bw[:40].decode("utf-8", "replace")))
    for k, v in sorted(c.items()):
        print("      kmail %-22s %d" % (k, v))
    if sum(v for k, v in c.items() if "DOWN" in k) == 0:
        break
    if rnd < ROUNDS:
        print("      (응답 없는 것이 있어 2분 뒤 다시 본다)")
        sys.stdout.flush()
        time.sleep(120)

old = sum(v for k, v in c.items() if k.endswith(":OLD"))
works = sum(v for k, v in c.items() if k.endswith(":WORKS"))
down = sum(v for k, v in c.items() if "DOWN" in k)
s, h, b = get(K + "/api/version")
vk = json.loads(b).get("v") if (s == 200 and b.strip().startswith(b'{"v"')) else None
vw = json.loads(bw).get("v") if (sw == 200 and bw.strip().startswith(b'{"v"')) else None
s1, h1, b1 = get(K + "/home")
s2, h2, b2 = get(K + "/mail/app")
s3, h3, b3 = get(K + "/")
extra = [
    ("kmail /home → works 로 넘김(307)", s1 == 307 and h1.get("Location") == W + "/home"),
    ("kmail /mail/app → 이음 로그인 · 돌아올 곳 kmail", s2 == 303 and "redirect_uri=https%3A%2F%2Fkmail.knknara.co.kr%2Fsso%2Fland" in h2.get("Location", "")),
    ("kmail / → 받은편지함", s3 == 303 and h3.get("Location") == "/mail/inbox?app=1"),
    ("kmail 과 works 가 같은 판", bool(vk) and vk == vw),
]
for name, ok in extra:
    print("   [%s] %s" % ("PASS" if ok else "FAIL", name))
if old == 0 and down == 0 and works > 0 and all(ok for _, ok in extra):
    verdict = "OK"
elif old > 0 and works == 0:
    verdict = "OLD_APP_BACK"
elif old > 0:
    verdict = "MIXED"
elif down > 0:
    verdict = "DOWN"
else:
    verdict = "CHECK"
print("VERDICT: %s | works판=%s kmail판=%s | WORKS %d · OLD %d · DOWN %d" % (verdict, vw, vk, works, old, down))
