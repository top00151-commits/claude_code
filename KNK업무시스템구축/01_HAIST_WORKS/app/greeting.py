# -*- coding: utf-8 -*-
"""z1191z136 (대표 2026-11-24): 웍스 홈 인사말 — 회사 근무 시간 · 휴일 · 창립기념일 · 직급 호칭 · 생일

대표 말씀: 「출근 9시 · 퇴근 18시 · 점심 13~14시 · 본사 창립기념일 6월 1일 · 베트남 창립기념일 10월 15일 기본 사항에 맞게 말을 표현」
          「1. 김정락님 아니고 김정락 대표이사님(직원들도 직급에 맞게) 2. 생년월일 — 생일날 생일 축하 멘트 · 하루 종일 상황에 맞게」
          「12~13시 『점심 드세요』·17시 『마무리』는 점심·퇴근으로 오해 — 다른 멘트로」
  · 시간은 직원 소속 기준(본사 = 한국 시간 · 베트남 법인 = 한국 −2시간) · 휴일도 소속 나라 공휴일
  · 순서: 생일 > 창립기념일 > 주말·공휴일 > 시간대
  · 호칭 = 이름 + 직급 + 님 · 「매니저(팀장)」처럼 괄호 직책은 괄호 안(팀장) · 직급 없으면 이름 + 님
  · 점심 이야기는 13~14시에만 · 퇴근 이야기는 18시 이후에만
"""
from datetime import datetime, timedelta

FOUNDING = {"KOR": ("06-01", "KNK 창립기념일"), "VN": ("10-15", "KNK VINA 창립기념일")}


SHORT_TITLE = {"대표이사": "대표", "전무이사": "전무", "상무이사": "상무"}
EXEC_WORDS = ("이사", "상무", "전무", "부사장", "사장", "대표", "법인장")


def title_of(name, rank):
    """「김정락 대표이사님」 · 「허동준 매니저님」 · 「매니저(팀장)」 → 「○○○ 팀장님」 · 직급 없으면 「○○○님」."""
    n = (name or "").strip()
    r = (rank or "").strip()
    if "(" in r and ")" in r:
        # z1191z139 (대표 11-24 「매니저는 팀장으로 · 임원직급은 임원직급으로 불러줘」):
        #   괄호 앞이 임원 직급(이사·상무·전무·부사장·사장·대표·법인장)이면 그 직급 · 아니면 괄호 안 직책(팀장)
        base = r[:r.index("(")].strip()
        inner = r[r.index("(") + 1:r.index(")")].strip()
        r = base if (base and any(k in base for k in EXEC_WORDS)) else (inner or base)
    # z1191z139 (대표 11-24 「대표이사·전무이사·상무이사 => 대표님·전무님·상무님」)
    r = SHORT_TITLE.get(r, r)
    return ("%s %s님" % (n, r)) if (n and r) else ("%s님" % n if n else "")


def local_now(entity, now_kst):
    """소속 기준 지금 시각 — 베트남 법인은 한국보다 2시간 늦다."""
    return now_kst - timedelta(hours=2) if (entity or "").upper() == "VN" else now_kst


def is_birthday(birth_md, birth_lunar_md, today):
    """생일인가 — 음력 생일(birth_lunar_md · 대표 「나는 음력 2월 9일」)이 있으면 그것만 · 없으면 이음 양력 월·일(birth_md)."""
    if (birth_lunar_md or "").strip():
        try:
            from .lunar_kr import is_lunar_md_today
        except ImportError:
            from lunar_kr import is_lunar_md_today
        return is_lunar_md_today(birth_lunar_md.strip(), today)
    bmd = (birth_md or "").strip()[-5:]
    return bool(bmd) and bmd == today.strftime("%m-%d")


# z1191z137 (대표 11-24 「멘트 부분이 너무 길어서 정신없는데」): 큰 제목 = 인사 + 호칭 · 그 뒤 말은 SEP 뒤 작은 한 줄(home.html 이 나눠 보임)
SEP = "\n"


def build(name, rank, entity, birth_md, now_kst, hol_kr=None, hol_vn=None, birth_lunar_md=None):
    """(인사말, 구분) — 구분은 화면 위 작은 글자(MORNING 등)."""
    who = title_of(name, rank)
    ent = "VN" if (entity or "").upper() == "VN" else "KOR"
    t = local_now(ent, now_kst or datetime.now())
    h, md, ymd = t.hour, t.strftime("%m-%d"), t.strftime("%Y-%m-%d")
    hol = (hol_vn if ent == "VN" else hol_kr) or {}
    if is_birthday(birth_md, birth_lunar_md, t.date()):
        if h < 12:
            tail = "행복한 하루 보내세요"
        elif h < 13:
            tail = "오늘 하루 특별하게 보내세요"
        elif h < 14:
            tail = "맛있는 점심 드시고 즐거운 하루 되세요"
        elif h < 18:
            tail = "기분 좋은 오후 보내세요"
        else:
            tail = "오늘도 수고 많으셨어요. 좋은 저녁 보내세요"
        return "생일 축하드립니다, %s! 🎂%s%s" % (who, SEP, tail), "birthday"
    fmd, fname = FOUNDING[ent]
    if md == fmd:
        return "오늘은 %s입니다 🎉%s함께해 주셔서 고맙습니다, %s" % (fname, SEP, who), "anniversary"
    if t.weekday() >= 5 or ymd in hol:
        why = hol.get(ymd) if ymd in hol else ("주말" if t.weekday() >= 5 else "")
        return "%s에도 나오셨네요, %s%s고생 많으십니다" % (why or "쉬는 날", who, SEP), "holiday"
    if h < 6:
        return "늦은 시간까지 애쓰시네요, %s%s너무 늦지 않게 쉬세요" % (who, SEP), "night"
    if h < 9:
        return "좋은 아침입니다, %s ☀️%s오늘 하루도 잘 부탁드립니다" % (who, SEP), "morning"
    if h < 12:
        return "오전 업무 힘내세요, %s 🌱" % who, "morning"
    if h < 13:
        return "오전 업무 막바지예요, %s%s조금만 더 힘내세요" % (who, SEP), "morning"
    if h < 14:
        return "점심시간이에요, %s 🍚%s맛있게 드시고 잠깐 쉬어 가세요" % (who, SEP), "lunch"
    if h < 17:
        return "오후도 힘내세요, %s 🌿" % who, "afternoon"
    if h < 18:
        return "남은 오후 업무도 힘내세요, %s" % who, "afternoon"
    if h < 21:
        return "오늘도 수고 많으셨습니다, %s" % who, "evening"
    return "늦은 시간까지 애쓰시네요, %s%s너무 늦지 않게 들어가세요" % (who, SEP), "night"
