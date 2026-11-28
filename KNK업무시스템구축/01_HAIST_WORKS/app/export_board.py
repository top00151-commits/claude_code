# -*- coding: utf-8 -*-
"""z1191z85 — 수출 관리 = 선적 건 보드 (대표 2026-11-20 「안지연 프로 입장에서 … 20년 넘게 수출입 실무를 한 배테랑이 만든 프로그램처럼」)

왜 바꾸나(운영 실측 11-20):
  - 예전 수출 관리 첫 화면은 「수출 수주 → CI → P/L → B/L → 통관」 표인데 그 표들이 모두 0건(한 번도 안 씀) — 열람 167번이 빈 화면을 봤다.
  - 실제 일은 인보이스 엑셀 한 장이 중심이다: 2026-01~11 인보이스 56장(수책통관 15 · 일반통관 41 · 약 USD 410만) ·
    안지연 프로가 ① HS 자동 채움에 15번 올림 → 법인(도안) 회신 → ③ 반영. 그 뒤(포워더·선적·베트남 통관·송금)는 시스템 어디에도 안 남는다.
어떻게:
  - **인보이스 번호 = 선적 한 건**(KNK-YYMMDD-n). 이미 올린 인보이스(자동 채움 기록 · 지난 수출 이력)에서 저절로 건이 생긴다 — 새로 칠 것 없음.
  - 건마다 6단계(서류 작성 → HS 확인·법인 → 출고 준비 → 운송 중 → 베트남 통관 → 마감)와 「지금 공은 누구에게」.
  - 손이 필요한 일을 맨 위에(법인 회신 늦음 · 선적일 지났는데 출고 기록 없음 · 도착 지났는데 통관 기록 없음 · 통관 30일 송금 없음 · 서류 점검 오류).
  - 건 한 장: 서류에서 읽은 것 · 서류 점검(export_check) · 선적/통관/대금 칸 · 서류철(최종 인보이스·AWB·수입신고서·송금증) · 포워더/법인에 보낼 글 복사.
  - 예전 화면(수주·CI·PL·BL 골격 · 출하 전 통관 정리)은 지우지 않고 맨 아래 접어 둔다.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
from datetime import datetime, timedelta

from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from . import export_price as XP

INV_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,39}$")
FILE_KINDS = [("invoice", "최종 인보이스·패킹(엑셀)"), ("awb", "AWB · B/L"), ("decl", "베트남 수입신고서"),
              ("co", "원산지증명(C/O)"), ("pay", "송금증"), ("etc", "기타")]
FILE_EXT = (".xlsx", ".xlsm", ".pdf", ".jpg", ".jpeg", ".png")
FILE_MAX_MB = 30
# (칸, 이름, 종류) — 종류: text · day · num · pick:a|b|c
FIELDS = [
    ("ship_mode", "운송", "pick:항공|해상|특송(쿠리어)|핸드캐리"),
    ("forwarder", "포워더", "text"),
    ("awb_no", "AWB · B/L 번호", "text"),
    ("pkgs", "포장 수(박스·팔레트)", "num"),
    ("gross_kg", "총중량(kg)", "num"),
    ("cbm", "부피(CBM)", "num"),
    ("etd", "출발(ETD)", "day"),
    ("eta", "도착(ETA)", "day"),
    ("vn_decl_no", "베트남 수입신고번호", "text"),
    ("vn_lane", "검사 구분", "pick:녹색(서류 통과)|황색(서류 심사)|적색(실물 검사)"),
    ("cleared_at", "통관 완료일", "day"),
    ("duty_vnd", "관세(VND)", "num"),
    ("vat_vnd", "부가세(VND)", "num"),
    ("paid_at", "송금 받은 날", "day"),
    ("paid_usd", "받은 금액(USD)", "num"),
    ("note", "메모", "text"),
]
FNAME = {k: n for k, n, _t in FIELDS}
STAGES = ["서류 작성", "HS 확인 · 법인", "출고 준비", "운송 중", "베트남 통관", "마감"]
BALL = ["본사(작성자)", "법인(HS 확인)", "본사 → 포워더", "포워더 · 법인", "본사(송금 확인)", "—"]
OLD_DAYS = 45            # 추적 칸이 하나도 없고 이보다 오래된 인보이스 = 「지난 건」
GO_LIVE = "2026-11-20"   # 보드 시작일 — 이보다 앞 인보이스는 적은 것이 없으면 「지난 건」(이미 보낸 10~11월 건이 첫날 「출고 기록 없음」으로 쏟아지지 않게)
REPLY_LATE_H = 24
CLEAR_LATE_D = 3         # 도착(ETA) 뒤 며칠까지 통관 기록이 없어도 기다리나
PAY_LATE_D = 30          # 통관 뒤 며칠 지나면 송금 확인을 묻나(T/T)


def _kind(v) -> str:
    s = str(v or "")
    if "수책" in s:
        return "수책통관"
    if "일반" in s or "소모품" in s:
        return "일반통관"
    return ""


def _day_of_no(ino: str) -> str:
    m = re.match(r"KNK-(\d\d)(\d\d)(\d\d)", ino or "")
    return "20%s-%s-%s" % m.groups() if m else ""


def _d(s):
    try:
        return datetime.strptime((s or "")[:10], "%Y-%m-%d")
    except ValueError:
        return None


_BG_LOCK = threading.Lock()
_CFG = {}     # 등록 때 받은 것(시험은 hs_fill_dir · base 를 임시 폴더로 바꿔 쓴다)


def _hs_dir():
    return _CFG["hs_fill_dir"]


def _ship_dir():
    return os.path.join(_CFG["base"], "data", "export_ship")


def _dt(s):
    try:
        return datetime.strptime((s or "")[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return _d(s)


def register_export_board(app, d):
    _CFG.update(d)
    ctx, guard, db_session = d["ctx"], d["guard"], d["db_session"]
    _gu199 = d.get("get_user") or (lambda _r: True)   # z1191z199: 권한 없음 → /home?no_perm=page · 로그인 풀림 → 로그인 화면
    udisp, kst_now, log = d["user_disp"], d["kst_now"], d["log"]

    def ensure(c):
        c.execute("""CREATE TABLE IF NOT EXISTS export_ship (
            invoice_no TEXT PRIMARY KEY, kind TEXT, inv_date TEXT,
            ship_mode TEXT, forwarder TEXT, awb_no TEXT, pkgs REAL, gross_kg REAL, cbm REAL, etd TEXT, eta TEXT,
            vn_decl_no TEXT, vn_lane TEXT, cleared_at TEXT, duty_vnd REAL, vat_vnd REAL,
            paid_at TEXT, paid_usd REAL, closed INTEGER DEFAULT 0, note TEXT,
            created_by INTEGER, created_at TEXT, updated_by INTEGER, updated_at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS export_ship_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT, field TEXT, old_value TEXT, new_value TEXT,
            by_user INTEGER, at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS export_ship_file (
            id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_no TEXT, kind TEXT, file_name TEXT, stored TEXT, size INTEGER,
            by_user INTEGER, at TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS export_ship_check (
            invoice_no TEXT PRIMARY KEY, src TEXT, src_key TEXT, result TEXT, at TEXT)""")
        c.execute("CREATE INDEX IF NOT EXISTS ix_export_ship_log_inv ON export_ship_log(invoice_no)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_export_ship_file_inv ON export_ship_file(invoice_no)")

    def _has(c, t):
        return c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone() is not None

    def collect(c) -> dict:
        """인보이스 번호 → 건(자동 채움 기록 · 지난 수출 이력 · 선적 칸 · 점검 결과를 합친 것)."""
        ensure(c)
        S = {}

        def get(no):
            return S.setdefault(no, {"invoice_no": no, "kind": "", "inv_date": _day_of_no(no), "lines": None, "amount": None,
                                     "logs": [], "hist": None, "ship": {}, "check": None})
        if _has(c, "export_hs_fill_log"):
            for r in c.execute("SELECT * FROM export_hs_fill_log WHERE COALESCE(invoice_no,'')<>'' ORDER BY id"):
                s = get(r["invoice_no"])
                s["logs"].append(dict(r))
                s["kind"] = s["kind"] or _kind(r["form"])
                s["lines"] = r["n_total"]
        if _has(c, "export_hist_inv"):
            for r in c.execute("SELECT * FROM export_hist_inv"):
                s = get(r["invoice_no"])
                s["hist"] = dict(r)
                s["kind"] = _kind(r["kind"]) or s["kind"]
                s["inv_date"] = r["inv_date"] or s["inv_date"]
                s["lines"] = r["n_lines"] or s["lines"]
                s["amount"] = r["total_amount"]
        for r in c.execute("SELECT * FROM export_ship"):
            s = get(r["invoice_no"])
            s["ship"] = dict(r)
            s["kind"] = s["kind"] or _kind(r["kind"])
            s["inv_date"] = s["inv_date"] or r["inv_date"] or ""
        for r in c.execute("SELECT invoice_no, result FROM export_ship_check"):
            if r["invoice_no"] in S:
                try:
                    S[r["invoice_no"]]["check"] = json.loads(r["result"] or "null")
                except ValueError:
                    pass
        # z1191z86: 단가 범위 밖 줄에 고른 것(허용·고치기)을 붙인다 — 점검 결과(파일)는 그대로 · 고른 것은 화면을 열 때마다 새로
        XP.ensure(c)
        AK = {}
        for r in c.execute("SELECT * FROM export_price_ack"):
            AK.setdefault(r["invoice_no"], {})[(r["part_key"], r["price_key"])] = dict(r)
        for no, s in S.items():
            price_overlay(s, AK.get(no, {}), c)
        for s in S.values():
            ck = s["check"] or {}
            sm = ck.get("summary") or {}
            if s["amount"] is None and sm.get("amount"):
                s["amount"] = sm["amount"]
            if s["lines"] is None and sm.get("lines"):
                s["lines"] = sm["lines"]
            judge(s)
        return S

    def price_overlay(s, ak, c=None):
        """점검 결과의 단가 범위 밖 줄 + 고른 것 → 그 항목의 표시(남음 = 확인할 것 · 고치기 = 오류 · 다 허용 = 괜찮음) · s["px"]."""
        s["px"], s["px_n"] = [], {"open": 0, "allow": 0, "fix": 0}
        ck = s.get("check") or {}
        for it in ck.get("items") or []:
            if "px" not in it:
                continue
            n = XP.overlay(it["px"], ak, udisp if c is not None else None, c)
            s["px"], s["px_n"] = it["px"], n
            base = it["title"].split(" — ")[0]
            if n["open"]:
                it["level"], it["title"] = "warn", base + " — 고를 것 %d" % n["open"]
            elif n["fix"]:
                it["level"], it["title"] = "err", base + " — 고치기 %d" % n["fix"]
            else:
                it["level"], it["title"] = "ok", base + " — 모두 허용함(%d)" % n["allow"]
        if s["px"]:
            lv = [x["level"] for x in ck.get("items") or []]
            sm = ck.setdefault("summary", {})
            sm["err"], sm["warn"] = lv.count("err"), lv.count("warn")

    def judge(s):
        """단계 · 공 · 손이 필요한 일."""
        sh, logs, now = s["ship"], s["logs"], kst_now()
        last = logs[-1] if logs else None
        #   지난 수출 이력에 최종본이 들어갔으면 HS 는 끝난 것(회신을 다른 길로 반영한 경우 · 운영 실측 11-20: 261015·260901)
        waiting = bool(last) and not s["hist"] and not last.get("reply_at") and ((last.get("n_need") or 0) + (last.get("n_check") or 0)) > 0
        hs_done = bool(s["hist"]) or (bool(last) and not waiting)
        if sh.get("closed") or sh.get("paid_at"):
            st = 5
        elif sh.get("cleared_at"):
            st = 4
        elif sh.get("etd") or sh.get("awb_no"):
            st = 3
        elif waiting:
            st = 1
        elif hs_done:
            st = 2
        else:
            st = 0
        tracked = any(sh.get(k) for k, _n, _t in FIELDS) or bool(sh.get("closed"))
        dd = _d(s["inv_date"])
        start = _CFG.get("go_live") or GO_LIVE
        pre = (s["inv_date"] or "") < start          # 시작일 전 — 회신 대기로 남은 옛 기록도 지난 건(운영 실측: 김정락 대표 시험 올림 4건 등)
        stale = dd is not None and (now - dd).days > OLD_DAYS
        s["old"] = (not tracked) and dd is not None and (pre or (stale and st != 1))
        s["stage"], s["stage_name"], s["ball"] = st, STAGES[st], BALL[st]
        al = []
        ck = (s["check"] or {}).get("summary") or {}
        sail = (s["check"] or {}).get("facts", {}).get("sail_date") or sh.get("etd") or ""
        if not s["old"]:
            if st == 1:
                t = _dt(last.get("filled_at"))
                h = (now - t).total_seconds() / 3600 if t else 0
                if h >= REPLY_LATE_H:
                    al.append("법인 HS 회신 기다린 지 %s" % ("%d시간" % h if h < 48 else "%d일" % (h // 24)))
            if st <= 2 and sail and _d(sail) and _d(sail) < now.replace(hour=0, minute=0, second=0, microsecond=0):
                al.append("선적일(%s)이 지났는데 출고 기록 없음" % sail)
            if st == 3 and sh.get("eta") and _d(sh["eta"]) and (now - _d(sh["eta"])).days > CLEAR_LATE_D:
                al.append("도착(%s) 뒤 %d일 — 베트남 통관 기록 없음" % (sh["eta"], (now - _d(sh["eta"])).days))
            if st == 4 and _d(sh.get("cleared_at")) and (now - _d(sh["cleared_at"])).days > PAY_LATE_D:
                al.append("통관 뒤 %d일 — 송금 확인 기록 없음(T/T)" % (now - _d(sh["cleared_at"])).days)
            pn = s.get("px_n") or {}
            if st < 5 and pn.get("open"):
                al.append("단가가 정한 범위 밖 %d줄 — 허용/고치기 고르기" % pn["open"])
            if st < 5 and ck.get("err"):
                al.append("서류 점검 오류 %d" % ck["err"] + (" (단가 고치기 %d 포함)" % pn["fix"] if pn.get("fix") else ""))
        s["alerts"] = al
        s["days"] = (now - dd).days if dd else None
        s["amount_txt"] = "${:,.0f}".format(s["amount"]) if s["amount"] else "—"   # z1191z103: 인보이스 TOTAL(USD) 앞에 $

    # ---------------- 보드 ----------------
    @app.get("/export", response_class=HTMLResponse)
    async def export_board(req: Request):
        u = guard(req)
        if not u:
            return RedirectResponse("/home?no_perm=page" if _gu199(req) else "/login", 303)   # z1191z199: 권한 없음 안내(chrome ?no_perm=) · 말없이 홈으로 보내지 않음
        with db_session() as c:
            S = collect(c)
            stp = XP.stamp(c)
        allx = sorted(S.values(), key=lambda s: (s["inv_date"] or "", s["invoice_no"]), reverse=True)
        live = [s for s in allx if not s["old"] and s["stage"] < 5]
        # z1191z86: 아직 점검 안 한 건 + 단가 조건·고치기가 바뀐 뒤의 옛 점검(예전 판 결과 포함)도 뒤에서 다시
        warm_checks([s["invoice_no"] for s in live if (s["logs"] or s["ship"]) and (s["check"] is None or (s["check"] or {}).get("stamp") != stp)])
        now = kst_now()
        cur_m = now.strftime("%Y-%m")
        done_m = [s for s in allx if s["stage"] == 5 and (s["ship"].get("paid_at") or s["ship"].get("updated_at") or "")[:7] == cur_m]
        cols = [(i, STAGES[i], BALL[i], [s for s in live if s["stage"] == i]) for i in range(0, 5)]
        cols = [x for x in cols if x[0] != 0 or x[3]]          # 「서류 작성」은 건이 있을 때만
        alerts = [(s, a) for s in live for a in s["alerts"]]
        # 달마다(최근 12달) — 수책 · 일반 건수와 금액
        months = {}
        for s in allx:
            m = (s["inv_date"] or "")[:7]
            if not m:
                continue
            x = months.setdefault(m, {"m": m, "수책통관": [0, 0.0], "일반통관": [0, 0.0], "": [0, 0.0]})
            x[s["kind"]][0] += 1
            x[s["kind"]][1] += s["amount"] or 0
        mrows = [months[k] for k in sorted(months, reverse=True)[:12]]
        y = now.strftime("%Y")
        ytd = {"n": sum(1 for s in allx if (s["inv_date"] or "").startswith(y)),
               "usd": sum(s["amount"] or 0 for s in allx if (s["inv_date"] or "").startswith(y))}
        this_m = months.get(cur_m) or {"수책통관": [0, 0.0], "일반통관": [0, 0.0], "": [0, 0.0]}
        return ctx(req, "export_board.html", user=u, active="export", cols=cols, alerts=alerts, live=live,
                   allx=allx, mrows=mrows, ytd=ytd, this_m=this_m, cur_m=cur_m, done_m=done_m, n_old=sum(1 for s in allx if s["old"]),
                   err=req.query_params.get("err") or "")

    @app.post("/export/s/new")
    async def export_ship_new(req: Request):
        u = guard(req)
        if not u:
            return JSONResponse({"ok": False, "error": "권한 없음"}, 403)
        form = await req.form()
        no = str(form.get("invoice_no") or "").strip().upper()
        if not INV_OK.match(no):
            return RedirectResponse("/export?err=no", 303)
        kind = _kind(form.get("kind"))
        with db_session() as c:
            ensure(c)
            if not c.execute("SELECT 1 FROM export_ship WHERE invoice_no=?", (no,)).fetchone():
                ts = kst_now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO export_ship(invoice_no, kind, inv_date, created_by, created_at, updated_by, updated_at) VALUES(?,?,?,?,?,?,?)",
                          (no, kind, _day_of_no(no) or kst_now().strftime("%Y-%m-%d"), u.get("id"), ts, u.get("id"), ts))
                c.execute("INSERT INTO export_ship_log(invoice_no, field, old_value, new_value, by_user, at) VALUES(?,?,?,?,?,?)",
                          (no, "선적 건", "", "직접 만듦" + (" · " + kind if kind else ""), u.get("id"), ts))
        return RedirectResponse("/export/s/" + no, 303)

    # ---------------- 서류 점검 ----------------
    def _check_src(c, no):
        """점검할 파일 — 서류철의 최종 인보이스(엑셀) → 없으면 자동 채움으로 받은 파일(30일 보관) · (경로, 이름, 출처) 또는 None."""
        r = c.execute("SELECT * FROM export_ship_file WHERE invoice_no=? AND kind='invoice' AND lower(file_name) LIKE '%.xls%' "
                      "ORDER BY id DESC LIMIT 1", (no,)).fetchone()
        if r:
            p = os.path.join(_ship_dir(), r["stored"])
            if os.path.exists(p):
                return p, r["file_name"], "서류철 최종 인보이스"
        if _has(c, "export_hs_fill_log"):
            for r in c.execute("SELECT stored, file_name FROM export_hs_fill_log WHERE invoice_no=? AND COALESCE(stored,'')<>'' ORDER BY id DESC", (no,)):
                p = os.path.join(_hs_dir(), r["stored"])
                if os.path.exists(p):
                    return p, r["file_name"], "HS 자동 채움 파일"
        return None

    def _hist_maps(c, no, keys, before=""):
        """before = 이 인보이스 날짜 — 그보다 앞선 수출만 「지난번」(뒤에 나간 인보이스와 견주지 않게 · 운영 실측 11-20).
        z1191z86: 「고치기」로 고른 단가는 단가 기준에서 뺀다(HS 는 그대로 봄)."""
        last, mine = {}, {}
        if not _has(c, "export_hist_line"):
            return last, mine
        fx = XP.fixed(c)
        lp, lh = {}, {}
        ks = sorted(k for k in keys if k)
        for i in range(0, len(ks), 400):
            part = ks[i:i + 400]
            for r in c.execute("SELECT part_key, unit_price, hs_code, invoice_no, inv_date FROM export_hist_line WHERE invoice_no<>? AND part_key IN (%s) "
                               "AND (?='' OR IFNULL(inv_date,'')<?) ORDER BY IFNULL(inv_date,''), id" % ",".join("?" * len(part)), [no] + part + [before, before]):
                k = r["part_key"]
                if r["unit_price"] and (r["invoice_no"], k, XP.pkey(r["unit_price"])) not in fx:
                    lp[k] = (r["unit_price"], r["invoice_no"], r["inv_date"] or "")
                if r["hs_code"]:
                    lh[k] = (r["hs_code"], r["invoice_no"], r["inv_date"] or "")
        for k in set(lp) | set(lh):
            p, h = lp.get(k), lh.get(k)
            ref = p or h
            last[k] = (p[0] if p else None, h[0] if h else "", ref[1], ref[2])
        for r in c.execute("SELECT part_key, hs_code FROM export_hist_line WHERE invoice_no=? AND COALESCE(hs_code,'')<>''", (no,)):
            mine[r["part_key"]] = r["hs_code"]
        return last, mine

    def _kind_of_no(c, no):
        """이 인보이스의 통관 구분 — 지난 수출 이력 → 자동 채움 양식 → 선적 칸."""
        if _has(c, "export_hist_inv"):
            r = c.execute("SELECT kind FROM export_hist_inv WHERE invoice_no=?", (no,)).fetchone()
            if r and _kind(r[0]):
                return _kind(r[0])
        if _has(c, "export_hs_fill_log"):
            r = c.execute("SELECT form FROM export_hs_fill_log WHERE invoice_no=? ORDER BY id DESC LIMIT 1", (no,)).fetchone()
            if r and XP.kind_of(r[0]):
                return XP.kind_of(r[0])
        r = c.execute("SELECT kind FROM export_ship WHERE invoice_no=?", (no,)).fetchone()
        return _kind(r[0]) if r else ""

    def compute_check(no, force=False):
        """점검(느린 엑셀 읽기는 DB 밖에서) → 결과 저장. 같은 파일이면 저장된 결과. 반환 (결과 또는 None, 출처)."""
        from . import export_check as X
        from .hs_fill import norm_key
        with db_session() as c:
            ensure(c)
            src = _check_src(c, no)
            old = c.execute("SELECT * FROM export_ship_check WHERE invoice_no=?", (no,)).fetchone()
            old = dict(old) if old else None
            kind = _kind_of_no(c, no)
            rng = XP.tol(XP.rules(c), kind)
            stp = XP.stamp(c)
        if not src:
            return (json.loads(old["result"]) if old else None), None
        p, fname, how = src
        # z1191z86: 단가 조건이 바뀌거나 「고치기」가 늘면 다시 점검(같은 파일이어도)
        key = "%s|%d|%d|%s" % (os.path.basename(p), int(os.path.getmtime(p)), os.path.getsize(p), stp)
        if old and old["src_key"] == key and not force:
            return json.loads(old["result"]), how
        with open(p, "rb") as fi:
            doc = X.read(fi.read())
        if not doc.get("ok"):
            res = {"facts": {}, "summary": {}, "items": [X._w("err", doc.get("error") or "파일을 읽지 못했습니다")]}
        else:
            keys = {norm_key(it["desc"]) for it in (doc.get("invoice") or {}).get("items") or []}
            with db_session() as c:
                last, mine = _hist_maps(c, no, keys, ((doc.get("invoice") or {}).get("facts") or {}).get("inv_date") or _day_of_no(no))
            res = X.check(doc, last, mine, rng)
        res["src_name"], res["src_how"] = fname, how
        res["rule"], res["rule_kind"] = XP.rule_text(*rng), kind
        res["stamp"] = stp          # 조건·고치기가 바뀌면 보드가 뒤에서 다시 점검(건 화면을 안 열어도)
        with db_session() as c:
            c.execute("INSERT INTO export_ship_check(invoice_no, src, src_key, result, at) VALUES(?,?,?,?,?) "
                      "ON CONFLICT(invoice_no) DO UPDATE SET src=excluded.src, src_key=excluded.src_key, result=excluded.result, at=excluded.at",
                      (no, fname, key, json.dumps(res, ensure_ascii=False), kst_now().strftime("%Y-%m-%d %H:%M:%S")))
        return res, how

    async def run_check(no, force=False):
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(compute_check, no, force)

    def warm_checks(nos):
        """보드 카드의 금액·점검 표시 — 아직 점검 안 한 진행 중 건을 뒤에서 점검해 둔다(보드를 늦추지 않게 · 한 번에 한 줄기)."""
        if not nos or not _BG_LOCK.acquire(blocking=False):
            return

        def run():
            try:
                for n in nos[:12]:
                    try:
                        compute_check(n)
                    except Exception as e:
                        log.warning("export warm check fail %s: %s", n, e)
            finally:
                _BG_LOCK.release()
        threading.Thread(target=run, daemon=True, name="export-warm-check").start()

    # ---------------- 건 한 장 ----------------
    @app.get("/export/s/{no}", response_class=HTMLResponse)
    async def export_ship_page(req: Request, no: str):
        u = guard(req)
        if not u:
            return RedirectResponse("/home?no_perm=page" if _gu199(req) else "/login", 303)   # z1191z199: 권한 없음 안내(chrome ?no_perm=) · 말없이 홈으로 보내지 않음
        if not INV_OK.match(no or ""):
            return RedirectResponse("/export", 303)
        try:
            await run_check(no)
        except Exception as e:      # 점검이 멈춰도 건 화면은 연다(점검 칸에 까닭)
            log.warning("export check fail %s: %s", no, e)
        with db_session() as c:
            S = collect(c)
            s = S.get(no)
            if not s:
                return RedirectResponse("/export?err=none", 303)
            files = [dict(r) for r in c.execute("SELECT * FROM export_ship_file WHERE invoice_no=? ORDER BY id DESC", (no,))]
            for f in files:
                f["kind_name"] = dict(FILE_KINDS).get(f["kind"], f["kind"])
                f["by_name"] = udisp(c, f["by_user"]) if f["by_user"] else ""
                f["size_txt"] = "%.1fMB" % (f["size"] / 1048576) if (f["size"] or 0) >= 1048576 else "%dKB" % max(1, (f["size"] or 0) // 1024)
            hist = [dict(r) for r in c.execute("SELECT * FROM export_ship_log WHERE invoice_no=? ORDER BY id DESC LIMIT 60", (no,))]
            for h in hist:
                h["by_name"] = udisp(c, h["by_user"]) if h["by_user"] else "시스템"
            for lg in s["logs"]:
                lg["filled_name"] = udisp(c, lg.get("filled_by")) if lg.get("filled_by") else ""
                lg["reply_name"] = udisp(c, lg.get("reply_by")) if lg.get("reply_by") else ""
                lg["has_file"] = bool(lg.get("stored")) and os.path.exists(os.path.join(_hs_dir(), lg["stored"]))
            # z1191z86: ① 받기에서 넘어왔으면(아직 안 고른 줄) — 다 고르면 그 파일을 바로 받게
            need = 0
            try:
                need = int(req.query_params.get("need") or 0)
            except ValueError:
                need = 0
            if need and not any(lg.get("id") == need and lg.get("has_file") for lg in s["logs"]):
                need = 0
            rs = XP.rules(c)
        ck = s["check"] or {}
        cur = {k: s["ship"].get(k) for k, _n, _t in FIELDS}
        px = {"no": no, "rows": s.get("px") or [], "rule": ck.get("rule") or XP.rule_text(*XP.tol(rs, s["kind"])),
              "kind": s["kind"], "reasons": list(XP.REASONS), "need": need}
        return ctx(req, "export_ship.html", user=u, active="export", s=s, files=files, hist=hist, fields=FIELDS,
                   cur=cur, cur_json=json.dumps(cur, ensure_ascii=False), stages=STAGES, file_kinds=FILE_KINDS,
                   ck=ck, px_json=json.dumps(px, ensure_ascii=False).replace("</", "<\\/"))

    @app.post("/export/s/{no}/check")
    async def export_ship_recheck(req: Request, no: str):
        u = guard(req)
        if not u:
            return JSONResponse({"ok": False, "error": "권한 없음"}, 403)
        if not INV_OK.match(no or ""):
            return JSONResponse({"ok": False, "error": "번호가 이상합니다"}, 400)
        res, how = await run_check(no, force=True)
        return JSONResponse({"ok": bool(res), "how": how})

    def _clean(k, t, v):
        v = "" if v is None else str(v).strip()
        if v == "":
            return None
        if t == "day":
            if not re.match(r"^20\d\d-\d\d-\d\d$", v):
                raise ValueError("%s 날짜 모양이 이상합니다(예: 2026-11-20)" % FNAME[k])
            return v
        if t == "num":
            try:
                return float(v.replace(",", ""))
            except ValueError:
                raise ValueError("%s 에는 숫자만 적어 주세요" % FNAME[k])
        if t.startswith("pick:"):
            if v not in t[5:].split("|"):
                raise ValueError("%s 고를 수 있는 값이 아닙니다" % FNAME[k])
            return v
        return v[:300]

    def _same(a, b):
        if a in (None, "") and b in (None, ""):
            return True
        try:
            return float(a) == float(b)
        except (TypeError, ValueError):
            return str(a) == str(b)

    @app.post("/export/s/{no}/save")
    async def export_ship_save(req: Request, no: str):
        u = guard(req)
        if not u:
            return JSONResponse({"ok": False, "error": "권한 없음"}, 403)
        if not INV_OK.match(no or ""):
            return JSONResponse({"ok": False, "error": "번호가 이상합니다"}, 400)
        try:
            body = await req.json()
        except Exception:
            return JSONResponse({"ok": False, "error": "보낸 값을 읽지 못했습니다"}, 400)
        old, new = body.get("old") or {}, body.get("new") or {}
        types = {k: t for k, _n, t in FIELDS}
        try:
            clean = {k: _clean(k, types[k], v) for k, v in new.items() if k in types}
        except ValueError as e:
            return JSONResponse({"ok": False, "error": str(e)}, 400)
        if clean.get("etd") and clean.get("eta") and clean["eta"] < clean["etd"]:
            return JSONResponse({"ok": False, "error": "도착(ETA)이 출발(ETD)보다 앞입니다"}, 400)
        ts = kst_now().strftime("%Y-%m-%d %H:%M:%S")
        with db_session() as c:
            ensure(c)
            S = collect(c)
            if no not in S:
                return JSONResponse({"ok": False, "error": "그런 선적 건이 없습니다"}, 404)
            row = S[no]["ship"]
            for k in clean:
                if not _same(row.get(k), old.get(k)):
                    return JSONResponse({"ok": False, "conflict": True,
                                         "error": "그사이 다른 사람이 「%s」을(를) 바꿨습니다 — 화면을 새로 열어 확인해 주세요" % FNAME[k]}, 409)
            chg = {k: v for k, v in clean.items() if not _same(row.get(k), v)}
            if not chg:
                return JSONResponse({"ok": True, "n": 0})
            if not row:
                c.execute("INSERT INTO export_ship(invoice_no, kind, inv_date, created_by, created_at) VALUES(?,?,?,?,?)",
                          (no, S[no]["kind"], S[no]["inv_date"], u.get("id"), ts))
            c.execute("UPDATE export_ship SET %s, updated_by=?, updated_at=? WHERE invoice_no=?" % ", ".join("%s=?" % k for k in chg),
                      list(chg.values()) + [u.get("id"), ts, no])
            for k, v in chg.items():
                c.execute("INSERT INTO export_ship_log(invoice_no, field, old_value, new_value, by_user, at) VALUES(?,?,?,?,?,?)",
                          (no, FNAME[k], "" if row.get(k) is None else str(row.get(k)), "" if v is None else str(v), u.get("id"), ts))
        return JSONResponse({"ok": True, "n": len(chg)})

    @app.post("/export/s/{no}/close")
    async def export_ship_close(req: Request, no: str):
        """마감 / 마감 풀기 — 송금 칸이 없는 건(무상 · 샘플 · 이미 정산)도 끝낼 수 있게."""
        u = guard(req)
        if not u:
            return JSONResponse({"ok": False, "error": "권한 없음"}, 403)
        if not INV_OK.match(no or ""):
            return JSONResponse({"ok": False, "error": "번호가 이상합니다"}, 400)
        form = await req.form()
        to = 1 if str(form.get("to") or "1") == "1" else 0
        ts = kst_now().strftime("%Y-%m-%d %H:%M:%S")
        with db_session() as c:
            ensure(c)
            S = collect(c)
            if no not in S:
                return JSONResponse({"ok": False, "error": "그런 선적 건이 없습니다"}, 404)
            if not S[no]["ship"]:
                c.execute("INSERT INTO export_ship(invoice_no, kind, inv_date, created_by, created_at) VALUES(?,?,?,?,?)",
                          (no, S[no]["kind"], S[no]["inv_date"], u.get("id"), ts))
            c.execute("UPDATE export_ship SET closed=?, updated_by=?, updated_at=? WHERE invoice_no=?", (to, u.get("id"), ts, no))
            c.execute("INSERT INTO export_ship_log(invoice_no, field, old_value, new_value, by_user, at) VALUES(?,?,?,?,?,?)",
                      (no, "마감", "" if to else "마감", "마감" if to else "다시 진행", u.get("id"), ts))
        return RedirectResponse("/export/s/" + no, 303)

    # ---------------- 서류철 ----------------
    @app.post("/export/s/{no}/file")
    async def export_ship_file_up(req: Request, no: str):
        u = guard(req)
        if not u:
            return JSONResponse({"ok": False, "error": "권한 없음"}, 403)
        if not INV_OK.match(no or ""):
            return JSONResponse({"ok": False, "error": "번호가 이상합니다"}, 400)
        form = await req.form()
        kind = str(form.get("kind") or "etc")
        if kind not in dict(FILE_KINDS):
            kind = "etc"
        f = form.get("file")
        fname = os.path.basename(getattr(f, "filename", "") or "") if f is not None else ""
        if not fname:
            return JSONResponse({"ok": False, "error": "파일을 골라 주세요"}, 400)
        ext = os.path.splitext(fname)[1].lower()
        if ext not in FILE_EXT:
            return JSONResponse({"ok": False, "error": "엑셀 · PDF · 사진(jpg·png)만 됩니다"}, 400)
        if kind == "invoice" and ext not in (".xlsx", ".xlsm"):
            return JSONResponse({"ok": False, "error": "최종 인보이스·패킹은 엑셀(.xlsx) 파일로 올려 주세요 — 점검에 씁니다"}, 400)
        raw = await f.read()
        if not raw:
            return JSONResponse({"ok": False, "error": "빈 파일입니다"}, 400)
        if len(raw) > FILE_MAX_MB * 1048576:
            return JSONResponse({"ok": False, "error": "파일이 너무 큽니다(%dMB 넘음)" % FILE_MAX_MB}, 400)
        os.makedirs(_ship_dir(), exist_ok=True)
        stored = secrets.token_hex(16) + ext
        with open(os.path.join(_ship_dir(), stored), "wb") as fo:
            fo.write(raw)
        ts = kst_now().strftime("%Y-%m-%d %H:%M:%S")
        with db_session() as c:
            ensure(c)
            S = collect(c)
            if no not in S:
                try:
                    os.remove(os.path.join(_ship_dir(), stored))
                except OSError:
                    pass
                return JSONResponse({"ok": False, "error": "그런 선적 건이 없습니다"}, 404)
            c.execute("INSERT INTO export_ship_file(invoice_no, kind, file_name, stored, size, by_user, at) VALUES(?,?,?,?,?,?,?)",
                      (no, kind, fname, stored, len(raw), u.get("id"), ts))
            c.execute("INSERT INTO export_ship_log(invoice_no, field, old_value, new_value, by_user, at) VALUES(?,?,?,?,?,?)",
                      (no, "서류철", "", "%s 올림 — %s" % (dict(FILE_KINDS)[kind], fname), u.get("id"), ts))
        if kind == "invoice":
            try:
                await run_check(no, force=True)
            except Exception as e:
                log.warning("export check after upload fail %s: %s", no, e)
        return JSONResponse({"ok": True})

    @app.get("/export/s/{no}/file/{fid:int}")
    async def export_ship_file_get(req: Request, no: str, fid: int):
        u = guard(req)
        if not u:
            return RedirectResponse("/home?no_perm=page" if _gu199(req) else "/login", 303)   # z1191z199: 권한 없음 안내(chrome ?no_perm=) · 말없이 홈으로 보내지 않음
        with db_session() as c:
            ensure(c)
            r = c.execute("SELECT * FROM export_ship_file WHERE id=? AND invoice_no=?", (fid, no)).fetchone()
        if not r:
            return HTMLResponse("파일이 없습니다", 404)
        p = os.path.join(_ship_dir(), r["stored"])
        if not os.path.exists(p):
            return HTMLResponse("파일이 서버에 없습니다", 404)
        return FileResponse(p, filename=r["file_name"])

    # ---------------- z1191z86 단가 범위 밖 줄 — 허용 / 고치기 고르기 ----------------
    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @app.post("/export/price-ack")
    async def export_price_ack(req: Request):
        """{invoice_no, items:[{key, now, desc, last, last_inv, diff, decision: allow|fix|'', reason}]} — 줄마다 한 번 고른다(''= 고른 것 지움)."""
        u = guard(req)
        if not u:
            return JSONResponse({"ok": False, "error": "권한 없음"}, 403)
        try:
            body = await req.json()
        except Exception:
            body = None
        if not isinstance(body, dict):
            return JSONResponse({"ok": False, "error": "보낸 값을 읽지 못했습니다"}, 400)
        no = str(body.get("invoice_no") or "").strip()
        items = body.get("items") or []
        if not INV_OK.match(no):
            return JSONResponse({"ok": False, "error": "인보이스 번호를 읽지 못한 파일이라 고른 것을 남길 수 없습니다 — 번호를 적은 파일로 다시 올려 주세요"}, 400)
        if not isinstance(items, list) or not items or len(items) > 2000:
            return JSONResponse({"ok": False, "error": "고를 줄이 없습니다"}, 400)
        clean = []
        for it in items:
            if not isinstance(it, dict):
                return JSONResponse({"ok": False, "error": "잘못된 요청입니다"}, 400)
            dec = str(it.get("decision") or "")
            reason = str(it.get("reason") or "").strip()[:200]
            key, pk = str(it.get("key") or "")[:300], XP.pkey(it.get("now"))
            if dec not in ("allow", "fix", "") or not key or not pk:
                return JSONResponse({"ok": False, "error": "잘못된 요청입니다"}, 400)
            if dec == "allow" and not reason:
                return JSONResponse({"ok": False, "error": "허용하는 까닭을 골라 주세요"}, 400)
            clean.append((key, pk, dec, reason, str(it.get("desc") or "")[:200], _num(it.get("last")),
                          str(it.get("last_inv") or "")[:40], _num(it.get("diff"))))
        ts = kst_now().strftime("%Y-%m-%d %H:%M:%S")
        out = []
        with db_session() as c:
            XP.ensure(c)
            ensure(c)
            for key, pk, dec, reason, desc, last, last_inv, diff in clean:
                old = c.execute("SELECT decision, reason FROM export_price_ack WHERE invoice_no=? AND part_key=? AND price_key=?",
                                (no, key, pk)).fetchone()
                oldtxt = ("허용 — " + (old["reason"] or "") if old["decision"] == "allow" else "고치기") if old else ""
                if dec:
                    c.execute("INSERT INTO export_price_ack(invoice_no, part_key, price_key, descr, base_price, base_invoice, diff, decision, reason, by_user, at) "
                              "VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(invoice_no, part_key, price_key) DO UPDATE SET "
                              "decision=excluded.decision, reason=excluded.reason, by_user=excluded.by_user, at=excluded.at, "
                              "descr=excluded.descr, base_price=excluded.base_price, base_invoice=excluded.base_invoice, diff=excluded.diff",
                              (no, key, pk, desc, last, last_inv, diff, dec, reason if dec == "allow" else "", u.get("id"), ts))
                else:
                    c.execute("DELETE FROM export_price_ack WHERE invoice_no=? AND part_key=? AND price_key=?", (no, key, pk))
                newtxt = ("허용 — " + reason) if dec == "allow" else ("고치기" if dec == "fix" else "고른 것 지움")
                if newtxt != oldtxt:
                    c.execute("INSERT INTO export_ship_log(invoice_no, field, old_value, new_value, by_user, at) VALUES(?,?,?,?,?,?)",
                              (no, "단가 확인", oldtxt, "%s 이번 %s (지난번 %s %s · %+.1f%%) → %s" % (
                                  desc[:40], ("%g" % float(pk)), ("%g" % last) if last is not None else "?", last_inv,
                                  diff if diff is not None else 0.0, newtxt), u.get("id"), ts))
                out.append({"key": key, "now": pk, "decision": dec, "reason": reason if dec == "allow" else "",
                            "at": ts[:16], "by_name": udisp(c, u.get("id")) if dec else ""})
        return JSONResponse({"ok": True, "items": out})

    # ---------------- z1191z86 단가 점검 조건(사용자가 정함) ----------------
    def _hist_diffs(c):
        """지난 수출 이력에서 같은 규격이 다시 나갈 때의 단가 변화(%) — 구분마다 · 조건을 고를 때 「이 조건이면 몇 줄」 미리 보기용."""
        out = {k: [] for k in XP.KINDS}
        if not _has(c, "export_hist_line"):
            return out
        fx = XP.fixed(c)
        last = {}
        for r in c.execute("SELECT part_key, kind, invoice_no, unit_price FROM export_hist_line WHERE unit_price>0 AND COALESCE(part_key,'')<>'' "
                           "ORDER BY part_key, IFNULL(inv_date,''), invoice_no, id"):
            if (r["invoice_no"], r["part_key"], XP.pkey(r["unit_price"])) in fx:
                continue
            pv = last.get(r["part_key"])
            if pv and pv[0] != r["invoice_no"] and _kind(r["kind"]) in out:
                out[_kind(r["kind"])].append(round((r["unit_price"] - pv[1]) / pv[1] * 100, 1))
            last[r["part_key"]] = (r["invoice_no"], r["unit_price"])
        return out

    @app.get("/export/rules", response_class=HTMLResponse)
    async def export_rules_page(req: Request):
        u = guard(req)
        if not u:
            return RedirectResponse("/home?no_perm=page" if _gu199(req) else "/login", 303)   # z1191z199: 권한 없음 안내(chrome ?no_perm=) · 말없이 홈으로 보내지 않음
        with db_session() as c:
            rs = XP.rules(c)
            for k in rs:
                rs[k]["by_name"] = udisp(c, rs[k]["by"]) if rs[k]["by"] else ""
            logs = [dict(r) for r in c.execute("SELECT * FROM export_price_rule_log ORDER BY id DESC LIMIT 30")]
            for lg in logs:
                lg["by_name"] = udisp(c, lg["by_user"]) if lg["by_user"] else ""
            diffs = _hist_diffs(c)
            acks = [dict(r) for r in c.execute("SELECT * FROM export_price_ack ORDER BY at DESC LIMIT 30")]
            for a in acks:
                a["by_name"] = udisp(c, a["by_user"]) if a["by_user"] else ""
        cur = {k: {"up": rs[k]["up"], "down": rs[k]["down"]} for k in XP.KINDS}
        return ctx(req, "export_rules.html", user=u, active="export", kinds=XP.KINDS, rs=rs, logs=logs, acks=acks,
                   cur_json=json.dumps(cur, ensure_ascii=False), diffs_json=json.dumps(diffs, ensure_ascii=False), default_pct=XP.DEFAULT_PCT)

    def _pct(v, nm):
        v = "" if v is None else str(v).strip().replace("%", "")
        if v == "":
            return None
        try:
            x = float(v)
        except ValueError:
            raise ValueError("%s 에는 숫자(%%)만 적어 주세요" % nm)
        if not (0 <= x <= XP.MAX_PCT):
            raise ValueError("%s 은 0 ~ %g 사이로 적어 주세요" % (nm, XP.MAX_PCT))
        return round(x, 2)

    @app.post("/export/rules")
    async def export_rules_save(req: Request):
        """{old:{구분:{up,down}}, new:{구분:{up,down}}} — 빈칸 = 그쪽은 안 봄 · 그사이 다른 사람이 바꿨으면 409."""
        u = guard(req)
        if not u:
            return JSONResponse({"ok": False, "error": "권한 없음"}, 403)
        try:
            body = await req.json()
        except Exception:
            body = None
        if not isinstance(body, dict) or not isinstance(body.get("new"), dict):
            return JSONResponse({"ok": False, "error": "보낸 값을 읽지 못했습니다"}, 400)
        new, old = {}, body.get("old") if isinstance(body.get("old"), dict) else {}
        try:
            for k in XP.KINDS:
                v = body["new"].get(k)
                if isinstance(v, dict):
                    new[k] = (_pct(v.get("up"), k + " 오름"), _pct(v.get("down"), k + " 내림"))
        except ValueError as e:
            return JSONResponse({"ok": False, "error": str(e)}, 400)
        if not new:
            return JSONResponse({"ok": False, "error": "바꿀 조건이 없습니다"}, 400)
        ts = kst_now().strftime("%Y-%m-%d %H:%M:%S")
        changed = 0
        with db_session() as c:
            rs = XP.rules(c)
            for k, (up, down) in new.items():
                o = old.get(k) if isinstance(old.get(k), dict) else {}
                try:
                    o_cur = (_pct(o.get("up"), k), _pct(o.get("down"), k))
                except ValueError:
                    o_cur = ("?", "?")
                if o_cur != (rs[k]["up"], rs[k]["down"]):
                    return JSONResponse({"ok": False, "error": "그사이 다른 사람이 조건을 바꿨습니다 — 화면을 새로 열어 확인해 주세요"}, 409)
            for k, (up, down) in new.items():
                if (up, down) == (rs[k]["up"], rs[k]["down"]):
                    continue
                c.execute("UPDATE export_price_rule SET up_pct=?, down_pct=?, updated_by=?, updated_at=? WHERE kind=?", (up, down, u.get("id"), ts, k))
                c.execute("INSERT INTO export_price_rule_log(kind, old_value, new_value, by_user, at) VALUES(?,?,?,?,?)",
                          (k, XP.rule_text(rs[k]["up"], rs[k]["down"]), XP.rule_text(up, down), u.get("id"), ts))
                changed += 1
        if changed:
            # 화면 약속 「진행 중인 건도 다시 점검」 — 보드를 열기 전에 뒤에서 미리(한 줄기 · 막혀 있으면 보드가 열릴 때)
            with db_session() as c:
                S = collect(c)
            warm_checks([s["invoice_no"] for s in S.values() if not s["old"] and s["stage"] < 5 and (s["logs"] or s["ship"])])
        return JSONResponse({"ok": True, "changed": changed})
