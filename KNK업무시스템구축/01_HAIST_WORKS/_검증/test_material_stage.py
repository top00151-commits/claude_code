#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""WP-04 기준전환 — 자재 관리 단계 시험 (임시 DB · 운영 무접촉)

⛔ 운영 DB 를 열지 않는다. 임시 폴더에 새 DB 를 만들어 거기서만 시험한다.

무엇을 확인하나
  ① 기존 프로젝트는 전부 'EXCEL' — 지금 동작이 안 바뀐다
  ② ⛔ Excel → 공식관리 **직행 금지**
  ③ ⛔ 사람 판정 없이 공식관리 **불가** (근거 유형·근거 글·판정자 셋 다)
  ④ 규칙을 지키면 넘어가고, 넘어간 사실이 기록된다
  ⑤ 잠금은 환경변수를 켜야만 걸린다 (기존 화면 안 막힘)
  ⑥ 되돌리기(공식관리 → 준비)도 기록된다

사용법:  python _검증/test_material_stage.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.pop("KNK_ENABLE_MATERIAL_STAGE_LOCK", None)

import app.database as D                                            # noqa: E402

# 🔴 DB 경로는 **환경변수가 아니라 모듈 상수** 다 (database.py:78 DB_PATH).
#    처음에 환경변수로 바꾸려다 실제로는 로컬 개발 DB 에 썼다. 상수를 직접 갈아끼운다.
TMP = tempfile.mkdtemp(prefix="knk_matstage_")
_REAL_DB = D.DB_PATH
D.DB_PATH = os.path.join(TMP, "test.db")
assert D.DB_PATH != _REAL_DB, "임시 DB 로 안 바뀌었습니다"

OK = [0, 0]


def c(label, cond, detail=""):
    OK[0 if cond else 1] += 1
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"   {detail}" if not cond and detail else ""))


