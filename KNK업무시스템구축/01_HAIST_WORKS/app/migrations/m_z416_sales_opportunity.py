"""
v5H226z416 (2026-06-14, 대표 지시) — 영업 기회(수주 전) 테이블

대표 지시: 수주 전 단계(미팅·제안서·견적서)를 '관리코드 발번 전'에 따로 관리하고,
수주 확정 시 프로젝트(관리코드)로 승격(B 구조). 미팅은 간단 체크+메모.

추가 테이블:
  sales_opportunities — 관리코드 없는 수주 전 영업 건
    · 기본: opp_no(OPP-YYMM-###)·title·customer·biz_div(예상 T/M/L/E)·model·owner·예상금액
    · 단계: 미팅 → 제안 → 견적 → 수주예정 → (수주확정/보류/실주)
    · 미팅/제안서/견적서: 각 done·date·memo
    · promoted_project_id(승격된 프로젝트), status(active/won/lost/hold)

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
        if "sales_opportunities" not in have:
            cur.execute("""
                CREATE TABLE sales_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opp_no TEXT,
                    title TEXT NOT NULL,
                    customer_id INTEGER,
                    customer_name TEXT,
                    biz_div TEXT,
                    model_name TEXT,
                    owner_user_id INTEGER,
                    expected_amount REAL DEFAULT 0,
                    currency TEXT DEFAULT 'KRW',
                    expected_order_ym TEXT,
                    stage TEXT DEFAULT '미팅',
                    status TEXT DEFAULT 'active',
                    meeting_done INTEGER DEFAULT 0,
                    meeting_date TEXT,
                    meeting_memo TEXT,
                    proposal_done INTEGER DEFAULT 0,
                    proposal_date TEXT,
                    proposal_memo TEXT,
                    quotation_done INTEGER DEFAULT 0,
                    quotation_date TEXT,
                    quotation_memo TEXT,
                    note TEXT,
                    promoted_project_id INTEGER,
                    created_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    updated_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_opp_stage "
                        "ON sales_opportunities(status, stage)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_opp_owner "
                        "ON sales_opportunities(owner_user_id)")
            created.append("sales_opportunities")
        # v5H226z418 (대표 지시): 정식 견적서 링크 컬럼 + 첨부파일 테이블 (idempotent)
        opp_cols = {r[1] for r in cur.execute("PRAGMA table_info(sales_opportunities)").fetchall()}
        if opp_cols and "quotation_id" not in opp_cols:
            try:
                cur.execute("ALTER TABLE sales_opportunities ADD COLUMN quotation_id INTEGER")
                created.append("sales_opportunities.quotation_id")
            except Exception:
                pass
        have2 = {r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "sales_opportunity_files" not in have2:
            cur.execute("""
                CREATE TABLE sales_opportunity_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opp_id INTEGER NOT NULL,
                    kind TEXT DEFAULT 'etc',
                    orig_name TEXT,
                    url TEXT,
                    size INTEGER DEFAULT 0,
                    uploaded_by INTEGER,
                    created_at TEXT DEFAULT (datetime('now','localtime'))
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_opp_files "
                        "ON sales_opportunity_files(opp_id, kind)")
            created.append("sales_opportunity_files")
        conn.commit()
    finally:
        conn.close()
    return {"created": created}


if __name__ == "__main__":
    import sys
    print(migrate(sys.argv[1] if len(sys.argv) > 1 else "data/knk.db"))
