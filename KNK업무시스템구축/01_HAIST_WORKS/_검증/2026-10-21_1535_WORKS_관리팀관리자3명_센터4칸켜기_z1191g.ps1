# WORKS 관리팀 관리자 3명 — 센터 진입 권한 4칸 켜기 (z1191g · 2026-10-21 · 대표 결정)
#
#   왜: z1191g 부터 관리자(admin)는 「관리 일」만 역할로 열리고, 매출·영업 · 자재·구매는 체크한 대로만 열립니다.
#       관리팀 관리자 3명은 지금 체크가 0개라, z1191g 배포 순간 두 센터가 닫힙니다(은행 대사·수금 등 업무가 막힘).
#       대표 결정(10-21): 이 3명은 「4칸 모두 켬」 — 필요 없는 칸은 배포 뒤 「🔑 권한 한꺼번에 설정」 화면에서 끄면 됩니다.
#   무엇을: 박지은(261) · 엄혜린(271) · 최혜연(300) 의 매출·영업 보기·등록, 자재·구매 보기·등록 4칸을 켭니다.
#   언제: z1191g 배포 **전에** 실행하세요. 지금은 관리자라서 어차피 다 열려 있어, 미리 켜도 달라지는 것은 없습니다.
#   안 건드림: 역할 · 팀 · 담당 사업부 · 그 밖의 모든 사람(이용식 법인장·흐엉은 그대로 0 — 대표 뜻).
#   지키는 것: 바꾸기 전 원문을 서버 data/backups/admincenter_z1191g_<시각>.json 에 남기고, 칸마다 사람 「변경 이력」에 남깁니다.
#             번호·이름·역할(관리자)·팀(관리팀)·지금 값이 예상과 하나라도 다르면 아무것도 안 바꿉니다. 다시 실행하면 「바꿀 것이 없습니다」.
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
Write-Host "=== WORKS 관리팀 관리자 3명 — 센터 4칸 켜기 ($mode) ===" -ForegroundColor Cyan
Write-Host ""

$py = @'
# -*- coding: utf-8 -*-
# WORKS 관리팀 관리자 3명 — 센터 진입 권한 4칸 켜기 (z1191g · 2026-10-21 · 대표 결정)
#   CHECK = 확인만(읽기 전용 연결) · APPLY = 한 연결에서 한 번에(바꾸기 전 원문을 data/backups/admincenter_z1191g_<시각>.json 에)
#   번호·이름·역할·팀·지금 값이 예상과 다르면 아무것도 안 바꾸고 멈춘다.
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
TEAM = 11          # 관리팀(본사) — 2026-10-21 운영 읽기
ACTOR = 85         # 김정락 대표 — 변경 이력의 「바꾼 사람」
PEOPLE = [(261, "박지은"), (271, "엄혜린"), (300, "최혜연")]
FLAGS = [("can_view_sales", "매출·영업 보기"), ("can_use_sales", "매출·영업 등록·편집"),
         ("can_view_logistics", "자재·구매 보기"), ("can_use_logistics", "자재·구매 등록·편집")]
NOTE = "z1191g 관리자 센터 체크 전환 — 대표 결정(관리팀 4칸 켬)"


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
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_history'").fetchone():
        print("멈춤: 변경 이력 표(user_history)가 없습니다.")
        con.close()
        return 4
    cols = ", ".join("COALESCE(%s,0) AS %s" % (f, f) for f, _ in FLAGS)
    problems, todo, done_already = [], [], []
    for uid, name in PEOPLE:
        r = con.execute("SELECT id, name, role, team_id, is_active, " + cols + " FROM users WHERE id=?", (uid,)).fetchone()
        if not r or r["name"] != name:
            problems.append("#%d: %s 을(를) 찾지 못했거나 이름이 다름(지금 %r)" % (uid, name, r["name"] if r else None))
            continue
        if r["role"] != "admin" or r["team_id"] != TEAM or r["is_active"] != 1:
            problems.append("#%d %s: 역할·팀·근무가 예상(관리자·관리팀·근무 중)과 다름(지금 %s · 팀 %s · 근무 %s)"
                            % (uid, name, r["role"], r["team_id"], r["is_active"]))
            continue
        now = {f: int(r[f]) for f, _ in FLAGS}
        if all(now.values()):
            done_already.append(name)
            continue
        todo.append({"id": uid, "name": name, "before": now})
    print("켤 사람 %d명 · 이미 4칸 켜진 사람 %d명" % (len(todo), len(done_already)))
    for t in todo:
        print("  %s(#%d): %s → 4칸 모두 켬" % (t["name"], t["id"], " · ".join("%s %s" % (lbl, "켬" if t["before"][f] else "끔") for f, lbl in FLAGS)))
    if done_already:
        print("  (이미 켜짐: %s)" % ", ".join(done_already))
    if problems:
        print("멈춤: 예상과 다른 것이 있어 아무것도 바꾸지 않습니다 —")
        for x in problems:
            print("  -", x)
        con.close()
        return 5
    if not todo:
        print("바꿀 것이 없습니다(3명 모두 이미 4칸 켜짐).")
        con.close()
        return 0
    if mode == "CHECK":
        print("확인만 했습니다(아무것도 바꾸지 않음). 바꾸려면 -Apply 를 붙여 다시 실행하세요.")
        con.close()
        return 0

    bdir = ROOT + "/data/backups"
    os.makedirs(bdir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bpath = "%s/admincenter_z1191g_%s.json" % (bdir, ts)
    with open(bpath, "w", encoding="utf-8") as f:
        json.dump({"when": ts, "what": "관리팀 관리자 3명 센터 4칸 켬(z1191g · 대표 결정)", "people": todo}, f, ensure_ascii=False, indent=1)
    print("원문 저장:", bpath)
    n = h = 0
    try:
        con.execute("BEGIN")
        for t in todo:
            cur = con.execute("UPDATE users SET " + ", ".join("%s=1" % f for f, _ in FLAGS) + " WHERE id=? AND role='admin' AND team_id=?",
                              (t["id"], TEAM))
            n += cur.rowcount
            for f, lbl in FLAGS:
                if not t["before"][f]:
                    con.execute("INSERT INTO user_history(user_id, changed_by, field, old_value, new_value, note) VALUES(?,?,?,?,?,?)",
                                (t["id"], ACTOR, lbl, "끔", "켬", NOTE))
                    h += 1
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
    left = [name for uid, name in PEOPLE
            if not all(con.execute("SELECT " + cols + " FROM users WHERE id=?", (uid,)).fetchone())]
    con.close()
    print("바꿈: %d명 · 변경 이력 %d줄 · 아직 4칸이 아닌 사람 %d명" % (n, h, len(left)))
    return 0 if not left else 8


if __name__ == "__main__":
    sys.exit(main((sys.argv[1] if len(sys.argv) > 1 else "CHECK").upper()))
'@

# 파이프로 그냥 보내면 한글이 CP949 로 바뀌며 깨진다 → base64 로 실어 보낸다(10-19 7건과 같은 방식)
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
ssh -p 32201 root@o.knknara.co.kr "echo $b64 | base64 -d > /tmp/_admincenter.py; PYTHONIOENCODING=utf-8 /opt/knk_haist/.venv/bin/python -I /tmp/_admincenter.py $mode; rc=`$?; rm -f /tmp/_admincenter.py; exit `$rc"
$rc = $LASTEXITCODE

Write-Host ""
if ($rc -eq 0) {
    Write-Host "끝났습니다." -ForegroundColor Green
} else {
    Write-Host "멈췄습니다(코드 $rc). 위 화면을 빅터에게 보여 주세요." -ForegroundColor Yellow
}
