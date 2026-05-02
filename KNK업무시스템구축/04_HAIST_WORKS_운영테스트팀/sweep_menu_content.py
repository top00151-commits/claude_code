"""2차 검증 — 메뉴 적합성·항목 위치·업무 적합·필드 라벨."""
import sys, urllib.request, urllib.parse, http.cookiejar, re, json
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
BASE = "http://localhost:8081"


def login(lid, pw="knk1234"):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = urllib.parse.urlencode({"login_id": lid, "password": pw}).encode("utf-8")
    op.open(urllib.request.Request(BASE+"/login", data=body, method="POST",
        headers={"Content-Type":"application/x-www-form-urlencoded","User-Agent":"S2"}))
    return op


def get(op, path):
    try:
        r = op.open(urllib.request.Request(BASE+urllib.parse.quote(path,safe="/?=&"),
            headers={"User-Agent":"S2"}), timeout=15)
        return r.getcode(), r.read().decode("utf-8","replace"), r.geturl()
    except Exception:
        return -1, "", BASE+path


findings = []
def add(sev, page, kind, detail):
    findings.append((sev, page, kind, detail))
    print(f"[{sev}] {page} | {kind} | {detail}")


# CEO 로그인 (전권 사용)
op = login("kjr")

print("===== 메뉴 항목 위치 적합성 =====")
# 사이드바 메뉴 일관성 (홈 vs 매출 vs 자재 base)
for path, expect_hub in [("/home","main"),("/sales","sales"),("/logistics","logi"),("/admin","main")]:
    code, body, _ = get(op, path)
    if code != 200: continue
    sidebar = re.search(r'<aside[^>]*class="[^"]*(?:sidebar|sb)[^"]*"[^>]*>(.*?)</aside>', body, re.S)
    if sidebar:
        items = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', sidebar.group(1))
        labels = [(href, re.sub(r'\s+',' ', txt).strip()) for href,txt in items if txt.strip() and href != '#']
        print(f"\n  {path} 사이드바 항목 ({len(labels)}개):")
        for h, l in labels[:20]:
            print(f"    {h:35s} | {l[:30]}")

print()
print("===== 페이지 제목 일관성 (HAIST WORKS vs KNK 혼재) =====")
PAGES_T = ["/home","/sales","/logistics","/changes","/tickets","/issues","/progress","/dashboard","/cockpit","/admin","/profile","/calendar","/feed","/parts","/po","/customers","/projects","/export","/sales/dashboard","/sales/quotations","/admin/health","/admin/permissions","/board/company"]
brand_kr = []
brand_haist = []
brand_mixed = []
for p in PAGES_T:
    code, body, _ = get(op, p)
    if code != 200: continue
    m = re.search(r"<title>(.*?)</title>", body, re.S)
    if not m: continue
    t = m.group(1).strip()
    has_knk = "KNK" in t
    has_haist = "HAIST WORKS" in t
    if has_knk and has_haist:
        brand_mixed.append((p, t))
    elif has_knk:
        brand_kr.append((p, t))
    elif has_haist:
        brand_haist.append((p, t))
print(f"\n  · KNK only: {len(brand_kr)}건")
for p,t in brand_kr[:5]: print(f"    {p}: {t[:50]}")
print(f"  · HAIST only: {len(brand_haist)}건")
for p,t in brand_haist[:5]: print(f"    {p}: {t[:50]}")
print(f"  · 혼재 mixed: {len(brand_mixed)}건")
if len(brand_kr) > 0 and len(brand_haist) > 0:
    add("S3", "전체", "title_brand_inconsistent", f"제목 'KNK' {len(brand_kr)}건 vs 'HAIST WORKS' {len(brand_haist)}건 — 브랜드 일관성 결함")

