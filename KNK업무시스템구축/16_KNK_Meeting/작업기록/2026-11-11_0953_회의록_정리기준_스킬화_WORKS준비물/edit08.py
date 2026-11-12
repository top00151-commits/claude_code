# -*- coding: utf-8 -*-
"""z1208 — 회의록 정리 기준(대표 2026-11-11) 을 ai_client.py 에 넣는다.
사용: py edit08.py <앱 폴더(app/ 가 들어 있는 곳)>
 · _MEETING_EXTRACT_SYSTEM 의 「출력은 오직 아래 JSON 한 개」 줄 바로 앞에 기준 묶음을 끼운다(기존 규칙 글은 그대로).
 · ai_extract_meeting 정규화 뒤에 기한(due) 서버 검사를 붙인다.
 · 줄 끝은 원본 그대로(newline="")."""
import io
import sys
import os

root = sys.argv[1]
p = os.path.join(root, "app", "ai_client.py")
with io.open(p, "r", encoding="utf-8", newline="") as f:
    s = f.read()
NL = "\r\n" if "\r\n" in s else "\n"
if "_MEETING_SUMMARY_SKILL" in s:
    print("STOP: 이미 들어가 있음"); sys.exit(2)

# ① 기준 묶음(스킬) 정의 — _MEETING_EXTRACT_SYSTEM 바로 위
A_ANCHOR = "_MEETING_EXTRACT_SYSTEM = (" + NL
assert s.count(A_ANCHOR) == 1, "A_ANCHOR"
SKILL = '''# 🔴 z1208 (대표 2026-11-11 「회의록 정리 기준 다시 설정 · 스킬화해서 적용」): 회의록 정리 기준 묶음.
#   같은 기준이 Claude 작업용 스킬 문서로도 있다(.claude/skills/knk-meeting-summary/SKILL.md) — 둘을 함께 고친다.
#   · 출력 모양(title·summary·decisions{who,what,due}·actions{assignee,task,due})·DB·화면은 **그대로**.
#   · 위 z1183·z1184 규칙 글은 지우지 않는다(옛 검사기가 그 글을 본다) → 부딪치면 이 묶음을 따르라고 적는다.
#   · 🔵 지시문만으론 AI 가 다 안 따른다(이음 v854~v867 교훈) → 기한 모양은 서버도 본다(_mtg_due_strict).
_MEETING_SUMMARY_SKILL = (
    "[회의록 정리 기준 — 위 규칙과 부딪치면 이 기준을 따른다]\\n"
    "1) 목적·목표: 「## 핵심」 첫 문장에 이 회의를 왜 했는지(목적)와 무엇을 정하거나 얻으려 했는지(목표)를 "
    "원문에 나온 만큼만 쓴다. 원문에 없으면 지어내지 않는다. 이어서 중요한 결정 · 실행할 일 · 남은 확인을 간결하게.\\n"
    "2) 줄이되 빼지 않는다: 반복·맞장구·잡담은 줄인다. 그러나 기술 조건 · 수치와 단위 · 예외(「~는 제외」「~일 때만」) · "
    "중요한 의견 차이(무엇을 왜 다르게 봤는지 · 화자가 분명할 때만 이름) · 모델명·품번·부품 번호·코드 예시 · "
    "검토했다가 채택하지 않은 대안과 그 이유는 빠뜨리지 않는다.\\n"
    "3) 상태 구분: 제안 · 검토 중 · 보류와 확정 결정을 섞지 않는다. decisions 에는 확정된 결정만 넣는다. "
    "제안은 summary 에 [제안], 검토 중·보류·결론 안 남은 것은 [미결](보류면 「보류」와 그 이유)로 남긴다. "
    "「제안」은 한쪽이 의견을 냈으나 받아들였는지 원문에 없는 것이다 — 일을 맡기거나 정한 말(「~해 주세요」「~합시다」"
    "「~로 종결하죠」)에 상대가 동의했거나 반대 없이 넘어갔으면 확정으로 보고 제안으로 낮추지 않는다. "
    "검토하던 것 중 하나를 고른 말(「감안하고 ~를 사용한다」「그걸로 가죠」)도 확정이다 — 세부(모델·금액·납기 등)가 "
    "아직 미정이어도 고른 것은 decisions 에 넣고, 남은 세부는 summary 에 [미결]로 따로 남긴다.\\n"
    "3-1) 「(내부 방침)」은 그 결정을 **우리 회사(KNK) 사람끼리만** 정했을 때만 붙인다. 고객사·협력사 등 외부 참석자가 "
    "함께 정했거나 외부에 요청·약속한 것이면 붙이지 않는다. [이번 회의 정보]의 참석자·제목에 외부 회사(고객사 등)가 있는 "
    "회의에서는, 회의 중 외부 참석자가 「좋습니다」「맞습니다」「종결하죠」「알겠습니다」로 받은 결정에 붙이지 않는다. "
    "외부와 정한 것인지 망설여지면 붙이지 않는다.\\n"
    "4) 방향 변경: 논의 중 방향이 바뀌었으면 decisions·actions 에는 **최종 합의**를 쓴다. 바뀐 경위는 summary 에 "
    "한 줄로 남긴다(예: 「처음에는 A 를 검토했으나 B 로 정했다」). 처음 제안한 일이 최종안에서도 필요한지 원문으로 "
    "분명하지 않으면 actions 에 넣지 않고 summary 에 「[확인 필요] <그 일> — 최종안에서도 필요한지 확인」으로 남긴다.\\n"
    "5) 행동 구분: 자료 작성 · 공유(전달) · 검토 · 승인 · 최종 완료는 서로 다른 행동이다. 원문이 말한 행동만 쓴다"
    "(「작성」만 말했으면 「작성해 공유·승인」으로 늘리지 않는다). 단계마다 담당이나 기한이 다르면 actions 를 단계별로 나눈다.\\n"
    "6) 피드백: 「검토하고 의견 드리겠다」「확인해서 회신하겠다」처럼 피드백을 따로 약속했을 때만 actions 에 "
    "피드백 항목을 따로 넣는다(task 예: 「<무엇>에 대한 검토 의견 회신」). 실행 담당자와 피드백 담당자를 임의로 같게 "
    "정하지 않는다 — 피드백을 누가 주는지 원문에 없으면 그 항목의 assignee 는 \\"\\".\\n"
    "7) 사람: 화자나 담당자가 불명확하면 이름을 추측하지 않는다(who·assignee 는 \\"\\"). 「제가」「저희가」「그쪽에서」처럼 "
    "누구인지 원문으로 분명하지 않으면 사람·회사 이름을 붙이지 말고 그 표현을 문장 안에 남긴다. 원문이 쪽을 이름으로 "
    "말했을 때만(「KNK 쪽에서 주시면」) 그 이름을 쓴다. 담당이 다른 일은 한 항목에 묶지 않는다. "
    "「○○ 팀장님 오시면 정리하자」처럼 사람이 **때·조건**으로만 나오면 그 사람은 담당이 아니다 — 그 사람이 하겠다고 "
    "했거나 그 사람에게 맡긴 말이 없으면 assignee 는 \\"\\" 로 두고, 그 조건은 8) 처럼 「(기한: ○○ 팀장님 오시면)」으로 남긴다.\\n"
    "8) 기한: due 는 날짜가 하나로 분명할 때만 YYYY-MM-DD 로 쓴다([이번 회의 정보]의 날짜·요일로 확실히 계산되는 "
    "「내일」「다음 주 화요일」 포함). 「자료를 받은 다음 날」「승인 나면 바로」「샘플 도착 후 1주」처럼 다른 일이 끝나야 "
    "정해지는 조건부 기한과 「이번 달 중」「다음 주 초」처럼 날짜 하나로 못 정하는 기한은 due 를 \\"\\" 로 비우고 "
    "task(결정이면 what) 끝에 원래 표현을 「(기한: <원문 표현>)」으로 남긴다. 「최대한 빨리」「○○ 팀장님 오시면」처럼 "
    "조건이나 막연한 때가 걸린 할 일도 할 일이다 — 빼지 말고 같은 방식으로 넣는다. 원문이 할 일과 함께 말한 때·바람"
    "(「최대한 빨리」「~할 때 같이」「~전에」)은 그 할 일에 반드시 붙인다 — 다 쓴 뒤 할 일마다 원문에서 그 일 근처에 "
    "때를 말한 표현이 있었는지 다시 확인한다.\\n"
    "9) 만들지 않는다: 원문에 없는 담당자 · 받는 사람(누구에게 공유·보고) · 기한 · 수치를 만들지 않는다. "
    "받는 사람이 원문에 없으면 「공유한다」까지만 쓴다(위 규칙의 「누구에게 공유하는지」보다 이것이 먼저다). "
    "원문에 없는 행동(「조정한다」「반영한다」「메일로」 같은 수단)을 덧붙이지 않는다. "
    "결정·할 일이 없으면 빈 배열.\\n"
)


'''
s = s.replace(A_ANCHOR, SKILL.replace("\n", NL) + A_ANCHOR, 1)

