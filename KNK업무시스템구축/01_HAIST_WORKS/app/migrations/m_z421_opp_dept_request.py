"""
v5H226z421 (2026-06-14, 대표 지시) — 영업 기회 → 부서 요청 흐름 (수주 전 부서 협업) 1단계

대표 지시(설계 확정 5문항):
  ① 요청은 '영업 기회'에서 시작(업무 순서 명확화)
  ② 영업 기회 1건당 '부서별 1요청'
  ③ 요청 생성 시 해당 부서 팀장에게 메신저(KNK Eum) 푸시
  ④ 구성원이 본인 활동·시간(h) 자가 기록 (← 시간/대시보드는 2단계)
  ⑤ 열람: 지금은 대표만(집계) · 팀장=우리 팀 요청 · PM·구성원=본인 할당

흐름: 영업(영업기회) → 부서 팀장에게 요청 → 팀장이 PM 지정 → PM이 구성원 추가
      → (2단계) 구성원이 검토·시장조사·기술조사·제안 활동/시간 기록 → 부서별 집계

추가 테이블:
  opp_dept_requests   — 영업 기회 → 부서 요청(부서별 1건)
  opp_request_members — PM이 추가한 구성원(role_in_req=pm/member)

idempotent: 이미 있으면 건너뜀. main.py startup() 에서 1회 호출.
"""
import sqlite3


def migrate(db_path: str) -> dict:
    created = []
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        have = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        if "opp_dept_requests" not in have:
            cur.execute("""
                CREATE TABLE opp_dept_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opp_id INTEGER NOT NULL,
                    team_id INTEGER NOT NULL,
                    title TEXT,
                    detail TEXT,
                    due_date TEXT,
                    status TEXT DEFAULT 'requested',
                    pm_user_id INTEGER,
                    requested_by INTEGER,
                    assigned_by INTEGER,
                    assigned_at TEXT,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_oppreq_team "
                        "ON opp_dept_requests(team_id, status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_oppreq_opp "
                        "ON opp_dept_requests(opp_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_oppreq_pm "
                        "ON opp_dept_requests(pm_user_id)")
            created.append("opp_dept_requests")

        if "opp_request_members" not in have:
            cur.execute("""
                CREATE TABLE opp_request_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    role_in_req TEXT DEFAULT 'member',
                    added_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_oppreqmem_req "
                        "ON opp_request_members(request_id)")
            cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_oppreqmem "
                        "ON opp_request_members(request_id, user_id)")
            created.append("opp_request_members")

        conn.commit()
    finally:
        conn.close()
    return {"created": created}


if __name__ == "__main__":
    import sys
    print(migrate(sys.argv[1] if len(sys.argv) > 1 else "data/knk.db"))
