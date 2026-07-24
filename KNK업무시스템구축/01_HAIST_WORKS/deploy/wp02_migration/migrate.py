# -*- coding: utf-8 -*-
"""WP-02 이관 리허설 — SQLite 사본 → PostgreSQL (재현 가능 도구)

⛔ 운영 DB에는 절대 쓰지 않는다. 원본은 항상 `mode=ro` 로만 연다.
⛔ 이 파일은 앱이 import 하지 않는다(배포돼도 실행되지 않음).

쓰는 법:
    python deploy/wp02_migration/migrate.py <사본.db> [--pg-port 55432] [--keep]

산출물(results/ 폴더):
    ddl.sql                 생성한 PostgreSQL DDL 전문
    type_mapping.csv        컬럼별 타입 매핑과 근거 규정
    object_matrix.csv       표별 객체(PK/FK/UNIQUE/CHECK/DEFAULT/INDEX) 전환 결과
    rowcount.csv            표별 이관 전후 행 수
    sums.csv                금액·수량 합계 대조 (Decimal 정확 비교)
    cleaned.csv             정제한 값(빈칸→NULL 등) 목록
    run.log                 실행 로그(시간 포함)

금액 비교는 **Decimal** 로만 한다 — float 합산은 큰 금액에서 원 단위가 깨진다(실측 19,460원).
"""
import argparse
import csv
import hashlib
import os
import re
import sqlite3
import sys
import time
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from type_map import build_table, classify, RE_MONEY, RE_QTY, RE_DECIMAL_OK  # noqa: E402

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    print("psycopg2 가 없습니다:  pip install psycopg2-binary")
    raise SystemExit(2)

RESULTS = os.path.join(HERE, "results")
LOG_LINES = []


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    LOG_LINES.append(line)
    print(line)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dec(v):
    """SQLite 값을 정확한 Decimal 로. float 경유를 최소화한다."""
    if v is None:
        return None
    if isinstance(v, int):
        return Decimal(v)
    return Decimal(repr(float(v)))


