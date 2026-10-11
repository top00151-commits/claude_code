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

    # ── 환산 없는 금액 합산 (z1097 · 2026-09-10) ──
    #    발주(PO) 목록 합계 = **세션05(자재구매) 소유 파일**(업무분장 V2). 세션01이 대신 고치지 않는다.
    #    위치·재현 결과를 세션05에 전달했다. 발주에 외화가 실제로 섞여 있는지는 **실측하지 않았다**
    #    (매출쪽 orders 는 실측했으나 purchase_orders 는 세션05 담당이라 열지 않았다).
    #    ⚠ 이 숫자를 늘리지 말 것 — 늘리면 새 위반으로 잡힌다. 세션05가 고치면 0 으로 내릴 것.
    # 2026-09-10 세션05가 고침 — 발주 목록 합계를 통화별로 나눠 그린다(_ccy_breakdown).
    "po_list.html": {"ccy": 0},

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


def check_amt_decimal(files):
    """§금액 = 소수 보존(z1095 · 이새롬 프로 신고). 금액칸 타이핑 포맷이 소수점을 지우면 잡는다.

    통화 표준(z751 대표 지시)은 **KRW 정수 · 외화 소수 2자리**다. 그런데 금액 입력칸의
    콤마 재포맷을 `value.replace(/[^0-9]/g,'')` 로 쓰면 숫자만 남아 **'.' 이 키 입력 즉시 지워진다**.
    못 넣는 것으로 끝나지 않는다 — **기존 값을 고치면 10배가 된다**(1,315.5 → 13,155).

    z986 에서 작업일정표를 고쳤는데 프로젝트 상세·등록폼이 빠져 **그대로 재발**했다(z1095).
    수량칸(check_qty)과 같은 번짐이라 같은 방식으로 소스에서 막는다.
    금액칸은 공용 `_v5_partials/knk_amt.html` 의 knkFmtAmtTyping/knkAttachAmt 를 쓸 것.

    ⚠날짜(YYYYMMDD)·전화번호 정규화에는 `[^0-9]` 가 정당하다 → **주변 ±3줄에 금액 신호가
      있을 때만** 위반으로 본다(변수명이 `pa` 처럼 짧아 같은 줄만 봐서는 못 잡는다 — 실제 사례).
    """
    bad = []
    strip_re = re.compile(r"replace\(\s*/\[\^0-9\]/g")
    amt_sig = re.compile(
        r"knk-money|pi-price|ti-pa|ux-money|price|amount|\bamt\b|금액|단가|money", re.I)
    # 주석은 실행되지 않으므로 검사 대상이 아니다(이 규칙을 설명하는 주석 자체가 잡혔다).
    #   Jinja 주석은 줄바꿈만 남기고 지워 **줄 번호를 유지**한다.
    jinja_cmt = re.compile(r"\{#.*?#\}", re.S)
    for p in files:
        if not p.endswith(".html"):
            continue
        src = jinja_cmt.sub(lambda m: "\n" * m.group(0).count("\n"), _read(p))
        lines = src.splitlines()
        for i, ln in enumerate(lines):
            if not strip_re.search(ln):
                continue
            if ln.lstrip().startswith(("//", "*", "/*")):     # JS 주석 줄
                continue
            lo, hi = max(0, i - 3), min(len(lines), i + 4)
            window = "\n".join(lines[lo:hi])
            if amt_sig.search(window):
                bad.append((p, i + 1, ln.strip()[:110]))
    return bad


def _blank_keep_lines(m):
    """주석을 지우되 줄바꿈은 남긴다 — 잡았을 때 알려주는 줄 번호가 어긋나지 않게."""
    return "\n" * m.group(0).count("\n")


def check_ccy_sum(files):
    """§통화 = 환산 없는 금액 합산 금지 (z1097 · 대표 신고 2026-09-10).

    화면에 **원화와 달러를 환산 없이 그대로 더한 값**이 떴다.
    프로젝트 005M2511 'BIM LINE' 아래쪽 「수주번호 합계」 =
    $83,882.73 + ₩1,720,000 → **$1,803,882.73**. 운영 실측 25건 · 오차 합계 약 41억원.
    부풀림은 1건뿐이고 나머지 24건은 **작게** 나와 아무도 눈치채지 못했다.

    ⭐ 왜 검사기까지 만드는가 — 같은 화면 **위쪽** '확정 매출' KPI 는 이미 통화별로
       나눠 그리고 있었다. 아래쪽만 규칙에서 빠진 것이다. 매출 대시보드도
       2026-05-04(v5H123)에 같은 결함을 고쳤는데 그때도 그 화면만 고쳤다.
       **한 곳만 고치면 반드시 다른 곳에서 되살아난다**(대표규정 「⛔한 곳만 고치고 완료 금지」).

    올바른 방법: 서버에서 `_ccy_breakdown(...)` 으로 통화별 합계 + 월 기준환율 원화 합계를
    만들고, 화면은 공용 매크로 `_v5_partials/knk_ccy_total.html` 의 `ccy_total()` 로 그린다.

    잡는 것 두 가지
      ① `|sum(attribute='금액칸')`
      ② `{% set ns.x = ns.x + (... 금액칸 ...) %}` 꼴 누적
    ⚠ 수량·건수·공수(qty·cnt·hours·duration)는 통화와 무관하므로 잡지 않는다.
    ⚠ 주석은 실행되지 않으므로 검사 대상이 아니다(이 규칙을 설명하는 주석이 잡히면 안 된다).
      Jinja 주석은 줄바꿈만 남기고 지워 **줄 번호를 유지**한다.
    """
    MONEY = (r"(?:total_amount|order_amount|total_so_amount|sum_amount|"
             r"paid_total|unit_price|total_price|amount|price|amt)")
    sum_re = re.compile(r"\|\s*sum\s*\(\s*attribute\s*=\s*['\"]" + MONEY + r"['\"]")
    acc_re = re.compile(r"\{%\s*set\s+(\w+)\.(\w+)\s*=\s*\1\.\2\s*\+[^%]*" + MONEY)
    jinja_cmt = re.compile(r"\{#.*?#\}", re.S)
    bad = []
    for p in files:
        if not p.endswith(".html"):
            continue
        src = jinja_cmt.sub(_blank_keep_lines, _read(p))
        for i, ln in enumerate(src.splitlines()):
            if sum_re.search(ln) or acc_re.search(ln):
                bad.append((p, i + 1, ln.strip()[:110]))
    return bad


