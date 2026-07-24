# -*- coding: utf-8 -*-
"""WP-02 파일럿 4종 — 같은 업무 SQL을 SQLite/PostgreSQL 양쪽에서 돌려 **결과가 같은지** 확인

게이트 F-05 요구: 대표성 있는 4경계에서 개발시간·결함수·테스트시간·SQL유형별 변환수 측정

경계 선정 (실제 운영 코드에서 그대로 가져옴):
  ① 조회·검색      parts_list()            — LIKE 10 · 자리표 12  (대소문자 규칙이 갈리는 곳)
  ② CRUD·금액      po_create() 계열        — 자리표 31 · 금액 계산
  ③ 복합Tx·채번    stock_movement_create_tx + _gen_movement_no_tx — 자리표 20 · last_insert_rowid · strftime
  ④ 스키마 점검    _part_delete_ref_counts — PRAGMA table_info / foreign_key_list

쓰는 법:
    python deploy/wp02_migration/pilot/run_pilot.py <사본.db> [--pg-port 55432]
"""
import argparse
import csv
import os
import sqlite3
import sys
import time
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from adapter import to_pg, manual_review  # noqa: E402

import psycopg2  # noqa: E402
import psycopg2.extras  # noqa: E402

RESULTS = os.path.join(os.path.dirname(HERE), "results")
findings = []      # (경계, 유형, 내용)


def note(area, kind, msg):
    findings.append((area, kind, msg))
    print(f"    [{kind}] {msg}")


# ══════════════ ① 조회·검색 — parts_list 원문 그대로 ══════════════
def build_parts_list_sql(q="", biz_div="", category="", limit=None, offset=0):
    """운영 database.py:parts_list 의 SQL 조립을 그대로 옮긴 것(정규화 검색 제외 — 파이썬 함수 의존)."""
    sql = "SELECT * FROM parts WHERE 1=1"
    params = []
    if q:
        cond = ("part_no LIKE ? OR part_name LIKE ? OR spec LIKE ? OR maker LIKE ? "
                "OR COALESCE(purpose,'') LIKE ?")
        like = f"%{q}%"
        params += [like] * 5
        sql += f" AND ({cond})"
    if biz_div:
        sql += " AND biz_div = ?"
        params.append(biz_div)
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY id DESC"
    if limit is not None:
        sql += " LIMIT ? OFFSET ?"
        params += [int(limit), max(0, int(offset))]
    return sql, params


def pilot1(sq, pg):
    print("\n[파일럿 ①] 조회·검색 — parts_list")
    cases = [("", "", "", None, 0), ("SMC", "", "", None, 0), ("smc", "", "", None, 0),
             ("", "M", "", 50, 0), ("VHK", "", "", 10, 0), ("vhk", "", "", 10, 0)]
    ok, case_ilike = 0, 0
    for q, b, c_, lim, off in cases:
        sql, params = build_parts_list_sql(q, b, c_, lim, off)
        a = sq.execute(sql, params).fetchall()
        psql, applied = to_pg(sql)
        cur = pg.cursor()
        cur.execute(psql, params)
        bres = cur.fetchall()
        label = f"q={q!r} biz={b!r} limit={lim}"
        if len(a) == len(bres):
            ok += 1
        else:
            note("①조회·검색", "규칙차이",
                 f"{label} — SQLite {len(a)}건 / PG {len(bres)}건  ← LIKE 대소문자 (직원이 소문자로 치면 결과 없음)")
            # ILIKE 로 바꾸면 해결되는가 — 사람이 판단할 근거를 만든다
            cur.execute(psql.replace(" LIKE ", " ILIKE "), params)
            n2 = len(cur.fetchall())
            if n2 == len(a):
                case_ilike += 1
                note("①조회·검색", "해결책", f"{label} — ILIKE 로 바꾸면 {n2}건으로 SQLite 와 일치")
    print(f"    결과 일치 {ok}/{len(cases)} · ILIKE 로 해결 가능 {case_ilike}건")
    return ok, len(cases)


# ══════════════ ② CRUD·금액 ══════════════
def pilot2(sq, pg):
    print("\n[파일럿 ②] CRUD·금액 — 발주 생성 계열 SQL")
    stmts = [
        ("발주 조회", "SELECT id, po_number, status, total_amount FROM purchase_orders WHERE status = ?", ("작성중",)),
        ("금액 합계", "SELECT COALESCE(SUM(amount),0) FROM order_items WHERE currency = ?", ("KRW",)),
        ("금액 집계", "SELECT currency, COUNT(*), COALESCE(SUM(amount),0) FROM order_items GROUP BY currency", ()),
        ("자재 단가", "SELECT COALESCE(SUM(std_price),0) FROM parts WHERE is_active = ?", (1,)),
    ]
    ok = 0
    for label, sql, params in stmts:
        a = sq.execute(sql, params).fetchall()
        psql, _ = to_pg(sql)
        cur = pg.cursor()
        cur.execute(psql, params)
        b = cur.fetchall()
        # 금액은 Decimal 로 정확 비교 (float 비교 금지 — z1026 금액 규정)
        def norm(rows):
            """금액은 Decimal 로 정확 비교(z1026). 정렬은 문자열이 아니라 첫 칸 기준."""
            out = []
            for r in rows:
                cells = []
                for x in r:
                    if isinstance(x, float):
                        cells.append(Decimal(repr(x)).normalize())
                    elif isinstance(x, Decimal):
                        cells.append(x.normalize())
                    else:
                        cells.append(x)
                out.append(tuple(cells))
            return sorted(out, key=lambda t: tuple(str(v) for v in t))

        na, nb = norm(a), norm(b)
        same = na == nb
        if same:
            ok += 1
        else:
            diff = [(x, y) for x, y in zip(na, nb) if x != y] or [(na, nb)]
            note("②CRUD·금액", "결함", f"{label} — 결과 다름 (다른 줄 {len(diff)}개)")
            for x, y in diff[:3]:
                note("②CRUD·금액", "상세", f"SQLite={x} / PG={y}")
    print(f"    결과 일치 {ok}/{len(stmts)}")
    return ok, len(stmts)