def guard_target(host: str, dbname: str):
    """P0-02: 도구 자체가 오작동을 거부한다 — 문구가 아니라 코드로 막는다.
    · 로컬 시험 호스트만 허용
    · 데이터베이스 이름은 시험 접두어 강제
    · 알려진 운영 호스트·운영 DB 이름은 실행 거부
    """
    LOCAL = {"127.0.0.1", "localhost", "::1"}
    PREFIX = "knk_rehearsal"          # 시험 DB 접두어(뒤에 _seq, _pilot 등 붙일 수 있음)
    FORBIDDEN_HOST_HINT = ("knknara", "haist", "nas", "prod")
    FORBIDDEN_DB = {"knk", "knk_haist", "haist", "works", "postgres", "template0", "template1"}

    if host not in LOCAL:
        raise SystemExit(f"⛔ 중단: 이 도구는 로컬 시험 서버에서만 씁니다 (받은 값: {host})")
    if any(h in host.lower() for h in FORBIDDEN_HOST_HINT):
        raise SystemExit(f"⛔ 중단: 운영으로 보이는 주소입니다 ({host})")
    if dbname.lower() in FORBIDDEN_DB:
        raise SystemExit(f"⛔ 중단: 운영 데이터베이스 이름입니다 ({dbname})")
    if not dbname.startswith(PREFIX):
        raise SystemExit(f"⛔ 중단: 시험 데이터베이스 이름은 '{PREFIX}' 로 시작해야 합니다 (받은 값: {dbname})")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", dbname):
        raise SystemExit(f"⛔ 중단: 데이터베이스 이름에 쓸 수 없는 글자가 있습니다 ({dbname})")
    print(f"[안전확인] 대상 서버 {host} · 데이터베이스 {dbname} — 시험 전용으로 확인됨")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--pg-host", default="127.0.0.1")
    ap.add_argument("--pg-port", type=int, default=55432)
    ap.add_argument("--pg-user", default="postgres")
    ap.add_argument("--dbname", default="knk_rehearsal")
    ap.add_argument("--keep", action="store_true", help="끝나고 데이터베이스를 지우지 않는다")
    ap.add_argument("--allow-clean", action="store_true",
                    help="P0-03: 값 정제(빈칸→NULL 등)를 허용한다. 기본은 **정제 대상이 있으면 중단**")
    a = ap.parse_args()

    guard_target(a.pg_host, a.dbname)      # ← P0-02 안전장치
    os.makedirs(RESULTS, exist_ok=True)
    t_all = time.time()
    log(f"원본 사본: {a.src}")
    log(f"원본 SHA-256: {sha256_file(a.src)}")

    src = sqlite3.connect(f"file:{a.src}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    tables = [r[0] for r in src.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite%' ORDER BY name")]
    log(f"대상 표 {len(tables)}개")

    admin = psycopg2.connect(host=a.pg_host, port=a.pg_port, user=a.pg_user, dbname="postgres")
    admin.autocommit = True
    cur0 = admin.cursor()
    cur0.execute("SELECT version()")
    pgver = cur0.fetchone()[0]
    log(f"PostgreSQL: {pgver.split(',')[0]}")
    t0 = time.time()
    cur0.execute(f'DROP DATABASE IF EXISTS {a.dbname} WITH (FORCE)')
    cur0.execute(f'CREATE DATABASE {a.dbname} ENCODING UTF8 TEMPLATE template0')
    admin.close()
    t_create = time.time() - t0
    log(f"데이터베이스 생성 {t_create:.2f}s")

    con = psycopg2.connect(host=a.pg_host, port=a.pg_port, user=a.pg_user, dbname=a.dbname)
    cur = con.cursor()

    # ── 1) 스키마
    t0 = time.time()
    ddl_all, mapping_all, objmatrix, made, failed_schema = [], [], [], 0, []
    for t in tables:
        cols = src.execute(f"PRAGMA table_info([{t}])").fetchall()
        pk_cols = [c[1] for c in cols if c[5]]
        fks = src.execute(f"PRAGMA foreign_key_list([{t}])").fetchall()
        idxs = src.execute(f"PRAGMA index_list([{t}])").fetchall()
        ddl, mapping = build_table(t, [tuple(c) for c in cols], pk_cols)
        ddl_all.append(ddl + ";")
        mapping_all.extend(mapping)
        objmatrix.append({
            "table": t, "columns": len(cols),
            "pk": ",".join(pk_cols) or "-",
            "pk_kind": "복합" if len(pk_cols) > 1 else ("단일" if pk_cols else "없음"),
            "fk_count": len(fks),
            "index_count": len(idxs),
            "unique_index": sum(1 for i in idxs if i[2]),
            "fk_moved": "미이전(2차)", "index_moved": "미이전(2차)",
        })
        try:
            cur.execute(ddl)
            con.commit()
            made += 1
        except Exception as e:
            con.rollback()
            failed_schema.append((t, str(e)[:120]))
    t_schema = time.time() - t0
    log(f"스키마 생성 {made}/{len(tables)} · 실패 {len(failed_schema)} · {t_schema:.2f}s")

    # ── 2) 데이터
    t0 = time.time()
    moved, rows_total, failed_data, cleaned = 0, 0, [], []
    for t in tables:
        if any(f[0] == t for f in failed_schema):
            continue
        info = src.execute(f"PRAGMA table_info([{t}])").fetchall()
        cols = [c[1] for c in info]
        numeric_cols = {c[1] for c in info if (c[2] or "").upper().split("(")[0] in ("INTEGER", "REAL")}
        qty_cols = {c for c in numeric_cols if RE_QTY.search(c) and not RE_DECIMAL_OK.search(c)}
        rows = src.execute(f"SELECT * FROM [{t}]").fetchall()
        if not rows:
            moved += 1
            continue

        def fix(col, v):
            if col in numeric_cols and isinstance(v, str):
                s = v.strip()
                if s == "":
                    cleaned.append((t, col, "빈칸→NULL", ""))
                    return None
                try:
                    return Decimal(s)
                except Exception:
                    cleaned.append((t, col, "숫자아님→NULL", s[:30]))
                    return None
            if col in qty_cols and v is not None:
                d = dec(v)
                if d is not None and d != d.to_integral_value():
                    cleaned.append((t, col, "수량 소수 발견(z1048 위반)", str(v)))
                return None if d is None else int(d.to_integral_value())
            if col in numeric_cols and isinstance(v, float):
                return dec(v)          # 금액·실수는 Decimal 로 전달(부동소수점 오차 차단)
            return v

        data = [tuple(fix(c, r[c]) for c in cols) for r in rows]
        collist = ", ".join(f'"{c}"' for c in cols)
        tmpl = "(" + ", ".join(["%s"] * len(cols)) + ")"
        try:
            psycopg2.extras.execute_values(
                cur, f'INSERT INTO "{t}" ({collist}) VALUES %s', data, template=tmpl, page_size=500)
            con.commit()
            moved += 1
            rows_total += len(data)
        except Exception as e:
            con.rollback()
            failed_data.append((t, len(data), str(e)[:140]))
    t_data = time.time() - t0
    log(f"데이터 이관 {moved}/{len(tables)} · {rows_total:,}행 · 실패 {len(failed_data)} · {t_data:.2f}s")

    # ── P0-03: 값이 조용히 바뀌면 안 된다. 정제 대상이 있으면 **기본은 중단**한다.
    if cleaned:
        log(f"⚠ 원본과 다르게 담은 값 {len(cleaned)}건 — cleaned.csv 참조")
        if not a.allow_clean:
            with open(os.path.join(RESULTS, "cleaned.csv"), "w", newline="", encoding="utf-8-sig") as f:
                wr = csv.writer(f)
                wr.writerow(["표", "컬럼", "처리", "원본값"])
                wr.writerows(cleaned)
            log("⛔ 중단: 원본 보존 원칙에 따라 값 변경이 있으면 진행하지 않습니다.")
            log("   업무 담당자 확인·승인 후 --allow-clean 으로 다시 실행하세요.")
            con.close()
            return 2

    # ── P0-01: 기존 ID 를 그대로 넣었으므로 자동번호(sequence)를 최대값 다음으로 맞춘다.
    #    이 처리가 없으면 **이관 직후 첫 등록이 PK 충돌로 실패**한다(실증: parts id=1 중복).
    t0 = time.time()
    seq_rows, seq_fixed, seq_fail = [], 0, []
    for t in tables:
        if any(f[0] == t for f in failed_schema) or any(f[0] == t for f in failed_data):
            continue
        cur.execute("""SELECT c.column_name FROM information_schema.columns c
                       WHERE c.table_schema='public' AND c.table_name=%s
                         AND c.is_identity='YES'""", (t,))
        for (col,) in cur.fetchall():
            cur.execute("SELECT pg_get_serial_sequence(%s,%s)", (t, col))
            seq = cur.fetchone()[0]
            if not seq:
                continue
            cur.execute(f'SELECT COALESCE(MAX("{col}"),0) FROM "{t}"')
            mx = cur.fetchone()[0]
            # 빈 표면 1부터, 값이 있으면 MAX+1 부터 나오게 한다
            cur.execute("SELECT setval(%s, %s, %s)", (seq, mx if mx > 0 else 1, bool(mx > 0)))
            con.commit()
            # 시험 등록 → 생성된 번호 확인 → 되돌리기
            test_ok, test_id, test_err = False, None, ""
            try:
                cur.execute(f'INSERT INTO "{t}" DEFAULT VALUES RETURNING "{col}"')
                test_id = cur.fetchone()[0]
                test_ok = test_id > mx
                con.rollback()
            except Exception as e:
                con.rollback()
                # NOT NULL 등으로 빈 행 등록이 안 되는 표는 번호만 확인한다
                cur.execute(f"SELECT last_value, is_called FROM {seq}")
                lv, called = cur.fetchone()
                test_id = lv + 1 if called else lv
                test_ok = test_id > mx
                test_err = str(e).split("\n")[0][:60]
            seq_rows.append((t, col, mx, test_id, "정상" if test_ok else "★확인필요", test_err))
            if test_ok:
                seq_fixed += 1
            else:
                seq_fail.append((t, col, mx, test_id))
    t_seq = time.time() - t0
    log(f"자동번호 조정 {seq_fixed}개 · 확인필요 {len(seq_fail)} · {t_seq:.2f}s")

    # ── 3) 검증: 행 수 + 금액/수량 합계(Decimal)
    t0 = time.time()
    rowcounts, sums, mismatch = [], [], 0
    for t in tables:
        if any(f[0] == t for f in failed_schema) or any(f[0] == t for f in failed_data):
            rowcounts.append((t, "-", "-", "이관실패"))
            continue
        a_n = src.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM "{t}"')
        b_n = cur.fetchone()[0]
        ok = a_n == b_n
        if not ok:
            mismatch += 1
        rowcounts.append((t, a_n, b_n, "일치" if ok else "불일치"))

        for c in src.execute(f"PRAGMA table_info([{t}])").fetchall():
            col, decl = c[1], (c[2] or "").upper().split("(")[0]
            if decl not in ("INTEGER", "REAL"):
                continue
            if not (RE_MONEY.search(col) or RE_QTY.search(col)):
                continue
            vals = src.execute(
                f"SELECT [{col}] FROM [{t}] WHERE [{col}] IS NOT NULL AND typeof([{col}]) IN ('integer','real')"
            ).fetchall()
            if not vals:
                continue
            a_sum = sum(dec(v[0]) for v in vals)
            cur.execute(f'SELECT COALESCE(SUM("{col}"),0) FROM "{t}"')
            b_raw = cur.fetchone()[0]
            b_sum = Decimal(str(b_raw))
            diff = b_sum - a_sum
            kind = "수량" if RE_QTY.search(col) else "금액"
            # SQLite REAL = double precision. 절대값이 2^53 을 넘으면 **원본 저장값 자체가 근사값**이라
            # 어떤 방식으로 옮겨도 마지막 자리가 맞지 않는다(이관 결함이 아니라 원본의 한계).
            over = sum(1 for (v,) in vals if v is not None and abs(float(v)) > 9007199254740992.0)
            if diff == 0:
                verdict = "일치"
            elif over:
                verdict = f"원본정밀도한계({over}건 · 2^53 초과)"
            else:
                verdict = "★불일치"
            sums.append((t, col, kind, str(a_sum), str(b_sum), str(diff), verdict))
    t_verify = time.time() - t0
    bad_sums = [s for s in sums if s[6] != "일치"]
    log(f"검증 {t_verify:.2f}s · 행수 불일치 {mismatch} · 합계 대조 {len(sums)}종 · 불일치 {len(bad_sums)}")

    # ── 4) Rollback (데이터베이스 삭제)
    t_rollback = 0.0
    if not a.keep:
        con.close()
        t0 = time.time()
        admin = psycopg2.connect(host=a.pg_host, port=a.pg_port, user=a.pg_user, dbname="postgres")
        admin.autocommit = True
        admin.cursor().execute(f"DROP DATABASE {a.dbname} WITH (FORCE)")
        admin.close()
        t_rollback = time.time() - t0
        log(f"Rollback(시험DB 삭제) {t_rollback:.2f}s")

    # ── 산출물 저장
    def w(name, header, rows_):
        with open(os.path.join(RESULTS, name), "w", newline="", encoding="utf-8-sig") as f:
            wr = csv.writer(f)
            wr.writerow(header)
            wr.writerows(rows_)

    with open(os.path.join(RESULTS, "ddl.sql"), "w", encoding="utf-8") as f:
        f.write("-- WP-02 리허설 DDL (자동 생성) · KNK 표기 규정 반영\n")
        f.write("\n\n".join(ddl_all))
    w("type_mapping.csv", ["표", "컬럼", "SQLite선언", "PostgreSQL", "분류", "근거규정"], mapping_all)
    w("object_matrix.csv",
      ["표", "컬럼수", "기본키", "기본키종류", "FK수", "인덱스수", "UNIQUE인덱스", "FK이전", "인덱스이전"],
      [[o["table"], o["columns"], o["pk"], o["pk_kind"], o["fk_count"], o["index_count"],
        o["unique_index"], o["fk_moved"], o["index_moved"]] for o in objmatrix])
    w("rowcount.csv", ["표", "SQLite", "PostgreSQL", "판정"], rowcounts)
    w("sums.csv", ["표", "컬럼", "분류", "SQLite합계", "PG합계", "차이", "판정"], sums)
    w("cleaned.csv", ["표", "컬럼", "처리", "원본값"], cleaned)
    w("identity_sequence.csv", ["표", "컬럼", "현재MAX", "다음발급번호", "판정", "비고"], seq_rows)

    summary = [
        ("원본", a.src), ("원본SHA256", sha256_file(a.src)), ("PostgreSQL", pgver.split(",")[0]),
        ("표", len(tables)), ("테이블·PK생성", made), ("테이블생성실패", len(failed_schema)),
        ("데이터성공", moved), ("데이터실패", len(failed_data)), ("이관행수", rows_total),
        ("행수불일치", mismatch), ("합계대조", len(sums)), ("합계불일치", len(bad_sums)),
        ("정제건수", len(cleaned)),
        ("자동번호조정", seq_fixed), ("자동번호확인필요", len(seq_fail)),
        ("미이전객체", "FK·인덱스·뷰·트리거·UNIQUE/CHECK/NOT NULL/DEFAULT (2차 범위)"),
        ("DB생성초", f"{t_create:.2f}"), ("스키마초", f"{t_schema:.2f}"), ("데이터초", f"{t_data:.2f}"),
        ("자동번호초", f"{t_seq:.2f}"),
        ("검증초", f"{t_verify:.2f}"), ("Rollback초", f"{t_rollback:.2f}"),
        ("전체초", f"{time.time() - t_all:.2f}"),
    ]
    w("summary.csv", ["항목", "값"], summary)
    with open(os.path.join(RESULTS, "run.log"), "a", encoding="utf-8") as f:
        f.write("\n".join(LOG_LINES) + "\n" + "-" * 60 + "\n")

    print("\n" + "=" * 64)
    for k, v in summary:
        print(f"  {k:14s} {v}")
    print("=" * 64)
    if failed_schema:
        print(" 스키마 실패:", failed_schema[:5])
    if failed_data:
        print(" 데이터 실패:", failed_data[:5])
    if bad_sums:
        print(" 합계 불일치:")
        for s in bad_sums[:10]:
            print(f"   {s[0]}.{s[1]} ({s[2]}) SQLite={s[3]} PG={s[4]} 차이={s[5]}")
    return 0 if not (failed_schema or failed_data or mismatch or bad_sums) else 1


if __name__ == "__main__":
    sys.exit(main())
