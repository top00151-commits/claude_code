# WORKS 프로젝트 9건 — 글자 「None」 이 든 칸 비우기 (z1190c · 2026-10-16)
#
#   무엇을: 프로젝트 수정 화면이 빈 칸을 글자 None 으로 보여 주던 탓에, 그대로 저장되어 글자 None 이 남은 프로젝트 9개
#           (005T2601 · 001M2607 · 005M2511 · 006M2510 · 999M2604 · 002M2602 · 관리번호 없는 1건 · 014T2606 · 015T2607)의
#           2차 발주처·담당자 칸(이름·부서·직책·전화·메일·메모) 중 **정확히 글자 None 인 칸만** 비웁니다(모두 47칸).
#           2차가 글자 None 이던 6개는 「2단 발주」 표시도 끕니다(최종 고객 매출이 비어 있을 때만 — 지금 6개 모두 비어 있음).
#   안 건드림: 진짜 값이 든 칸 · 고객사·금액·상태·날짜 · 그 밖의 모든 프로젝트·수주
#   지키는 것: 바꾸기 전 원문을 서버 data/backups/none9_z1190c_<시각>.json 에 남깁니다. 찾은 프로젝트가 예상 9개와 다르면 아무것도 안 바꿉니다.
#   순서: z1190c(수정 화면이 None 을 다시 넣지 않게 고친 것) 배포 뒤에 실행하세요. 배포 전에 실행해도 되지만, 그 사이 누가 수정 화면에서 저장하면 다시 생길 수 있습니다.
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
Write-Host "=== WORKS 프로젝트 9건 글자 None 칸 비우기 ($mode) ===" -ForegroundColor Cyan
Write-Host ""

$py = @'
# -*- coding: utf-8 -*-
# WORKS 프로젝트 9건 — 글자 'None' 이 든 칸 비우기 (z1190c · 2026-10-16)
#   원인: 수정 화면 입력 칸이 Jinja |default('') 라 DB NULL 이 글자 None 으로 보였고, 손대지 않고 저장해도 그대로 남았다.
#         2차 발주처가 글자 None 이면 「2단 발주」로도 판정되어 상세 화면에 「최종 고객 🌐 None」이 보였다.
#   하는 일: 아래 9개 프로젝트의 7칸 중 정확히 글자 'None'(앞뒤 빈칸 무시)인 칸만 NULL 로.
#           2차가 글자 None 이던 6개는 two_tier_order 를 0 으로(final_amount 가 비어 있을 때만).
#   CHECK = 확인만(읽기 전용 연결) · APPLY = 바꿈(한 연결에서 한 번에 · 바꾸기 전 원문을 data/backups/none9_z1190c_<시각>.json 에 남김)
#   찾은 프로젝트가 예상 9개(번호)와 다르면 아무것도 안 바꾸고 멈춘다.
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
COLS = ["secondary_customer", "cc_name", "cc_dept", "cc_position", "cc_phone", "cc_email", "cc_note"]
NAMES = {"secondary_customer": "2차 발주처", "cc_name": "담당자", "cc_dept": "부서", "cc_position": "직책",
         "cc_phone": "전화", "cc_email": "메일", "cc_note": "메모"}
EXPECT = {821, 1003, 1010, 1011, 1029, 1040, 1043, 1061, 1079}      # 2026-10-16 22:2x 운영 읽기로 찾은 9개
EXPECT_2ND = {821, 1029, 1040, 1043, 1061, 1079}                    # 그중 2차 발주처가 글자 None 인 6개


