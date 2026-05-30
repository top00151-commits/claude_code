"""페이지별 미렌더 토큰 / dead link / 크기 실측."""
import sys, urllib.request, urllib.parse, http.cookiejar, re
sys.stdout.reconfigure(encoding="utf-8")


def session(login_id, pw="knk1234"):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = urllib.parse.urlencode({"login_id": login_id, "password": pw}).encode("utf-8")
    op.open(urllib.request.Request(
        "http://localhost:8081/login", data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "UA"}
    ))
    return op


def get(op, path):
    r = op.open(urllib.request.Request(
        "http://localhost:8081" + urllib.parse.quote(path, safe="/?=&"),
        headers={"User-Agent": "UA"}
    ))
    return r.read().decode("utf-8", "replace")


def scan(op, label, paths):
    print(f"\n=== {label} ===")
    for p in paths:
        try:
            h = get(op, p)
        except Exception as e:
            print(f"{p:28s} | ERROR: {e}")
            continue
        # 미렌더 JS 템플릿
        unrendered = re.findall(r'\$\{[a-zA-Z_][a-zA-Z0-9_.]*\}', h)
        # dead href="#"
        dead = len(re.findall(r'href="#"', h))
        # inline onclick
        onclicks = len(re.findall(r'\sonclick=', h))
        print(f"{p:28s} | len={len(h):6d} | jsTemplate={len(set(unrendered)):3d} | dead#={dead:3d} | onclick={onclicks:3d}")
        if unrendered:
            s = sorted(set(unrendered))[:5]
            print(f"   미렌더 예: {s}")


ceo = session("kjr")
scan(ceo, "CEO (kjr)", [
    "/home", "/cockpit", "/dashboard", "/bottlenecks", "/changes",
    "/admin/health", "/search?q=프로젝트", "/admin"
])

p3 = session("마준영")
scan(p3, "P3 제조 (마준영)", ["/home", "/daily", "/tickets", "/issues", "/progress", "/feed"])

p6 = session("윤경호")
scan(p6, "P6 설계팀장 (윤경호)", ["/team", "/changes", "/cockpit", "/rates", "/board/team"])

p10 = session("쑤아잉")
scan(p10, "P10 베트남 (쑤아잉)", ["/home", "/daily", "/board/company", "/profile"])
