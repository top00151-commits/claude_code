# -*- coding: utf-8 -*-
"""HAIST WORKS 표준 규정 자동 검사 — 배포 전 필수 (v5H226z1029 · 대표 지시)

왜 만들었나
  규정을 문서에만 적어두면 지켜지지 않는다. 실제로 다음 사고가 났다:
    · z1028 — 클라 JS 문법 오류가 나면 **화면 전체가 죽는데** WORKS엔 검사기가 없었다
              (메신저는 deploy/check_js_syntax.py 로 막고 있었다).
    · z1026 — 줄 강조에 `background: ... !important` 를 쓰면 원가 열 색이 지워진다.
    · z1009 — 표 높이에 `100vh` 매직넘버를 쓰면 노트북에서 표가 1~2줄만 보인다.

쓰는 법
    python deploy/check_standards.py            # 전체 검사
    python deploy/check_standards.py --changed  # 지금 git 에 잡힌 변경 파일만
    종료코드 0 = 통과 / 1 = 위반 있음

⚠이 검사기는 '새로 들어온 위반'을 막는 용도다. 기존 코드의 오래된 위반은
   ALLOW(면제 목록)에 근거와 함께 적어 통과시킨다 — 지금 잘 도는 화면을
   무리해서 바꾸지 않는다는 대표 방침([[feedback_no_rework_working]]).
"""
import io
import os
import re
import subprocess
import sys

# z1044: 윈도 콘솔 기본 코드페이지(cp949)에서 '—' 같은 글자에 UnicodeEncodeError 로 **검사기 자체가 죽었다**
#   (trace_concept.py 와 같은 결함 — 검사기가 죽으면 검사를 안 한 것과 같다).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join(ROOT, "app", "templates")
CSS = os.path.join(ROOT, "static", "css")

# ── 면제(BASELINE): 규정을 만들기 **전부터 있던** 것들. 지금 잘 도는 화면을 무리해서
#    바꾸지 않는다는 대표 방침에 따라 통과시키되, **개수를 적어두고 늘어나면 잡는다.**
#    → 기존 것은 넘어가고 **새로 생기는 위반은 반드시 걸린다.**
#    그 화면을 다음에 손볼 때 knk-row-flag / data-knk-fill 로 옮기고 숫자를 줄일 것.
BASELINE = {
    # 셸 스킨의 실승자(z48~). !important 로 덮어쓰는 구조 자체가 전제라 전량 면제.
    "design_quiet_v3.html": {"important": None, "vh": None},
    "design_v2.html": {"important": None, "vh": None},
    "print.css": {"important": None, "vh": None},

    # ── 표 줄/셀 강조 (knk-row-flag 로 옮길 후보) ──
    #    전부 '상태 표시'라 동작은 정상. 해당 화면 개편 시 덧칠 방식으로 통일.
    "sales_shipments_receipts.html": {"important": 1},   # sr-hl 행 하이라이트
    "stock_safety.html": {"important": 2},               # 안전재고 미달 행(경고/위험) — 의미상 danger
    "schedule_board.css": {"important": 5},              # 선택행·포커스행·고객사 미매칭·세금계산서 불일치/정상

    # ── 100vh 매직넘버 ──
    #    knk_inputs.html = 공용 기본값(.tbl-wrap.tbl-sticky/.list-scroll). z1009 는 opt-in 규정이라
    #    기존 ~35개 목록은 **의도적으로 미전환**. 공용 기본값을 건드리면 전 화면이 흔들린다.
    "knk_inputs.html": {"vh": 4},
    #    아래 3개는 z1009 에서 data-knk-fill 로 전환 완료된 화면인데 **옛 CSS 값이 남아 있다.**
    #    실제로는 JS 가 인라인 max-height 를 넣어 이기므로 동작은 정상이고,
    #    JS 가 못 뜨는 상황의 안전망 역할도 한다 → 지금은 그대로 둔다(정리 시 함께 제거).
    "contacts_list.html": {"vh": 1},
    "customers_list.html": {"vh": 1},
    "export_prep_detail.html": {"vh": 1},
}


