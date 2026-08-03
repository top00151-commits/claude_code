# -*- coding: utf-8 -*-
"""z1073f 되돌림 감지 시험 — 깨끗한 임시 DB 에서 4번 올려 본다.

핵심은 **변별력**이다: 되돌림이 아닌 평범한 설계변경에서는 반드시 **0** 이 나와야 한다.
0 이 안 나오면 "아무 변경에나 되돌림이라 우기는" 쓸모없는 경고가 된다.

시나리오
  v1  R1 올림              → 추가 13 · 변경 0            · 되돌림 0 (이력 자체가 없음)
  v2  R2 올림 (설계변경)     → 변경 4                     · 되돌림 0  ← ★변별력★ 진짜 새 변경
  v3  R1 다시 올림 (예전 파일) → 변경 4                    · 되돌림 4  ← ★핵심★ v2 를 되돌림
  v4  R2 다시 올림           → 변경 4                     · 되돌림 4  (v3 을 되돌림)
"""
import os
import sys
import tempfile

ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from app import database as db                                   # noqa: E402

db.DB_PATH = os.path.join(tempfile.mkdtemp(prefix="knk_revtest_"), "t.db")
db.init_db()

from app import bom as B                                         # noqa: E402

XLSX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xlsx")
R1 = os.path.join(XLSX, "001M2607 구매품 LIST_260729-R1.xlsx")
R2 = os.path.join(XLSX, "001M2607 구매품 LIST_260803-R2(설계변경).xlsx")

with db.db_session() as c:
    c.execute("INSERT INTO teams (id, code, name) VALUES (10,'PUR','구매팀')")
    c.execute("INSERT INTO users (name, login_id, password, team_id, is_active)"
              " VALUES ('시험','t','x',10,1)")
    UID = c.execute("SELECT id FROM users WHERE login_id='t'").fetchone()[0]
    c.execute("INSERT INTO projects (mgmt_code, name, status) VALUES ('001M2607','시험','진행중')")
    PID = c.execute("SELECT id FROM projects WHERE mgmt_code='001M2607'").fetchone()[0]


def items_of(path):
    res = B.parse_bom_file(path, os.path.basename(path))
    out = []
    for sh in res.get("sheets", []):
        out.extend(sh.get("items", []))
    return out


def step(no, path, want_chg, want_rev):
    items = items_of(path)
    plan = B.plan_diff(PID, items)                 # 미리보기 — DB 안 건드림
    chg, rev = len(plan["changes"]), plan.get("revert_cnt", 0)
    vers = plan.get("revert_vers", [])
    ok = (chg == want_chg and rev == want_rev)
    print("%s v%d  %-34s 변경 %2d(기대 %2d) · 되돌림 %2d(기대 %2d) %s"
          % ("✅" if ok else "❌", no, os.path.basename(path)[:32], chg, want_chg, rev, want_rev,
             ("· v" + ", v".join(str(v) for v in vers)) if vers else ""))
    if rev:
        for ch in plan["changes"]:
            for fld, ov in ch["fields"].items():
                if ov.get("revert"):
                    print("        %-14s %-11s %s → %s   (v%s 에서 한 변경)"
                          % (ch["file"].get("part_no"), fld, ov["old"], ov["new"],
                             ov["revert"]["version_no"]))
    B.apply_upload(PID, items, "merge", UID, os.path.basename(path), None)
    return ok


print("=" * 92)
print("z1073f 되돌림 감지 — 깨끗한 임시 DB")
print("=" * 92)
res = [
    step(1, R1, 0, 0),      # 첫 업로드: 전부 추가, 변경 0
    step(2, R2, 4, 0),      # ★변별력★ 진짜 설계변경 — 되돌림 아님
    step(3, R1, 4, 4),      # ★핵심★ 예전 파일 → v2 를 되돌림
    step(4, R2, 4, 4),      # 또 되돌림
]
print("=" * 92)
print("합계: %d통과 / %d실패" % (sum(res), len(res) - sum(res)))
sys.exit(0 if all(res) else 1)
