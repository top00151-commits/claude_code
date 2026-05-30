"""04 운영테스트팀 — 페르소나별 실제 업무 시뮬레이션.

각 페르소나의 '오늘 해야 할 일'을 순차로 실행하고, 관찰 결과를 log 에 기록.
"""
import sys
import re
import time
import json
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8081"
OUT = Path(__file__).parent / "02_테스트실행로그_2026-04-21.md"


class PersonaSession:
    def __init__(self, name, login_id, password="knk1234"):
        self.name = name
        self.login_id = login_id
        self.password = password
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj),
            urllib.request.HTTPRedirectHandler(),
        )
        self.log_lines = []
        self.issues = []

    def _req(self, method, path, data=None):
        # 경로 내 한글을 퍼센트 인코딩
        if "?" in path:
            p, q = path.split("?", 1)
            path = urllib.parse.quote(p, safe="/") + "?" + urllib.parse.quote(q, safe="=&")
        else:
            path = urllib.parse.quote(path, safe="/")
        url = BASE + path
        body = None
        headers = {"User-Agent": "Persona-Test/1.0"}
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = self.opener.open(req, timeout=15)
            return resp.getcode(), resp.read().decode("utf-8", errors="replace"), resp.geturl()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace"), url
        except Exception as e:
            return -1, f"ERROR: {type(e).__name__}: {e}", url

    def visit(self, label, path, method="GET", data=None, expect=None, check_text=None):
        code, body, final_url = self._req(method, path, data)
        snippet = ""
        notes = []
        if expect is not None and code != expect:
            notes.append(f"expected {expect} got {code}")
            self.issues.append(f"[{path}] 예상 {expect} ≠ 실제 {code}")
        if check_text:
            for t in check_text:
                if t not in body:
                    notes.append(f"missing text '{t}'")
                    self.issues.append(f"[{path}] 기대 텍스트 '{t}' 누락")
        # 제목 추출
        m = re.search(r"<title>(.*?)</title>", body, re.S)
        title = m.group(1).strip() if m else "(no title)"
        self.log_lines.append(
            f"- `{method} {path}` → **{code}** | title=「{title}」 final=`{final_url.replace(BASE, '')}` {('⚠️ ' + '; '.join(notes)) if notes else '✅'}"
        )
        return code, body

    def login(self):
        self.log_lines.append(f"\n### 로그인: {self.name} ({self.login_id})\n")
        code, body = self.visit("login page", "/login", expect=200)
        code, body = self.visit(
            "submit login",
            "/login",
            method="POST",
            data={"login_id": self.login_id, "password": self.password},
        )
        # 로그인 성공 시 보통 302/303 후 /home 리다이렉트. opener가 따라감.
        return code


def persona_P1_newbie():
    """신입 관리팀원 엄주영 - 1개월차"""
    s = PersonaSession("P1_신입_엄주영", "엄주영")
    s.log_lines.append("## P1 — 신입 관리팀원 '엄주영' (team=11, member, 1개월)")
    s.login()
    s.visit("홈", "/home", expect=200, check_text=["Task"])
    s.visit("일일업무", "/daily", expect=200)
    s.visit("전사게시판", "/board/company", expect=200)
    s.visit("설계변경", "/changes", expect=200)
    s.visit("프로필", "/profile", expect=200)
    s.visit("검색", "/search?q=회의", expect=200)
    s.visit("알림", "/notifications", expect=200)
    return s


def persona_P3_mfg():
    """3년차 제조팀원 마준영"""
    s = PersonaSession("P3_제조_마준영", "마준영")
    s.log_lines.append("\n## P3 — 3년차 제조팀원 '마준영' (team=7)")
    s.login()
    s.visit("홈", "/home", expect=200)
    s.visit("자재 허브", "/logistics", expect=200)
    s.visit("자재(파트) 리스트", "/parts", expect=200)
    s.visit("출고 페이지", "/stock/issue", expect=200)
    s.visit("이슈 생성 폼", "/issues/new", expect=200)
    s.visit("진행률", "/progress", expect=200)
    s.visit("피드", "/feed", expect=200)
    return s


def persona_P6_leader():
    """설계팀장 윤경호"""
    s = PersonaSession("P6_설계팀장_윤경호", "윤경호")
    s.log_lines.append("\n## P6 — 설계팀장 '윤경호' (team=4, executive)")
    s.login()
    s.visit("팀 대시", "/team", expect=200)
    s.visit("설계변경 리스트", "/changes", expect=200)
    s.visit("cockpit", "/cockpit", expect=200)
    s.visit("대시보드", "/dashboard", expect=200)
    s.visit("병목", "/bottlenecks", expect=200)
    s.visit("단가 승인", "/rates", expect=200)
    s.visit("팀 게시판", "/board/team", expect=200)
    return s


def persona_P10_vn():
    """베트남 법인 쑤아잉"""
    s = PersonaSession("P10_베트남_쑤아잉", "쑤아잉")
    s.log_lines.append("\n## P10 — 베트남 법인 '쑤아잉' (team=12, member)")
    s.login()
    s.visit("홈", "/home", expect=200)
    # 언어 변경 시도: vi (베트남어) / en (영어)
    s.visit("언어 vi 변경", "/api/set-lang?lang=vi", expect=200)
    s.visit("홈(vi 적용 후)", "/home", expect=200)
    s.visit("언어 en 변경", "/api/set-lang?lang=en", expect=200)
    s.visit("홈(en 적용 후)", "/home", expect=200)
    s.visit("전사게시판", "/board/company", expect=200)
    s.visit("부품 조회", "/parts", expect=200)
    s.visit("프로필", "/profile", expect=200)
    return s


def persona_CEO():
    """대표이사 김정락"""
    s = PersonaSession("CEO_김정락", "kjr")
    s.log_lines.append("\n## CEO — 대표이사 '김정락(kjr)'")
    s.login()
    s.visit("cockpit", "/cockpit", expect=200)
    s.visit("병목", "/bottlenecks", expect=200)
    s.visit("대시보드", "/dashboard", expect=200)
    s.visit("설계변경", "/changes", expect=200)
    s.visit("admin health", "/admin/health", expect=200)
    s.visit("검색", "/search?q=프로젝트", expect=200)
    s.visit("관리자", "/admin", expect=200)
    return s


def main():
    all_lines = [
        "# 02 테스트 실행 로그 — 2026-04-21 1라운드",
        "",
        "> 스크립트: `run_persona_test.py`. 서버: `http://localhost:8081`.",
        "> 각 페르소나는 로그인 후 '오늘 해야 할 일' 경로를 순차 방문. 응답 코드·제목 기록.",
        "",
    ]
    all_issues = []
    for fn in [persona_P1_newbie, persona_P3_mfg, persona_P6_leader, persona_P10_vn, persona_CEO]:
        try:
            s = fn()
            all_lines.extend(s.log_lines)
            if s.issues:
                all_issues.append(f"\n### {s.name} 발견 이슈")
                all_issues.extend(f"- {i}" for i in s.issues)
        except Exception as e:
            all_lines.append(f"\n❌ {fn.__name__} 실패: {e}")
        time.sleep(0.3)

    if all_issues:
        all_lines.append("\n---\n\n# 즉시 발견 이슈")
        all_lines.extend(all_issues)

    OUT.write_text("\n".join(all_lines), encoding="utf-8")
    print(f"로그 저장: {OUT}")
    print(f"총 이슈: {len(all_issues) - len([x for x in all_issues if x.startswith(chr(10))])}")


if __name__ == "__main__":
    main()