def _rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


# 안 쓰는 옛 파일·백업은 검사 대상이 아니다(고칠 이유가 없고, 잡아봐야 소음만 된다).
SKIP_DIRS = ("__pycache__", "_legacy_base", "_v4_backup", "_legacy", "backup")


def _walk(base, exts):
    for dp, _dn, fn in os.walk(base):
        low = dp.replace("\\", "/").lower()
        if any(("/" + s) in low or low.endswith(s) for s in SKIP_DIRS):
            continue
        for f in fn:
            if f.lower().endswith(exts):
                yield os.path.join(dp, f)


def _read(p):
    try:
        return io.open(p, encoding="utf-8").read()
    except Exception:
        return ""


def _strip_jinja(s):
    """Jinja 문법 제거 → 순수 JS. {{ }} 는 값 자리이므로 안전한 리터럴 0 으로."""
    s = re.sub(r"\{\{-?\s*.*?\s*-?\}\}", "0", s, flags=re.S)
    s = re.sub(r"\{%-?.*?-?%\}", "", s, flags=re.S)
    s = re.sub(r"\{#.*?#\}", "", s, flags=re.S)
    return s


def check_js(files):
    """§11 인라인 <script> 문법 — 오류 하나가 화면 전체를 죽인다."""
    try:
        import esprima
    except ImportError:
        return [("(건너뜀)", 0, "esprima 미설치 — `pip install esprima` 후 다시 검사하세요")], 0
    bad, n = [], 0
    for p in files:
        if not p.endswith(".html"):
            continue
        src = _read(p)
        for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", src, re.S | re.I):
            body = m.group(1)
            if not body.strip():
                continue
            n += 1
            ln = src[: m.start()].count("\n") + 1
            try:
                esprima.parseScript(_strip_jinja(body))
            except Exception as e:
                bad.append((_rel(p), ln, str(e).split("\n")[0]))
    return bad, n


def _is_comment(line):
    t = line.strip()
    return t.startswith(("/*", "*", "//", "#", "{#")) or "z1009" in t or "z1026" in t


def check_important(files):
    """§8 '표의 줄/셀 배경'을 !important 로 덮는 것만 잡는다.

    ⚠전부 잡으면 안 된다 — hover 강조·드래그 상태·인쇄·셸 스킨은 !important 가 정당하고
      실제로 114건이 나와 검사기가 소음이 된다. 문제가 되는 건
      **표의 줄/셀을 상시 배경으로 덮어 기존 열 색(원가열 #fff7ed 등)을 지우는 경우**뿐이다.
    """
    bad = []
    pat = re.compile(r"background[^;:]*:[^;]*!important", re.I)
    # 선택자에 tr/td/th 가 있고, 일시적 상태(hover/active/drag/선택)나 인쇄가 아닌 것
    sel_tbl = re.compile(r"(^|[\s,.#>])(tr|td|th|tbody)([\s.:,{>]|$)", re.I)
    transient = re.compile(r":hover|:active|:focus|\.drag|\.selected|\.active|@media\s+print", re.I)
    for p in files:
        name = os.path.basename(p)
        if BASELINE.get(name, {}).get("important", 0) is None:
            continue
        src = _read(p)
        in_print = False
        for i, line in enumerate(src.splitlines(), 1):
            low = line.lower()
            if "@media" in low and "print" in low:
                in_print = True
            if in_print and "}" in line and "{" not in line:
                in_print = False
            if in_print or _is_comment(line):
                continue
            if not pat.search(line) or "knk-row-flag" in line:
                continue
            sel = line.split("{")[0]
            if sel_tbl.search(sel) and not transient.search(line):
                bad.append((_rel(p), i, line.strip()[:100]))
    return bad


