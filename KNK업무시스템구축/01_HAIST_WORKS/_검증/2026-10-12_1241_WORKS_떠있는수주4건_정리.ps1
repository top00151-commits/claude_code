# WORKS 떠 있는 수주 4건 정리 (2026-10-12 · 대표 선택 「정리 스크립트를 대표님이 실행」 · 이새롬 프로 「4건 모두 삭제해도 된다」)
#
#   지움: 프로젝트에 붙지 않은 수주 4건 — M-260305-1 · M-260305-3 · M-260414-1 · T-260605-2
#         (7/6·7/15 일괄 등록 때 남은 예전 것 · 7/22·8/3 에 프로젝트로 다시 등록됨 · 딸린 품목·출하·계산서·수금 0)
#   남김: 다시 등록된 수주 7건(002M2602 · 005M2602 · 004T2510)과 그 밖의 모든 자료
#   방법: WORKS 의 수주 삭제 기능(delete_order)을 그대로 씀 · 4건을 한 번에 · 하나라도 실패하면 모두 되돌림
#         지우기 전에 4건 원문(모든 칸)을 서버 data/backups/floatso_4rows_<시각>.json 에 남김
#
# 그냥 실행하면 **확인만** 합니다(아무것도 지우지 않음).
# 실제로 지우려면 뒤에 -Apply 를 붙이세요.
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
Write-Host "=== WORKS 떠 있는 수주 4건 정리 ($mode) ===" -ForegroundColor Cyan
Write-Host ""

$py = @'
# -*- coding: utf-8 -*-
# WORKS 떠 있는 수주 4건 정리 (2026-10-12 · 대표 「정리 스크립트를 대표님이 실행」 · 이새롬 프로 「4건 모두 삭제해도 된다」)
#   지우는 것: 프로젝트에 붙지 않은 수주 4건 — 7/6·7/15 일괄 등록 때 남은 예전 것(7/22·8/3 에 프로젝트로 다시 등록됨)
#   남는 것 : 다시 등록된 수주 7건(002M2602 · 005M2602 · 004T2510)과 그 밖의 모든 자료
#   CHECK = 확인만(아무것도 안 지움) · APPLY = 지움(WORKS 의 수주 삭제 기능 delete_order 를 그대로 씀 · 4건을 한 번에 · 하나라도 실패하면 모두 되돌림)
import datetime
import json
import sqlite3
import sys

ROOT = "/opt/knk_haist"
DB = ROOT + "/data/knk.db"

# 지울 수주: id → (수주번호, 고객 id, 금액, 대수)
TARGETS = {
    2561: ("M-260305-1", 1, 1693300000.0, 7),
    2581: ("M-260305-3", 1, 1451400000.0, 6),
    2565: ("M-260414-1", 1, 995600000.0, 7),
    2161: ("T-260605-2", 50, 5500000.0, 1),
}
# 남는 짝(나중에 프로젝트로 다시 등록된 수주): 지울 id → [남는 id]
TWINS = {
    2561: [2597, 2599, 2600],
    2581: [2598],
    2565: [2607, 2608],
    2161: [2648],
}


def won(v):
    return "{:,.0f}원".format(float(v or 0))


def child_tables(c):
    """order_id 칸이 있는 표(orders 제외) — WORKS delete_order 가 지우는 범위와 같다."""
    out = []
    for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
        if t in ("orders", "sqlite_sequence"):
            continue
        cols = [r[1] for r in c.execute("PRAGMA table_info(%s)" % t).fetchall()]
        if "order_id" in cols:
            out.append(t)
    return out


def name_of(c, table, rid):
    if rid is None:
        return ""
    try:
        r = c.execute("SELECT name FROM %s WHERE id=?" % table, (rid,)).fetchone()
        return (r[0] if r else "") or ""
    except sqlite3.Error:
        return ""