# ② 지시문 안 — JSON 출력 줄 바로 앞에 묶음을 끼운다
B_ANCHOR = '    "출력은 오직 아래 JSON 한 개. 마크다운 코드펜스·설명·인사말 금지.\\n"' + NL + "    '{\"title\":\"\",\"summary\":\"\",'" + NL
assert s.count(B_ANCHOR) == 1, "B_ANCHOR (회의록 JSON 줄)"
s = s.replace(B_ANCHOR, "    + _MEETING_SUMMARY_SKILL +   # z1208" + NL + B_ANCHOR, 1)

# ③ 기한 서버 검사 함수 — ai_extract_meeting 바로 위
C_ANCHOR = "def ai_extract_meeting(body: str, context: str = \"\") -> tuple[bool, dict]:" + NL
assert s.count(C_ANCHOR) == 1, "C_ANCHOR"
HELP = '''_DUE_DATE_RE = re.compile(r"^(\\d{4})-(\\d{2})-(\\d{2})")


def _mtg_due_strict(rows: list, core: str) -> None:
    """z1208: due 는 「YYYY-MM-DD 하나」만 둔다. 그 밖의 글(「자료 받은 다음 날」「11/15」「다음 주 초」)이 오면
    due 를 비우고 원래 표현을 core(what/task) 끝에 「(기한: …)」으로 옮긴다(글은 버리지 않는다).
    날짜 뒤에 시각 등이 붙었으면 날짜만 due 에 두고 원래 표현을 같은 방식으로 남긴다. 없는 날짜(2026-02-30)도 비운다."""
    from datetime import date as _d
    for r in rows:
        raw = (r.get("due") or "").strip()
        if not raw:
            continue
        m = _DUE_DATE_RE.match(raw)
        ok_date = ""
        if m:
            try:
                _d(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                ok_date = m.group(0)
            except ValueError:
                ok_date = ""
        r["due"] = ok_date
        if ok_date == raw:
            continue
        #  AI 가 「기한: 다음에」「(기한: …)」처럼 머리말째 넣은 경우 — 머리말·괄호는 떼고 붙인다(「기한: 기한:」 막기)
        show = re.sub(r"^\\(?\\s*기한\\s*[:：]\\s*", "", raw)
        if raw.startswith("(") and show.endswith(")"):
            show = show[:-1].strip()
        show = show or raw
        text = r.get(core) or ""
        if show not in text:
            r[core] = (text + " (기한: " + show + ")").strip()


'''
s = s.replace(C_ANCHOR, HELP.replace("\n", NL) + C_ANCHOR, 1)