print()
print("===== 입력 폼 필드 검증 (등록 폼 5종) =====")
FORMS = ["/changes/new","/tickets/new","/issues/new","/projects/new","/parts/new","/suppliers/new","/po/new","/sales/quotations","/sales/orders"]
for p in FORMS:
    code, body, _ = get(op, p)
    if code != 200:
        add("S2", p, "form_unreachable", f"등록 폼 접근 불가 ({code})")
        continue
    inputs = re.findall(r'<input[^>]*name="([^"]+)"[^>]*>', body)
    selects = re.findall(r'<select[^>]*name="([^"]+)"[^>]*>', body)
    textareas = re.findall(r'<textarea[^>]*name="([^"]+)"', body)
    required = re.findall(r'<(?:input|select|textarea)[^>]*required[^>]*name="([^"]+)"', body) + \
               re.findall(r'name="([^"]+)"[^>]*required', body)
    placeholders = re.findall(r'placeholder="([^"]+)"', body)
    print(f"\n  {p}: input {len(inputs)} / select {len(selects)} / textarea {len(textareas)} / required {len(set(required))}")
    print(f"    placeholder 예시: {placeholders[:3]}")
    # placeholder 길이 7자 초과 check (디자인 원칙 위반)
    long_ph = [ph for ph in placeholders if len(ph) > 25]
    if long_ph:
        add("S3", p, "placeholder_too_long", f"placeholder ≥25자 {len(long_ph)}건 (디자인 원칙 §1-7 위반)")

print()
print("===== 사용 가이드 페이지 깨짐 =====")
code, body, _ = get(op, "/guide")
if code == 200:
    has_sidebar = '<aside' in body
    has_dock = 'class="dock"' in body or 'victorDock' in body
    has_topbar = 'class="topbar"' in body
    sections = re.findall(r'<h[12][^>]*>(.*?)</h[12]>', body)
    print(f"  /guide: sidebar={has_sidebar}, dock={has_dock}, topbar={has_topbar}, sections={len(sections)}")
    if has_sidebar or has_dock or has_topbar:
        add("S2", "/guide", "guide_not_standalone", f"가이드가 standalone 아님 (sidebar={has_sidebar}, dock={has_dock}, topbar={has_topbar})")

print()
print("===== /dashboard 안내 배너 (OPS-012 회귀) =====")
op_leader = login("lhr")  # 이해림 leader
code, body, final = get(op_leader, "/dashboard")
final_path = final.replace(BASE, "")
banner = "flash" in body.lower() or "전사 대시보드" in body and "경영진" in body
print(f"  leader /dashboard → final={final_path} | 안내 배너={banner}")
if final_path != "/dashboard" and not banner:
    add("S2", "/dashboard", "no_flash_banner_for_leader", "leader 가 /dashboard 차단 시 안내 배너 부재 (OPS-012 5차 누적)")

print()
print("===== 메뉴 죽은 링크 (href='#') =====")
op = login("kjr")
code, body, _ = get(op, "/home")
dead = re.findall(r'href="#"[^>]*>([^<]{1,30})</a>', body)
dead_clean = [re.sub(r'\s+', ' ', d).strip() for d in dead if d.strip() and d.strip() not in ('×','▾','▼','▲','◀','▶','⌄')]
print(f"  /home dead links: {len(dead_clean)}건")
for d in dead_clean[:10]:
    print(f"    href=# | text=「{d[:30]}」")
if dead_clean:
    add("S3", "/home", "dead_links", f"/home 에 dead link {len(dead_clean)}건 — 클릭해도 동작 안 함")

print()
print("===== /api/task 입력 검증 (OPS-002 회귀) =====")
op = login("ajy")
test_cases = [
    ({"title":"","category":"기타","hours":1}, "빈 제목"),
    ({"title":"음수","category":"기타","hours":-5}, "음수 시간"),
    ({"title":"40h","category":"기타","hours":40}, "40시간/일"),
    ({"title":"잘못카테","category":"존재하지않는카테고리","hours":1}, "잘못된 카테고리"),
]
for payload, desc in test_cases:
    body = json.dumps(payload).encode()
    try:
        r = op.open(urllib.request.Request(BASE+"/api/task", data=body, method="POST",
            headers={"Content-Type":"application/json","User-Agent":"S2"}))
        code = r.getcode()
        resp = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        code = e.code
        resp = e.read().decode("utf-8")
    print(f"  {desc}: {code} | {resp[:80]}")
    if code == 200 and '"ok":true' in resp:
        add("S2", "/api/task", f"input_validation_{desc}", f"{desc} 입력이 200 저장됨 (서버 검증 부재 — OPS-002 회귀)")

print()
print(f"===== 2차 검증 결함 총 {len(findings)}건 =====")
with open("sweep2_results.json","w",encoding="utf-8") as f:
    json.dump(findings, f, ensure_ascii=False, indent=2)
