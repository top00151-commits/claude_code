"""3라운드: 설문 기반 8종 실명 페르소나 — 신규 3종 시스템(변경/티켓/진행률) 검증.

비간섭 원칙 준수: 기동 전 git status 확인, 기동 후 10분 이내 종료 책임은 호출자.
"""
import sys
import re
import time
import json
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://localhost:8081"
OUT = Path(__file__).parent / "02_테스트실행로그_round3_2026-04-23.md"


class Persona:
    def __init__(self, code, label, login, team_desc):
        self.code = code
        self.label = label
        self.login = login
        self.team_desc = team_desc
        self.log = []
        self.findings = []
        cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def _req(self, method, path, form=None, jsonb=None):
        url = BASE + urllib.parse.quote(path, safe="/?=&")
        headers = {"User-Agent": "OpsTest/3.0"}
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
            return r.getcode(), r.read().decode("utf-8", "replace"), r.geturl(), int((time.time()-t0)*1000)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), url, int((time.time()-t0)*1000)
        except Exception as e:
            return -1, f"ERROR:{e}", url, 0

    def login_now(self):
        code, body, url, ms = self._req("POST", "/login",
                                         form={"login_id": self.login, "password": "knk1234"})
        self.log.append(f"로그인 → {code} | {url.replace(BASE,'')} | {ms}ms")
        return code

    def visit(self, path, label=""):
        code, body, url, ms = self._req("GET", path)
        m = re.search(r"<title>(.*?)</title>", body, re.S)
        title = (m.group(1).strip() if m else "")[:40]
        final = url.replace(BASE, "")
        flag = "✅"
        base = path.split("?")[0]
        if final.split("?")[0] != base and not final.startswith(base):
            flag = "⚠️폴백"
            self.findings.append(f"폴백: `{path}` → `{final}` (title:「{title}」) {label}")
        if code >= 400:
            flag = "❌"
            self.findings.append(f"{code}: `{path}` {label}")
        self.log.append(f"  {flag} `GET {path}` → {code} | 「{title}」 | {ms}ms {'| ' + label if label else ''}")
        return code, body

    def check_body(self, body, label, *probes):
        found = {p: body.count(p) for p in probes}
        self.log.append(f"  >> [{label}] {found}")
        missing = [p for p, c in found.items() if c == 0]
        if missing:
            self.findings.append(f"{label} 누락: {missing}")
        return found


