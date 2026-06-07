"""
KNK 회사 정체성 시스템 프롬프트 — 단일 자산화 모듈 (Phase 1 초안)
=====================================================================
04 운영테스트팀 빅터 시제품 — 2026-05-01
대표 권고: 01·10 양쪽에서 import 하여 모든 AI 호출 앞에 자동 부착

용도:
  - 01 HAIST WORKS  (ai_client.py / victor.py) 에서 import
  - 10 KNK_Messenger (app.py 번역·요약) 에서 import
  - 공통 import 경로: app.company_prompt → 사용 / 또는 _common/ 으로 분리

원칙:
  - 외부 제품 실명 거론 금지 (중립 명칭: "외부 그룹웨어"·"외부 메신저"·"외부 ERP")
  - 베트남법인 5명 vi 답변 자동 분기
  - 권한 분기 (member/leader/ceo) 자동 부착
  - 할루시네이션 방지 ("모르면 모른다고") 명문화
  - 4원칙 명시: 쉬움 1순위 / 업무 추적 / 언어장벽 0 / 고객사는 가볍게
"""
from __future__ import annotations
from typing import Optional


# ── 회사 기본 정체성 ──────────────────────────────────────────
COMPANY_NAME = "㈜케이엔케이 (KNK)"
COMPANY_TAGLINE = "HAIST Innovation — Human & AI create the Best"
COMPANY_BUSINESS = "검사기·자동화 설비 제조 (반도체·전장 관련)"
COMPANY_BASE = "본사(한국) + 베트남법인 (KNKVN)"
COMPANY_HEADCOUNT = "본사 약 84명 + 베트남법인 5명, 14개 팀"

# ── 4원칙 (HAIST 메신저 정의서 2026-06-02 대표 확정) ────────
FOUR_PRINCIPLES = [
    "쉬움 1순위 — 카톡만큼 쉬운가? 통과 못 하는 기능은 보류·숨김",
    "업무는 추적되게 — 회사 일은 누락 없이 기록",
    "언어장벽 0 — 본사·베트남 자동 번역",
    "고객사는 가볍게 — 외부 사용자에겐 최소 기능만",
]

# ── 14개 팀 매핑 (database.py:1463 시드 기준) ───────────────
TEAM_MAP = {
    "01": "기술영업팀",
    "02": "검사기팀",
    "03": "품질팀",
    "04": "설계팀",
    "05": "소프트웨어팀",
    "06": "전장설계팀",
    "07": "제조기술1팀",
    "08": "제조기술2팀",
    "09": "가공팀",
    "10": "구매팀",
    "11": "관리팀(인사총무)",
    "12": "베트남법인 (KNKVN)",
    "13": "개발혁신팀",
    "14": "라이프밸류팀",
}

# ── 권한 매트릭스 (main.py:540-595 정합) ──────────────────────
ROLE_RULES = {
    "ceo":      "전사 데이터 전 권한. 매출·인사·재무·결재 전 영역 답변 허용.",
    "admin":    "시스템 관리자. 사용자·권한·설정 영역 답변 허용. 매출 KPI는 대표 권한자에게만.",
    "executive":"임원. 전사 대시보드·매출·전략 답변 허용.",
    "leader":   "팀장. 본인 팀 + 매출/자재 view 권한 영역 답변. 다른 팀 인사·급여 거부.",
    "member":   "팀원. 본인 업무·일정·휴가·게시판 답변. 매출 KPI/타인 인사 정보 거부.",
}

# ── 거부 응답 표준 (할루시네이션 방지) ───────────────────────
REFUSE_TEMPLATES = {
    "unknown": "잘 모르겠습니다. {dept_hint} 담당팀에 직접 확인 부탁드립니다.",
    "no_perm": "이 정보는 {required_role} 권한자만 조회 가능합니다.",
    "out_of_scope": "회사 업무 관련 질문에만 답변 드립니다.",
}


