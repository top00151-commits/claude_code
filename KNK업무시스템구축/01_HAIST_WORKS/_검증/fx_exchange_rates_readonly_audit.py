# -*- coding: utf-8 -*-
"""exchange_rates 운영 **읽기 전용** 조회 — 대표 승인 2026-07-30 20:28 §3

⛔ 절대 준수 (지시 §3 금지사항):
   · SELECT 만. INSERT/UPDATE/DELETE 없음.
   · exchange_rates **한 표만**. 다른 업무 표와 JOIN 없음.
   · 고객·거래·사용자 개인정보 조회 없음 (created_by 조차 읽지 않는다).
   · 서비스 재시작·DB 파일 변경 없음 — mode=ro 로만 연다.
   · 이상 행 자동 삭제·보정 없음.

조회 범위 (지시 §3 그대로):
   ① 통화·연월별 전체 행 수
   ② 월 1일 행 수
   ③ 월 1일이 아닌 행 수
   ④ 이상 행의 통화·날짜·출처·환율
   ⑤ (추가) 지금 적용되는 값 vs 월 1일 행 값 — 금액 영향 확인
   ⑥ (추가) 출처(source)별 건수 — 어느 입력 경로가 실제로 쓰였나

쓰는 법
-------
운영(NAS)에서 **읽기 전용**으로 1회:
    ssh -p 32201 root@o.knknara.co.kr \
      "PYTHONIOENCODING=utf-8 /opt/knk_haist/.venv/bin/python -" < 이_파일
  (표준 입력으로 흘려 실행 — 운영에 파일을 남기지 않는다)

사본·로컬 DB 로:
    python _검증/fx_exchange_rates_readonly_audit.py <db경로>

2026-07-30 20:31 실행 결과: 39행 전부 '월기준'·전부 월 1일 · 중복 0 · 금액영향 0.
  → `2026-07-30_2033_세션05_운영조회결과_환율_exchange_rates_읽기전용_실측.md`
⛔ 운영 실행은 **대표 승인이 있을 때만**. 읽기 전용이라도 임의 반복 실행하지 않는다.
"""
import sqlite3
import sys

DB = sys.argv[1] if len(sys.argv) > 1 else "/opt/knk_haist/data/knk.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
q = con.execute


def line(c="─", n=78):
    print(c * n)


print("=" * 78)
print(" exchange_rates 읽기 전용 조회 — 대표 승인 §3 (2026-07-30)")
print("=" * 78)

# ── 0. 총량 + 날짜 형식 온전성 ────────────────────────────────────────────
tot = q("SELECT COUNT(*) n FROM exchange_rates").fetchone()["n"]
krw = q("SELECT COUNT(*) n FROM exchange_rates WHERE COALESCE(to_currency,'KRW')='KRW'").fetchone()["n"]
badfmt = q(
    "SELECT COUNT(*) n FROM exchange_rates "
    "WHERE rate_date IS NULL OR LENGTH(rate_date)<>10 OR substr(rate_date,5,1)<>'-' "
    "   OR substr(rate_date,8,1)<>'-'"
).fetchone()["n"]
print(f"\n[0] 전체 {tot}행 · to_currency=KRW {krw}행 · 날짜형식 이상 {badfmt}행")
if badfmt:
    print("    ⚠ 날짜 형식이 YYYY-MM-DD 가 아닌 행이 있습니다 — '1일 판정' 자체가 흔들립니다.")
    for r in q(
        "SELECT from_currency, rate_date, source, rate FROM exchange_rates "
        "WHERE rate_date IS NULL OR LENGTH(rate_date)<>10 OR substr(rate_date,5,1)<>'-' "
        "   OR substr(rate_date,8,1)<>'-' LIMIT 20"
    ):
        print(f"      · {r['from_currency']:>4} | {r['rate_date']} | {r['source']} | {r['rate']}")

# ── 1~3. 통화·연월별 전체 / 1일 / 1일 아님 ────────────────────────────────
print("\n[1~3] 통화·연월별 행 수 (to_currency=KRW · rate>0)")
line()
print(f"  {'통화':>5} {'연월':>9} {'전체':>5} {'1일':>4} {'1일아님':>7}   비고")
line()
rows = q(
    "SELECT UPPER(from_currency) ccy, substr(rate_date,1,7) ym, COUNT(*) total,"
    " SUM(CASE WHEN substr(rate_date,9,2)='01' THEN 1 ELSE 0 END) d1,"
    " SUM(CASE WHEN substr(rate_date,9,2)<>'01' THEN 1 ELSE 0 END) dx"
    " FROM exchange_rates"
    " WHERE COALESCE(to_currency,'KRW')='KRW' AND rate>0"
    "   AND UPPER(COALESCE(from_currency,''))<>'' AND UPPER(from_currency)<>'KRW'"
    " GROUP BY ccy, ym ORDER BY ccy, ym"
).fetchall()

