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
    # ── 수량칸 소수 허용(z1048) ──
    #    _legacy_po_form_v4.html = **안 쓰이는 옛 발주 폼**(살아있는 po_form.html 이 따로 있고,
    #    서버 어디서도 이 이름으로 렌더하지 않음 — 실측 확인). 파일명이 `_legacy_` 로 시작할 뿐
    #    디렉터리가 아니라 SKIP_DIRS 에 안 걸린다. 지우는 건 별건이라 면제만.
    "_legacy_po_form_v4.html": {"qty": 2, "important": None, "vh": None},
    #    z1045 에서 정규식을 `-wrap` 까지 넓히자 새로 드러난 1건.
    #    `.so-card.so-fullscreen .so-units-wrapper` = **전체화면(풀스크린) 전용** 규칙이라
    #    100vh 가 맞는 값이다(화면 전체를 쓰는 상태). z1009 예외 '사용자 높이조절'에 해당 → 면제.
    "project_detail.css": {"vh": 1},
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
    # z1045: `\.wrap` 는 **`.hsd-wrap` 을 못 잡았다**(마침표 바로 뒤 wrap 만 매칭) —
    #   HS 사전의 `max-height:calc(100vh - 330px)` 가 이 구멍으로 규정 시행 후에도 그대로 남아 있었다.
    #   → `-wrap` 도 잡도록 넓힘. 검사기가 못 잡으면 규정은 문서에만 있는 것과 같다.
    scroll_sel = re.compile(r"tbl-wrap|list-scroll|-scroll|scrollbox|tbody|table|[.\-]wrap", re.I)
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


def check_qty(files):
    """§수량 = 정수(z1048 · 대표 지시). 수량 입력칸이 소수를 허용하면 잡는다.

    안지연 프로가 **두 번** 신고했다(*"또 0.01 단위로 변하네요"*) — 한 곳씩 고치니
    새 화면으로 계속 번졌다(전수 조사에서 26곳). 공용 처리기(`_v5_partials/knk_qty.html`)가
    런타임에 고쳐 주지만, **소스에 남아 있으면 다음 사람이 그대로 복사한다** → 여기서 막는다.

    ⚠판별 정규식에 단어경계(`[^a-z]`)를 쓰지 말 것 — `re.I` 때문에 대문자가 경계에서 빠져
      **`qtyInput` 같은 camelCase 를 놓친다**(실제로 재고 조정 화면이 뚫렸다).
    ⛔`min` 이 소수면 step=1 이어도 허용값이 0.01·1.01·2.01 이 된다 → 같이 잡는다.
    """
    bad = []
    namey = re.compile(r"qty|quantity|수량", re.I)
    not_qty = re.compile(
        r"price|amount|cost|rate|pct|percent|margin|weight|kg|cbm|fx|단가|금액|환율|중량|비율", re.I)
    tag_re = re.compile(r"<input\b[^>]*>", re.I)
    frac = re.compile(r'step\s*=\s*["\'](0?\.\d+|any)["\']|(?:\bmin|\bmax)\s*=\s*["\']\d*\.\d+["\']', re.I)
    for p in files:
        if not p.endswith(".html"):
            continue
        src = _read(p)
        for m in tag_re.finditer(src):
            tag = m.group(0)
            low = tag.lower()
            if 'type="number"' not in low and "type='number'" not in low:
                continue
            if "data-knk-decimal" in low:      # 소수가 정당하다고 표시한 칸은 면제
                continue
            attrs = " ".join(re.findall(r'(?:name|id|class|data-k)\s*=\s*["\']([^"\']*)', tag))
            if not namey.search(attrs) or not_qty.search(attrs):
                continue
            if frac.search(tag):
                ln = src[: m.start()].count("\n") + 1
                bad.append((_rel(p), ln, tag.strip()[:100]))
    return bad


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

    qty_new, qty_old = split_baseline(check_qty(files), "qty")
    if qty_new:
        fail += len(qty_new)
        print("  ❌ 수량칸 소수 허용 : 새로 %d건 → step=\"1\" (min/max 도 정수) · 소수가 맞으면 data-knk-decimal" % len(qty_new))
        for f, l, m in qty_new[:20]:
            print("       %s:%s  %s" % (f, l, m))
    else:
        print("  ✅ 수량칸 소수 허용 : 새 위반 없음 (기존 면제 %d건)" % qty_old)

    print("=" * 72)
    if fail:
        print("결과: 위반 %d건 — 고치거나, 정당한 사유면 ALLOW 에 사유와 함께 추가하세요." % fail)
        return 1
    print("결과: 전부 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
