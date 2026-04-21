"""D04-재시뮬: set-lang GET 지원 수정 후 베트남·영문 직원 언어 전환 검증."""
import sys, urllib.request, urllib.parse, http.cookiejar, json
sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8081"


def session(login_id, pw="knk1234"):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = urllib.parse.urlencode({"login_id": login_id, "password": pw}).encode("utf-8")
    op.open(urllib.request.Request(
        BASE + "/login", data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "UA"}
    ))
    return op


def call(op, method, path, json_body=None):
    url = BASE + urllib.parse.quote(path, safe="/?=&")
    headers = {"User-Agent": "UA"}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        r = op.open(req)
        return r.getcode(), r.read().decode("utf-8", "replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), url


def check_translations(html, lang):
    probes = {
        "ko": ["업무현황", "내 계정", "로그아웃"],
        "vi": ["Công việc", "Tài khoản", "Đăng xuất"],
        "en": ["Overview", "My Account", "Logout"],
    }
    return {p: html.count(p) for p in probes.get(lang, [])}


print("=" * 70)
print("D04-재시뮬 결과: /api/set-lang GET/POST 지원 검증")
print("=" * 70)

for persona in ["쑤아잉", "땀", "탕", "박지만", "이용식"]:
    print(f"\n▶ {persona} (베트남 법인)")
    op = session(persona)
    # 1) GET 쿼리스트링
    code, body, url = call(op, "GET", "/api/set-lang?lang=vi")
    print(f"  GET ?lang=vi       → {code} | final={url.replace(BASE, '')}")
    code, h, _ = call(op, "GET", "/home")
    tr = check_translations(h, "vi")
    print(f"  홈 vi 번역 검출:   {tr}")

    # 2) en 으로 전환
    code, body, url = call(op, "GET", "/api/set-lang?lang=en")
    print(f"  GET ?lang=en       → {code}")
    code, h, _ = call(op, "GET", "/home")
    tr = check_translations(h, "en")
    print(f"  홈 en 번역 검출:   {tr}")

    # 3) POST JSON 호환성
    code, body, _ = call(op, "POST", "/api/set-lang", json_body={"lang": "ko"})
    print(f"  POST JSON ko       → {code} | {body[:80]}")

    break  # 대표 1명으로 먼저 결과 확인

print("\n=== 영어권 사용자: 폴란드/해외 셋업 예시 (admin/ceo 아닌 일반 member 로 확인) ===")
op = session("엄주영")  # 한국인이지만 en 설정을 걸어본다
code, body, url = call(op, "GET", "/api/set-lang?lang=en")
print(f"GET ?lang=en (엄주영)  → {code} | final={url.replace(BASE, '')}")
code, h, _ = call(op, "GET", "/home")
tr = check_translations(h, "en")
print(f"홈 en 번역 검출:      {tr}")