def main():
    print("=" * 74)
    print("  WP-04 기준전환 — 자재 관리 단계 시험 (임시 DB)")
    print("=" * 74)
    print(f"  임시 DB : {D.DB_PATH}")
    print(f"  실제 DB : {_REAL_DB}  ← 여기는 건드리지 않습니다")
    # ⛔ 임시 DB 가 아니면 아예 시작하지 않는다 (한 번 실수했다)
    if not D.DB_PATH.startswith(TMP):
        print("\n[중단] 임시 DB 로 안 바뀌었습니다. 실제 DB 를 건드릴 뻔했습니다.")
        sys.exit(1)
    _before = os.path.getmtime(_REAL_DB) if os.path.exists(_REAL_DB) else None

    D.init_db()
    with D.db_session() as conn:
        conn.execute("INSERT INTO projects(name, mgmt_code) VALUES('시험설비','A999T9901')")
        pid = conn.execute("SELECT id FROM projects WHERE mgmt_code='A999T9901'").fetchone()[0]
        conn.execute("INSERT INTO users(name, login_id, password, role) "
                     "VALUES('시험담당','TEST9901','x','admin')")
        uid = conn.execute("SELECT id FROM users WHERE login_id='TEST9901'").fetchone()[0]

        # ① 기본값
        c("① 새 프로젝트는 'EXCEL' (지금 하던 대로)",
          D.get_material_stage(conn, pid) == "EXCEL", D.get_material_stage(conn, pid))

        # ⑤ 잠금은 꺼져 있어야 (환경변수 없이는)
        c("⑤ 환경변수 없으면 잠금 안 걸림 (기존 화면 안 막힘)",
          D.material_stage_locked(conn, pid) is False)

        # ② 직행 금지
        r = D.set_material_stage(conn, pid, "OFFICIAL", decided_by=uid,
                                 entered_kind="발주", entered_basis="발주서 확인", entered_by=uid)
        c("② ⛔ Excel → 공식관리 직행이 막힘",
          r["ok"] is False and "전환 준비" in r.get("error", ""), str(r))
        c("②-b 막혔으면 단계가 그대로", D.get_material_stage(conn, pid) == "EXCEL")

        # 준비 단계로는 갈 수 있다
        r = D.set_material_stage(conn, pid, "PREPARE", decided_by=uid, note="시작자료 모으는 중")
        c("   Excel → 전환 준비 는 됨", r["ok"] is True, str(r))

        # ③ 사람 판정 없이 공식관리 불가 — 세 가지 각각
        r = D.set_material_stage(conn, pid, "OFFICIAL", decided_by=uid)
        c("③-a ⛔ 제작 진입 근거(발주/가공/입고/조립) 없으면 막힘",
          r["ok"] is False and "골라" in r.get("error", ""), str(r))
        r = D.set_material_stage(conn, pid, "OFFICIAL", decided_by=uid,
                                 entered_kind="발주", entered_by=uid)
        c("③-b ⛔ 무엇을 보고 판정했는지 없으면 막힘",
          r["ok"] is False and "무엇을 보고" in r.get("error", ""), str(r))
        r = D.set_material_stage(conn, pid, "OFFICIAL", decided_by=uid,
                                 entered_kind="발주", entered_basis="발주서 3건 확인")
        c("③-c ⛔ 판정한 사람이 없으면 막힘",
          r["ok"] is False and "누가 판정" in r.get("error", ""), str(r))
        # 있지도 않은 근거 유형
        r = D.set_material_stage(conn, pid, "OFFICIAL", decided_by=uid,
                                 entered_kind="아직 아님", entered_basis="x", entered_by=uid)
        c("③-d ⛔ '아직 아님' 으로는 공식관리로 못 감",
          r["ok"] is False, str(r))
        c("③-e 막힌 동안 단계가 그대로", D.get_material_stage(conn, pid) == "PREPARE")

        # ④ 제대로 갖추면 넘어가고 기록된다
        r = D.set_material_stage(conn, pid, "OFFICIAL", decided_by=uid,
                                 entered_kind="발주", entered_basis="협력사 발주서 3건 · 8/10 발송",
                                 entered_by=uid, scope_kind="관리번호전체", note="0단계 시험")
        c("④ 근거를 갖추면 공식관리로 넘어감", r["ok"] is True, str(r))
        c("④-b 단계가 바뀜", D.get_material_stage(conn, pid) == "OFFICIAL")
        h = D.material_baseline_history(conn, pid)
        c("④-c 넘어간 기록이 2건 (준비 · 공식)", len(h) == 2, f"{len(h)}건")
        last = h[0]
        c("④-d 기록에 근거·판정자·판정시각이 남음",
          last["entered_kind"] == "발주" and "발주서" in (last["entered_basis"] or "")
          and last["entered_by"] == uid and last["entered_at"],
          str({k: last[k] for k in ("entered_kind", "entered_by", "entered_at")}))
        c("④-e 기록에 전환 전/후 단계가 남음",
          last["stage_from"] == "PREPARE" and last["stage_to"] == "OFFICIAL")

        # ⑤ 잠금 — 환경변수를 켰을 때만
        os.environ["KNK_ENABLE_MATERIAL_STAGE_LOCK"] = "1"
        c("⑤-b 공식관리는 잠금 대상이 아님",
          D.material_stage_locked(conn, pid) is False)
        conn.execute("INSERT INTO projects(name, mgmt_code) VALUES('시험설비2','A999T9902')")
        pid2 = conn.execute("SELECT id FROM projects WHERE mgmt_code='A999T9902'").fetchone()[0]
        c("⑤-c 환경변수를 켜면 Excel 단계는 잠김",
          D.material_stage_locked(conn, pid2) is True)
        os.environ.pop("KNK_ENABLE_MATERIAL_STAGE_LOCK", None)
        c("⑤-d 환경변수를 끄면 다시 안 잠김",
          D.material_stage_locked(conn, pid2) is False)

        # ⑥ 되돌리기
        r = D.set_material_stage(conn, pid, "PREPARE", decided_by=uid, note="잘못 넘겨 되돌림")
        c("⑥ 공식관리 → 준비 로 되돌릴 수 있고", r["ok"] is True, str(r))
        c("⑥-b 되돌린 것도 기록에 남음",
          len(D.material_baseline_history(conn, pid)) == 3)

        # 같은 단계로 또 넘기기
        r = D.set_material_stage(conn, pid, "PREPARE", decided_by=uid)
        c("   같은 단계로 다시 넘기면 막힘", r["ok"] is False, str(r))

        # ⛔ 기존 데이터 무변경 — projects 의 다른 칸이 안 건드려졌나
        row = conn.execute("SELECT name, mgmt_code FROM projects WHERE id=?", (pid,)).fetchone()
        c("⛔ 프로젝트의 다른 칸은 그대로",
          row[0] == "시험설비" and row[1] == "A999T9901")

    # ⭐ 실제 DB 를 정말로 안 건드렸나 — 수정시각으로 확인
    _after = os.path.getmtime(_REAL_DB) if os.path.exists(_REAL_DB) else None
    c("⭐ 실제 DB 무변경 (수정시각 그대로)", _before == _after, f"{_before} → {_after}")

    print("\n" + "=" * 74)
    print(f"  PASS {OK[0]} / FAIL {OK[1]}")
    print("=" * 74)
    sys.exit(1 if OK[1] else 0)


if __name__ == "__main__":
    main()
