# WORKS KNK VINA 추가 발주 14건 거래구분 → 수출 (z1186 · 2026-10-16 · 이새롬 프로 확인 「다 KNKVINA 거래 건이며 수출입니다」)
#
#   무엇을: 드림텍(아산) 프로젝트에 추가로 들어온 KNK VINA 발주 14건(T-260622-5·-6 · T-261001-3~11 · T-261002-3~5)의
#           호기 거래구분을 '수출'로 바꿉니다. 지금은 비어서 프로젝트 값(내수)을 따르거나 '내수'로 적혀 있습니다.
#   안 건드림: 발주처·금액·상태·날짜·거래명세서·계산서 칸 · 그 밖의 모든 수주
#   지키는 것: 바꾸기 전 원문을 서버 data/backups/fix14_z1186_<시각>.json 에 남깁니다. 하나라도 예상과 다르면 아무것도 안 바꿉니다.
#   ⚠ 출하 끝난 2건(T-260622-5·-6)은 거래명세서 날짜·계산서 칸이 적혀 있습니다 — 거래구분이 수출이 되면 납품·수금 화면의 부가세 표시가 영세율로 바뀝니다.
#
# 그냥 실행하면 **확인만** 합니다(아무것도 바꾸지 않음).
# 실제로 바꾸려면 뒤에 -Apply 를 붙이세요.
#
#   확인 :  powershell -ExecutionPolicy Bypass -File "이 파일"
#   적용 :  powershell -ExecutionPolicy Bypass -File "이 파일" -Apply
param([switch]$Apply)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$mode = "CHECK"
if ($Apply) { $mode = "APPLY" }

Write-Host ""
Write-Host "=== WORKS KNK VINA 추가 발주 14건 거래구분 → 수출 ($mode) ===" -ForegroundColor Cyan
Write-Host ""

$py = @'
# -*- coding: utf-8 -*-
# WORKS KNK VINA 추가 발주 14건 거래구분 → 수출 (z1186 · 2026-10-16 · 이새롬 프로 확인 「다 KNKVINA 거래 건이며 수출입니다」)
#   대상: 드림텍(아산) 프로젝트에 추가로 들어온 KNK VINA 발주 14건 — 호기 거래구분이 비어 프로젝트 값(내수)을 물려받았거나 '내수'로 적혀 있음
#   하는 일: 그 14개 수주의 호기 거래구분(order_items.is_export)만 1(수출)로. 발주처·금액·상태·날짜·계산서 칸은 안 건드린다.
#   CHECK = 확인만(아무것도 안 바꿈) · APPLY = 바꿈(한 연결에서 한 번에 · 바꾸기 전 원문을 data/backups/fix14_z1186_<시각>.json 에 남김)
#   하나라도 예상과 다르면(수주 없음 · 발주처가 KNK VINA 아님 · 취소 · 호기 0) 아무것도 안 바꾸고 멈춘다.
import datetime
import json
import os
import sqlite3
import sys

for _s in (sys.stdout, sys.stderr):   # -I 는 PYTHONIOENCODING 을 무시한다 → 여기서 utf-8 로
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("KNK_FIX14_ROOT", "/opt/knk_haist")
DB = ROOT + "/data/knk.db"
VINA_NAME = "KNK VINA"
TARGETS = ["T-260622-5", "T-260622-6", "T-261001-3", "T-261001-4", "T-261001-5", "T-261001-6", "T-261001-7",
           "T-261001-8", "T-261001-9", "T-261001-10", "T-261001-11", "T-261002-3", "T-261002-4", "T-261002-5"]