def check_vh(files):
    """§5 '스크롤 표 높이'의 100vh 매직넘버만 잡는다.

    ⚠셸 레이아웃(`.main{height:calc(100vh - topbar)}`)은 정상이고 필요하다.
      z1009 도 opt-in 규정이라 기존 목록 표는 그대로 두기로 했다.
      → **새로 만드는 스크롤 컨테이너의 max-height 매직넘버**만 대상.
    """
    bad = []
    pat = re.compile(r"max-height\s*:\s*calc\([^)]*100vh", re.I)
    scroll_sel = re.compile(r"tbl-wrap|list-scroll|-scroll|scrollbox|tbody|table|\.wrap", re.I)
    for p in files:
        name = os.path.basename(p)
        if BASELINE.get(name, {}).get("vh", 0) is None:
            continue
        src = _read(p)
        for i, line in enumerate(src.splitlines(), 1):
            if _is_comment(line) or not pat.search(line):
                continue
            if scroll_sel.search(line.split("{")[0]):
                bad.append((_rel(p), i, line.strip()[:100]))
    return bad


def collect(changed_only):
    if changed_only:
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "HEAD"], cwd=ROOT
            ).decode("utf-8", "replace")
            files = []
            for ln in out.splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                ap = os.path.join(ROOT, os.path.basename(ROOT).join(["", ""]) or "", ln)
                # 모노레포 기준 경로 → 이 앱 기준으로 보정
                cand = os.path.join(ROOT, ln.split("01_HAIST_WORKS/")[-1])
                if os.path.exists(cand):
                    files.append(cand)
                elif os.path.exists(ap):
                    files.append(ap)
            if files:
                return files
        except Exception:
            pass
    files = list(_walk(TPL, (".html",)))
    if os.path.isdir(CSS):
        files += list(_walk(CSS, (".css",)))
    return files


def split_baseline(hits, rule):
    """BASELINE 개수 이내면 '기존(면제)', 넘치면 '새 위반'으로 가른다."""
    by_file = {}
    for f, l, m in hits:
        by_file.setdefault(os.path.basename(f), []).append((f, l, m))
    new, old = [], 0
    for name, rows in by_file.items():
        keep = BASELINE.get(name, {}).get(rule, 0) or 0
        old += min(len(rows), keep)
        if len(rows) > keep:
            new.extend(rows[keep:])
    return new, old


def main():
    changed_only = "--changed" in sys.argv
    files = collect(changed_only)
    print("=" * 72)
    print("HAIST WORKS 표준 규정 검사 — 대상 %d개 파일%s" % (len(files), " (변경분만)" if changed_only else ""))
    print("=" * 72)

    fail = 0

    js_bad, js_n = check_js(files)
    if js_bad and js_bad[0][0] == "(건너뜀)":
        print("  ⚠ JS 문법      : %s" % js_bad[0][2])
    elif js_bad:
        fail += len(js_bad)
        print("  ❌ JS 문법      : %d건 (검사 %d개 블록)" % (len(js_bad), js_n))
        for f, l, m in js_bad:
            print("       %s:%s  %s" % (f, l, m))
    else:
        print("  ✅ JS 문법      : 통과 (인라인 script %d개)" % js_n)

    imp_new, imp_old = split_baseline(check_important(files), "important")
    if imp_new:
        fail += len(imp_new)
        print("  ❌ 표 줄/셀 background !important : 새로 %d건 → knk-row-flag(덧칠) 사용" % len(imp_new))
        for f, l, m in imp_new[:20]:
            print("       %s:%s  %s" % (f, l, m))
    else:
        print("  ✅ 표 줄/셀 background !important : 새 위반 없음 (기존 면제 %d건)" % imp_old)

    vh_new, vh_old = split_baseline(check_vh(files), "vh")
    if vh_new:
        fail += len(vh_new)
        print("  ❌ 스크롤표 100vh 매직넘버 : 새로 %d건 → data-knk-fill 사용" % len(vh_new))
        for f, l, m in vh_new[:20]:
            print("       %s:%s  %s" % (f, l, m))
    else:
        print("  ✅ 스크롤표 100vh 매직넘버 : 새 위반 없음 (기존 면제 %d건)" % vh_old)

    print("=" * 72)
    if fail:
        print("결과: 위반 %d건 — 고치거나, 정당한 사유면 ALLOW 에 사유와 함께 추가하세요." % fail)
        return 1
    print("결과: 전부 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
