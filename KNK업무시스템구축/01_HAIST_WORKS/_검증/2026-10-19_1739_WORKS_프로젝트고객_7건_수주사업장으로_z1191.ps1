# WORKS 프로젝트 고객 7건 — 수주와 같은 사업장으로 (z1191 · 2026-10-19 · 이새롬 프로 확인)
#
#   무엇을: 첫 수주(와 대부분 수주)의 발주처와 프로젝트 고객(대표값)이 달랐던 7개 프로젝트의 프로젝트 고객을 수주 사업장으로 바꿉니다.
#     · 009T2607 · 013T2606 · 014T2606 · 014T2607 · 015T2607 · 016T2607 : 드림텍(아산) → 드림텍(동탄)   (이새롬 프로 「드림텍(동탄)」)
#     · 999M2604                                                          : 드림텍(본사) → 드림텍(아산)   (이새롬 프로 「드림텍(아산)이 맞음」)
#   안 건드림: 수주(발주처·금액·상태·계산서 칸) · 호기 · 그 밖의 모든 프로젝트. 정식 상호는 셋 다 「(주) 드림텍」이라 이름 칸도 그대로입니다.
#   지키는 것: 바꾸기 전 원문을 서버 data/backups/projcust7_z1191_<시각>.json 에 남깁니다.
#             지금 값이 예상(옛 사업장 · 첫 수주는 새 사업장)과 하나라도 다르면 아무것도 안 바꿉니다. 다시 실행하면 「바꿀 것이 없습니다」.
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
Write-Host "=== WORKS 프로젝트 고객 7건 → 수주 사업장 ($mode) ===" -ForegroundColor Cyan
Write-Host ""

$py = @'
# -*- coding: utf-8 -*-
# WORKS 프로젝트 고객 7건 → 수주 사업장 (z1191 · 2026-10-19 · 이새롬 프로 확인)
#   CHECK = 확인만(읽기 전용 연결) · APPLY = 바꿈(한 연결에서 한 번에 · 바꾸기 전 원문을 data/backups/projcust7_z1191_<시각>.json 에)
#   프로젝트 id·관리번호·옛 고객·새 고객이 예상과 다르거나, 첫 수주 발주처가 새 고객이 아니면 아무것도 안 바꾸고 멈춘다.
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