def check_project_amount_sum(_files=None):
    """§프로젝트 수주금액 저장 = 공용 함수로만 (z1097b · 대표 지시 2026-09-10).

    z1097 에서 **화면**의 통화 무시 합산을 고쳤는데, `projects.order_amount` 를 채우는
    자리가 서버 코드에 **14곳** 남아 있었다. 전부 `SELECT SUM(total_amount) FROM orders
    WHERE project_id=?` — 통화를 안 본다. 그대로 두면 수주를 고치거나 프로젝트 상세를
    열 때마다 **저장값이 다시 오염된다.**
    z1093(매 기동 팀 시드)·z1094(기동 cascade 백필)와 **똑같은 '되살아남' 함정**이다.
    ⭐ 데이터만 고치고 끝내면 반드시 되돌아온다.

    올바른 방법: `_recalc_project_amount(c, pid, ...)` 로 값을 구하고
                 `_apply_project_amount(c, pid, ...)` 로 저장한다.

    잡는 것 (app/main.py 만 검사 — 화면이 아니라 서버 코드다)
      ① `UPDATE projects SET order_amount` 직접 실행 — 공용 함수 안이 아닌 곳
      ② `SUM(total_amount) FROM orders WHERE project_id` 직접 조회

    면제: 값이 이미 `_recalc_project_amount` 에서 온 조건부 저장(자가치유·expected_amount
    동시 저장)은 같은 줄이나 바로 윗줄에 **`ccy-ok`** 주석을 달아 통과시킨다.
    ⛔ 이 표식을 '검사를 지나가려고' 붙이지 말 것 — 값의 출처를 주석에 적을 것.
    """
    src_path = os.path.join(ROOT, "app", "main.py")
    if not os.path.exists(src_path):
        return []
    body = _read(src_path)
    lines = body.split("\n")

    # 공용 함수 두 개의 몸통 줄 범위는 면제한다(거기서는 당연히 써야 한다).
    allow = set()
    for i, ln in enumerate(lines):
        if ln.startswith("def _recalc_project_amount(") or ln.startswith("def _apply_project_amount("):
            j = i + 1
            while j < len(lines) and (lines[j].startswith((" ", "\t")) or not lines[j].strip()):
                allow.add(j)
                j += 1
    upd = re.compile(r"UPDATE\s+projects\s+SET\s+order_amount")
    sel = re.compile(r"SUM\(\s*total_amount\s*\)\s*FROM\s+orders", re.I)
    proj = re.compile(r"project_id\s*=\s*\?")
    bad = []
    for i, ln in enumerate(lines):
        if i in allow:
            continue
        st = ln.strip()
        if st.startswith("#"):
            continue
        _near = ln + "\n" + (lines[i - 1] if i else "") + "\n" + (lines[i - 2] if i > 1 else "")
        if "ccy-ok" in _near:
            continue
        if upd.search(ln):
            bad.append((src_path, i + 1, st[:110]))
        elif sel.search(ln) and (proj.search(ln) or proj.search(lines[i + 1] if i + 1 < len(lines) else "")):
            bad.append((src_path, i + 1, st[:110]))
    return bad


def check_nas_quiet_schedulers(_files=None):
    """§NAS 백업 시간 = 매주 월요일 02:00~07:30(한국시간) 묶음 작업 금지 (z1101 · 2026-09-16).

    전산(최보현 상무이사) 확정 2026-09-15 16:05 — NAS 가 월요일 02:00 에 스냅샷 → 로컬 백업 →
    서버간 백업을 연쇄로 돌린다. 그동안 무거운 쓰기가 끼면 백업이 느려지고 중복이 생긴다.
    실측(2026-09-16): 04:10 명부 동기화가 **9/14(월) 04:10 에도 돌며 DB 사본 약 280MB 를 썼다.**
    고객 등급 재계산은 '기동 뒤 24시간마다'라 **재기동 시각을 따라 떠다니고**, 기동 직후에도 한 번 돈다.

    올바른 방법: 공용 판정 `_nas_quiet_wait_secs()` / `_nas_quiet_now()` 를 거친다
                 (이음 `10_KNK_Messenger/app.py` 와 같은 이름·같은 규칙).

    잡는 것 (app/main.py · 파이썬 구문 트리로 본다 — 주석·문자열에 적힌 이름은 인정하지 않는다)
      ① 판정 상수가 월요일·02:00·07:30 이 아니다 / 공용 판정이 없다 / 07:30 을 포함하도록 바뀌었다
      ② `Timer(` 로 스스로 예약하는 함수가 판정을 부르지 않는다(아래 면제 제외)
      ③ 판정을 부르긴 하지만 무거운 작업(등급 재계산·명부 동기화·DB 사본)보다 **뒤에서** 부른다
      ④ 명부 동기화 시각 계산 `_seconds_until_next_0410` 이 판정을 안 거친다
      ⑤ 앱 기동(`startup`) 중 등급 재계산이 판정 조건 밖에서 돈다

    면제 (사유를 여기 적는다 — 늘릴 땐 전산·대표 확인)
      · 평일 16:30 업무카드 알림 — 고정 시각이 금지 시간 밖
      · 메일 자동 가져오기 5분 — 가벼운 상시 수집 · 금지 대상인지 전산 확인 전 · 끄면 월요일 메일이 늦는다
    """
    import ast as _ast
    src_path = os.path.join(ROOT, "app", "main.py")
    if not os.path.exists(src_path):
        return []
    try:
        tree = _ast.parse(_read(src_path))
    except SyntaxError as e:
        return [(src_path, getattr(e, "lineno", 0) or 0, "main.py 구문 오류 — 검사 불가: %s" % e)]
    QN = {"_nas_quiet_wait_secs", "_nas_quiet_now"}
    PRED = QN | {"_seconds_until_next_0410"}
    HEAVY = {"refresh_all_customer_tiers", "_run_directory_autosync", "backup_db_file"}
    EXEMPT = {
        "_daily_reminder_tick": "평일 16:30 고정 — 금지 시간 밖",
        "_start_daily_reminder_scheduler": "평일 16:30 고정 — 금지 시간 밖",
        "_mail_fetch_tick": "메일 5분 상시 수집 — 전산 확인 전",
        "_start_mail_fetch_scheduler": "메일 5분 상시 수집 — 전산 확인 전",
    }
    bad = []

    def _name(call):
        f = call.func
        if isinstance(f, _ast.Name):
            return f.id
        if isinstance(f, _ast.Attribute):
            return f.attr
        return ""

    def _calls(node):
        return [x for x in _ast.walk(node) if isinstance(x, _ast.Call)]

    funcs, consts = {}, {}
    for n in tree.body:
        if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
            funcs[n.name] = n
        elif (isinstance(n, _ast.Assign) and len(n.targets) == 1
              and isinstance(n.targets[0], _ast.Name) and n.targets[0].id.startswith("NAS_QUIET_")):
            try:
                consts[n.targets[0].id] = (_ast.literal_eval(n.value), n.lineno)
            except Exception:
                consts[n.targets[0].id] = (None, n.lineno)

    # ① 상수·공용 판정·경계
    for k, v in (("NAS_QUIET_WEEKDAY", 0), ("NAS_QUIET_START", (2, 0)), ("NAS_QUIET_END", (7, 30))):
        got = consts.get(k)
        if not got:
            bad.append((src_path, 1, "① %s 가 없다 — 월요일 02:00~07:30 판정 상수 필수" % k))
        elif got[0] != v:
            bad.append((src_path, got[1], "① %s = %r — 전산 확정값 %r 과 다르다" % (k, got[0], v)))
    qw = funcs.get("_nas_quiet_wait_secs")
    if qw is None or "_nas_quiet_now" not in funcs:
        bad.append((src_path, 1, "① 공용 판정 _nas_quiet_wait_secs / _nas_quiet_now 가 없다"))
    elif not any(isinstance(x, _ast.Compare) and len(x.ops) == 2
                 and isinstance(x.ops[0], _ast.LtE) and isinstance(x.ops[1], _ast.Lt)
                 for x in _ast.walk(qw)):
        bad.append((src_path, qw.lineno, "① 경계는 `시작 <= 지금 < 끝` — 07:30 정각부터는 다시 돌아야 한다"))

    # ② ③ 스스로 예약하는 함수
    for name, fn in funcs.items():
        cs = _calls(fn)
        if not any(_name(c) == "Timer" for c in cs) or name in EXEMPT:
            continue
        pred_lines = [c.lineno for c in cs if _name(c) in PRED]
        if not pred_lines:
            bad.append((src_path, fn.lineno, "② %s — Timer 로 예약하는데 NAS 백업 시간 판정을 안 거친다" % name))
            continue
        heavy_lines = [c.lineno for c in cs if _name(c) in HEAVY]
        if heavy_lines and min(pred_lines) > min(heavy_lines):
            bad.append((src_path, min(heavy_lines), "③ %s — 판정보다 무거운 작업이 먼저 돈다" % name))

    # ④ 명부 동기화 시각 계산
    s0410 = funcs.get("_seconds_until_next_0410")
    if s0410 is not None and not any(_name(c) in QN for c in _calls(s0410)):
        bad.append((src_path, s0410.lineno,
                    "④ _seconds_until_next_0410 — 월요일 04:10(금지 시간 안)을 피하지 않는다"))

    # ⑤ 앱 기동 중 등급 재계산 — 판정 조건의 '돌아도 되는 쪽'에 있어야 한다
    st = funcs.get("startup")
    if st is not None:
        parents = {}
        for p in _ast.walk(st):
            for ch in _ast.iter_child_nodes(p):
                parents[ch] = p
        for c in _calls(st):
            if _name(c) != "refresh_all_customer_tiers":
                continue
            node, guarded = c, False
            while node in parents:
                par = parents[node]
                if isinstance(par, _ast.If) and any(_name(x) in QN for x in _calls(par.test)):
                    negated = isinstance(par.test, _ast.UnaryOp) and isinstance(par.test.op, _ast.Not)
                    in_else = any(node is x for x in par.orelse)
                    in_body = any(node is x for x in par.body)
                    if (in_else and not negated) or (in_body and negated):
                        guarded = True
                        break
                node = par
            if not guarded:
                bad.append((src_path, c.lineno,
                            "⑤ startup — 기동 직후 등급 재계산이 NAS 백업 시간 판정 밖에서 돈다"))
    return bad


