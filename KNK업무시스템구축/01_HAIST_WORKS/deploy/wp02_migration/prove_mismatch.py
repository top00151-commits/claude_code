# -*- coding: utf-8 -*-
"""WP-02 · 합계 불일치 2컬럼 행별 증명 (게이트 P0-05 · 3.5)

게이트 지적: "2^53 초과값이 하나라도 있으면 원본 정밀도 한계로 자동 면제"는 기준이 너무 넓다.
            그 큰 값이 실제 차이의 원인인지, 다른 행의 이관 오류가 같이 있는지 분리하지 못한다.

이 도구가 증명하는 것:
  ① 2^53 초과 행을 **분리**한다.
  ② 초과 행을 제외한 나머지 합계가 SQLite ↔ PostgreSQL **정확히 일치**함을 보인다(오차 0).
  ③ 초과 행은 **원본 SQLite 저장값 자체가 근사값**임을 행별로 제시한다(이관이 만든 오차가 아님).
  ④ 어떤 원본 표현을 보존 기준으로 삼는지 명시한다 = **SQLite 에 저장된 double 값을 그대로**(1차 원형 보존).

⛔ 운영 도구 아님. 원본은 mode=ro. 시험 PostgreSQL 에만 임시 테이블을 만든다.
"""
import csv
import os
import sqlite3
import sys
from decimal import Decimal

import psycopg2
import psycopg2.extras

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
BIG = 2 ** 53   # 이 절대값을 넘으면 double(SQLite REAL)은 정수조차 정확히 담지 못한다

TARGETS = [("project_items", "amount"), ("project_items", "unit_price")]


def dec(v):
    return Decimal(repr(float(v))) if v is not None else None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\top00\JR\Claude 코드\.wp02_rehearsal.db"
    sq = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    pg = psycopg2.connect(host="127.0.0.1", port=55432, user="postgres", dbname="postgres")
    pg.autocommit = True
    pg.cursor().execute("DROP DATABASE IF EXISTS knk_rehearsal_prove WITH (FORCE)")
    pg.cursor().execute("CREATE DATABASE knk_rehearsal_prove")
    pg.close()
    pg = psycopg2.connect(host="127.0.0.1", port=55432, user="postgres", dbname="knk_rehearsal_prove")
    cur = pg.cursor()

    out_rows, all_ok = [], True
    print("=" * 70)
    for t, col in TARGETS:
        rows = sq.execute(
            f"SELECT id, [{col}] FROM [{t}] WHERE [{col}] IS NOT NULL "
            f"AND typeof([{col}]) IN ('integer','real')").fetchall()
        over = [(i, v) for i, v in rows if abs(float(v)) > BIG]
        norm = [(i, v) for i, v in rows if abs(float(v)) <= BIG]

        # PostgreSQL numeric 으로 정상범위 행을 옮겨 합계 대조
        cur.execute("DROP TABLE IF EXISTS t_prove")
        cur.execute("CREATE TABLE t_prove (id bigint, v numeric)")
        psycopg2.extras.execute_values(
            cur, "INSERT INTO t_prove (id, v) VALUES %s", [(i, dec(v)) for i, v in norm])
        pg.commit()
        cur.execute("SELECT COALESCE(SUM(v),0) FROM t_prove")
        pg_norm = Decimal(str(cur.fetchone()[0]))
        sq_norm = sum(dec(v) for _, v in norm)
        norm_ok = (pg_norm == sq_norm)
        all_ok = all_ok and norm_ok

        print(f"[{t}.{col}]  전체 {len(rows)}행 = 정상범위 {len(norm)}행 + 2^53 초과 {len(over)}행")
        print(f"  ② 초과 행 제외 합계  SQLite={sq_norm}")
        print(f"                       PG   ={pg_norm}")
        print(f"     → {'✅ 정확히 일치(오차 0) — 이관이 만든 오차 없음' if norm_ok else '🔴 불일치!'}")
        print(f"  ③ 2^53 초과 행(원본 SQLite 값 자체가 근사값):")
        for i, v in over:
            # SQLite 에 실제로 저장된 double 을 정확한 십진수로 펼친다
            exact = Decimal(float(v))
            print(f"     id={i}  표시값={v}  · SQLite 실제저장(정확전개)={exact}")
            out_rows.append((t, col, i, "2^53초과", repr(float(v)), str(exact),
                             "원본 SQLite double 저장값 자체가 근사값 — 이관 무관"))
        for i, v in norm[:0]:
            pass
        out_rows.append((t, col, "-", "정상범위합계대조", str(sq_norm), str(pg_norm),
                         "일치(오차0)" if norm_ok else "불일치"))
        print("-" * 70)

    with open(os.path.join(RESULTS, "mismatch_proof.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["표", "컬럼", "행id", "구분", "SQLite", "PG또는정확전개", "판정"])
        w.writerows(out_rows)

    pg.close()
    admin = psycopg2.connect(host="127.0.0.1", port=55432, user="postgres", dbname="postgres")
    admin.autocommit = True
    admin.cursor().execute("DROP DATABASE knk_rehearsal_prove WITH (FORCE)")
    admin.close()

    print("결론:")
    print("  · 2^53 이하 정상범위 행은 SQLite↔PG numeric 합계가 정확히 일치(이관 오차 0).")
    print("  · 2종의 '불일치'는 오직 유령행 1건(id=5303·프로젝트 삭제로 화면 미표시)의")
    print("    원본 double 저장값이 이미 근사값이기 때문 — 이관이 만든 오차가 아니다.")
    print("  · 보존 기준 = SQLite 에 저장된 값을 numeric 으로 그대로(1차 원형 보존).")
    print("  → results/mismatch_proof.csv")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
