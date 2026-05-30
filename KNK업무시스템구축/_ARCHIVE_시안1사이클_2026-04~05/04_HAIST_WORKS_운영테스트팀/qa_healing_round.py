"""05 디자인팀 힐링 테마 QA — S1 매출 권한 + 빅터 도크 + i18n 회귀.

대상 커밋: f61f06c · 72490a3 · 623ce02
응답 파일: 05_HAIST_WORKS_디자인팀/_FROM_04_힐링QA결과_01.md (별도 작성)
"""
import sys, re, time, json
import urllib.request, urllib.parse, urllib.error, http.cookiejar
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://localhost:8081"
OUT = Path(__file__).parent / "qa_healing_results.md"


def session(login_id, pw="knk1234"):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    body = urllib.parse.urlencode({"login_id": login_id, "password": pw}).encode("utf-8")
    op.open(urllib.request.Request(
        BASE + "/login", data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "QA"}
    ))
    return op


def get(op, path):
    url = BASE + urllib.parse.quote(path, safe="/?=&")
    req = urllib.request.Request(url, headers={"User-Agent": "QA"})
    try:
        r = op.open(req, timeout=15)
        return r.getcode(), r.read().decode("utf-8", "replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), url


def get_json(op, path):
    code, body, _ = get(op, path)
    try:
        return code, json.loads(body)
    except Exception:
        return code, body[:200]


def kw_count(body, *keywords):
    return {k: body.count(k) for k in keywords}


# ============= 페르소나 정의 (힐링 QA 사양) =============
# CEO: kjr (김정락, role=ceo)
# 팀장 leader: 정성진 (구매팀장 leader)  — 매출 미노출 기대
# 평직원 member: 마준영 (제조1팀 member) — 매출 완전 차단 기대

results = []

def section(title):
    results.append(f"\n## {title}\n")
    print(f"\n=== {title} ===")

def line(s):
    results.append(s)
    print(s)


# ===== S1-A 매출 KPI 권한 분기 =====
section("S1-A 매출 KPI 권한 분기")

REVENUE_KW = ["₩", "매출", "monthly_revenue", "yoy_delta", "이번 달 매출", "억", "🔒", "경영진"]

for label, login, role in [("CEO kjr", "kjr", "ceo"),
                            ("팀장 정성진", "정성진", "leader"),
                            ("평직원 마준영", "마준영", "member")]:
    op = session(login)
    code, body, url = get(op, "/home")
    found = kw_count(body, *REVENUE_KW)
    line(f"\n### {label} (`{login}` role={role})")
    line(f"- `/home` → {code} | final={url.replace(BASE,'')}")
    line(f"- 매출 키워드 노출: `{found}`")
    # 권한 핵심 검증
    has_revenue_amount = body.count("₩") > 0 or body.count("이번 달 매출") > 0
    has_executive_badge = body.count("🔒") > 0 or body.count("경영진") > 0
    if role == "ceo":
        verdict = "🟢 PASS" if (has_revenue_amount and has_executive_badge) else "🔴 FAIL"
        line(f"- 기대: ₩금액 노출 + 🔒뱃지. 결과: **{verdict}**")
    else:
        verdict = "🟢 PASS" if not has_revenue_amount else "🔴 FAIL (매출 누출!)"
        line(f"- 기대: 매출 금액 미노출. 결과: **{verdict}**")
    # /dashboard 직접 접근 시도
    code, body, url = get(op, "/dashboard")
    final = url.replace(BASE, "")
    line(f"- `/dashboard` 직접 접근 → {code} | final={final}")
    if role == "ceo":
        ok = "/dashboard" in final or final == "/dashboard"
        line(f"  CEO 정상 접근 기대 → {'🟢 PASS' if ok else '🔴 FAIL'}")
    else:
        ok = "/dashboard" not in final.split("?")[0] or final.startswith("/login")
        line(f"  비경영진 차단 기대 → {'🟢 PASS' if ok else '🔴 FAIL'}")


# ===== S1-B 빅터 도크 포지셔닝 =====
section("S1-B 빅터 도크 포지셔닝")

op = session("kjr")
code, body, _ = get(op, "/home")
# 빅터 도크 관련 마크업 검사
dock_classes = re.findall(r'class="[^"]*dock[^"]*"', body)
dock_tab_count = body.count(".dock-tab") + len(re.findall(r'class="[^"]*dock-tab[^"]*"', body))
position_fixed_dock = re.findall(r'\.dock\s*\{[^}]*position\s*:\s*fixed', body, re.S)
victor_button = body.count("🤖") + body.count("빅터") + body.count("victor") + body.count("Victor")
ctrl_k_present = "Ctrl+K" in body or "ctrl+k" in body or "ctrlKey" in body
header_chip = "user-chip" in body or "사용자" in body or "워크스페이스" in body or "logout" in body or "로그아웃" in body
line(f"\n홈 페이지 빅터 도크 마크업 검사 (CEO 시점):")
line(f"- `class=\"...dock...\"` 매치 수: {len(dock_classes)} 종")
if dock_classes:
    line(f"  예시: {dock_classes[:5]}")
line(f"- `.dock-tab` 발견: {dock_tab_count} (기대 0건 — 미수정 시 0보다 큼)")
line(f"- inline `.dock {{ position: fixed }}` 패턴: {len(position_fixed_dock)} 건 (기대 0)")
line(f"- 🤖/빅터/Victor 키워드: {victor_button}")
line(f"- Ctrl+K 단축키 안내: {ctrl_k_present}")
line(f"- 헤더 사용자칩·로그아웃: {header_chip}")


# ===== S2 / S3 i18n 회귀 =====
section("S3 i18n 회귀 (3종 언어 + 중국어 부재)")

op = session("쑤아잉")
# 언어 셀렉터 마크업: vi 옵션 존재 / zh 옵션 부재
code, body, _ = get(op, "/home")
opts = re.findall(r'<option[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', body)
lang_options = [(v, l) for v, l in opts if v in ("ko", "vi", "en", "zh", "zh-CN", "ja")]
line(f"\n홈 페이지 내 언어 옵션 마크업: {lang_options}")

# 셀렉터가 select 가 아니라 다른 위젯이면 i18n 키 직접 점검
for lang in ("ko", "vi", "en"):
    code, body, _ = get(op, f"/api/set-lang?lang={lang}")
    code, body, _ = get(op, "/home")
    probes = {
        "ko": ["업무현황", "내 계정", "로그아웃"],
        "vi": ["Công việc", "Tài khoản", "Đăng xuất"],
        "en": ["Overview", "My Account", "Logout"],
    }[lang]
    found = kw_count(body, *probes)
    line(f"- lang={lang} 적용 후 핵심 라벨: {found}")

# 중국어 옵션 무존재 확인
code, body, _ = get(op, "/home")
zh_present = any(("zh" in v or "中文" in l or "汉语" in l) for v, l in lang_options)
line(f"- 중국어 옵션 존재 여부: {'🔴 FAIL — 부적절 노출' if zh_present else '🟢 PASS — 미노출'}")


# ===== S2 사용성 — 힐링 톤 시간대 인사 =====
section("S2 힐링 톤 시간대 인사말·페르소나 인상")

op = session("kjr")
code, body, _ = get(op, "/home")
greetings = ["오늘도 평안", "안녕하세요", "좋은 아침", "Good", "Xin chào", "오늘 하루도"]
g = kw_count(body, *greetings)
line(f"홈 인사말 키워드: {g}")
# sage 관련 색상 토큰
sage_kw = kw_count(body, "sage", "Sage", "#7A9A7E", "healing", "힐링", "amber", "앰버")
line(f"힐링 토큰 키워드: {sage_kw}")


OUT.write_text("\n".join(results), encoding="utf-8")
print(f"\n저장: {OUT}")