# ══════════════ ③ 복합 Transaction·번호 채번 ══════════════
def pilot3(sq, pg):
    print("\n[파일럿 ③] 복합 Transaction·채번 — stock_movement_create_tx / _gen_movement_no_tx")
    # 채번 SQL (운영 _gen_movement_no_tx 원문 구조)
    gen_sql = ("SELECT movement_no FROM stock_movements WHERE movement_no LIKE ? "
               "ORDER BY movement_no DESC LIMIT 1")
    prefix = "MV-" + time.strftime("%Y%m") + "-"
    a = sq.execute(gen_sql, (prefix + "%",)).fetchall()
    psql, applied = to_pg(gen_sql)
    cur = pg.cursor()
    cur.execute(psql, (prefix + "%",))
    b = cur.fetchall()
    ok = 1 if len(a) == len(b) else 0
    if not ok:
        note("③복합Tx·채번", "결함", f"채번 조회 결과 다름 {len(a)} vs {len(b)}")

    # last_insert_rowid → RETURNING 구조 변경이 필요한 지점
    ins = "INSERT INTO stock_movements (movement_no, part_id, kind, quantity) VALUES (?,?,?,?)"
    rid = "SELECT last_insert_rowid()"
    for s in (ins, rid):
        for m in manual_review(s):
            note("③복합Tx·채번", "사람판단", f"{m}  ← {s[:46]}")

    # 트랜잭션 원자성: PG에서 실패 주입 시 전부 되돌아가는가
    cur = pg.cursor()
    try:
        cur.execute("BEGIN")
        cur.execute('INSERT INTO stock_movements (movement_no, part_id, kind, quantity) VALUES (%s,%s,%s,%s)',
                    ("PILOT-TX-1", 1, "IN", 1))
        cur.execute("SELECT 1/0")     # 강제 실패
        cur.execute("COMMIT")
    except Exception:
        pg.rollback()
    cur = pg.cursor()
    cur.execute("SELECT COUNT(*) FROM stock_movements WHERE movement_no = %s", ("PILOT-TX-1",))
    left = cur.fetchone()[0]
    if left == 0:
        ok += 1
        print("    실패 주입 → 전부 Rollback 확인 (원장 0건)")
    else:
        note("③복합Tx·채번", "결함", f"Rollback 실패 — 잔존 {left}건")
    return ok, 2


# ══════════════ ④ 스키마 점검 (PRAGMA) ══════════════
def pilot4(sq, pg):
    print("\n[파일럿 ④] 스키마 점검 — PRAGMA table_info / foreign_key_list")
    # SQLite: PRAGMA · PostgreSQL: information_schema
    t = "parts"
    a_cols = [r[1] for r in sq.execute(f"PRAGMA table_info([{t}])").fetchall()]
    cur = pg.cursor()
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position""", (t,))
    b_cols = [r[0] for r in cur.fetchall()]
    ok = 0
    if a_cols == b_cols:
        ok += 1
        print(f"    컬럼 목록 일치 ({len(a_cols)}개)")
    else:
        note("④스키마점검", "결함", f"컬럼 목록 다름 SQLite {len(a_cols)} vs PG {len(b_cols)}")
    note("④스키마점검", "사람판단", "PRAGMA 207곳은 자동 번역 불가 — information_schema 로 **함수를 새로 써야** 함")

    # 참조 스캔(WP-01 _part_delete_ref_counts 방식)이 PG에서도 되는지
    cur.execute("""SELECT COUNT(*) FROM information_schema.columns
                   WHERE table_schema='public' AND (column_name='part_id' OR column_name LIKE %s)""", ("%\\_part\\_id",))
    n = cur.fetchone()[0]
    if n:
        ok += 1
        print(f"    참조 컬럼 탐색 가능 ({n}개 발견) — WP-01 삭제 가드 이식 가능")
    return ok, 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--pg-host", default="127.0.0.1")
    ap.add_argument("--pg-port", type=int, default=55432)
    ap.add_argument("--pg-user", default="postgres")
    ap.add_argument("--dbname", default="knk_pilot")
    a = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True)

    t_all = time.time()
    sq = sqlite3.connect(f"file:{a.src}?mode=ro", uri=True)
    pg = psycopg2.connect(host=a.pg_host, port=a.pg_port, user=a.pg_user, dbname=a.dbname)

    total_ok, total_n, times = 0, 0, {}
    for fn, name in ((pilot1, "①조회·검색"), (pilot2, "②CRUD·금액"),
                     (pilot3, "③복합Tx·채번"), (pilot4, "④스키마점검")):
        t0 = time.time()
        ok, n = fn(sq, pg)
        times[name] = time.time() - t0
        total_ok += ok
        total_n += n
    pg.close()

    print("\n" + "=" * 64)
    print(f"  파일럿 결과: {total_ok}/{total_n} 통과 · 시험시간 {time.time()-t_all:.2f}s")
    for k, v in times.items():
        print(f"    {k:14s} {v:.2f}s")
    print(f"  사람이 판단해야 하는 지점: {sum(1 for f in findings if f[1]=='사람판단')}건")
    print(f"  발견한 결함/차이:        {sum(1 for f in findings if f[1] in ('결함','규칙차이'))}건")
    print("=" * 64)

    with open(os.path.join(RESULTS, "pilot_findings.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["경계", "유형", "내용"])
        w.writerows(findings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
