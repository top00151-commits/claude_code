# -*- coding: utf-8 -*-
"""z1104 시험 — 저장하면 '저장한 그 화면'으로 돌아오는가 (이새롬 프로 신고 2026-09-16).

신고 원문: "1번 화면에서 수정-저장 하면 2번 화면으로 넘어갑니다. 저장 후 저장된 화면으로 나와야 합니다."

  1번 화면 = /project/{id}?so=T-260909-2  (작업일정표에서 관리번호를 눌러 들어온 '보던 수주' 카드)
  2번 화면 = /project/{id}                (조건이 없어 가장 오래된 '최초 수주' 카드)

원인: 저장 뒤 새로고침이 `location.pathname + '?_t=' + Date.now()` 라 주소의 조건(?so=)을 통째로 버렸다.
덤: 매번 달라지는 _t 가 화면 위치 복원(z984b) 열쇠까지 어긋내 화면이 맨 위로 올라갔다.

이 시험은 **진짜 코드**만 본다.
  §2 는 chrome.html 에서 normSearch / knkReloadKeepView 원문을 뽑아 node 로 실제 실행한다.
  §3 은 project_detail.html 의 카드 선택 Jinja 원문을 뽑아 실제로 렌더한다(옛 방식 재현 포함).
  §4 는 규정을 어긴 코드 10종을 만들어 배포 전 검사기가 정말 잡는지 본다.

실행:  python _검증/test_reload_keep_view_20260916.py
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = os.path.join(ROOT, "app", "templates", "_v5_partials", "chrome.html")
DETAIL = os.path.join(ROOT, "app", "templates", "project_detail.html")
TPL = os.path.join(ROOT, "app", "templates")

OK = FAIL = 0
_sec = ""


def sec(t):
    global _sec
    _sec = t
    print("\n" + "━" * 72)
    print(t)
    print("━" * 72)


def chk(name, cond, got=""):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅ %s" % name)
    else:
        FAIL += 1
        print("  ❌ %s%s" % (name, ("   ← %s" % got) if got else ""))


def read(p):
    return io.open(p, encoding="utf-8").read()


def brace_block(src, start_pat):
    """`start_pat` 다음의 '{' 부터 짝이 맞는 '}' 까지 원문을 그대로 잘라 온다(코드를 베끼지 않기 위함)."""
    m = re.search(start_pat, src)
    assert m, "원문을 못 찾음: %s" % start_pat
    i = src.index("{", m.end() - 1)
    depth, j = 0, i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
        j += 1
    raise AssertionError("괄호 짝이 안 맞음: %s" % start_pat)


OLD_RELOAD = "window.location.href = window.location.pathname + '?_t=' + Date.now();"

# ════════════════════════════════════════════════════════════════════
sec("§1. 소스 — 옛 방식이 남아 있는가")
# ════════════════════════════════════════════════════════════════════
detail = read(DETAIL)
chrome = read(CHROME)

chk("project_detail.html 에 옛 새로고침(주소 버림) 0곳",
    detail.count(OLD_RELOAD) == 0, "%d곳 남음" % detail.count(OLD_RELOAD))
chk("project_detail.html 이 공용 함수를 8곳에서 쓴다",
    detail.count("knkReloadKeepView();") == 8,
    "%d곳" % detail.count("knkReloadKeepView();"))

# 검사기와 별개로 한 번 더 — 더 느슨한 그물로 전 템플릿을 훑는다(주석은 실행되지 않으므로 지운다)
_pat_old = re.compile(r"location\s*\.\s*pathname\s*\+\s*['\"]\?")


def strip_comments(s):
    s = re.sub(r"\{#.*?#\}", "", s, flags=re.S)      # Jinja 주석
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)      # JS 블록 주석(이 규칙을 설명하는 글이 여기 있다)
    s = re.sub(r"(?m)^\s*//.*$", "", s)              # JS 줄 주석
    return s


sweep, n_files = [], 0
for dp, dn, fn in os.walk(TPL):
    if "_legacy" in dp.replace("\\", "/"):
        continue
    for f in fn:
        if not f.endswith(".html"):
            continue
        p = os.path.join(dp, f)
        n_files += 1
        for ln in strip_comments(read(p)).splitlines():
            if not _pat_old.search(ln):
                continue
            if "(q ?" in ln:   # 공용 함수 자신 — 조건이 있을 때만 '?' 를 붙인다(주소를 안 버린다)
                continue
            sweep.append("%s:%s" % (os.path.basename(p), ln.strip()[:60]))
chk("전 템플릿 %d개 스윕 — 주소 버리는 새로고침 0건" % n_files, not sweep, " / ".join(sweep[:3]))

chk("chrome.html 에 공용 knkReloadKeepView 정의가 있다",
    "window.knkReloadKeepView = function" in chrome)
chk("공용 함수는 두 번 정의돼도 덮어쓰지 않는다(중복 include 방어)",
    "if (window.knkReloadKeepView) return;" in chrome)
chk("위치 복원 열쇠에서 캐시버스터 _t 를 뺀다",
    "=== '_t') continue;" in chrome.replace("p.slice(0, eq)) ", "p.slice(0, eq)) "))

_inc = detail.find('include "_v5_partials/chrome.html"')
_use = detail.find("knkReloadKeepView();")
chk("project_detail.html 이 chrome.html 을 포함한다(함수가 정의된다)", _inc >= 0)
chk("공용 함수 정의(include)가 쓰는 자리보다 앞에 온다", 0 <= _inc < _use,
    "include=%d use=%d" % (_inc, _use))

# ════════════════════════════════════════════════════════════════════
sec("§2. 진짜 JS 실행 — chrome.html 원문을 node 로 돌린다")
# ════════════════════════════════════════════════════════════════════
js_norm = brace_block(chrome, r"function normSearch\(s\)\s*")
js_reload = brace_block(chrome, r"window\.knkReloadKeepView\s*=\s*function\(\)\s*")
chk("normSearch 원문 추출(%d자)" % len(js_norm), "keep.sort()" in js_norm)
chk("knkReloadKeepView 원문 추출(%d자)" % len(js_reload), "URLSearchParams" in js_reload)

PROBE_T = """
'use strict';
var __out = {};
var location = { pathname: '/project/8', search: '', href: '', hash: '',
                 reload: function(){ location.href = '(reload)'; } };
