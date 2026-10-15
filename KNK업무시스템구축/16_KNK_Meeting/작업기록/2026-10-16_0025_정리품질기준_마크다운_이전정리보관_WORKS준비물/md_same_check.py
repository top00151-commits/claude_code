# -*- coding: utf-8 -*-
"""z1183 검사기 ① — 정리 글 「가벼운 마크다운」 그리기가 **서버(회의록 양식)와 화면(JS)에서 똑같은가** · 막기(escape) · 옛 정리.
서버 = main.py 의 _md_lite_line · _md_plain (📄 회의록 양식 · 🎤 목록 미리보기 · 🔍 검색 한 줄)
화면 = _v5_partials/knk_md_lite.html 의 KNKMdLite.line · plain (🗓 회의록 화면 · 🎤 음성 메모 화면 · 📋 복사)
둘이 어긋나면 같은 정리가 양식과 화면에서 다르게 보인다 → 같은 줄을 둘에 넣어 (종류, 그린 글)을 한 줄씩 맞춰 본다.
쓰는 법: py md_same_check.py <app 폴더(app_new/app)>     판정: 종료코드(0=통과) + 요약 줄. 서버·브라우저를 띄우지 않는다.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
APP = sys.argv[1]
OK = FAIL = 0


def chk(name, cond, detail=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  OK   %s" % name)
    else:
        FAIL += 1
        print("  FAIL %s %s" % (name, detail))


# ── 서버 쪽: main.py 에서 z1183 덩어리만 꺼내 돌린다(앱 전체를 띄우지 않는다) ──
src = io.open(os.path.join(APP, "main.py"), encoding="utf-8").read()
a = src.find("# ── z1183: 정리 글 「가벼운 마크다운」")
b = src.find("def _mtg_doc_sum_lines(summary):", a)
c_end = src.find("\n\n\n", b)
chk("main.py 에 z1183 그리기 덩어리가 있다", a >= 0 and b > a and c_end > b)
NS = {}
exec(src[a:c_end], NS)
py_line, py_plain, py_doc = NS["_md_lite_line"], NS["_md_plain"], NS["_mtg_doc_sum_lines"]

# ── 화면 쪽: 부품의 <script> 를 node 로 ──
part = io.open(os.path.join(APP, "templates", "_v5_partials", "knk_md_lite.html"), encoding="utf-8").read()
js = part[part.find("<script>") + len("<script>"):part.rfind("</script>")]

CASES = [
    "", "   ", "## 핵심", "# 제목", "### 소제목 ###", "#### 넷", "##핵심", "결론", "■ 목적", "회의 내용", "회의내용",
    "내용:", "할 일", "할일", "**결론**", "핵심", "[납기]", "[결정] 2호기 납기 11-20 확정", "[확인 필요] 숫자 충돌",
    "[확인필요] 붙여 씀", "[내부 방침] 외부 공유 안 함", "[제안] 카메라 2대", "[미결] 셋업 날짜", "[결정]", "[]", "[a]b]",
    "[안건 1] 납기", "핵심: 결론 한 줄", "핵심：전각 쌍점", "핵심 요약", "- 목록", "  - 두 단", "\t- 탭 들여쓰기", " - 한 칸",
    "* 별 목록", "• 점 목록", "-붙임", "- ", "1. 첫째", "12) 열둘", "123. 셋자리", "１. 전각 숫자", "**굵게** 시작",
    "가운데 **굵게** 끝", "**안 닫힘", "****", "<script>alert(1)</script>", "a & b < c > d \" ' e",
    "- [결정] 목록 안 표시", "## **굵은 소제목**", "- **무엇을** — 김한국 · 2026-11-20까지", "끝 공백   ",
    "(우려) 카메라 납기", "  ## 들여쓴 소제목", "- 「따옴표」·가운데점", "<b>굵게</b> 흉내", "[<img src=x>]",
    "## <i>소제목</i>", "핵심: **2호기** 납기 확정", "1. [결정] 번호 안 표시",
]
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write("var window = {};\n" + js + "\n")
    f.write("var CASES = " + json.dumps(CASES, ensure_ascii=False) + ";\n")
    f.write("var TEXT = " + json.dumps("\n".join(CASES), ensure_ascii=False) + ";\n")
    f.write("process.stdout.write(JSON.stringify({lines: CASES.map(function(c){ var x = window.KNKMdLite.line(c);"
            " return [x.k, x.h]; }), plain: window.KNKMdLite.plain(TEXT), render: window.KNKMdLite.render(TEXT)}));\n")
    jsf = f.name
r = subprocess.run(["node", jsf], capture_output=True)
os.remove(jsf)
out = r.stdout.decode("utf-8")
chk("화면 부품 스크립트가 node 에서 돈다", r.returncode == 0, r.stderr.decode("utf-8", "replace")[-300:])
J = json.loads(out) if r.returncode == 0 else {"lines": [], "plain": "", "render": ""}

print("\n■ ① 줄마다 (종류, 그린 글) — 서버 = 화면")
same = 0
for i, cse in enumerate(CASES):
    pk, ph = py_line(cse)
    jk, jh = (J["lines"][i] if i < len(J["lines"]) else (None, None))
    if (pk, ph) == (jk, jh):
        same += 1
    else:
        chk("줄 %r" % cse, False, "\n       서버: %r\n       화면: %r" % ((pk, ph), (jk, jh)))
chk("%d줄 모두 같다" % len(CASES), same == len(CASES), "%d/%d" % (same, len(CASES)))
chk("복사·미리보기 글(plain)도 같다", py_plain("\n".join(CASES)) == J["plain"])

print("\n■ ② 종류가 기대대로")
K = {c: py_line(c)[0] for c in CASES}
for cse, want in [("## 핵심", "s"), ("##핵심", "s"), ("결론", "s"), ("■ 목적", "s"), ("**결론**", "s"), ("핵심", "s"),
                  ("[납기]", "h"), ("[안건 1] 납기", "p"), ("핵심: 결론 한 줄", "k"), ("핵심：전각 쌍점", "k"),
                  ("핵심 요약", "p"), ("- 목록", "li"), (" - 한 칸", "li"), ("  - 두 단", "li2"), ("\t- 탭 들여쓰기", "li2"),
                  ("* 별 목록", "li"), ("• 점 목록", "li"), ("-붙임", "p"), ("1. 첫째", "ol"), ("12) 열둘", "ol"),
                  ("123. 셋자리", "p"), ("１. 전각 숫자", "p"), ("#### 넷", "p"), ("", "e"), ("   ", "e"), ("[]", "p"),
                  ("[결정] 2호기 납기 11-20 확정", "p"), ("[결정]", "p")]:
    chk("%-22r → %s" % (cse, want), K[cse] == want, "실제 %s" % K[cse])

print("\n■ ③ 🔴 막기(escape) — 정리 글 안의 꺾쇠가 화면 코드가 되지 않는다")
for cse in ["<script>alert(1)</script>", "<b>굵게</b> 흉내", "[<img src=x>]", "## <i>소제목</i>", "a & b < c > d \" ' e"]:
    h = py_line(cse)[1]
    chk("%r → 태그 없음" % cse[:24], "<script" not in h and "<img" not in h and "<i>" not in h and "<b>굵게" not in h, h)
chk("& < > \" ' 다섯 글자를 막는다", py_line("a & b < c > d \" ' e")[1] == "a &amp; b &lt; c &gt; d &quot; &#39; e",
    py_line("a & b < c > d \" ' e")[1])
chk("**굵게** 는 막은 뒤 <b> 로", py_line("가운데 **굵게** 끝")[1] == "가운데 <b>굵게</b> 끝")
chk("[결정] 표시는 색 글씨", py_line("[결정] 2호기 납기 11-20 확정")[1].startswith('<span class="tg tg-dec">[결정]</span> '))
chk("[확인필요](붙여 씀)도 같은 색", 'tg-chk' in py_line("[확인필요] 붙여 씀")[1])
chk("[내부 방침] 표시", 'tg-int' in py_line("[내부 방침] 외부 공유 안 함")[1])
chk("목록 안 표시도 색 글씨", py_line("- [결정] 목록 안 표시")[1].startswith('<span class="tg tg-dec">'))

print("\n■ ④ 복사·미리보기 글(plain) — 기호만 빠지고 내용은 그대로")
pl = py_plain("## 핵심\n2호기 **납기** 확정.\n\n## 납기\n- **11-20** 출하\n  - 셋업 25일\n[결정] 확정")
chk("「## 핵심」→「■ 핵심」", pl.split("\n")[0] == "■ 핵심", pl.split("\n")[0])
chk("**굵게** 표시만 빠진다", "2호기 납기 확정." in pl and "**" not in pl, pl)
chk("목록 「- 」·들여쓰기·[결정] 은 그대로", "- 11-20 출하" in pl and "  - 셋업 25일" in pl and "[결정] 확정" in pl, pl)
chk("빈 줄도 그대로(문단 사이)", pl.split("\n")[2] == "")

print("\n■ ⑤ 옛 정리도 예전처럼 (z1181 「결론·목적·회의 내용」 · 그 전 「핵심: + [안건명]」)")
old81 = py_doc("결론\n- 2호기 납기 확정\n목적\n- 일정 협의\n회의 내용\n[납기]\n- 11월 20일 출하 (합의)")
chk("z1181 틀: 머리말 셋 = s", [x["kind"] for x in old81 if x["kind"] == "s"] == ["s", "s", "s"], [x["kind"] for x in old81])
chk("z1181 틀: [납기] = h · 목록 = li", [x["kind"] for x in old81][5:] == ["h", "li"], [x["kind"] for x in old81])
oldk = py_doc("핵심: 11월 납기 확정\n\n[납기]\n- 11월 20일 출하 (합의)")
chk("옛 틀: 핵심 = k · 빈 줄 = e · [납기] = h · 목록 = li", [x["kind"] for x in oldk] == ["k", "e", "h", "li"],
    [x["kind"] for x in oldk])
chk("아직 정리 전(빈 글) = 빈 목록(양식에 안내)", py_doc("") == [] and py_doc("   \n ") == [])
chk("줄마다 원래 글(t)도 남는다", old81[1]["t"] == "- 2호기 납기 확정")

print("\n===== z1183 md_same_check: 통과 %d · 실패 %d =====" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