def check_reload_keep_view(files):
    """§저장 후 새로고침 = 보던 화면 그대로 (z1104 · 이새롬 프로 신고 2026-09-16).

    신고 원문: "1번 화면에서 수정-저장 하면 2번 화면으로 넘어갑니다. 저장 후 저장된 화면으로 나와야 합니다."
    원인: 저장 뒤 새로고침이 `location.href = location.pathname + '?_t=' + Date.now()` 였다.
    `pathname` 만 쓰면 **지금 주소의 조건이 통째로 버려진다.** 프로젝트 상세는 `?so=<수주번호>` 로
    '보던 수주'를 메인(편집) 카드로 올리므로(z695), 저장만 하면 가장 오래된 수주(최초 수주) 카드로 튀었다.
    같은 이유로 매번 달라지는 `_t` 가 화면 위치 복원(z984b) 열쇠까지 어긋내 화면이 맨 위로 올라갔다.
    project_detail.html 한 곳이 아니라 **같은 줄이 8곳**이었다 — 한 곳만 고치면 나머지에서 그대로 재발한다.

    올바른 방법: 공용 `knkReloadKeepView()` (`_v5_partials/chrome.html`) — 주소 조건은 그대로 두고
                 `_t` 만 새로 끼운다. 조건 없이 그냥 다시 읽으면 되는 자리는 `location.reload()` 도 좋다
                 (그 역시 주소를 안 버린다).

    잡는 것: `location.href=` / `location.assign(` / `location.replace(` 에
             `location.pathname + '?…'` 를 넘기는 모든 자리(줄바꿈이 끼어 있어도 잡는다).
    빼는 것: 주석 줄 · Jinja 주석(`{# #}`). WORKS 의 화면 JS 는 전부 템플릿 인라인이라 .html 만 본다
             (static 에 .js 파일 0개 — 2026-09-16 실측).
    """
    bad = []
    pat = re.compile(
        r"location\s*\.\s*(?:href\s*=|assign\s*\(|replace\s*\()\s*"
        r"(?:window\s*\.\s*)?location\s*\.\s*pathname\s*\+\s*['\"]\?", re.S)
    jinja_cmt = re.compile(r"\{#.*?#\}", re.S)
    for p in files:
        if not p.endswith(".html"):
            continue
        src = jinja_cmt.sub(_blank_keep_lines, _read(p))
        lines = src.splitlines()
        for m in pat.finditer(src):
            i = src.count("\n", 0, m.start())
            ln = lines[i] if i < len(lines) else ""
            if ln.lstrip().startswith(("//", "*", "/*")):     # 규칙을 설명하는 주석 줄은 위반이 아니다
                continue
            bad.append((p, i + 1, ln.strip()[:110]))
    return bad


def _js_func(src, name):
    """템플릿에서 최상위 JS 함수 한 개의 본문을 잘라 온다(`in APP` 같은 계수 함정을 피하려 구간으로 본다)."""
    import re as _re
    # z1135: 들여쓴 함수(공용 부품 knk_amt.html 처럼 IIFE 안에 든 것)도 찾는다
    m = _re.search(r"(?m)^[ 	]*(?:async\s+)?function\s+" + _re.escape(name) + r"\s*\(", src)
    if not m:
        return None
    nxt = _re.search(r"(?m)^[ 	]*(?:async\s+)?function\s+", src[m.end():])
    return src[m.start(): m.end() + (nxt.start() if nxt else len(src) - m.end())]