def main(mode):
    if mode not in ("CHECK", "APPLY"):
        print("쓰는 법: CHECK | APPLY")
        return 2
    if not os.path.exists(DB):
        print("멈춤: DB 가 없습니다:", DB)
        return 3
    ro = (mode != "APPLY")
    con = sqlite3.connect(("file:%s?mode=ro" % DB) if ro else DB, uri=ro, timeout=30)
    con.row_factory = sqlite3.Row
    problems, plan = [], []
    for no in TARGETS:
        o = con.execute("SELECT o.id, o.order_no, o.status, o.currency, o.total_amount, o.customer_id, "
                        "COALESCE(cu.alias, cu.name, '') AS cust, p.mgmt_code, COALESCE(p.is_export,0) AS p_exp "
                        "FROM orders o LEFT JOIN customers cu ON cu.id=o.customer_id LEFT JOIN projects p ON p.id=o.project_id "
                        "WHERE o.order_no=?", (no,)).fetchall()
        if len(o) != 1:
            problems.append("%s: 수주가 %d건(1건이어야 함)" % (no, len(o)))
            continue
        o = o[0]
        if (o["cust"] or "").strip() != VINA_NAME:
            problems.append("%s: 발주처가 %r (KNK VINA 아님)" % (no, o["cust"]))
        if str(o["status"] or "").upper() == "CANCELLED":
            problems.append("%s: 취소된 수주" % no)
        its = con.execute("SELECT id, unit_label, is_export, COALESCE(unit_status,'') AS st, statement_date, "
                          "tax_invoice_date, tax_invoice_amt1 FROM order_items WHERE order_id=? ORDER BY id", (o["id"],)).fetchall()
        if not its:
            problems.append("%s: 호기 0개" % no)
        plan.append({"order_id": o["id"], "order_no": no, "mgmt_code": o["mgmt_code"], "status": o["status"],
                     "currency": o["currency"], "amount": o["total_amount"], "cust": o["cust"], "project_is_export": o["p_exp"],
                     "items": [dict(i) for i in its]})
    n_items = sum(len(x["items"]) for x in plan)
    n_change = sum(1 for x in plan for i in x["items"] if i["is_export"] != 1)
    print("대상 수주 %d건 · 호기 %d개 · 바뀔 호기 %d개(지금 내수 또는 빈칸 → 수출)" % (len(plan), n_items, n_change))
    for x in plan:
        now = sorted({("수출" if i["is_export"] == 1 else ("내수" if i["is_export"] == 0 else "빈칸(→프로젝트 내수)")) for i in x["items"]})
        bill = sum(1 for i in x["items"] if i["statement_date"] or i["tax_invoice_date"] or i["tax_invoice_amt1"])
        print("  %-12s %-9s %-9s %s %12s · 호기 %2d · 지금 %s%s" % (
            x["order_no"], x["mgmt_code"], x["status"], x["currency"], "{:,.2f}".format(x["amount"] or 0), len(x["items"]),
            "/".join(now), (" · ⚠ 명세서·계산서 칸 적힌 호기 %d" % bill) if bill else ""))
    if problems:
        print("멈춤: 예상과 다른 것이 있어 아무것도 바꾸지 않습니다 —")
        for p in problems:
            print("  -", p)
        con.close()
        return 4
    if n_change == 0:
        print("바꿀 것이 없습니다(이미 모두 수출).")
        con.close()
        return 0
    if mode == "CHECK":
        print("확인만 했습니다(아무것도 바꾸지 않음). 바꾸려면 -Apply 를 붙여 다시 실행하세요.")
        con.close()
        return 0

    bdir = ROOT + "/data/backups"
    os.makedirs(bdir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bpath = "%s/fix14_z1186_%s.json" % (bdir, ts)
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump({"when": ts, "what": "order_items.is_export -> 1 (KNK VINA 추가 발주 14건)", "orders": plan}, f, ensure_ascii=False, indent=1)
    print("원문 저장:", bpath)
    ids = [x["order_id"] for x in plan]
    q = ",".join("?" * len(ids))
    try:
        con.execute("BEGIN")
        cur = con.execute("UPDATE order_items SET is_export=1 WHERE order_id IN (%s) AND COALESCE(is_export,-1)<>1" % q, ids)
        if cur.rowcount != n_change:
            con.execute("ROLLBACK")
            print("멈춤: 바뀐 호기 수(%d)가 예상(%d)과 다릅니다 — 모두 되돌렸습니다." % (cur.rowcount, n_change))
            con.close()
            return 5
        con.execute("COMMIT")
    except Exception as e:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        print("멈춤: 바꾸다 오류 — 모두 되돌렸습니다:", str(e)[:200])
        con.close()
        return 6
    left = con.execute("SELECT COUNT(*) FROM order_items WHERE order_id IN (%s) AND COALESCE(is_export,-1)<>1" % q, ids).fetchone()[0]
    con.close()
    print("바꿈: 호기 %d개 → 수출 · 남은 내수/빈칸 %d" % (n_change, left))
    return 0 if left == 0 else 7


if __name__ == "__main__":
    sys.exit(main((sys.argv[1] if len(sys.argv) > 1 else "CHECK").upper()))
'@

# 파이프로 그냥 보내면 한글이 CP949 로 바뀌며 깨진다 → base64 로 실어 보낸다(10-13 호기 비고 되돌리기와 같은 방식)
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
ssh -p 32201 root@o.knknara.co.kr "echo $b64 | base64 -d > /tmp/_fix14.py; PYTHONIOENCODING=utf-8 /opt/knk_haist/.venv/bin/python -I /tmp/_fix14.py $mode; rc=`$?; rm -f /tmp/_fix14.py; exit `$rc"
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "끝났습니다." -ForegroundColor Green
} else {
    Write-Host "멈췄습니다(코드 $rc). 위 화면을 빅터에게 보여 주세요." -ForegroundColor Yellow
}