def round3():
    out = ["# 02 테스트 실행 로그 — 3라운드 2026-04-23",
           "",
           "> 설문 기반 실명 페르소나 8종. 신규 3종 시스템(변경/티켓/진행률) 검증.",
           "> 원천: HAIST_WORKS_설문요약.md + 핸드오프_2026-04-23.md",
           ""]

    # ============ PS-01 정성진 구매팀 leader ============
    p = Persona("PS-01", "구매팀 매니저", "정성진", "team=10 구매팀 leader")
    p.login_now()
    out.append(f"\n## {p.code} — {p.label} `{p.login}` ({p.team_desc})\n")
    out.append("_설문 고통: 카톡 출고 요청 누락·ERP 이중 입력. 1순위 기능 티켓·홈KPI 검증_\n")

    code, home = p.visit("/home", "홈 KPI 통합 확인")
    # 홈에 변경/티켓/진행률 KPI 위젯이 있는지
    p.check_body(home, "홈 KPI 통합",
                 "변경", "티켓", "진행률", "미확인", "지연", "요청")
    p.visit("/tickets", "요청 티켓 리스트")
    p.visit("/tickets/new", "티켓 등록 폼")
    p.visit("/logistics", "자재 허브 — can_use_logistics 회귀")
    p.visit("/po", "PO 리스트")
    p.visit("/parts", "부품 마스터")

    out.extend(p.log)
    if p.findings:
        out.append(f"\n**발견 {len(p.findings)}건**: " + "; ".join(p.findings))

    # ============ PS-02 박지은 관리팀 leader ============
    p = Persona("PS-02", "관리팀 팀장", "박지은", "team=11 관리팀 leader")
    p.login_now()
    out.append(f"\n## {p.code} — {p.label} `{p.login}` ({p.team_desc})\n")
    p.visit("/home")
    p.visit("/dashboard", "OPS-012 회귀 체크 — leader 가 /dashboard 200 OK?")
    p.visit("/board/company")
    p.visit("/admin", "관리팀 leader 의 admin 권한")
    out.extend(p.log)
    if p.findings:
        out.append(f"\n**발견 {len(p.findings)}건**: " + "; ".join(p.findings))

    # ============ PS-03 이해림 영업 이사 ============
    p = Persona("PS-03", "영업 이사", "이해림", "team=1 기술영업팀 leader")
    p.login_now()
    out.append(f"\n## {p.code} — {p.label} `{p.login}` ({p.team_desc})\n")
    out.append("_설문 매일 원하는 정보 1위: 모델별 진척율. 진행률 대시보드 직격_\n")
    p.visit("/home")
    code, body = p.visit("/progress", "진행률 대시보드 메인")
    # 12공정 키워드 탐지
    p.check_body(body, "진행률 12공정 라벨",
                 "수주", "설계", "전장", "SW", "가공", "구매",
                 "조립", "검수", "출하", "Set-up", "KNKVN")
    code, proj = p.visit("/progress/1", "개별 프로젝트 공정 상세")
    p.check_body(proj, "개별 공정 UI",
                 "담당", "예정", "실제", "지연", "완료", "진행")
    # API 확인
    code, apibody, _, ms = p._req("GET", "/api/progress/summary")
    p.log.append(f"  >> /api/progress/summary → {code} ({ms}ms) | {apibody[:120]}")
    out.extend(p.log)
    if p.findings:
        out.append(f"\n**발견 {len(p.findings)}건**: " + "; ".join(p.findings))

    # ============ PS-04 김형렬 전장설계팀 leader ============
    p = Persona("PS-04", "전장설계팀장", "김형렬", "team=6 전장설계팀 leader")
    p.login_now()
    out.append(f"\n## {p.code} — {p.label} `{p.login}` ({p.team_desc})\n")
    out.append("_기구→전장 변경 1~3일 지연. 변경 Inform 시스템 이 업무 직격_\n")
    p.visit("/home")
    code, changes = p.visit("/changes", "변경 리스트")
    p.check_body(changes, "변경 리스트 표시",
                 "긴급", "일반", "영향", "전장", "기구")
    code, unread, _, _ = p._req("GET", "/api/changes/unread")
    p.log.append(f"  >> /api/changes/unread → {code} | {unread[:120]}")
    # 최근 변경 상세 1건 진입
    m = re.search(r'href="/changes/(\d+)"', changes)
    if m:
        cid = m.group(1)
        code, detail = p.visit(f"/changes/{cid}", "변경 상세 진입")
        p.check_body(detail, "변경 상세 필드",
                     "before", "after", "영향", "긴급", "ack", "확인")
    out.extend(p.log)
    if p.findings:
        out.append(f"\n**발견 {len(p.findings)}건**: " + "; ".join(p.findings))

    # ============ PS-05 임택훈 제조기술2팀 leader ============
    p = Persona("PS-05", "제조2팀장", "임택훈", "team=8 제조기술2팀 leader")
    p.login_now()
    out.append(f"\n## {p.code} — {p.label} `{p.login}` ({p.team_desc})\n")
    out.append("_설문 사고사례: 30일 link 만료·변경 통보 누락. 변경+게시판 검증_\n")
    p.visit("/home")
    p.visit("/changes")
    p.visit("/board/team", "팀 게시판 — 개인PC 파일 대체 가능?")
    p.visit("/board/new", "게시판 글 작성 폼")
    out.extend(p.log)
    if p.findings:
        out.append(f"\n**발견 {len(p.findings)}건**: " + "; ".join(p.findings))

    # ============ PS-06 윤영조 가공팀 leader ============
    p = Persona("PS-06", "가공팀장", "윤영조", "team=9 가공팀 leader")
    p.login_now()
    out.append(f"\n## {p.code} — {p.label} `{p.login}` ({p.team_desc})\n")
    out.append("_긴급 가공 우선순위 기준 없음. 티켓/변경 urgency 검증_\n")
    code, tickets = p.visit("/tickets")
    p.check_body(tickets, "티켓 리스트 긴급 구분",
                 "긴급", "urgency", "정상", "대기", "진행")
    code, ticket_new = p.visit("/tickets/new")
    p.check_body(ticket_new, "티켓 등록 폼 필드",
                 "urgency", "긴급", "제목", "내용", "대상")
    p.visit("/progress")
    out.extend(p.log)
    if p.findings:
        out.append(f"\n**발견 {len(p.findings)}건**: " + "; ".join(p.findings))

    # ============ PS-07 김정록 품질팀 leader ============
    p = Persona("PS-07", "품질팀장", "김정록", "team=3 품질팀 leader")
    p.login_now()
    out.append(f"\n## {p.code} — {p.label} `{p.login}` ({p.team_desc})\n")
    out.append("_이슈 종이 기록. issues DB 검증 + OPS-012 회귀_\n")
    code, dash = p.visit("/dashboard", "🔁 OPS-012 회귀: leader /dashboard 200?")
    p.visit("/issues")
    code, issue_new = p.visit("/issues/new")
    p.check_body(issue_new, "이슈 폼 필수 필드",
                 "고객", "customer", "프로젝트", "증상", "처리", "severity", "심각")
    out.extend(p.log)
    if p.findings:
        out.append(f"\n**발견 {len(p.findings)}건**: " + "; ".join(p.findings))

    # ============ PS-08 이한중 SW팀 leader ============
    p = Persona("PS-08", "SW팀장", "이한중", "team=5 소프트웨어팀 leader")
    p.login_now()
    out.append(f"\n## {p.code} — {p.label} `{p.login}` ({p.team_desc})\n")
    out.append("_일정 변경 통보 늦음. 홈 KPI + 변경 유형 분류 검증_\n")
    code, home = p.visit("/home")
    # SW 담당자 홈에 변경 카테고리가 SW 필터로 보이는지
    p.check_body(home, "홈에서 SW 관련 변경 표시",
                 "소프트웨어", "SW", "변경", "일정")
    p.visit("/changes")
    # 변경 등록 폼 change_type 옵션
    code, cnew = p.visit("/changes/new")
    p.check_body(cnew, "변경 등록 change_type 카테고리",
                 "기구", "전기", "전장", "SW", "BOM", "도면", "일정", "컨셉")
    out.extend(p.log)
    if p.findings:
        out.append(f"\n**발견 {len(p.findings)}건**: " + "; ".join(p.findings))

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"저장: {OUT}")


if __name__ == "__main__":
    round3()
