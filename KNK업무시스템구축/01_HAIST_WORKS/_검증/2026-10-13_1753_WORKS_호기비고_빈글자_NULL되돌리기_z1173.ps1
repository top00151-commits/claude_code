# WORKS 호기 비고 ''(빈 글자) → NULL 되돌리기 (z1173 · 2026-10-13 · 대표 「등록 메모 같이 고친다」)
#
#   무엇을: 수주 호기 줄의 비고가 ''(빈 글자)이고 한 번도 수정되지 않은 행 — 등록 때 빈칸이 '' 로 들어간 것(z1173 전 코드)
#           '' 는 z983 규칙에서 「일부러 지움」이라 작업일정표 기타사항이 등록 메모를 숨겼습니다(10-13 실측 17행).
#   어떻게: 그 행의 비고를 NULL(한 번도 안 적음)로 바꿉니다 → 일정표가 등록 메모를 다시 보여줍니다. 다른 칸은 안 건드립니다.
#           바꾸기 전 원문을 서버 data/backups/notefix_z1173_<시각>.json 에 남깁니다. 하나라도 어긋나면 모두 되돌립니다.
#   ⚠ 비고에 '306' 이 든 4행은 이 스크립트가 안 건드립니다 → works.knknara.co.kr/admin/note-sweep?v=306 에서 「전부 비우기」
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
Write-Host "=== WORKS 호기 비고 '' → NULL 되돌리기 ($mode) ===" -ForegroundColor Cyan
Write-Host ""

$py = @'
# -*- coding: utf-8 -*-
# WORKS 호기 비고 ''(빈 글자) → NULL 되돌리기 (z1173 · 2026-10-13 · 대표 「등록 메모 같이 고친다」)
#   대상: order_items 에서 비고(line_note)가 ''(빈 글자)이고 한 번도 수정되지 않은 행(updated_at 이 NULL)
#         = 등록 때 빈칸이 '' 로 들어간 것(z1173 전 코드). '' 는 z983 규칙에서 「일부러 지움」이라
#           작업일정표 기타사항이 등록 메모(projects.logi_note)를 숨겼다(10-13 실측 56행 · 그중 한 번도 수정 안 된 17행).
#   하는 일: 그 행의 비고를 NULL(한 번도 안 적음)로 — 일정표가 등록 메모를 다시 보여준다. 다른 칸은 안 건드린다.
#   CHECK = 확인만(아무것도 안 바꿈) · APPLY = 바꿈(한 연결에서 한 번에 · 바꾸기 전 원문을 data/backups/notefix_z1173_<시각>.json 에 남김)
import datetime
import json
import os
import sqlite3
import sys

for _s in (sys.stdout, sys.stderr):   # -I 는 PYTHONIOENCODING 을 무시한다 → 여기서 utf-8 로(서버는 원래 utf-8 · 시험 PC 는 cp949)
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.environ.get("KNK_NOTEFIX_ROOT", "/opt/knk_haist")
DB = ROOT + "/data/knk.db"
LIMIT = 60   # 이보다 많으면 멈춤(10-13 실측 17행 · 배포 뒤 새 등록은 NULL 로 들어가므로 늘지 않는다)

SEL = ("SELECT oi.id, oi.order_id, COALESCE(o.order_no,'') AS order_no, COALESCE(p.mgmt_code,'') AS mgmt_code, "
       "COALESCE(oi.unit_label,'') AS unit_label, oi.line_note, oi.updated_at, COALESCE(p.logi_note,'') AS memo, "
       "COALESCE(o.created_at,'') AS created_at "
       "FROM order_items oi JOIN orders o ON o.id=oi.order_id LEFT JOIN projects p ON p.id=o.project_id "
       "WHERE oi.line_note='' AND oi.updated_at IS NULL ORDER BY oi.id")


