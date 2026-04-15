"""
KNK 물류허브 — 데이터베이스 모듈
SQLite 기반, 점진적 확장 가능 스키마.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, date

# ─────────────────────────────────────────────────────────────
# KNK 표준 상수 (엑셀정리스킬 §11~12 준수)
# ─────────────────────────────────────────────────────────────
BIZ_CODE = {"검사기": "T", "자동화": "M"}      # 사업부명 → 코드
BIZ_NAME = {v: k for k, v in BIZ_CODE.items()} # 코드 → 사업부명

STAGES = ["제안작성", "제안제출", "수주확정", "납품", "개조", "A/S"]
NEEDS_CODE_STAGES = ("수주확정", "납품", "개조", "A/S")  # 채번 대상

PO_TYPES = ["신규", "추가"]
STATUSES = ["수주예정", "진행중", "납품완료", "취소", "보류"]


DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "knk_logistics.db",
)


def now_str() -> str:
    """현재 시각 'YYYY-MM-DD HH:MM:SS' 문자열"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def get_conn():
    """SQLite 연결 컨텍스트 매니저 — Row 팩토리 + 외래키 ON"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """스키마 생성 + 누락 컬럼 마이그레이션"""
    with get_conn() as conn:
        # ── 부품 마스터 ───────────────────────────────────────────
        conn.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            part_no     TEXT NOT NULL UNIQUE,   -- 부품번호 (고유)
            part_name   TEXT NOT NULL,           -- 품명
            spec        TEXT,                    -- 규격
            maker       TEXT,                    -- 메이커
            origin      TEXT,                    -- 원산지 (KOREA/JAPAN/...)
            unit        TEXT DEFAULT 'EA',       -- 단위 (EA/SET/KG/...)
            currency    TEXT DEFAULT 'KRW',      -- KRW/USD
            std_price   REAL DEFAULT 0,          -- 표준단가
            biz_div     TEXT,                    -- 사업부 (T 검사기 / M 자동화 / 공통)
            category    TEXT,                    -- 분류 (완성품/자재/소모품)
            note        TEXT,                    -- 비고
            is_active   INTEGER DEFAULT 1,       -- 사용여부
            created_at  TEXT,
            updated_at  TEXT
        )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_parts_part_no ON parts(part_no)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_parts_biz_div ON parts(biz_div)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_parts_category ON parts(category)")

        # ── 프로젝트 (관리코드 발행대장) ─────────────────────────
        # KNK PMS 표준 8자리: [일련 3] + [사업부 1] + [연월 4]  예: 001T2604
        conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            mgmt_code     TEXT UNIQUE,             -- 관리코드 8자리 (제안 단계는 NULL)
            biz_div       TEXT NOT NULL,           -- 사업부 코드 T/M
            project_name  TEXT NOT NULL,           -- 프로젝트명
            customer      TEXT,                    -- 고객사
            model         TEXT,                    -- 모델/품명
            stage         TEXT DEFAULT '제안작성',  -- 영업단계
            po_type       TEXT DEFAULT '신규',      -- 신규/추가
            status        TEXT DEFAULT '수주예정',  -- 진행상태
            customer_po   TEXT,                    -- 고객 PO번호 (원문)
            currency      TEXT DEFAULT 'KRW',      -- KRW/USD
            order_amount  REAL DEFAULT 0,          -- 수주금액
            order_date    TEXT,                    -- 수주일 YYYY-MM-DD
            due_date      TEXT,                    -- 납기일 YYYY-MM-DD
            pm            TEXT,                    -- PM
            sales         TEXT,                    -- 담당영업
            note          TEXT,
            created_at    TEXT,
            updated_at    TEXT
        )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_proj_mgmt_code ON projects(mgmt_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_proj_biz_div ON projects(biz_div)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_proj_stage ON projects(stage)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_proj_status ON projects(status)")


# ─────────────────────────────────────────────────────────────
# 부품 (parts) CRUD
# ─────────────────────────────────────────────────────────────

def list_parts(q: str = "", biz_div: str = "", category: str = "") -> list[sqlite3.Row]:
    sql = "SELECT * FROM parts WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (part_no LIKE ? OR part_name LIKE ? OR spec LIKE ? OR maker LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like, like]
    if biz_div:
        sql += " AND biz_div = ?"
        params.append(biz_div)
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id DESC"
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_part(pid: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM parts WHERE id = ?", (pid,)).fetchone()


def create_part(data: dict) -> int:
    cols = ["part_no", "part_name", "spec", "maker", "origin", "unit",
            "currency", "std_price", "biz_div", "category", "note",
            "is_active", "created_at", "updated_at"]
    now = now_str()
    values = [
        data.get("part_no", "").strip(),
        data.get("part_name", "").strip(),
        data.get("spec", "").strip(),
        data.get("maker", "").strip(),
        data.get("origin", "").strip(),
        data.get("unit", "EA").strip() or "EA",
        data.get("currency", "KRW").strip() or "KRW",
        float(data.get("std_price") or 0),
        data.get("biz_div", "").strip(),
        data.get("category", "").strip(),
        data.get("note", "").strip(),
        1 if data.get("is_active", 1) else 0,
        now, now,
    ]
    placeholders = ",".join(["?"] * len(cols))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO parts ({','.join(cols)}) VALUES ({placeholders})",
            values,
        )
        return cur.lastrowid


def update_part(pid: int, data: dict) -> None:
    fields = ["part_no", "part_name", "spec", "maker", "origin", "unit",
              "currency", "std_price", "biz_div", "category", "note", "is_active"]
    sets = ", ".join([f"{f} = ?" for f in fields]) + ", updated_at = ?"
    values = [
        data.get("part_no", "").strip(),
        data.get("part_name", "").strip(),
        data.get("spec", "").strip(),
        data.get("maker", "").strip(),
        data.get("origin", "").strip(),
        data.get("unit", "EA").strip() or "EA",
        data.get("currency", "KRW").strip() or "KRW",
        float(data.get("std_price") or 0),
        data.get("biz_div", "").strip(),
        data.get("category", "").strip(),
        data.get("note", "").strip(),
        1 if data.get("is_active", 1) else 0,
        now_str(),
    ]
    with get_conn() as conn:
        conn.execute(f"UPDATE parts SET {sets} WHERE id = ?", values + [pid])


def delete_part(pid: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM parts WHERE id = ?", (pid,))


def count_parts() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM parts WHERE is_active = 1").fetchone()[0]
        by_div = conn.execute(
            "SELECT biz_div, COUNT(*) AS n FROM parts GROUP BY biz_div"
        ).fetchall()
    return {
        "total": total,
        "active": active,
        "by_div": {r["biz_div"] or "(미지정)": r["n"] for r in by_div},
    }


# ─────────────────────────────────────────────────────────────
# 프로젝트 (projects) — 관리코드 발행대장
# ─────────────────────────────────────────────────────────────

def generate_mgmt_code(biz_div: str, today: date | None = None) -> str:
    """KNK PMS 표준 관리코드 자동 채번
    포맷: [일련 3자리][사업부 1자리][YYMM 4자리] = 8자리
    예) 001T2604
    같은 사업부·같은 연월 안에서 일련번호 +1 (UNIQUE 제약으로 중복 차단)
    """
    if biz_div not in ("T", "M"):
        raise ValueError(f"사업부 코드는 T 또는 M이어야 합니다 (입력: {biz_div})")

    today = today or date.today()
    yymm = today.strftime("%y%m")          # "2604"
    prefix_pat = f"%{biz_div}{yymm}"       # LIKE 패턴

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT mgmt_code FROM projects WHERE mgmt_code LIKE ?",
            (prefix_pat,),
        ).fetchall()

    max_seq = 0
    for r in rows:
        code = r["mgmt_code"] or ""
        if len(code) == 8 and code[3] == biz_div and code[4:] == yymm:
            try:
                max_seq = max(max_seq, int(code[:3]))
            except ValueError:
                pass

    return f"{max_seq + 1:03d}{biz_div}{yymm}"


def _maybe_assign_code(data: dict) -> str | None:
    """영업단계가 채번 대상이고 코드가 비어있으면 자동 채번"""
    stage = (data.get("stage") or "").strip()
    biz_div = (data.get("biz_div") or "").strip()
    existing = (data.get("mgmt_code") or "").strip()

    if existing:
        return existing  # 사용자가 직접 입력한 코드는 존중
    if stage in NEEDS_CODE_STAGES and biz_div in ("T", "M"):
        return generate_mgmt_code(biz_div)
    return None


def list_projects(q: str = "", biz_div: str = "", stage: str = "",
                  status: str = "") -> list[sqlite3.Row]:
    sql = "SELECT * FROM projects WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (mgmt_code LIKE ? OR project_name LIKE ? OR customer LIKE ? OR model LIKE ? OR pm LIKE ? OR sales LIKE ?)"
        like = f"%{q}%"
        params += [like] * 6
    if biz_div:
        sql += " AND biz_div = ?"
        params.append(biz_div)
    if stage:
        sql += " AND stage = ?"
        params.append(stage)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY id DESC"
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_project(pid: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM projects WHERE id = ?", (pid,)).fetchone()


def create_project(data: dict) -> tuple[int, str | None]:
    """프로젝트 생성. 채번이 일어나면 (id, code), 아니면 (id, None) 반환"""
    code = _maybe_assign_code(data)
    cols = ["mgmt_code", "biz_div", "project_name", "customer", "model",
            "stage", "po_type", "status", "customer_po", "currency",
            "order_amount", "order_date", "due_date", "pm", "sales", "note",
            "created_at", "updated_at"]
    now = now_str()
    values = [
        code,
        data.get("biz_div", "").strip(),
        data.get("project_name", "").strip(),
        data.get("customer", "").strip(),
        data.get("model", "").strip(),
        data.get("stage", "제안작성").strip() or "제안작성",
        data.get("po_type", "신규").strip() or "신규",
        data.get("status", "수주예정").strip() or "수주예정",
        data.get("customer_po", "").strip(),
        data.get("currency", "KRW").strip() or "KRW",
        float(data.get("order_amount") or 0),
        data.get("order_date", "").strip(),
        data.get("due_date", "").strip(),
        data.get("pm", "").strip(),
        data.get("sales", "").strip(),
        data.get("note", "").strip(),
        now, now,
    ]
    placeholders = ",".join(["?"] * len(cols))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO projects ({','.join(cols)}) VALUES ({placeholders})",
            values,
        )
        return cur.lastrowid, code


def update_project(pid: int, data: dict) -> str | None:
    """프로젝트 수정. 기존 코드가 비어있고 단계가 채번대상으로 바뀌면 자동 채번"""
    current = get_project(pid)
    if not current:
        return None

    # 기존 코드가 있으면 유지, 없고 단계가 채번 대상이면 신규 채번
    new_code = current["mgmt_code"]
    if not new_code:
        stage = (data.get("stage") or "").strip()
        biz_div = (data.get("biz_div") or "").strip()
        if stage in NEEDS_CODE_STAGES and biz_div in ("T", "M"):
            new_code = generate_mgmt_code(biz_div)

    fields = ["mgmt_code", "biz_div", "project_name", "customer", "model",
              "stage", "po_type", "status", "customer_po", "currency",
              "order_amount", "order_date", "due_date", "pm", "sales", "note"]
    sets = ", ".join([f"{f} = ?" for f in fields]) + ", updated_at = ?"
    values = [
        new_code,
        data.get("biz_div", "").strip(),
        data.get("project_name", "").strip(),
        data.get("customer", "").strip(),
        data.get("model", "").strip(),
        data.get("stage", "제안작성").strip() or "제안작성",
        data.get("po_type", "신규").strip() or "신규",
        data.get("status", "수주예정").strip() or "수주예정",
        data.get("customer_po", "").strip(),
        data.get("currency", "KRW").strip() or "KRW",
        float(data.get("order_amount") or 0),
        data.get("order_date", "").strip(),
        data.get("due_date", "").strip(),
        data.get("pm", "").strip(),
        data.get("sales", "").strip(),
        data.get("note", "").strip(),
        now_str(),
    ]
    with get_conn() as conn:
        conn.execute(f"UPDATE projects SET {sets} WHERE id = ?", values + [pid])
    return new_code


def delete_project(pid: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (pid,))


def count_projects() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
        with_code = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE mgmt_code IS NOT NULL AND mgmt_code != ''"
        ).fetchone()[0]
        in_progress = conn.execute(
            "SELECT COUNT(*) FROM projects WHERE status = '진행중'"
        ).fetchone()[0]
        by_div = conn.execute(
            "SELECT biz_div, COUNT(*) AS n FROM projects GROUP BY biz_div"
        ).fetchall()
        by_stage = conn.execute(
            "SELECT stage, COUNT(*) AS n FROM projects GROUP BY stage"
        ).fetchall()
    return {
        "total": total,
        "with_code": with_code,
        "in_progress": in_progress,
        "by_div": {(BIZ_NAME.get(r["biz_div"]) or r["biz_div"] or "(미지정)"): r["n"]
                   for r in by_div},
        "by_stage": {r["stage"] or "(미지정)": r["n"] for r in by_stage},
    }
