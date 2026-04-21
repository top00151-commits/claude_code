"""D04-03: 2라운드 페르소나 6종 시뮬레이션.

P2 1년차 설계(김범수) · P4 5년차 구매(허동준) · P5 품질팀장(김정록)
P7 타부서 영업(이현) · P8 모바일 출장 · P9 폴란드 셋업(en)
+ P10 쑤아잉 부분 번역 커버리지 재점검

관찰 포인트:
 - "일이 늘어나는가" 판정 (D04-04)
 - 입력 반복 부담
 - 권한 리다이렉트 silent-fail 여전 여부
 - 모바일/해외 UA·언어 전환시 번역 커버리지
"""
import sys
import re
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://localhost:8081"
OUT = Path(__file__).parent / "02_테스트실행로그_round2_2026-04-21.md"


class Persona:
    def __init__(self, code, name, login, role_desc,
                 user_agent="PersonaTest/2.0", lang_pref=None):
        self.code = code
        self.name = name
        self.login = login
        self.role_desc = role_desc
        self.ua = user_agent
        self.lang_pref = lang_pref
        self.log = []
        self.findings = []
        cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def _h(self):
        return {"User-Agent": self.ua}

    def _req(self, method, path, form=None, jsonb=None):
        url = BASE + urllib.parse.quote(path, safe="/?=&")
        headers = self._h()
        data = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif jsonb is not None:
            data = json.dumps(jsonb).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        t0 = time.time()
        try:
            r = self.opener.open(req, timeout=15)
            elapsed = int((time.time() - t0) * 1000)
            body = r.read().decode("utf-8", "replace")
            return r.getcode(), body, r.geturl(), elapsed
        except urllib.error.HTTPError as e:
            elapsed = int((time.time() - t0) * 1000)
            return e.code, e.read().decode("utf-8", "replace"), url, elapsed
        except Exception as e:
            return -1, f"ERROR: {type(e).__name__}: {e}", url, 0

    def login_now(self):
        code, body, url, ms = self._req("POST", "/login",
                                          form={"login_id": self.login, "password": "knk1234"})
        self.log.append(f"로그인 → {code} | {url.replace(BASE, '')} | {ms}ms")
        if self.lang_pref:
            c, b, u, m = self._req("GET", f"/api/set-lang?lang={self.lang_pref}")
            self.log.append(f"lang={self.lang_pref} → {c} ({m}ms)")
        return code

    def visit(self, path, expect_page=None):
        code, body, url, ms = self._req("GET", path)
        m = re.search(r"<title>(.*?)</title>", body, re.S)
        title = m.group(1).strip() if m else "(no title)"
        final = url.replace(BASE, "")
        flag = "✅"
        if path != final.split("?")[0]:
            # 폴백 감지
            flag = "⚠️ 폴백"
            self.findings.append(f"폴백: `GET {path}` → final=`{final}` (title:「{title}」)")
        if code >= 400:
            flag = "❌"
            self.findings.append(f"{code}: `GET {path}`")
        self.log.append(f"  {flag} `GET {path}` → {code} | 「{title[:30]}」 | {ms}ms | final={final}")
        return code, body

    def post_json(self, path, obj, expect_code=200, label=""):
        code, body, url, ms = self._req("POST", path, jsonb=obj)
        flag = "✅" if code == expect_code else "❌"
        self.log.append(f"  {flag} `POST {path}` {label} → {code} | {ms}ms | {body[:80]}")
        if code != expect_code:
            self.findings.append(f"POST {path} ({label}) 예상 {expect_code} != 실제 {code}")
        return code, body


def body_has(body, *texts):
    return {t: body.count(t) for t in texts}


