"""대표 지시 — 전 페이지 sweep × 5 페르소나, 100건 결함 발굴."""
import sys, urllib.request, urllib.parse, http.cookiejar, re, json, time
sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://localhost:8081"


def login(lid, pw="knk1234"):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = urllib.parse.urlencode({"login_id": lid, "password": pw}).encode("utf-8")
    try:
        op.open(urllib.request.Request(BASE+"/login", data=body, method="POST",
            headers={"Content-Type":"application/x-www-form-urlencoded","User-Agent":"Sweep"}), timeout=10)
        # confirm
        r = op.open(urllib.request.Request(BASE+"/home", headers={"User-Agent":"Sweep"}), timeout=10)
        return op if r.geturl().endswith("/home") else None
    except Exception:
        return None


def get(op, path):
    try:
        r = op.open(urllib.request.Request(BASE+urllib.parse.quote(path,safe="/?=&"),
            headers={"User-Agent":"Sweep"}), timeout=15)
        return r.getcode(), r.read().decode("utf-8","replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", BASE+path
    except Exception:
        return -1, "", BASE+path


# 페르소나
PERSONAS = [
    ("kjr","김정락","CEO 전권"),
    ("ajy","안지연","영업 USE+수출"),
    ("lh","이현","영업 USE"),
    ("jsj","정성진","자재 USE+매출 VIEW"),
    ("kks","김기선","무권한"),
]

# 점검 대상 페이지 (95개 — admin/permissions 일부 + dynamic 제외)
PAGES = """/home /daily /calendar /history /now /summary /me /profile /notifications /notifications/badge
/feed /search /team /team/permissions /board/company /board/team /board/new
/changes /changes/new /tickets /tickets/new /issues /issues/new
/progress /progress-dashboard /bottlenecks /cockpit /ceo /dashboard
/sales /sales/dashboard /sales/quotations /sales/orders /sales/production
/sales/shipments-receipts /sales/outstanding /sales/aging /sales/forecast
/projects /projects/new /customers
/export /export/fta /export/fta/new /export/orders/new /export/weekly
/logistics /parts /parts/new /suppliers /suppliers/new /po /po/new
/production/work-orders /production/work-orders/new
/stock/movements /stock/issue /stock/adjust /stock/balances /stock/audits
/stock/abc /stock/safety /stock/turnover /stock/receipts /stock/issues
/stock/adjustments /stock/reorder-recommendations
/rates /rates/alerts /rates/dashboard /fx/rates
/qc/inspection-reports /qc/inspection-reports/new
/qms /qms/capa /qms/pareto /qms/recurrence
/admin /admin/health /admin/company-info /admin/external-assets /admin/hiworks-settings
/admin/permissions /admin/permissions/matrix /admin/permissions/audit /admin/permissions/groups
/admin/settings /admin/reminders
/guide /hr/hiworks""".split()

print(f"점검 대상 페이지: {len(PAGES)}개 × 5 페르소나 = {len(PAGES)*5}건")
print()

# 페르소나 로그인
sessions = {}
for lid, name, role in PERSONAS:
    op = login(lid)
    sessions[lid] = op
    print(f"  {'✅' if op else '❌'} {lid} ({name}) login")
print()

findings = []   # 결함
positives = []  # 긍정


def add(severity, persona, page, kind, detail):
    findings.append({"sev":severity, "p":persona, "page":page, "kind":kind, "detail":detail})


# 페르소나별 sweep
print("="*70)
print("Sweep 시작")
print("="*70)
for lid, name, role in PERSONAS:
    op = sessions.get(lid)
    if not op:
        add("S1", lid, "/login", "auth_fail", f"{name} 로그인 실패")
        continue

    fallback_home = []
    fallback_login = []
    err_500 = []
    err_404 = []
    title_kr = 0
    title_haist = 0
    has_sb_active = []
    no_sb_active = []
    ws_active = {}
    sales_base_pages = []
    logi_base_pages = []
    keyword_hits = {}

    for p in PAGES:
        code, body, final = get(op, p)
        final_path = final.replace(BASE, "").split("?")[0]
        # error
        if code >= 500:
            err_500.append(p)
            add("S1", lid, p, "500_error", f"{code} 서버 오류")
            continue
        if code == 404:
            err_404.append(p)
            add("S2", lid, p, "404_error", "라우트 부재")
            continue
        if code != 200:
            add("S2", lid, p, f"http_{code}", f"비정상 응답")
            continue
        # silent fallback
        if final_path != p.split("?")[0] and final_path != p:
            if final_path == "/home":
                fallback_home.append(p)
            elif final_path == "/login":
                fallback_login.append(p)
            else:
                add("S3", lid, p, "redirect", f"→ {final_path}")
        # title 일관성
        m_title = re.search(r"<title>(.*?)</title>", body, re.S)
        if m_title:
            t = m_title.group(1).strip()
            if "KNK" in t and "HAIST WORKS" not in t: title_kr += 1
            if "HAIST WORKS" in t: title_haist += 1
        # sidebar active
        if re.search(r'class="[^"]*sb-active[^"]*"', body):
            has_sb_active.append(p)
        else:
            no_sb_active.append(p)
        # ws-tab active
        ws_match = re.search(r'class="ws-tab active[^"]*"[^>]*>.*?<span class="ws-name"[^>]*>([^<]+)', body, re.S)
        if ws_match:
            name_active = ws_match.group(1).strip()
            ws_active.setdefault(name_active, []).append(p)
        # base 추적
        if 'topbar-hub-sales' in body: sales_base_pages.append(p)
        if 'topbar-hub-logi' in body: logi_base_pages.append(p)
        # 내부 코드명 잔존 점검
        for kw in ['Top3','S1 매출','P11','QA-H','TODO','FIXME','XXX']:
            if kw in body:
                keyword_hits.setdefault(kw, []).append(p)

    # 페르소나별 요약
    print(f"\n[{lid} {name} ({role})]")
    print(f"  fallback→/home: {len(fallback_home)}건")
    print(f"  fallback→/login: {len(fallback_login)}건")
    print(f"  500 에러: {len(err_500)}건")
    print(f"  404 에러: {len(err_404)}건")
    print(f"  title 'KNK' 형식: {title_kr} / 'HAIST WORKS': {title_haist}")
    print(f"  sb-active 적용 페이지: {len(has_sb_active)}/{len(PAGES)}")
    print(f"  ws-active: {dict((k,len(v)) for k,v in ws_active.items())}")
    print(f"  sales-base: {len(sales_base_pages)}, logi-base: {len(logi_base_pages)}")
    print(f"  코드명 잔존: {dict((k,len(v)) for k,v in keyword_hits.items()) if keyword_hits else '0'}")

    # 결함 누적
    for p in fallback_home:
        # CEO와 무권한자 분리
        if lid == "kks":
            pass  # 무권한은 fallback이 정상
        elif lid == "kjr":
            add("S1", lid, p, "ceo_fallback", "CEO 인데 /home 폴백 — 권한 미정합")
        else:
            add("S2", lid, p, "fallback_home", f"{name} → /home 폴백 (silent)")
    for p in fallback_login:
        add("S1", lid, p, "fallback_login", f"{name} → /login (세션 단절)")

# 추가 검증: 페이지 존재 vs 메뉴 노출 일관성
print()
print("="*70)
print("교차 검증: 메뉴 vs 라우트")
print("="*70)
# 이건 sweep 내에서 검출됨

# 결과 저장
with open("sweep_results.json", "w", encoding="utf-8") as f:
    json.dump({"findings": findings, "personas": [p[0] for p in PERSONAS]}, f, ensure_ascii=False, indent=2)

# 분류
sev_count = {"S1":0,"S2":0,"S3":0}
for fd in findings:
    sev_count[fd["sev"]] += 1

print()
print("="*70)
print(f"발견 결함 총 {len(findings)}건 — S1:{sev_count['S1']} / S2:{sev_count['S2']} / S3:{sev_count['S3']}")
print("="*70)

# 페이지별 통합 (중복 제거)
by_page_kind = {}
for fd in findings:
    key = (fd["page"], fd["kind"])
    by_page_kind.setdefault(key, []).append(fd["p"])

print(f"\n결함 종류 (중복 페르소나 그룹화): {len(by_page_kind)}건")
for (page, kind), personas in sorted(by_page_kind.items()):
    print(f"  [{kind}] {page} | 영향: {personas}")