def check_date_cell_guard(_files=None):
    """§날짜 칸 = ①달력이 뜨고 ②날짜만 저장된다 (z1132 · 이새롬 프로 신고 2026-09-29).

    신고 원문: "발주일, 납품일도 발행일처럼 달력창이 뜨게 해주세요 / 발행일 입력시 날짜로만
    입력되게 해주세요. 발행일에 금액을 입력해도 저장이 됩니다."

    왜 두 신고가 한 뿌리인가: 공용 달력(`_v5_partials/knk_datepicker.html`)은
    `input.knk-cal` / `input[type=date]` 에만 붙는다. 작업일정표는 표 칸을 클릭하면 **그 자리에서
    맨 글자칸**을 만들어 달력이 안 붙었다(신고 ①). 그리고 달력은 브라우저 기본 달력을 끄려고
    `type=date` → `type=text` 로 바꾸므로 **브라우저 검사가 사라진다** — 그런데 화면에도 서버에도
    '날짜냐' 확인이 없어 금액 글자가 그대로 저장됐다(신고 ②).
    실측(2026-09-29 운영 읽기 전용): 이미 45건 — 소모품 발행일 43건(`2026-01-28-1` 꼴)·
    소모품 납품일 1건(`2026-02-6`)·원납기 1건(`확인 중`).

    올바른 방법
      · 화면: 편집칸은 `_mkCellInput()` 으로 만든다(날짜 칸이면 `knk-cal` 이 붙어 달력이 뜬다),
              저장 전 `_dateOk()` 를 거친다.
      · 서버: `database.date_cell_ok()` 로 막는다 — **마지막 방어선**. 화면 검사만으로는
              엑셀 일괄수정·다른 진입 경로를 못 막는다.

    잡는 것
      ① schedule_board.html 에 `_mkCellInput`·`_dateOk` 가 없거나 달력(`knk-cal`)을 안 붙인다
      ② 날짜 칸을 여는 편집기가 편집칸을 직접 만든다(`_mkCellInput` 을 안 쓴다)
      ③ 날짜를 저장하는 화면 함수가 `_dateOk` 를 안 거친다
      ④ 날짜를 저장하는 서버 함수가 `date_cell_ok` 를 안 거친다(구문 트리로 본다)
    """
    import ast as _ast
    bad = []
    tpl = os.path.join(TPL, "schedule_board.html")
    if os.path.exists(tpl):
        src = _read(tpl)
        # ① 공용 한 벌
        mk = _js_func(src, "_mkCellInput")
        if mk is None:
            bad.append((tpl, 1, "① 공용 _mkCellInput() 이 없다 — 날짜 칸에 달력이 안 붙는다"))
        elif "knk-cal" not in mk:
            bad.append((tpl, 1, "① _mkCellInput() 이 날짜 칸에 달력(knk-cal)을 안 붙인다"))
        if _js_func(src, "_dateOk") is None:
            bad.append((tpl, 1, "① 공용 _dateOk() 가 없다 — 날짜 형식을 검사할 수 없다"))
        # ② ③ 날짜 칸을 다루는 편집기
        for fn in ("startEdit", "startUnitEdit"):
            body = _js_func(src, fn)
            if body is None:
                continue
            if "_mkCellInput" not in body and "cell-input" in body:
                bad.append((tpl, 1, "② %s — 편집칸을 직접 만든다. _mkCellInput() 을 쓸 것(달력이 안 붙는다)" % fn))
        for fn in ("startEdit", "startUnitEdit", "startTaxInvEdit", "_uxSave"):
            body = _js_func(src, fn)
            if body is None:
                continue
            if "_dateOk" not in body:
                bad.append((tpl, 1, "③ %s — 날짜를 저장하는데 _dateOk() 를 안 거친다" % fn))
    # ④ 서버 — 마지막 방어선
    for rel, funcs in (("app/database.py", ("schedule_cell_update",)),
                       ("app/main.py", ("schedule_board_row_tax", "schedule_board_unit_field",
                                        "schedule_tax_invoice_issue"))):
        p = os.path.join(ROOT, *rel.split("/"))
        if not os.path.exists(p):
            continue
        try:
            tree = _ast.parse(_read(p))
        except SyntaxError as e:
            bad.append((p, getattr(e, "lineno", 0) or 0, "%s 구문 오류 — 검사 불가: %s" % (rel, e)))
            continue
        found = {}
        for n in _ast.walk(tree):
            if isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and n.name in funcs:
                found[n.name] = n
        for fn in funcs:
            node = found.get(fn)
            if node is None:
                bad.append((p, 1, "④ %s() 를 못 찾았다 — 날짜 검사 위치가 바뀌었는지 확인할 것" % fn))
                continue
            names = set()
            for c in _ast.walk(node):
                if isinstance(c, _ast.Call):
                    f = c.func
                    names.add(f.id if isinstance(f, _ast.Name) else (f.attr if isinstance(f, _ast.Attribute) else ""))
            if "date_cell_ok" not in names:
                bad.append((p, node.lineno,
                            "④ %s — 날짜 칸을 저장하는데 date_cell_ok() 를 안 거친다(서버가 마지막 방어선)" % fn))
    return bad


def check_amt_sign(files):
    r"""§금액 칸 = 마이너스(네고·할인) 보존 (z1135 · 이새롬 프로 신고 2026-10-02).

    신고 원문: "마이너스 건은 세금계산서 입력을 해도 플러스로 인식됩니다."
    실측(999T2606 SENSOR): 수주 금액 **-1,865,000** 인데 1차 세금계산서는 **+1,865,000**.

    원인: 금액 칸의 타이핑 재포맷이 `value.replace(/[^0-9.]/g,'')` 라 **'-' 를 키 입력 즉시 지웠다.**
    z1095 의 '.'(소수점) 삭제와 **같은 종류**다 — 그때는 10배가 됐고 이번엔 부호가 뒤집힌다.
    같은 화면 안에서도 단가·금액 칸(`_MONEY_STRIP`=통화기호·콤마만 제거)은 마이너스가 되는데
    세금계산서 금액만 안 되어, 한 줄 안에서 부호가 어긋났다.

    올바른 방법: 공용 `_v5_partials/knk_amt.html` 의 `knkFmtAmtTyping`(타이핑)·`knkAmtToRaw`(저장).
                 둘 다 **맨 앞 '-' 하나만** 살린다(중간·중복 '-' 는 버린다).

    잡는 것
      ① 공용 함수가 부호를 안 지킨다(사람이 되돌려 놓는 것을 막는다)
      ② 금액 칸에서 `[^0-9.]` 로 숫자·점만 남긴다(= 부호 삭제) · 주변 ±3줄에 금액 신호가 있을 때만
      ③ 금액 타이핑 포맷 **사본**이 또 생겼다(공용을 안 부르고 스스로 구현)
    빼는 것: 주석 · `[^0-9.\-]`(부호를 지키는 올바른 형태) · 날짜·전화 정규화(금액 신호 없음)
    """
    bad = []
    # z1135: 신호를 넓힌다 — 세금계산서 팝업 저장 줄(`av=(pa.value||'')...`)이 주변 3줄에
    #   'amt' 신호가 없어 빠져나가던 구멍을 시험(§4)이 찾아냈다.
    amt_sig = re.compile(
        r"knk-money|pi-price|ti-pa|ti-amt|ti-pd|ux-money|price|amount|amt|금액|단가|money"
        r"|AmtTyping|AmtToRaw|pa\.value|taxSave|taxinv|tax_invoice|세금계산서|인보이스|발행",
        re.I)
    LEAD_NEG = re.compile(r"\^\\s\*-|\^-|charAt\(0\)\s*===\s*'-'|startsWith\('-'\)|\[0\]\s*===\s*'-'")
    strip_sign = re.compile(r"replace\(\s*/\[\^0-9\.\]/g")      # [^0-9.] 만 — [^0-9.\-] 는 안 걸린다
    jinja_cmt = re.compile(r"\{#.*?#\}", re.S)

    # ① 공용 한 벌이 부호를 지키는가
    shared = os.path.join(TPL, "_v5_partials", "knk_amt.html")
    if os.path.exists(shared):
        src = _read(shared)
        for fn in ("fmtAmtTyping", "amtToRaw"):
            body = _js_func(src, fn)
            if body is None:
                bad.append((shared, 1, "① 공용 %s() 가 없다" % fn))
            elif not LEAD_NEG.search(body):
                bad.append((shared, 1,
                            "① 공용 %s() 가 **맨 앞 마이너스**를 보지 않는다 — 네고(할인) 금액이 양수가 된다" % fn))

    # ② ③ 화면들
    for p in files:
        if not p.endswith(".html"):
            continue
        # 공용 부품 자신은 ① 에서 이미 봤다 — 부호를 먼저 떼어 둔 뒤 숫자만 남기는 게 올바른 구현이다
        _is_shared = os.path.basename(p) == "knk_amt.html"
        src = jinja_cmt.sub(_blank_keep_lines, _read(p))
        lines = src.splitlines()
        for i, ln in enumerate(lines):
            if _is_shared or not strip_sign.search(ln):
                continue
            if ln.lstrip().startswith(("//", "*", "/*")):
                continue
            lo, hi = max(0, i - 5), min(len(lines), i + 6)
            if amt_sig.search("\n".join(lines[lo:hi])):
                bad.append((p, i + 1, ln.strip()[:110]))
        # 금액 타이핑 포맷 사본 — 공용을 부르지 않고 스스로 만들면 또 갈라진다
        for fn in ("_fmtAmtTyping", "fmtAmtTyping"):
            if os.path.basename(p) == "knk_amt.html":
                continue
            body = _js_func(src, fn)
            if body is None:
                continue
            if "knkFmtAmtTyping" not in body:
                bad.append((p, 1,
                            "③ %s() 사본 — 공용 knkFmtAmtTyping() 을 부를 것(사본은 화면마다 따로 재발한다)" % fn))
    return bad