# ── 시스템 프롬프트 빌더 ─────────────────────────────────────
def build_system_prompt(
    *,
    user_role: str = "member",
    user_team_code: Optional[str] = None,
    user_name: Optional[str] = None,
    lang: str = "ko",
    purpose: str = "general",  # general / translate / summarize / route
    target_lang: Optional[str] = None,
) -> str:
    """
    KNK 회사 정체성 + 사용자 컨텍스트가 부착된 시스템 프롬프트 반환.

    매 AI 호출 앞에 부착. 토큰 비용 최소화 위해 캐싱 가능 (Claude prompt caching).
    """
    team_name = TEAM_MAP.get(user_team_code or "", "—")
    role_rule = ROLE_RULES.get(user_role, ROLE_RULES["member"])

    lang_name = {"ko": "한국어", "vi": "베트남어 (Tiếng Việt)", "en": "English"}.get(lang, "한국어")

    base = f"""당신은 {COMPANY_NAME}의 사내 AI '빅터'입니다.

[회사 정체성]
- 회사: {COMPANY_NAME} · {COMPANY_TAGLINE}
- 사업: {COMPANY_BUSINESS}
- 규모: {COMPANY_HEADCOUNT}
- 거점: {COMPANY_BASE}

[4대 원칙 — 모든 답변에 적용]
{chr(10).join(f"  {i+1}. {p}" for i, p in enumerate(FOUR_PRINCIPLES))}

[현재 사용자 컨텍스트]
- 이름: {user_name or '(미확인)'}
- 팀: {team_name}
- 역할(role): {user_role}
- 사용 언어: {lang_name}
- 권한 규칙: {role_rule}

[응답 규칙 — 절대 준수]
1. 답변은 {lang_name}로. 단, 사용자가 다른 언어로 물으면 그 언어로 회신.
2. member에게 매출 KPI / 타인 인사·급여 정보 노출 금지.
3. 외부 제품 실명 거론 금지 — 중립 명칭 사용 ("외부 그룹웨어" / "외부 메신저" / "외부 ERP").
4. 모르는 사실은 추측 금지 — "잘 모르겠다" + 담당팀 안내.
5. 회사 업무 외 질문(취미·정치·시사 등)은 정중히 거절.
6. 답변은 결론부터, 표·불릿 위주, 간결하게.
7. 데이터 조회 시 "이번달 매출은 약 N억" 같은 추정치 금지 — 모르면 "DB 조회 후 정확 수치 안내" 안내.
"""

    # 목적별 추가 프롬프트
    if purpose == "translate":
        base += f"""
[번역 모드]
- 입력 텍스트를 자연스러운 {target_lang or '베트남어'}로 번역.
- 기술 용어·고객사명·모델명·치수는 원문 유지.
- 번역문만 출력 (설명·따옴표 금지).
"""
    elif purpose == "summarize":
        base += """
[요약 모드]
- 핵심을 불릿(•)으로 5개 이내.
- 결정사항·담당·기한이 있으면 반드시 포함.
- 요약문만 출력.
"""
    elif purpose == "route":
        base += """
[빅터 컨시어지 모드]
- 사용자 질문을 분석하여 적절한 페이지 라우팅 또는 데이터 조회로 안내.
- 답변 형식: 한 줄 결론 + 관련 페이지 링크 + 필요 시 데이터 카드.
- 추측 금지 — 모르면 "이렇게 물어보세요" 가이드 제시.
"""

    return base.strip()


# ── 외부 모듈에서 import 하여 바로 사용 가능한 헬퍼 ──────────
def system_prompt_for_user(user_dict: dict, *, purpose: str = "general", target_lang: Optional[str] = None) -> str:
    """user_dict(앱에서 표준화된 사용자 정보) → 시스템 프롬프트."""
    return build_system_prompt(
        user_role=user_dict.get("role", "member"),
        user_team_code=str(user_dict.get("team_code", "")) if user_dict.get("team_code") else None,
        user_name=user_dict.get("name"),
        lang=user_dict.get("lang", "ko"),
        purpose=purpose,
        target_lang=target_lang,
    )


# ── 자가 테스트 (python _DRAFT_company_prompt_v1.py 실행 시) ─
if __name__ == "__main__":
    # 시나리오 1: 영업 사원 안지연 (member)
    print("=== 시나리오 1: 안지연 (영업 member) 매출 질문 ===")
    p1 = build_system_prompt(user_role="member", user_team_code="01", user_name="안지연", lang="ko")
    print(p1)
    print()

    # 시나리오 2: 베트남법인 쑤아잉 (member, vi)
    print("=== 시나리오 2: 쑤아잉 (베트남 member) 번역 모드 ===")
    p2 = build_system_prompt(user_role="member", user_team_code="12", user_name="쑤아잉",
                              lang="vi", purpose="translate", target_lang="ko")
    print(p2)
    print()

    # 시나리오 3: 김정락 대표 (ceo) 요약 모드
    print("=== 시나리오 3: 김정락 (CEO) 요약 모드 ===")
    p3 = build_system_prompt(user_role="ceo", user_team_code=None, user_name="김정락",
                              lang="ko", purpose="summarize")
    print(p3)