ROOT = os.environ.get("KNK_FIX_ROOT", "/opt/knk_haist")
DB = ROOT + "/data/knk.db"
DONGTAN, ASAN, BONSA = 78, 75, 74    # 드림텍(동탄) · 드림텍(아산) · 드림텍(본사) — 2026-10-19 운영 읽기
PLAN = [  # (관리번호, 프로젝트 id, 옛 고객, 새 고객)
    ("009T2607", 1077, ASAN, DONGTAN), ("013T2606", 1060, ASAN, DONGTAN), ("014T2606", 1061, ASAN, DONGTAN),
    ("014T2607", 1078, ASAN, DONGTAN), ("015T2607", 1079, ASAN, DONGTAN), ("016T2607", 1080, ASAN, DONGTAN),
    ("999M2604", 1029, BONSA, ASAN),
]


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
    cc = {r[1] for r in con.execute("PRAGMA table_info(customers)")}
    nm = "COALESCE(NULLIF(alias,''), name)" if "alias" in cc else "name"
    cname = {r[0]: (r[1], r[2]) for r in con.execute("SELECT id, %s, name FROM customers WHERE id IN (?,?,?)" % nm, (DONGTAN, ASAN, BONSA))}
    if len(cname) != 3:
        print("멈춤: 드림텍 사업장 고객 번호(78·75·74)를 찾지 못했습니다:", cname)
        con.close()
        return 4
    problems, todo, done_already = [], [], []
    for mc, pid, old, new in PLAN:
        p = con.execute("SELECT id, mgmt_code, customer_id, COALESCE(customer_name,'') AS cn FROM projects WHERE id=?", (pid,)).fetchone()
        if not p or p["mgmt_code"] != mc:
            problems.append("%s: 프로젝트 #%d 를 찾지 못했거나 관리번호가 다름" % (mc, pid))
            continue
        so = con.execute("SELECT order_no, customer_id FROM orders WHERE project_id=? ORDER BY id LIMIT 1", (pid,)).fetchone()
        if not so or so["customer_id"] != new:
            problems.append("%s: 첫 수주 발주처가 %s 이 아님(지금 #%s)" % (mc, cname[new][0], so["customer_id"] if so else None))
            continue
        if p["customer_id"] == new:
            done_already.append(mc)
            continue
        if p["customer_id"] != old:
            problems.append("%s: 프로젝트 고객이 예상(%s)과 다름(지금 #%s)" % (mc, cname[old][0], p["customer_id"]))
            continue
        todo.append({"mgmt_code": mc, "pid": pid, "old": old, "new": new, "first_so": so["order_no"], "customer_name_before": p["cn"]})
    print("바꿀 프로젝트 %d개 · 이미 바뀐 것 %d개" % (len(todo), len(done_already)))
    for t in todo:
        print("  %-9s 프로젝트 고객 %s → %s   (첫 수주 %s = %s)" % (t["mgmt_code"], cname[t["old"]][0], cname[t["new"]][0], t["first_so"], cname[t["new"]][0]))
    if done_already:
        print("  (이미 바뀜: %s)" % ", ".join(done_already))
    if problems:
        print("멈춤: 예상과 다른 것이 있어 아무것도 바꾸지 않습니다 —")
        for x in problems:
            print("  -", x)
        con.close()
        return 5
    if not todo:
        print("바꿀 것이 없습니다(이미 모두 수주 사업장).")
        con.close()
        return 0
    if mode == "CHECK":
        print("확인만 했습니다(아무것도 바꾸지 않음). 바꾸려면 -Apply 를 붙여 다시 실행하세요.")
        con.close()
        return 0

    bdir = ROOT + "/data/backups"
    os.makedirs(bdir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bpath = "%s/projcust7_z1191_%s.json" % (bdir, ts)
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump({"when": ts, "what": "projects.customer_id → 수주 사업장 (이새롬 프로 확인)", "projects": todo}, f, ensure_ascii=False, indent=1)
    print("원문 저장:", bpath)
    n = 0
    try:
        con.execute("BEGIN")
        for t in todo:
            cur = con.execute("UPDATE projects SET customer_id=?, customer_name=? WHERE id=? AND customer_id=?",
                              (t["new"], cname[t["new"]][1], t["pid"], t["old"]))
            n += cur.rowcount
        if n != len(todo):
            con.execute("ROLLBACK")
            print("멈춤: 바뀐 수(%d)가 예상(%d)과 다릅니다 — 모두 되돌렸습니다." % (n, len(todo)))
            con.close()
            return 6
        con.execute("COMMIT")
    except Exception as e:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        print("멈춤: 바꾸다 오류 — 모두 되돌렸습니다:", str(e)[:200])
        con.close()
        return 7
    left = [mc for mc, pid, old, new in PLAN
            if con.execute("SELECT customer_id FROM projects WHERE id=?", (pid,)).fetchone()[0] != new]
    con.close()
    print("바꿈: 프로젝트 %d개 · 아직 다른 것 %d개" % (n, len(left)))
    return 0 if not left else 8


if __name__ == "__main__":
    sys.exit(main((sys.argv[1] if len(sys.argv) > 1 else "CHECK").upper()))
'@

# 파이프로 그냥 보내면 한글이 CP949 로 바뀌며 깨진다 → base64 로 실어 보낸다(10-13 호기 비고 되돌리기와 같은 방식)
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
ssh -p 32201 root@o.knknara.co.kr "echo $b64 | base64 -d > /tmp/_projcust7.py; PYTHONIOENCODING=utf-8 /opt/knk_haist/.venv/bin/python -I /tmp/_projcust7.py $mode; rc=`$?; rm -f /tmp/_projcust7.py; exit `$rc"
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "끝났습니다." -ForegroundColor Green
} else {
    Write-Host "멈췄습니다(코드 $rc). 위 화면을 빅터에게 보여 주세요." -ForegroundColor Yellow
}