globalThis.window = {};
__NORMSEARCH__
__RELOAD__;
/* 위치 복원 열쇠 — chrome.html 과 같은 규칙 */
function key(){ return 'knkpos:' + location.pathname + normSearch(location.search); }

function go(search){ location.search = search; location.href = ''; window.knkReloadKeepView(); return location.href; }

__out.norm_drop_t   = normSearch('?so=T-260909-2&_t=1758000000000');
__out.norm_same_1   = (function(){ location.search='?so=T-260909-2';                  return key(); })();
__out.norm_same_2   = (function(){ location.search='?so=T-260909-2&_t=1758000000001'; return key(); })();
__out.norm_same_3   = (function(){ location.search='?_t=1758000000002&so=T-260909-2'; return key(); })();
__out.norm_only_t   = (function(){ location.search='?_t=9';                           return key(); })();
__out.norm_no_q     = (function(){ location.search='';                                return key(); })();
__out.keep_so       = go('?so=T-260909-2');
__out.keep_empty    = go('');
__out.keep_existing = go('?so=T-260909-2&_t=1111111111111');
__out.keep_korean   = go('?so=%ED%8A%B9%EC%A1%B0-1&tab=%EC%88%98%EC%A3%BC');
__out.keep_multi    = go('?so=T-1&biz=T&period=');
__out.twice_a       = go('?so=T-260909-2');
__out.twice_b       = go(__out.twice_a.split('?')[1] ? '?' + __out.twice_a.split('?')[1] : '');
/* URLSearchParams 가 없는 낡은 브라우저 → 폴백으로 주소를 안 버려야 한다 */
var _USP = globalThis.URLSearchParams; delete globalThis.URLSearchParams;
try { __out.fallback = go('?so=T-260909-2'); } finally { globalThis.URLSearchParams = _USP; }
console.log(JSON.stringify(__out));
"""
# 주소에 %ED.. 같은 글자가 있어 % 서식 대신 자리 표시를 바꿔 끼운다
PROBE = PROBE_T.replace("__NORMSEARCH__", js_norm).replace("__RELOAD__", js_reload)

tmpd = tempfile.mkdtemp(prefix="z1104_")
jsf = os.path.join(tmpd, "probe.js")
io.open(jsf, "w", encoding="utf-8", newline="\n").write(PROBE)
try:
    raw = subprocess.check_output(["node", jsf], stderr=subprocess.STDOUT).decode("utf-8", "replace")
    R = json.loads(raw.strip().splitlines()[-1])
    node_ok = True
except Exception as e:  # node 가 없으면 §2 는 건너뛴다(시험 자체가 죽지 않게)
    print("  ⚠ node 실행 불가 — §2 건너뜀: %s" % e)
    R, node_ok = {}, False

if node_ok:
    chk("열쇠에서 _t 가 빠진다  ?so=..&_t=.. → ?so=..",
        R["norm_drop_t"] == "?so=T-260909-2", R["norm_drop_t"])
    chk("⭐저장 전과 저장 후의 '화면 위치 열쇠'가 같다(맨 위로 안 올라감)",
        R["norm_same_1"] == R["norm_same_2"] == R["norm_same_3"],
        "%s / %s / %s" % (R["norm_same_1"], R["norm_same_2"], R["norm_same_3"]))
    chk("_t 뿐이면 조건 없는 화면과 같은 열쇠",
        R["norm_only_t"] == R["norm_no_q"], "%s vs %s" % (R["norm_only_t"], R["norm_no_q"]))
    chk("⭐보던 수주(?so=)가 살아 있다",
        "so=T-260909-2" in R["keep_so"], R["keep_so"])
    chk("캐시버스터 _t 는 새로 붙는다",
        re.search(r"[?&]_t=\d{10,}", R["keep_so"]) is not None, R["keep_so"])
    chk("경로는 그대로", R["keep_so"].startswith("/project/8?"), R["keep_so"])
    chk("조건이 없던 화면은 _t 만 붙는다",
        re.match(r"^/project/8\?_t=\d+$", R["keep_empty"]) is not None, R["keep_empty"])
    chk("_t 가 이미 있으면 갈아끼운다(쌓이지 않음)",
        R["keep_existing"].count("_t=") == 1 and "1111111111111" not in R["keep_existing"],
        R["keep_existing"])
    chk("한글 조건도 그대로 유지",
        "%ED%8A%B9%EC%A1%B0-1" in R["keep_korean"] and "tab=" in R["keep_korean"],
        R["keep_korean"])
    chk("조건이 여러 개여도 전부 유지",
        "so=T-1" in R["keep_multi"] and "biz=T" in R["keep_multi"], R["keep_multi"])
    chk("두 번 연속 저장해도 조건이 살아 있다(_t 는 1개)",
        "so=T-260909-2" in R["twice_b"] and R["twice_b"].count("_t=") == 1, R["twice_b"])
    chk("URLSearchParams 없는 브라우저 → 폴백도 주소를 안 버린다",
        R["fallback"] == "(reload)", R["fallback"])

# ════════════════════════════════════════════════════════════════════
sec("§3. 화면 재현 — project_detail.html 의 카드 선택 Jinja 원문으로")
# ════════════════════════════════════════════════════════════════════
try:
    from jinja2 import Environment
    _m = re.search(r"\{%\s*set _focus = .*?\{%\s*endif\s*%\}", detail, re.S)
    assert _m, "카드 선택 Jinja 원문을 못 찾음"
    JINJA = _m.group(0) + "{{ _ord[0].order_no }}"
    env = Environment()
    tpl = env.from_string(JINJA)

    class O(dict):
        __getattr__ = dict.get

    # 011T2606 PBA 실제 화면(신고 사진) 그대로 — 발주일 내림차순(최신 먼저)
    orders = [O(id=91, order_no="T-260909-2"), O(id=77, order_no="T-260716-1"),
              O(id=61, order_no="T-260701-3"), O(id=42, order_no="T-260615-1")]

    def main_card(url_query):
        so = ""
        for kv in url_query.lstrip("?").split("&"):
            if kv.startswith("so="):
                so = kv[3:]
        # {% set %} 줄이 남기는 빈 줄은 화면에 안 보이는 공백이다 — 카드 순서만 본다
        return tpl.render(project_orders=orders, focus_so=so).strip()

    chk("1번 화면 — ?so=T-260909-2 → 메인 카드 T-260909-2",
        main_card("?so=T-260909-2") == "T-260909-2", main_card("?so=T-260909-2"))
    chk("2번 화면 — 조건 없음 → 메인 카드는 최초 수주 T-260615-1",
        main_card("") == "T-260615-1", main_card(""))
    chk("\U0001F534신고 재현 — 옛 새로고침(?_t= 만) → T-260615-1 로 튄다",
        main_card("?_t=1758000000000") == "T-260615-1", main_card("?_t=1758000000000"))
    chk("⭐수리 확인 — 새 새로고침(?so=..&_t=..) → T-260909-2 그대로",
        main_card("?so=T-260909-2&_t=1758000000000") == "T-260909-2",
        main_card("?so=T-260909-2&_t=1758000000000"))
    if node_ok:
        chk("⭐끝에서 끝까지 — 1번 화면 저장 → 다시 1번 화면",
            main_card("?" + R["keep_so"].split("?", 1)[1]) == "T-260909-2",
            main_card("?" + R["keep_so"].split("?", 1)[1]))
except ImportError:
    print("  ⚠ jinja2 없음 — §3 건너뜀")

# ════════════════════════════════════════════════════════════════════
sec("§4. 배포 전 검사기 역시험 — 어긴 코드를 정말 잡는가")
# ════════════════════════════════════════════════════════════════════
sys.path.insert(0, os.path.join(ROOT, "deploy"))
try:
    import check_standards as CS
except Exception as e:
    print("  ⚠ 검사기 import 실패 — §4 건너뜀: %s" % e)
    CS = None

if CS is not None:
    def run_on(body):
        p = os.path.join(tmpd, "t.html")
        io.open(p, "w", encoding="utf-8", newline="").write("<script>\n%s\n</script>\n" % body)
        return CS.check_reload_keep_view([p])

    BAD = [
        ("① 신고된 그 줄",
         "window.location.href = window.location.pathname + '?_t=' + Date.now();"),
        ("② window 없이",
         "location.href = location.pathname + '?_t=' + Date.now();"),
        ("③ 쌍따옴표",
         'location.href = window.location.pathname + "?_t=" + Date.now();'),
        ("④ 조건을 새로 지어 붙임",
         "location.href = location.pathname + '?tab=1';"),
        ("⑤ assign()",
         "location.assign(location.pathname + '?_t=' + Date.now());"),
        ("⑥ replace()",
         "window.location.replace(window.location.pathname + '?_t=' + Date.now());"),
        ("⑦ 줄바꿈이 끼어도",
         "window.location.href =\n    window.location.pathname\n      + '?_t=' + Date.now();"),
        ("⑧ 공백 변형",
         "location . href = location . pathname + '?_t=' + Date.now();"),
        ("⑨ 조건문 안 한 줄",
         "if (j.ok) { window.location.href = window.location.pathname + '?_t=' + Date.now(); }"),
        ("⑩ async 블록 안",
         "async function f(){ await g(); window.location.href = window.location.pathname + '?_t=' + Date.now(); }"),
    ]
    for nm, body in BAD:
        hits = run_on(body)
        chk("어긴 코드를 잡는다 — %s" % nm, len(hits) == 1, "%d건" % len(hits))

    GOOD = [
        ("공용 함수 호출", "knkReloadKeepView();"),
        ("그냥 다시 읽기", "location.reload();"),
        ("공용 함수 정의 자신", "location.href = location.pathname + (q ? ('?' + q) : '');"),
        ("주석 줄", "// location.href = location.pathname + '?_t=' + Date.now();"),
        ("주석 블록 줄", "  * location.href = location.pathname + '?_t=' + Date.now();"),
        ("다른 주소로 보내기", "location.href = '/projects';"),
        ("조건을 유지한 이동", "location.href = location.pathname + location.search;"),
    ]
    for nm, body in GOOD:
        hits = run_on(body)
        chk("멀쩡한 코드는 안 잡는다 — %s" % nm, len(hits) == 0, "%d건" % len(hits))

    # Jinja 주석 안은 실행되지 않는다
    p = os.path.join(tmpd, "j.html")
    io.open(p, "w", encoding="utf-8", newline="").write(
        "{# location.href = location.pathname + '?_t=' + Date.now(); #}\n<script>var a=1;</script>\n")
    chk("Jinja 주석 안은 안 잡는다", len(CS.check_reload_keep_view([p])) == 0)

    # 실제 화면 파일 — 고친 뒤에는 0건
    chk("⭐project_detail.html — 위반 0건", len(CS.check_reload_keep_view([DETAIL])) == 0)
    chk("⭐chrome.html(공용 함수 본체) — 위반 0건",
        len(CS.check_reload_keep_view([CHROME])) == 0)

    # 잡았을 때 알려주는 줄 번호가 맞는가
    p = os.path.join(tmpd, "n.html")
    io.open(p, "w", encoding="utf-8", newline="").write(
        "<script>\nvar a=1;\nvar b=2;\nwindow.location.href = window.location.pathname + '?_t=' + Date.now();\n</script>\n")
    h = CS.check_reload_keep_view([p])
    chk("알려주는 줄 번호가 정확하다(4행)", h and h[0][1] == 4, h[0][1] if h else "못 잡음")

# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("결과: %d/%d 통과%s" % (OK, OK + FAIL, "" if not FAIL else "  — ❌ 실패 %d" % FAIL))
print("=" * 72)
sys.exit(1 if FAIL else 0)