def run():
    out = ["# 02 테스트 실행 로그 — 2라운드 2026-04-21",
           "",
           "> D04-03 이행. 6종 페르소나 + P10 커버리지 재점검.",
           ""]

    personas = [
        Persona("P2", "1년차 설계팀원", "김범수", "team=4 설계팀 member"),
        Persona("P4", "5년차 구매팀 주임", "허동준", "team=10 구매팀 member"),
        Persona("P5", "경력직 품질팀장", "김정록", "team=3 품질팀 leader"),
        Persona("P7", "타부서(기술영업팀)", "이현", "team=1 기술영업팀 member"),
        Persona("P8", "출장 중 모바일", "마준영", "team=7 제조1 member (모바일 UA)",
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"),
        Persona("P9", "폴란드 해외 셋업", "이치권", "team=2 검사기 member (en 언어 설정)",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Poland-Setup",
                lang_pref="en"),
        Persona("P10r", "베트남 법인 재검증", "쑤아잉", "team=12 베트남법인 (vi 언어)",
                lang_pref="vi"),
    ]

    for p in personas:
        out.append(f"\n## {p.code} — {p.name} '{p.login}' ({p.role_desc})\n")
        p.login_now()

    # === P2 1년차 설계팀 김범수: 설계변경 등록 + 진행률 + 티켓 ===
    p = personas[0]
    p.visit("/home")
    p.visit("/changes")  # 설계변경 리스트 — 설계팀원이 자기 일
    p.visit("/changes/new")  # 설계변경 등록 폼
    p.visit("/progress")
    p.visit("/tickets")
    # 일일 Task Card 생성 (JSON)
    p.post_json("/api/task", {
        "title": "도면 #A-202 업데이트", "category": "설계",
        "status": "진행중", "hours": 4, "notes": "고객 승인 대기"
    }, label="정상 업무 등록")
    # 같은 카드 10번 반복 등록 (반복 입력 부담 측정)
    t0 = time.time()
    for i in range(10):
        p.post_json("/api/task", {
            "title": f"반복 {i+1}", "category": "설계", "hours": 0.5
        }, label=f"rep#{i+1}")
    total = int((time.time()-t0)*1000)
    p.log.append(f"  >> 10건 연속 업로드 총 {total}ms (건당 {total//10}ms)")

    # === P4 허동준: PO 발행·단가 승인 ===
    p = personas[1]
    p.visit("/home")
    p.visit("/logistics")  # 구매 실무자는 자재 허브 써야
    p.visit("/parts")
    p.visit("/suppliers")
    p.visit("/po")
    p.visit("/po/new")
    p.visit("/rates")

    # === P5 김정록 품질팀장: 이슈·티켓·팀 뷰·경영진 보고 ===
    p = personas[2]
    p.visit("/team")
    p.visit("/issues")
    p.visit("/issues/new")
    p.visit("/tickets")
    p.visit("/dashboard")
    p.visit("/cockpit")
    p.visit("/bottlenecks")
    p.visit("/progress")

    # === P7 이현 기술영업팀: 타부서 → 고객·프로젝트 조회 ===
    p = personas[3]
    p.visit("/home")
    p.visit("/search?q=프로젝트")
    p.visit("/calendar")
    p.visit("/board/company")
    # 타부서 프로젝트 상세 접근 가능한지 (/project/1)
    p.visit("/project/1")
    # 자재 조회 시도 (영업이 고객에게 부품 현황 답해야 할 경우)
    p.visit("/parts")

    # === P8 마준영 출장 중 모바일: 승인·티켓 처리 ===
    p = personas[4]
    p.visit("/home")
    p.visit("/tickets")
    p.visit("/notifications")
    p.visit("/changes")

    # === P9 이치권 폴란드 셋업 (en): 부품 조회·티켓 ===
    p = personas[5]
    p.visit("/home")
    p.visit("/tickets")
    p.visit("/parts")
    p.visit("/progress")
    # en 번역 커버리지 점검
    code, body, _, _ = p._req("GET", "/home")
    tr = body_has(body, "Overview", "My Account", "Logout", "Daily Work",
                  "Task", "업무현황", "내 계정")
    p.log.append(f"  >> en 번역 커버리지 (홈): {tr}")
    code, body, _, _ = p._req("GET", "/cockpit")
    tr = body_has(body, "Overview", "Dashboard", "코크핏", "전사")
    p.log.append(f"  >> en 번역 커버리지 (cockpit): {tr}")

    # === P10 쑤아잉 베트남 재검증 (vi) ===
    p = personas[6]
    p.visit("/home")
    p.visit("/daily")
    p.visit("/board/company")
    p.visit("/notifications")
    p.visit("/profile")
    # vi 번역 커버리지
    code, body, _, _ = p._req("GET", "/home")
    tr = body_has(body, "Công việc", "Tài khoản", "Đăng xuất", "Hôm nay",
                  "업무현황", "진행중", "내 업무")
    p.log.append(f"  >> vi 번역 커버리지 (홈): {tr}")
    code, body, _, _ = p._req("GET", "/board/company")
    # 게시판 본문도 번역되는지 (게시물 본문은 원문 보존이 맞긴 함)
    tr = body_has(body, "Bảng thông báo", "공지", "Thông báo", "전사")
    p.log.append(f"  >> vi 번역 커버리지 (게시판): {tr}")

    # 최종 로그 출력
    for p in personas:
        out.append(f"\n### {p.code} {p.name} — `{p.login}`")
        out.append(f"\n_{p.role_desc}_\n")
        out.extend(p.log)
        if p.findings:
            out.append(f"\n**발견**: {len(p.findings)}건")
            for f in p.findings:
                out.append(f"- {f}")

    OUT.write_text("\n".join(out), encoding="utf-8")
    total_findings = sum(len(p.findings) for p in personas)
    print(f"저장: {OUT}")
    print(f"총 발견: {total_findings}건")
    print()
    for p in personas:
        if p.findings:
            print(f"[{p.code} {p.login}] {len(p.findings)}건")
            for f in p.findings[:3]:
                print(f"  - {f}")


if __name__ == "__main__":
    run()