def _py_top_func(src, name):
    """파이썬 원문에서 **최상위 함수 한 개**를 잘라 온다 → (시작 줄, 원문). 없으면 (None, None).
    main.py 는 4만 줄이 넘어 통째로 구문 분석하면 느리다 — 이름으로 찾아 다음 최상위 문장 앞까지만 자른다."""
    m = re.search(r"(?m)^(?:async\s+)?def\s+" + re.escape(name) + r"\s*\(", src)
    if not m:
        return None, None
    ln = src[:m.start()].count("\n") + 1
    eol = src.find("\n", m.end())                       # def 줄의 끝 — 여기서부터 찾아야 한다
    if eol < 0:                                         #   (자른 문자열의 맨 앞도 `^` 에 맞아 def 줄 한가운데서 끊겼었다)
        return ln, src[m.start():]
    nxt = re.search(r"(?m)^[^\s#]", src[eol + 1:])      # 다음 최상위 문장(데코레이터·def·대입)
    end = eol + 1 + (nxt.start() if nxt else len(src) - eol - 1)
    return ln, src[m.start():end]


def check_tax_sign(files):
    r"""§세금계산서 발행 판정은 금액의 부호를 가정하지 않는다 (z1137 · 이새롬 프로 신고 2026-10-02).

    신고 원문: "마이너스 세금계산서는 미발행으로 인식 됩니다. 마이너스 세금계산서도 발행으로 처리될수있게"
    실측(999T2606 SENSOR · 운영 읽기 전용): 수주 **-1,865,000** · 1차 세금계산서 **-1,865,000**
      (z1135 덕에 마이너스로 제대로 저장됨). 그런데
        ① 작업일정표 색 판정이 `total>0` 일 때만 돌아 **무색(미발행처럼)**
        ② 납품·수금이 `발행합계 <= 0` 을 「전부 미발행」으로 세어 **위쪽 숫자에 들어감**
    z1135(입력이 '-' 를 지움)와 **같은 뿌리**다 — 「금액은 플러스」라는 가정. 입력을 고쳐도 **판정**에 남아 있었다.
    마이너스 건에 플러스로 잘못 넣어도 무색이라 걸러지지 않던 것도 같은 줄이다.

    올바른 방법
      · 화면: 수주금액이 **0 인지만** 본다(`total!==0`). 견줄 금액이 있으면 부호와 무관하게 견준다.
      · 서버: 납품·수금의 발행 판정은 `_sr_bill_state()` 한 곳(순수 함수). 미발행 잔액은 **수주금액의 방향으로** 본다.
      · 위쪽 숫자는 줄의 상태(state)와 **같은 조건**으로 센다 — 따로 세면 숫자≠목록이 된다(27 대 20 이었다).

    잡는 것
      ① `refreshTaxStatus()` 가 수주금액을 「0보다 큰가」로 거른다
      ② 수주금액(`rowamt`)을 읽은 줄이 「0보다 큰가」로 거른다(1차 금액 미리 채움 등)
      ③ `_sr_bill_state()` 가 없거나, **원문을 뽑아 실제로 돌려 보니** 마이너스를 미발행으로 본다
      ④ 납품·수금 화면 함수가 `_sr_bill_state()` 를 안 거치고 스스로 판정한다
      ⑤ 「마감이월」 위쪽 숫자를 줄의 상태가 아닌 다른 조건으로 센다
      ⑥ 납품·수금 줄이 미발행 잔액을 「0보다 큰가」로 강조한다
    빼는 것: 주석(설명에 옛 조건을 적어 둔 것)
    """
    bad = []
    js_cmt = re.compile(r"//[^\n]*")
    jinja_cmt = re.compile(r"\{#.*?#\}", re.S)
    GT0 = re.compile(r"(?<![=\-<>!])>\s*0(?![\d.])")      # `>0` · `> 0` (`=>` · `>=` · `0.5` 는 아님)

    # ① 작업일정표 색 판정
    board = os.path.join(TPL, "schedule_board.html")
    if os.path.exists(board):
        src = jinja_cmt.sub(_blank_keep_lines, _read(board))
        body = _js_func(src, "refreshTaxStatus")
        if body is None:
            bad.append((board, 1, "① refreshTaxStatus() 가 없다 — 색 판정 함수 이름을 바꿨으면 이 검사도 함께 고칠 것"))
        else:
            ln0 = src[:src.find(body)].count("\n") + 1
            for i, ln in enumerate(body.splitlines()):
                if re.search(r"\btotal\s*>\s*0(?![\d.])", js_cmt.sub("", ln)):
                    bad.append((board, ln0 + i,
                                "① 수주금액을 「0보다 큰가」로 거른다 — 마이너스(네고) 건이 무색(미발행처럼)이 된다 → total!==0"))

    # ② ⑥ 화면들
    for p in files:
        if not p.endswith(".html"):
            continue
        src = jinja_cmt.sub(_blank_keep_lines, _read(p))
        for i, ln in enumerate(src.splitlines()):
            code = js_cmt.sub("", ln)
            if "rowamt" in code and GT0.search(code):
                bad.append((p, i + 1, "② 수주금액(rowamt)을 「0보다 큰가」로 거른다 — " + ln.strip()[:80]))
            if re.search(r"\bunbilled\s*>\s*0(?![\d.])", code):
                bad.append((p, i + 1, "⑥ 미발행 잔액을 「0보다 큰가」로 본다 — 마이너스 잔액도 남은 것이다 → != 0"))

    # ③ ④ ⑤ 서버 — 납품·수금
    main_py = os.path.join(ROOT, "app", "main.py")
    if os.path.exists(main_py):
        msrc = _read(main_py)
        ln_st, st = _py_top_func(msrc, "_sr_bill_state")
        if st is None:
            bad.append((main_py, 1, "③ _sr_bill_state() 가 없다 — 납품·수금 발행 판정의 공용 순수 함수"))
        else:
            try:
                ns = {}
                exec(compile(st, "_sr_bill_state", "exec"), ns)
                fn = ns["_sr_bill_state"]
                cases = [   # (수주금액, 발행합계, 하나도 안 끊음?, 잔액 남음?, 설명)
                    (-1865000, -1865000, False, False, "마이너스로 다 끊었는데 미발행으로 본다"),
                    (-1865000, 0, True, True, "마이너스 수주를 안 끊었는데 발행 대기로 안 본다"),
                    (-1865000, -1000000, False, True, "마이너스 수주를 일부만 끊었는데 발행 대기로 안 본다"),
                    (1865000, 1865000, False, False, "플러스로 다 끊은 건의 판정이 바뀌었다"),
                    (1865000, 0, True, True, "플러스 수주를 안 끊은 건의 판정이 바뀌었다"),
                    (1865000, 1000000, False, True, "플러스 수주를 일부만 끊은 건의 판정이 바뀌었다"),
                ]
                for tot, iss, e_none, e_due, why in cases:
                    r = fn(tot, iss, 0.5)
                    if bool(r.get("nothing_issued")) != e_none or bool(r.get("billing_due")) != e_due:
                        bad.append((main_py, ln_st, "③ _sr_bill_state(%d, %d) — %s" % (tot, iss, why)))
            except Exception as e:      # 못 돌리면 통과가 아니라 위반이다(죽은 검사 = 안 한 검사)
                bad.append((main_py, ln_st, "③ _sr_bill_state() 를 돌려 볼 수 없다: %r" % (e,)))
        ln_pg, pg = _py_top_func(msrc, "sales_shipments_receipts_page")
        if pg is None:
            bad.append((main_py, 1, "④ sales_shipments_receipts_page() 가 없다 — 이름을 바꿨으면 이 검사도 함께 고칠 것"))
        else:
            has_call = False
            for i, ln in enumerate(pg.splitlines()):
                code = ln.split("#", 1)[0]
                if "_sr_bill_state(" in code:
                    has_call = True
                if re.search(r"issued_amt[\"'\]]*\s*<=|\b_unb\s*>\s*_eps", code):
                    bad.append((main_py, ln_pg + i, "④ 발행 판정을 스스로 한다 — _sr_bill_state() 를 거칠 것: " + ln.strip()[:70]))
                if "carryover_cnt" in code and "마감이월" not in code:
                    bad.append((main_py, ln_pg + i,
                                "⑤ 「마감이월」 위쪽 숫자를 줄의 상태(state)와 다른 조건으로 센다 — 숫자≠목록이 된다"))
            if not has_call:
                bad.append((main_py, ln_pg, "④ 납품·수금 화면이 _sr_bill_state() 를 부르지 않는다"))
    return bad