# ④ 정규화 직후 호출 — result 를 만든 바로 뒤(베트남어 표시 손보기 앞)
D_ANCHOR = '        "title": str(data.get("title", "") or "").strip()[:60],' + NL + "    }" + NL + "    if _vi_n:" + NL + '        _vi_finish(result, _vi_n, "회의록")' + NL
D_HEAD = '        "title": str(data.get("title", "") or "").strip()[:60],' + NL + "    }" + NL
D_CALL = ("    _mtg_due_strict(result[\"decisions\"], \"what\")    # z1208 — 기한은 분명한 날짜만" + NL
          + "    _mtg_due_strict(result[\"actions\"], \"task\")" + NL)
if s.count(D_ANCHOR) == 1:
    s = s.replace(D_ANCHOR, D_HEAD + D_CALL + D_ANCHOR[len(D_HEAD):], 1)
elif os.environ.get("EDIT08_SOFT") == "1" and s.count(D_HEAD + "    return (True, result)" + NL) == 1:
    # 옛 사본(z1188 베트남어 표시 전) — 같은 자리(정규화 직후)에
    s = s.replace(D_HEAD + "    return (True, result)" + NL, D_HEAD + D_CALL + "    return (True, result)" + NL, 1)
else:
    raise AssertionError("D_ANCHOR")

tmp = p + ".tmp08"
with io.open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(s)
os.replace(tmp, p)
print("OK z1208 →", p)
