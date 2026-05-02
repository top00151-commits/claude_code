"""01 발주서 27건 회귀 — S1·S3·S5·S6·S8·S12 HTTP 자동화."""
import sys, urllib.request, urllib.parse, http.cookiejar, re, json
sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://localhost:8081"


def session(login_id, pw="knk1234"):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = urllib.parse.urlencode({"login_id": login_id, "password": pw}).encode("utf-8")
    try:
        op.open(urllib.request.Request(BASE + "/login", data=body, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Reg27"}))
        # Try a protected page to confirm login (login page has no /home access)
        r = op.open(urllib.request.Request(BASE + "/home", headers={"User-Agent": "Reg27"}))
        return op, r.geturl()
    except Exception as e:
        return None, str(e)


def get(op, path):
    try:
        r = op.open(urllib.request.Request(BASE + urllib.parse.quote(path, safe="/?=&"),
            headers={"User-Agent": "Reg27"}), timeout=15)
        return r.getcode(), r.read().decode("utf-8", "replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace") if e.fp else "", BASE + path


PERSONAS = [
    ("kjr", "김정락 CEO", "전권"),
    ("ajy", "안지연", "영업 USE+수출"),  # 발주서 'ahj' 오타 — 실제 DB 'ajy'
    ("lh",  "이현", "영업 USE"),         # 발주서 'lhh' 오타 — 실제 'lh'
    ("jsj", "정성진", "자재 USE+매출 VIEW"),  # 발주서 'jss' 오타 — 실제 'jsj'
    ("kks", "김기선", "무권한"),          # 발주서 'kgs' 오타 — 실제 'kks'
]

print("="*80)
print("[S1] 인증 — 5명 로그인")
print("="*80)
sessions = {}
for lid, name, role in PERSONAS:
    op, final = session(lid)
    if op:
        sessions[lid] = op
        print(f"  ✅ {lid:5s} | {name:10s} | {role:15s} | final={final.replace(BASE,'')}")
    else:
        print(f"  ❌ {lid:5s} | {name:10s} | login FAIL: {final}")

print()
print("="*80)
print("[S3-A] 매출 사이드바 active — 안지연 (ahj) 11개 라우트")
print("="*80)
SALES_ROUTES = [
    ("/sales", "sales_home"),
    ("/projects", "sales_projects"),
    ("/sales/quotations", "sales_quotations"),
    ("/sales/orders", "sales_orders"),
    ("/customers", "customers"),
    ("/sales/production", "sales_production"),
    ("/export", "export"),
    ("/export/fta", "export_fta"),
    ("/sales/shipments-receipts", "sales_shipments"),
    ("/sales/outstanding", "sales_outstanding"),
    ("/sales/dashboard", "sales_dashboard"),
]
op = sessions.get("ajy")
if op:
    for url, expected_active in SALES_ROUTES:
        code, body, final = get(op, url)
        # active 클래스 검증
        active_match = re.search(r'class="[^"]*sb-active[^"]*"[^>]*>([^<]*)', body)
        active_text = re.sub(r'\s+', ' ', active_match.group(1) if active_match else "(없음)").strip()[:40]
        is_sales_base = '<header class="topbar topbar-hub-sales">' in body or 'topbar-hub-sales' in body
        flag = "✅" if code == 200 and (active_match or is_sales_base) else "⚠️"
        print(f"  {flag} {url:35s} → {code} | active=「{active_text}」 | sales-base={is_sales_base}")
else:
    print("  안지연 로그인 실패로 건너뜀")

print()
print("="*80)
print("[S3-B] 자재 사이드바 active — 정성진 (jss) 10개 라우트")
print("="*80)
LOGI_ROUTES = [
    "/logistics", "/parts", "/suppliers", "/po",
    "/production/work-orders", "/stock/movements",
    "/stock/issue", "/stock/adjust", "/rates", "/fx/rates",
]
op = sessions.get("jsj")
if op:
    for url in LOGI_ROUTES:
        code, body, final = get(op, url)
        active_match = re.search(r'class="[^"]*sb-active[^"]*"[^>]*>([^<]*)', body)
        active_text = re.sub(r'\s+', ' ', active_match.group(1) if active_match else "(없음)").strip()[:40]
        is_logi_base = 'topbar-hub-logi' in body
        is_polled = final.replace(BASE, "").split("?")[0] != url.split("?")[0]
        flag = "✅" if code == 200 and (active_match or is_logi_base) and not is_polled else ("⚠️폴백" if is_polled else "⚠️")
        print(f"  {flag} {url:30s} → {code} | active=「{active_text}」 | logi-base={is_logi_base} | final={final.replace(BASE,'')}")
else:
    print("  정성진 로그인 실패")

print()
print("="*80)
print("[S5] 권한 R/W 분리 — 정성진 (매출 VIEW)")
print("="*80)
op = sessions.get("jsj")
if op:
    code, body, final = get(op, "/sales")
    print(f"  /sales 조회 → {code} (기대: 200, VIEW 가능)")
    # /projects/new POST 시도 (등록 시도)
    try:
        body_data = urllib.parse.urlencode({"name": "테스트", "biz_div": "공통"}).encode()
        r = op.open(urllib.request.Request(BASE + "/projects/new", data=body_data, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Reg27"}), timeout=10)
        c = r.getcode()
    except urllib.error.HTTPError as e:
        c = e.code
    except Exception as e:
        c = -1
    print(f"  POST /projects/new (등록 시도) → {c} (기대: 403/302 차단)")

print()
print("="*80)
print("[S6] 무권한 — 김기선 (kgs)")
print("="*80)
op = sessions.get("kks")
if op:
    code, body, _ = get(op, "/home")
    has_sales_tab = "/sales" in body and "워크스페이스" in body
    has_logi_tab = "/logistics" in body and "워크스페이스" in body
    print(f"  /home 워크스페이스 탭에 매출 노출: {has_sales_tab}")
    print(f"  /home 워크스페이스 탭에 자재 노출: {has_logi_tab}")
    code, body, final = get(op, "/projects")
    print(f"  /projects 직접 → {code} | final={final.replace(BASE,'')}")
    code, body, final = get(op, "/sales")
    print(f"  /sales 직접 → {code} | final={final.replace(BASE,'')}")

print()
print("="*80)
print("[S8] 변경 공지 명칭 (변경 알림 → 변경 공지)")
print("="*80)
op = sessions.get("kjr")
if op:
    for path in ["/changes", "/home"]:
        code, body, _ = get(op, path)
        n_alarm = body.count("변경 알림")
        n_notice = body.count("변경 공지")
        print(f"  {path}: '변경 알림'×{n_alarm} / '변경 공지'×{n_notice}")

print()
print("="*80)
print("[S12] 내부 코드명 노출 0 — 사용자 화면")
print("="*80)
op = sessions.get("kjr")
if op:
    KEYWORDS = ["S1 매출", "S2 ", "S3 ", "Top3", "P11", "QA-H"]
    PAGES = ["/home", "/sales", "/sales/dashboard", "/sales/production", "/export", "/guide"]
    for path in PAGES:
        code, body, _ = get(op, path)
        if code != 200:
            print(f"  {path}: code={code} 스킵")
            continue
        hits = {k: body.count(k) for k in KEYWORDS}
        any_hit = sum(hits.values())
        flag = "✅" if any_hit == 0 else "❌"
        print(f"  {flag} {path}: {hits}")