def inspect(c):
    """지우기 전 확인. 문제가 하나라도 있으면 problems 에 담는다(그러면 지우지 않는다)."""
    problems, rows, twins = [], {}, {}
    for oid, (no, cust, amt, qty) in TARGETS.items():
        r = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if r is None:
            problems.append("%s(%d): 수주가 없습니다(이미 지워졌을 수 있음)" % (no, oid))
            continue
        r = dict(r)
        rows[oid] = r
        if r.get("order_no") != no:
            problems.append("%d: 수주번호가 %s 가 아니라 %s" % (oid, no, r.get("order_no")))
        if r.get("customer_id") != cust:
            problems.append("%s: 고객이 바뀜(%s)" % (no, r.get("customer_id")))
        if abs(float(r.get("total_amount") or 0) - amt) > 0.5:
            problems.append("%s: 금액이 바뀜(%s)" % (no, won(r.get("total_amount"))))
        if int(r.get("unit_qty") or 0) != qty:
            problems.append("%s: 대수가 바뀜(%s)" % (no, r.get("unit_qty")))
        if r.get("project_id") is not None:
            problems.append("%s: 프로젝트(%s)에 붙어 있음" % (no, r.get("project_id")))
        twins[oid] = []
        for tid in TWINS[oid]:
            t = c.execute(
                "SELECT o.id, o.order_no, o.project_id, o.total_amount, o.unit_qty, o.status, p.mgmt_code "
                "FROM orders o LEFT JOIN projects p ON p.id=o.project_id WHERE o.id=?", (tid,)).fetchone()
            if t is None or t["project_id"] is None:
                problems.append("%s: 남아야 할 짝 수주(%d)가 없거나 프로젝트에 안 붙어 있음" % (no, tid))
            else:
                twins[oid].append(dict(t))
    ids = tuple(TARGETS)
    child = {}
    for t in child_tables(c):
        n = c.execute("SELECT COUNT(*) FROM %s WHERE order_id IN (%s)" % (t, ",".join("?" * len(ids))), ids).fetchone()[0]
        if n:
            child[t] = n
    if child:
        problems.append("딸린 자료가 있음: %s" % child)
    n_free = c.execute("SELECT COUNT(*) FROM orders WHERE project_id IS NULL").fetchone()[0]
    return rows, twins, child, n_free, problems


def report(c, rows, twins, child, n_free):
    print("[지울 수주 %d건] (프로젝트 없음 · 딸린 자료 %s)" % (len(rows), "0" if not child else child))
    for oid, r in rows.items():
        print("   %-11s %-12s %d대 %16s  %-13s 등록 %s (%s)" % (
            r.get("order_no"), name_of(c, "customers", r.get("customer_id")), int(r.get("unit_qty") or 0),
            won(r.get("total_amount")), r.get("status"), str(r.get("created_at") or "")[:16],
            name_of(c, "users", r.get("created_by"))))
        for t in twins.get(oid, []):
            print("        └ 남는 짝  %s %-12s %d대 %16s  %s" % (
                t["mgmt_code"], t["order_no"], int(t["unit_qty"] or 0), won(t["total_amount"]), t["status"]))
    print("프로젝트 없는 수주(전체): %d건" % n_free)


def delete_all(c, delete_order):
    """4건을 WORKS 의 delete_order 로 지운다. 하나라도 실패하면 예외 → 부른 쪽 연결이 모두 되돌린다."""
    done = []
    for oid in TARGETS:
        res = delete_order(c, oid, restore_project=True)
        if not (res or {}).get("ok"):
            raise RuntimeError("%d 삭제 실패: %s" % (oid, (res or {}).get("message")))
        done.append((oid, res.get("message")))
    return done


