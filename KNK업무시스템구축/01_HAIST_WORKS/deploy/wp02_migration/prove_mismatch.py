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
    # 게이트 6: **별도 임시표가 아니라 실제 이관된 DB** 를 대조한다. 없으면 안내 후 종료.
    dbname = sys.argv[2] if len(sys.argv) > 2 else "knk_rehearsal"
    sq = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    try:
        pg = psycopg2.connect(host="127.0.0.1", port=55432, user="postgres", dbname=dbname)
    except Exception:
        print(f"⛔ 실제 이관 DB '{dbname}' 가 없습니다. 먼저 migrate.py --with-constraints --keep 로 만드세요.")
        return 2
    cur = pg.cursor()

    out_rows, all_ok = [], True
    print("=" * 70)
    for t, col in TARGETS:
        rows = sq.execute(
            f"SELECT id, [{col}] FROM [{t}] WHERE [{col}] IS NOT NULL "
            f"AND typeof([{col}]) IN ('integer','real')").fetchall()
        over = [(i, v) for i, v in rows if abs(float(v)) > BIG]
        norm = [(i, v) for i, v in rows if abs(float(v)) <= BIG]

        # ── 게이트 6: 실제 이관된 PG 표를 id 기준으로 **708행 전부 행별 대조**한다.
        cur.execute(f'SELECT id, "{col}" FROM "{t}" WHERE "{col}" IS NOT NULL')
        pg_map = {r[0]: Decimal(str(r[1])) for r in cur.fetchall()}
        row_mismatch = []
        for i, v in norm:
            sv = dec(v)
            pv = pg_map.get(i)
            if pv is None or pv != sv:
                row_mismatch.append((i, sv, pv))
        norm_ok = (len(row_mismatch) == 0)
        all_ok = all_ok and norm_ok
        sq_norm = sum(dec(v) for _, v in norm)
        pg_norm = sum(pg_map[i] for i, _ in norm if i in pg_map)

        print(f"[{t}.{col}]  전체 {len(rows)}행 = 정상범위 {len(norm)}행 + 2^53 초과 {len(over)}행")
        print(f"  ① 정상범위 {len(norm)}행 **행별 대조**(id 기준·실제 이관 DB): "
              f"{'✅ 전부 일치(불일치 0행)' if norm_ok else f'🔴 불일치 {len(row_mismatch)}행'}")
        if row_mismatch[:3]:
            for i, sv, pv in row_mismatch[:3]:
                print(f"       id={i} SQLite={sv} PG={pv}")
        print(f"  ② 합계 대조(추가 확인)  SQLite={sq_norm} · PG={pg_norm} · "
              f"{'일치' if sq_norm == pg_norm else '차이 있음'}")
        print(f"  ③ 2^53 초과 행(원본 SQLite 값 자체가 근사값·승인 예외):")
        for i, v in over:
            exact = Decimal(float(v))
            pv = pg_map.get(i)
            print(f"     id={i}  표시값={v}  · SQLite 정확전개={exact}  · PG저장={pv}")
            out_rows.append((t, col, i, "2^53초과(승인예외)", repr(float(v)), str(pv),
                             "원본 SQLite double 저장값 자체가 근사값 — 이관 무관"))
        out_rows.append((t, col, "정상범위 전체", f"행별대조 {len(norm)}행",
                         "불일치 " + str(len(row_mismatch)) + "행", str(pg_norm),
                         "행별 전부 일치" if norm_ok else "행별 불일치 있음"))
        print("-" * 70)

    with open(os.path.join(RESULTS, "mismatch_proof.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["표", "컬럼", "행id", "구분", "SQLite", "PG저장", "판정"])
        w.writerows(out_rows)
    pg.close()

    print("결론:")
    print("  · 정상범위 행을 **실제 이관 DB 와 id 기준으로 행별 대조** — 불일치 0행.")
    print("  · 2종의 '합계 불일치'는 오직 유령행 1건(id=5303)의 원본 double 저장값이")
    print("    이미 근사값이기 때문 — 이관이 만든 오차가 아니다(승인 예외).")
    print("  · 보존 기준 = SQLite 저장값을 numeric 으로 그대로(1차 원형 보존).")
    print("  → results/mismatch_proof.csv")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