def is_none_txt(v):
    return v is not None and str(v).strip() == "None"


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
    have = {r[1] for r in con.execute("PRAGMA table_info(projects)")}
    miss = [c for c in COLS + ["two_tier_order", "final_amount"] if c not in have]
    if miss:
        print("멈춤: projects 에 칸이 없습니다:", miss)
        con.close()
        return 4
    cond = " OR ".join("TRIM(COALESCE(%s,''))='None'" % c for c in COLS)
    rows = con.execute("SELECT id, mgmt_code, name, two_tier_order, final_amount, %s FROM projects WHERE %s ORDER BY id"
                       % (", ".join(COLS), cond)).fetchall()
    plan = []
    for r in rows:
        cells = [c for c in COLS if is_none_txt(r[c])]
        tt_off = ("secondary_customer" in cells) and (r["two_tier_order"] == 1) and not (r["final_amount"] or 0)
        plan.append({"id": r["id"], "mgmt_code": r["mgmt_code"], "name": r["name"], "two_tier_order": r["two_tier_order"],
                     "final_amount": r["final_amount"], "cells": cells, "two_tier_off": tt_off,
                     "before": {c: r[c] for c in COLS}})
    n_cells = sum(len(x["cells"]) for x in plan)
    n_tt = sum(1 for x in plan if x["two_tier_off"])
    print("찾은 프로젝트 %d개 · 비울 칸 %d · 「2단 발주」 끌 프로젝트 %d" % (len(plan), n_cells, n_tt))
    for x in plan:
        print("  %-14s %-24s · 비울 칸 %d: %s%s" % (
            x["mgmt_code"] or "(관리번호 없음 #%d)" % x["id"], (x["name"] or "")[:24], len(x["cells"]),
            "·".join(NAMES[c] for c in x["cells"]), " · 2단 발주 끔" if x["two_tier_off"] else ""))
    found = {x["id"] for x in plan}
    found_2nd = {x["id"] for x in plan if "secondary_customer" in x["cells"]}
    problems = []
    if found - EXPECT:   # 예상 밖 프로젝트가 더 있으면 멈춘다(예상한 것 중 이미 비어 있는 것은 괜찮다 — 다시 실행해도 안전)
        problems.append("예상 밖 프로젝트에 글자 None 이 있음 — 번호 %s" % sorted(found - EXPECT))
    if found_2nd - EXPECT_2ND:
        problems.append("예상 밖 프로젝트의 2차 발주처가 글자 None — 번호 %s" % sorted(found_2nd - EXPECT_2ND))
    if EXPECT - found:
        print("  (이미 비어 있는 프로젝트 %d개 — 번호 %s)" % (len(EXPECT - found), sorted(EXPECT - found)))
    if any(x["final_amount"] for x in plan if x["id"] in EXPECT_2ND):
        problems.append("2차가 글자 None 인데 최종 고객 매출이 적힌 프로젝트가 있음(2단 발주를 끄지 않아야 할 수 있음)")
    if problems:
        print("멈춤: 예상과 다른 것이 있어 아무것도 바꾸지 않습니다 —")
        for p in problems:
            print("  -", p)
        con.close()
        return 5
    if n_cells == 0:
        print("바꿀 것이 없습니다(이미 모두 비어 있음).")
        con.close()
        return 0
    if mode == "CHECK":
        print("확인만 했습니다(아무것도 바꾸지 않음). 바꾸려면 -Apply 를 붙여 다시 실행하세요.")
        con.close()
        return 0

    bdir = ROOT + "/data/backups"
    os.makedirs(bdir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bpath = "%s/none9_z1190c_%s.json" % (bdir, ts)
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump({"when": ts, "what": "projects 글자 'None' 칸 -> NULL · 2차가 None 이던 프로젝트 two_tier_order -> 0",
                   "projects": plan}, f, ensure_ascii=False, indent=1)
    print("원문 저장:", bpath)
    done_cells = done_tt = 0
    try:
        con.execute("BEGIN")
        for x in plan:
            for c in x["cells"]:
                cur = con.execute("UPDATE projects SET %s=NULL WHERE id=? AND TRIM(COALESCE(%s,''))='None'" % (c, c), (x["id"],))
                done_cells += cur.rowcount
            if x["two_tier_off"]:
                cur = con.execute("UPDATE projects SET two_tier_order=0 WHERE id=? AND two_tier_order=1 "
                                  "AND secondary_customer IS NULL AND COALESCE(final_amount,0)=0", (x["id"],))
                done_tt += cur.rowcount
        if done_cells != n_cells or done_tt != n_tt:
            con.execute("ROLLBACK")
            print("멈춤: 바뀐 수(칸 %d · 2단 %d)가 예상(칸 %d · 2단 %d)과 다릅니다 — 모두 되돌렸습니다." % (done_cells, done_tt, n_cells, n_tt))
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
    left = con.execute("SELECT COUNT(*) FROM projects WHERE %s" % cond).fetchone()[0]
    con.close()
    print("바꿈: 칸 %d개 비움 · 2단 발주 %d개 끔 · 남은 글자 None 프로젝트 %d" % (done_cells, done_tt, left))
    return 0 if left == 0 else 8


if __name__ == "__main__":
    sys.exit(main((sys.argv[1] if len(sys.argv) > 1 else "CHECK").upper()))
'@

# 파이프로 그냥 보내면 한글이 CP949 로 바뀌며 깨진다 → base64 로 실어 보낸다(10-13 호기 비고 되돌리기와 같은 방식)
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
ssh -p 32201 root@o.knknara.co.kr "echo $b64 | base64 -d > /tmp/_none9.py; PYTHONIOENCODING=utf-8 /opt/knk_haist/.venv/bin/python -I /tmp/_none9.py $mode; rc=`$?; rm -f /tmp/_none9.py; exit `$rc"
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "끝났습니다." -ForegroundColor Green
} else {
    Write-Host "멈췄습니다(코드 $rc). 위 화면을 빅터에게 보여 주세요." -ForegroundColor Yellow
}