def main(mode):
    if mode not in ("CHECK", "APPLY"):
        print("쓰는 법: CHECK | APPLY")
        return 2
    if not os.path.exists(DB):
        print("멈춤: DB 가 없습니다:", DB)
        return 3
    con = sqlite3.connect(DB if mode == "APPLY" else "file:%s?mode=ro" % DB, uri=(mode != "APPLY"), timeout=30)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute(SEL).fetchall()]
    print("대상(비고 '' · 한 번도 수정 안 됨): %d행" % len(rows))
    for r in rows:
        print("  item %-6s %-14s %-10s %-8s 메모=%r 등록=%s" % (r["id"], r["order_no"], r["mgmt_code"], r["unit_label"],
                                                              r["memo"][:30], r["created_at"][:10]))
    n306 = con.execute("SELECT COUNT(*) FROM order_items WHERE TRIM(COALESCE(line_note,''))='306'").fetchone()[0]
    print("(참고) 비고가 '306' 인 호기 행: %d — 이건 이 스크립트가 안 건드립니다 → /admin/note-sweep?v=306 에서 「전부 비우기」" % n306)
    if not rows:
        print("바꿀 것이 없습니다.")
        con.close()
        return 0
    if len(rows) > LIMIT:
        print("멈춤: 대상이 %d행으로 예상(%d)보다 많습니다. 빅터에게 알려 주세요." % (len(rows), LIMIT))
        con.close()
        return 4
    if mode == "CHECK":
        print("확인만 했습니다(아무것도 바꾸지 않음). 바꾸려면 -Apply 를 붙여 다시 실행하세요.")
        con.close()
        return 0

    ids = [r["id"] for r in rows]
    bdir = ROOT + "/data/backups"
    os.makedirs(bdir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bpath = "%s/notefix_z1173_%s.json" % (bdir, ts)
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump({"when": ts, "what": "order_items.line_note '' -> NULL (updated_at IS NULL)", "rows": rows},
                  f, ensure_ascii=False, indent=1)
    print("원문 저장:", bpath)
    try:
        con.execute("BEGIN")
        q = ",".join("?" * len(ids))
        cur = con.execute("UPDATE order_items SET line_note=NULL WHERE id IN (%s) AND line_note='' AND updated_at IS NULL" % q, ids)
        if cur.rowcount != len(ids):
            con.execute("ROLLBACK")
            print("멈춤: 바뀐 행 수(%d)가 대상(%d)과 다릅니다 — 모두 되돌렸습니다." % (cur.rowcount, len(ids)))
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
    left = con.execute("SELECT COUNT(*) FROM order_items WHERE line_note='' AND updated_at IS NULL").fetchone()[0]
    now_null = con.execute("SELECT COUNT(*) FROM order_items WHERE id IN (%s) AND line_note IS NULL" % ",".join("?" * len(ids)), ids).fetchone()[0]
    con.close()
    print("바꿈: %d행 → NULL · 남은 대상 %d · 확인(NULL 된 행) %d" % (len(ids), left, now_null))
    return 0 if (left == 0 and now_null == len(ids)) else 7


if __name__ == "__main__":
    sys.exit(main((sys.argv[1] if len(sys.argv) > 1 else "CHECK").upper()))
'@

# 파이프로 그냥 보내면 한글이 CP949 로 바뀌며 깨진다 → base64 로 실어 보낸다(10-12 떠 있는 수주 정리와 같은 방식)
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
ssh -p 32201 root@o.knknara.co.kr "echo $b64 | base64 -d > /tmp/_notefix.py; PYTHONIOENCODING=utf-8 /opt/knk_haist/.venv/bin/python -I /tmp/_notefix.py $mode; rc=`$?; rm -f /tmp/_notefix.py; exit `$rc"
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "끝났습니다." -ForegroundColor Green
} else {
    Write-Host "멈췄습니다(코드 $rc). 위 화면을 빅터에게 보여 주세요." -ForegroundColor Yellow
}