def verify_after(c):
    ids = tuple(TARGETS)
    left = c.execute("SELECT COUNT(*) FROM orders WHERE id IN (%s)" % ",".join("?" * len(ids)), ids).fetchone()[0]
    twin_ids = tuple(t for v in TWINS.values() for t in v)
    twins_ok = c.execute("SELECT COUNT(*) FROM orders WHERE project_id IS NOT NULL AND id IN (%s)"
                         % ",".join("?" * len(twin_ids)), twin_ids).fetchone()[0]
    child = 0
    for t in child_tables(c):
        child += c.execute("SELECT COUNT(*) FROM %s WHERE order_id IN (%s)" % (t, ",".join("?" * len(ids))), ids).fetchone()[0]
    n_free = c.execute("SELECT COUNT(*) FROM orders WHERE project_id IS NULL").fetchone()[0]
    return {"남은 대상": left, "남은 짝": twins_ok, "짝 전체": len(twin_ids), "딸린 자료": child, "프로젝트 없는 수주": n_free}


def ro_conn():
    c = sqlite3.connect("file:%s?mode=ro" % DB, uri=True)
    c.row_factory = sqlite3.Row
    return c


def main(mode):
    c = ro_conn()
    rows, twins, child, n_free, problems = inspect(c)
    report(c, rows, twins, child, n_free)
    c.close()
    if problems:
        print("")
        print("!! 확인에서 걸린 것이 있어 멈춥니다(아무것도 안 지움):")
        for p in problems:
            print("   - " + p)
        print("빅터에게 이 화면을 보여 주세요.")
        sys.exit(2)
    if mode != "APPLY":
        print("")
        print("확인만 했습니다. 아무것도 지우지 않았습니다.")
        print("실제로 지우려면 -Apply 를 붙여 다시 실행하세요.")
        sys.exit(0)

    # ── 적용 ──
    # 1) 지우기 전 4건 원문(모든 칸)을 남긴다 — 되살릴 때 쓴다(딸린 자료가 0 이라 이것만으로 원래대로 돌릴 수 있다)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    keep = "%s/data/backups/floatso_4rows_%s.json" % (ROOT, ts)
    with open(keep, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in rows.items()}, f, ensure_ascii=False, indent=1, default=str)
    print("")
    print("지우기 전 원문 저장: " + keep)

    # 2) WORKS 의 수주 삭제 기능 그대로 · 한 연결 · 한 번에
    sys.path.insert(0, ROOT)
    from app.database import db_session
    from app.project_workflow import delete_order
    try:
        with db_session() as w:
            _r, _t, _c, _n, again = inspect(w)          # 같은 연결에서 한 번 더(그 사이 바뀌었으면 멈춤)
            if again:
                raise RuntimeError("지우기 직전 확인에서 걸림: %s" % again)
            for oid, msg in delete_all(w, delete_order):
                print("   지움: %s" % msg)
    except Exception as e:
        print("!! 지우지 못했습니다 — 모두 되돌렸습니다(운영 자료 그대로): %s" % e)
        sys.exit(3)

    # 3) 확인(읽기만)
    c = ro_conn()
    v = verify_after(c)
    c.close()
    print("")
    print("결과: %s" % v)
    ok = v["남은 대상"] == 0 and v["남은 짝"] == v["짝 전체"] and v["딸린 자료"] == 0
    print("✅ 4건 삭제 끝 · 남는 짝 그대로" if ok else "⚠ 결과가 예상과 다릅니다 — 빅터에게 이 화면을 보여 주세요.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "CHECK")
'@

# 파이프로 그냥 보내면 한글이 CP949 로 바뀌며 깨진다 → base64 로 실어 보낸다(10-11 사본 정리와 같은 방식)
# WORKS 가 쓰는 파이썬(.venv)으로 돌린다 — WORKS 의 수주 삭제 기능을 그대로 불러 쓰기 때문
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
ssh -p 32201 root@o.knknara.co.kr "echo $b64 | base64 -d > /tmp/_floatso.py; PYTHONIOENCODING=utf-8 /opt/knk_haist/.venv/bin/python -I /tmp/_floatso.py $mode; rc=`$?; rm -f /tmp/_floatso.py; exit `$rc"
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "끝났습니다." -ForegroundColor Green
} else {
    Write-Host "멈췄습니다(코드 $rc). 위 화면을 빅터에게 보여 주세요." -ForegroundColor Yellow
}