def check_user_lang(files):
    r"""§사람마다의 WORKS 화면 언어 = 이음 메신저에서 고른 언어 · 한국어·베트남어 (z1155 · 대표 2026-10-10).

    대표 지시: 「웍스에는 기본적으로 한국어, 베트남어 적용을 해줘... 사용자 설정은 이음메신저에서 직원동기화할때
               이음메신저 선택 언어로 동일하게 개인별 적용하면 됨」 + 「내 프로필」은 「이음 따름 표시만」.
    겪은 것(세션 16 지시서 2026-10-10): 「내 프로필」 언어 칸이 한국어·English 둘뿐이라, 베트남어(vi)인 52명이
      이 화면에서 이메일만 고쳐 저장해도 **말없이 한국어로** 바뀌었다(맞는 선택지가 없으면 브라우저는 첫 항목을 보낸다).
      언어를 바꾸는 창구 둘(/me · /api/set-lang)의 기준도 달랐다(/me 는 i18n 에 없는 zh 까지 받았다).

    잡는 것
      ① i18n.USER_LANGS 가 없거나 ("ko","vi") 가 아니다 · user_lang_from_messenger() 를 **실제로 돌려 보니** 틀린다
      ② 화면에 언어 고르는 칸(<select name="lang">)이 있는데 USER_LANGS 중 빠진 것이 있다 — 원래 사고의 모양
      ③ 「내 프로필」(profile.html)에 언어를 **바꾸는** 칸(name="lang")이 다시 생겼다 — 대표 결정 「이음 따름 표시만」
      ④ /me 저장(me_update)이 언어를 쓴다
      ⑤ /api/set-lang 이 USER_LANGS 로 거르지 않거나, 모르는 값·빈 값을 한국어로 바꿔 저장한다
      ⑥ 명부 한 사람 → payload(_directory_user_to_payload)에 lang 이 없다 · 명부를 받는 두 창구가 그 함수를 안 쓰고
         dict 를 따로 만든다 · upsert_user_from_payload 가 이음 언어를 안 쓴다
      ⑦ 화면 공통 ctx() 가 USER_LANGS 밖 값(옛 en·zh)을 그대로 화면 언어로 쓴다
    빼는 것: 예전·백업 화면(_legacy · _backup) · 주석
    """
    bad = []
    app = os.path.join(ROOT, "app")
    i18n_p = os.path.join(app, "i18n.py")
    main_p = os.path.join(app, "main.py")
    sso_p = os.path.join(app, "sso_client.py")
    prof_p = os.path.join(TPL, "profile.html")
    jinja_cmt = re.compile(r"\{#.*?#\}", re.S)
    html_cmt = re.compile(r"<!--.*?-->", re.S)

    # ① 기준 한 곳 — 원문을 실제로 돌려 본다(못 돌리면 위반)
    langs = ("ko", "vi")
    try:
        ns = {}
        exec(compile(_read(i18n_p), i18n_p, "exec"), ns)
        ul = ns.get("USER_LANGS")
        if tuple(ul or ()) != ("ko", "vi"):
            bad.append((i18n_p, 1, "① USER_LANGS 가 (\"ko\",\"vi\") 가 아니다: %r — 대표 결정은 한국어·베트남어" % (ul,)))
        else:
            langs = tuple(ul)
        fn = ns.get("user_lang_from_messenger")
        cases = [(None, None), ("", None), ("  ", None), ("ko", "ko"), ("vi", "vi"), ("VI", "vi"),
                 (" vi ", "vi"), ("en", "ko"), ("zh", "ko"), ("xx", "ko")]
        if not callable(fn):
            bad.append((i18n_p, 1, "① user_lang_from_messenger() 가 없다 — 이음 언어를 WORKS 언어로 바꾸는 한 곳"))
        else:
            for v, want in cases:
                got = fn(v)
                if got != want:
                    bad.append((i18n_p, 1, "① user_lang_from_messenger(%r) = %r (맞는 값 %r)" % (v, got, want)))
    except Exception as e:
        bad.append((i18n_p, 1, "① i18n.py 를 돌려 보지 못했다(%s) — 못 돌리면 통과가 아니라 위반" % e))

    # ② ③ 화면
    tpls = set(p for p in files if p.endswith(".html"))
    if os.path.exists(prof_p):
        tpls.add(prof_p)
    for p in sorted(tpls):
        rp = p.replace("\\", "/")
        if "/_legacy" in rp or "_backup" in rp:
            continue
        src = html_cmt.sub(_blank_keep_lines, jinja_cmt.sub(_blank_keep_lines, _read(p)))
        for m in re.finditer(r"<select\b[^>]*\bname\s*=\s*[\"']lang[\"'][^>]*>(.*?)</select>", src, re.S | re.I):
            vals = set(re.findall(r"value\s*=\s*[\"']([^\"']+)[\"']", m.group(1)))
            miss = [x for x in langs if x not in vals]
            if miss:
                bad.append((p, src[:m.start()].count("\n") + 1,
                            "② 언어 고르는 칸에 %s 이(가) 없다 — 그 언어인 사람이 저장하면 말없이 첫 항목으로 바뀐다"
                            % "·".join(miss)))
        if os.path.abspath(p) == os.path.abspath(prof_p):
            for m in re.finditer(r"<(?:select|input|textarea)\b[^>]*\bname\s*=\s*[\"']lang[\"']", src, re.I):
                bad.append((p, src[:m.start()].count("\n") + 1,
                            "③ 「내 프로필」에 언어를 바꾸는 칸이 있다 — 대표 결정 「이음 따름 표시만」"
                            "(바꿔도 다음 동기화 때 이음 값으로 돌아간다)"))

    # ④ ⑤ ⑦ 서버 창구
    msrc = _read(main_p) if os.path.exists(main_p) else ""

    def _code_lines(body, ln0):
        """주석·설명글(docstring) 줄을 빼고 (줄번호, 줄) 을 돌려준다."""
        out, in_doc = [], False
        for i, ln in enumerate(body.splitlines()):
            s = ln.strip()
            if in_doc:
                if '"""' in s:
                    in_doc = False
                continue
            if s.startswith('"""'):
                if s.count('"""') == 1:
                    in_doc = True
                continue
            if s.startswith("#"):
                continue
            out.append((ln0 + i, ln.split("  #")[0]))
        return out

    ln0, body = _py_top_func(msrc, "me_update")
    if body is None:
        bad.append((main_p, 1, "④ me_update() 가 없다 — /me 저장 함수 이름을 바꿨으면 이 검사도 함께 고칠 것"))
    else:
        for n, ln in _code_lines(body, ln0):
            if re.search(r"\blang\s*=\s*\?|[\"']lang=\?|\blang\s*:\s*str\s*=\s*Form", ln):
                bad.append((main_p, n, "④ /me 저장이 언어를 받거나 쓴다 — 언어는 이음 따름(여기선 바꾸지 않는다)"))

    ln0, body = _py_top_func(msrc, "api_set_lang")
    if body is None:
        bad.append((main_p, 1, "⑤ api_set_lang() 가 없다 — 이름을 바꿨으면 이 검사도 함께 고칠 것"))
    else:
        code = _code_lines(body, ln0)
        if not any("USER_LANGS" in ln for _, ln in code):
            bad.append((main_p, ln0, "⑤ /api/set-lang 이 USER_LANGS 로 거르지 않는다 — 기준은 i18n.USER_LANGS 한 곳"))
        for n, ln in code:
            if re.search(r"^\s*lang\s*=\s*[\"']ko[\"']\s*$", ln) or re.search(r"get\(\s*[\"']lang[\"']\s*\)\s*or\s*[\"']ko", ln):
                bad.append((main_p, n, "⑤ 모르는 값·빈 값을 한국어로 바꿔 저장한다 — 바꾸지 말고 거절할 것"))
            if re.search(r"\bnot\s+in\s+LANGS\b", ln):
                bad.append((main_p, n, "⑤ LANGS(번역 사전 ko·vi·en)로 거른다 — 사람 언어는 USER_LANGS"))

    ln0, body = _py_top_func(msrc, "ctx")
    if body is None:
        bad.append((main_p, 1, "⑦ ctx() 가 없다"))
    elif "USER_LANGS" not in body:
        bad.append((main_p, ln0, "⑦ ctx() 가 USER_LANGS 밖 값(옛 en·zh)을 그대로 화면 언어로 쓴다"))

    # ⑥ 직원 동기화
    ssrc = _read(sso_p) if os.path.exists(sso_p) else ""
    ln0, body = _py_top_func(ssrc, "_directory_user_to_payload")
    if body is None:
        bad.append((sso_p, 1, "⑥ _directory_user_to_payload() 가 없다 — 이음 명부 한 사람 → payload 는 한 곳에서"))
    elif not re.search(r"[\"']lang[\"']\s*:\s*u\.get\(\s*[\"']lang[\"']\s*\)", body):
        bad.append((sso_p, ln0, "⑥ 명부 → payload 에 lang 이 없다 — 이음 언어가 WORKS 로 안 넘어온다"))
    for fname in ("sync_directory_from_messenger", "sync_employees_from_messenger_api"):
        ln0, body = _py_top_func(ssrc, fname)
        if body is None:
            bad.append((sso_p, 1, "⑥ %s() 가 없다 — 이름을 바꿨으면 이 검사도 함께 고칠 것" % fname))
            continue
        if "_directory_user_to_payload(" not in body:
            bad.append((sso_p, ln0, "⑥ %s() 가 _directory_user_to_payload() 를 안 쓴다" % fname))
        if re.search(r"[\"']name_kr[\"']\s*:\s*u\.get\(", body):
            bad.append((sso_p, ln0, "⑥ %s() 가 payload dict 를 따로 만든다 — 한쪽만 고치는 일이 생긴다" % fname))
    ln0, body = _py_top_func(ssrc, "upsert_user_from_payload")
    if body is None:
        bad.append((sso_p, 1, "⑥ upsert_user_from_payload() 가 없다"))
    else:
        if "user_lang_from_messenger(" not in body:
            bad.append((sso_p, ln0, "⑥ upsert 가 이음 언어를 user_lang_from_messenger() 로 읽지 않는다"))
        if not re.search(r"lang\s*=\s*COALESCE\(\s*\?\s*,\s*lang\s*\)", body):
            bad.append((sso_p, ln0, "⑥ upsert 가 기존 직원의 언어를 이음 값으로 맞추지 않는다(lang = COALESCE(?, lang))"))
    return bad