n_conflict = 0        # 같은 (통화,월)에 1일 행과 1일아님 행이 함께 = 실제 충돌
n_dx_only = 0         # 1일 행이 없고 1일아님만 = 월 기준환율로 쓸 수 없는 월
for r in rows:
    tag = ""
    if r["d1"] and r["dx"]:
        tag = "🔴 실제 중복 (1일 행과 다른 날짜 행이 함께)"
        n_conflict += 1
    elif not r["d1"] and r["dx"]:
        tag = "⚠ 1일 행 없음 (지시 §1: 월 기준환율로 쓰지 않음)"
        n_dx_only += 1
    print(f"  {r['ccy']:>5} {r['ym']:>9} {r['total']:>5} {r['d1']:>4} {r['dx']:>7}   {tag}")
line()
print(f"  (통화,월) 칸 {len(rows)}개 · 🔴실제 중복 {n_conflict}개 · ⚠1일없음 {n_dx_only}개")

# ── 4. 이상 행 상세 — 통화·날짜·출처·환율 ────────────────────────────────
print("\n[4] 이상 행 상세 — 월 1일이 **아닌** 행 (통화·날짜·출처·환율)")
line()
bad = q(
    "SELECT UPPER(from_currency) ccy, rate_date, COALESCE(source,'') src, rate"
    " FROM exchange_rates"
    " WHERE COALESCE(to_currency,'KRW')='KRW' AND rate>0"
    "   AND UPPER(COALESCE(from_currency,''))<>'' AND UPPER(from_currency)<>'KRW'"
    "   AND substr(rate_date,9,2)<>'01'"
    " ORDER BY ccy, rate_date"
).fetchall()
if not bad:
    print("  없음 — 1일이 아닌 행이 하나도 없습니다.")
else:
    for r in bad:
        print(f"  {r['ccy']:>5} | {r['rate_date']} | {r['src'][:18]:<18} | {r['rate']}")
print(f"  합계 {len(bad)}행")

# ── 5. 금액 영향 — 지금 코드가 고르는 값 vs 1일 행 값 ──────────────────────
#    _fx_load_rates 는 ORDER BY 없이 훑어 dict 에 덮어쓴다 → 마지막에 읽힌 행이 이긴다.
#    같은 순서로 재현해 '지금 적용되는 값'을 구하고, 1일 행 값과 비교한다.
print("\n[5] 금액 영향 — 지금 적용되는 값 vs 월 1일 행 값")
line()
cur = {}
for r in q(
    "SELECT UPPER(from_currency) ccy, substr(rate_date,1,7) ym, rate, rate_date"
    " FROM exchange_rates"
    " WHERE COALESCE(to_currency,'KRW')='KRW' AND rate>0"
):
    cur[(r["ccy"], r["ym"])] = (r["rate"], r["rate_date"])     # 덮어쓰기 = 앱과 같은 동작
d1v = {}
for r in q(
    "SELECT UPPER(from_currency) ccy, substr(rate_date,1,7) ym, rate"
    " FROM exchange_rates"
    " WHERE COALESCE(to_currency,'KRW')='KRW' AND rate>0 AND substr(rate_date,9,2)='01'"
):
    d1v[(r["ccy"], r["ym"])] = r["rate"]

diff = []
for k, (rv, rd) in sorted(cur.items()):
    if k[0] in ("", "KRW"):
        continue
    base = d1v.get(k)
    if base is None:
        continue
    if abs(float(rv) - float(base)) > 1e-9:
        diff.append((k[0], k[1], base, rv, rd))
if not diff:
    print("  없음 — 지금 적용되는 값이 모두 월 1일 행 값과 같습니다.")
else:
    print(f"  {'통화':>5} {'연월':>9} {'1일 행(정답)':>14} {'지금 적용':>14}  이긴 행 날짜")
    for ccy, ym, base, rv, rd in diff:
        print(f"  {ccy:>5} {ym:>9} {base:>14} {rv:>14}  {rd}")
print(f"  금액이 달라지는 (통화,월) = {len(diff)}개")

# ── 6. 출처(source)별 건수 — 어느 입력 경로가 실제로 쓰이는가 ───────────────
print("\n[6] 출처(source)별 건수 — 실제로 쓰이는 입력 경로")
line()
for r in q(
    "SELECT COALESCE(source,'(빈칸)') src, COUNT(*) n,"
    " SUM(CASE WHEN substr(rate_date,9,2)='01' THEN 1 ELSE 0 END) d1,"
    " SUM(CASE WHEN substr(rate_date,9,2)<>'01' THEN 1 ELSE 0 END) dx"
    " FROM exchange_rates GROUP BY src ORDER BY n DESC"
):
    print(f"  {r['src'][:24]:<24} {r['n']:>6}행  (1일 {r['d1']} · 1일아님 {r['dx']})")

con.close()
print("\n" + "=" * 78)
print(" 조회 끝 — SELECT 만 수행. 쓰기·삭제·보정 없음.")
print("=" * 78)