def check_customer_tier(files):
    r"""§고객 등급은 자동 산정(customer_tier.py) 한 곳만 쓴다 (z1156 · 대표 2026-10-11 「신규 유지」).

    v5H58(대표 지시 2026-05-03): 고객 등급은 점수로 **VIP·주요·일반·신규·휴면 5단계** 자동 산정, 수동 선택 폐지.
    그런데 v5H181(05-07)이 「'신규'는 비표준」으로 잘못 보고 **앱이 켜질 때마다** `UPDATE customers SET tier='일반'
    WHERE tier='신규'` 를 돌렸다 → 점수 1~24점 고객(운영 11곳)이 켤 때 '일반' → 24시간 재계산에 '신규' → 또 '일반'
    (운영 기록 1,265번). 같은 값을 두 곳이 서로 다르게 쓰면 화면은 「마지막으로 누가 썼나」에 따라 오락가락한다.

    잡는 것
      ① app/ 의 파이썬(customer_tier.py 밖)이 등급 값을 **일괄로 바꿔 쓴다** — `UPDATE customers SET tier=… WHERE tier=…`
      ② 앱 시작 함수 startup() 이 customers.tier 를 UPDATE 한다(기동 때 업무 데이터 일괄 수정 금지)
      ③ customer_tier.score_to_tier() 를 **실제로 돌려** 나오는 등급이 VIP·주요·일반·신규·휴면 5개가 아니다
         (등급 체계를 바꾸려면 대표 결정 + 이 검사를 함께 고칠 것)
    빼는 것: 주석·설명글
    """
    bad = []
    app = os.path.join(ROOT, "app")
    main_p = os.path.join(app, "main.py")
    ct_p = os.path.join(app, "customer_tier.py")
    BULK = re.compile(r"UPDATE\s+customers\s+SET\s+tier\s*=\s*(?:'[^']*'|\?)\s+WHERE\s+[^\"\n]*\btier\s*(?:=|IN\b)", re.I)
    for p in sorted(_walk(app, (".py",))):
        if os.path.abspath(p) == os.path.abspath(ct_p):
            continue
        for i, ln in enumerate(_read(p).splitlines(), 1):
            s = ln.strip()
            if s.startswith("#"):
                continue
            if BULK.search(ln):
                bad.append((p, i, "① 고객 등급을 일괄로 바꿔 쓴다 — 등급은 customer_tier.refresh_* 한 곳만(자동 산정과 서로 덮는다)"))
    ln0, body = _py_top_func(_read(main_p) if os.path.exists(main_p) else "", "startup")
    if body is None:
        bad.append((main_p, 1, "② startup() 이 없다 — 앱 시작 함수 이름을 바꿨으면 이 검사도 함께 고칠 것"))
    else:
        for i, ln in enumerate(body.splitlines()):
            if ln.strip().startswith("#"):
                continue
            if re.search(r"UPDATE\s+customers\s+SET\s+[^\"\n]*\btier\s*=", ln, re.I):
                bad.append((main_p, ln0 + i, "② 앱이 켜질 때 고객 등급을 고친다 — 기동 코드에서 업무 데이터를 일괄로 고치지 않는다"))
    try:
        ns = {}
        exec(compile(_read(ct_p), ct_p, "exec"), ns)
        f = ns["score_to_tier"]
        got = set()
        for sc in range(0, 101):
            for days in (None, 0, 30, 400):
                got.add(f(sc, days))
        want = {"VIP", "주요", "일반", "신규", "휴면"}
        if got != want:
            bad.append((ct_p, 1, "③ 자동 산정 등급이 %s — 대표 지시 5단계(VIP·주요·일반·신규·휴면)와 다르다"
                        % "·".join(sorted(got))))
    except Exception as e:
        bad.append((ct_p, 1, "③ customer_tier.score_to_tier() 를 돌려 보지 못했다(%s) — 못 돌리면 위반" % e))
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

    amt_new, amt_old = split_baseline(check_amt_decimal(files), "amt")
    if amt_new:
        fail += len(amt_new)
        print("  ❌ 금액칸 소수점 삭제 : 새로 %d건 → 공용 knkFmtAmtTyping/knkAttachAmt 사용"
              " (_v5_partials/knk_amt.html)" % len(amt_new))
        for f, l, m in amt_new[:20]:
            print("       %s:%s  %s" % (f, l, m))
    else:
        print("  ✅ 금액칸 소수점 보존 : 새 위반 없음 (기존 면제 %d건)" % amt_old)

    ccy_new, ccy_old = split_baseline(check_ccy_sum(files), "ccy")
    if ccy_new:
        fail += len(ccy_new)
        print("  ❌ 환산 없는 금액 합산 : 새로 %d건 → 서버 _ccy_breakdown() + 공용 ccy_total()"
              " (_v5_partials/knk_ccy_total.html)" % len(ccy_new))
        for f, l, m in ccy_new[:20]:
            print("       %s:%s  %s" % (f, l, m))
    else:
        print("  ✅ 환산 없는 금액 합산 : 새 위반 없음 (기존 면제 %d건)" % ccy_old)

    pa_bad = check_project_amount_sum()
    if pa_bad:
        fail += len(pa_bad)
        print("  ❌ 프로젝트 수주금액 직접 저장 : %d건 → _recalc_project_amount()/"
              "_apply_project_amount() 사용" % len(pa_bad))
        for f, l, m in pa_bad[:20]:
            print("       %s:%s  %s" % (os.path.basename(f), l, m))
    else:
        print("  ✅ 프로젝트 수주금액 저장 : 공용 함수로만 (직접 SUM 0건)")

    nas_bad = check_nas_quiet_schedulers()
    if nas_bad:
        fail += len(nas_bad)
        print("  ❌ NAS 백업 시간(월 02:00~07:30) 예약 작업 : %d건 → _nas_quiet_wait_secs()/"
              "_nas_quiet_now() 판정을 거칠 것" % len(nas_bad))
        for f, l, m in nas_bad[:20]:
            print("       %s:%s  %s" % (os.path.basename(f), l, m))
    else:
        print("  ✅ NAS 백업 시간(월 02:00~07:30) 예약 작업 : 모두 판정 거침")

    rkv_bad = check_reload_keep_view(files)
    if rkv_bad:
        fail += len(rkv_bad)
        print("  ❌ 저장 후 새로고침이 보던 화면을 버림 : %d건 → 공용 knkReloadKeepView() 사용"
              " (_v5_partials/chrome.html)" % len(rkv_bad))
        for f, l, m in rkv_bad[:20]:
            print("       %s:%s  %s" % (_rel(f), l, m))
    else:
        print("  ✅ 저장 후 새로고침 : 보던 화면(주소 조건) 유지")

    dc_bad = check_date_cell_guard()
    if dc_bad:
        fail += len(dc_bad)
        print("  ❌ 날짜 칸 달력·날짜 검사 : %d건 → 화면 _mkCellInput()/_dateOk() · 서버 date_cell_ok()"
              % len(dc_bad))
        for f, l, m in dc_bad[:20]:
            print("       %s:%s  %s" % (_rel(f), l, m))
    else:
        print("  ✅ 날짜 칸 : 달력이 붙고 날짜만 저장됨 (화면·서버 양쪽)")

    sign_bad = check_amt_sign(files)
    if sign_bad:
        fail += len(sign_bad)
        print("  ❌ 금액칸 마이너스(네고) 삭제 : %d건 → 공용 knkFmtAmtTyping()/knkAmtToRaw() 사용"
              " (_v5_partials/knk_amt.html)" % len(sign_bad))
        for f, l, m in sign_bad[:20]:
            print("       %s:%s  %s" % (_rel(f), l, m))
    else:
        print("  ✅ 금액칸 마이너스(네고·할인) : 부호 보존")

    ts_bad = check_tax_sign(files)
    if ts_bad:
        fail += len(ts_bad)
        print("  ❌ 세금계산서 발행 판정이 금액 부호를 가정 : %d건 → 화면 total!==0 · 서버 _sr_bill_state()"
              % len(ts_bad))
        for f, l, m in ts_bad[:20]:
            print("       %s:%s  %s" % (_rel(f), l, m))
    else:
        print("  ✅ 세금계산서 발행 판정 : 마이너스(네고·할인)도 같은 기준 (화면·서버)")

    ul_bad = check_user_lang(files)
    if ul_bad:
        fail += len(ul_bad)
        print("  ❌ 사람 화면 언어(이음 따름·한국어·베트남어) : %d건 → i18n.USER_LANGS · 「내 프로필」 보여 주기만"
              " · 직원 동기화가 이음 언어를 옮김" % len(ul_bad))
        for f, l, m in ul_bad[:20]:
            print("       %s:%s  %s" % (_rel(f), l, m))
    else:
        print("  ✅ 사람 화면 언어 : 이음 따름 · 한국어·베트남어 (동기화·내 프로필·바꾸는 창구)")

    ct_bad = check_customer_tier(files)
    if ct_bad:
        fail += len(ct_bad)
        print("  ❌ 고객 등급을 두 곳이 쓴다 : %d건 → 등급은 customer_tier.refresh_* 한 곳만(기동 때 일괄 수정 금지)" % len(ct_bad))
        for f, l, m in ct_bad[:20]:
            print("       %s:%s  %s" % (_rel(f), l, m))
    else:
        print("  ✅ 고객 등급 : 자동 산정 한 곳만 씀 (VIP·주요·일반·신규·휴면)")

    print("=" * 72)
    if fail:
        print("결과: 위반 %d건 — 고치거나, 정당한 사유면 ALLOW 에 사유와 함께 추가하세요." % fail)
        return 1
    print("결과: 전부 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
