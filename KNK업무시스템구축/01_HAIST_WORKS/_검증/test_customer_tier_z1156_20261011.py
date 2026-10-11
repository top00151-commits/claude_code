# -*- coding: utf-8 -*-
"""z1156 시험 — 앱이 켜질 때 고객 등급 '신규'를 '일반'으로 덮던 v5H181 정리 코드를 뺐다 (대표 2026-10-11 「신규 유지」).

v5H58(대표 지시 2026-05-03): 고객 등급 = 점수로 VIP·주요·일반·신규·휴면 5단계 자동 산정.
v5H181(05-07)이 '신규'를 비표준으로 잘못 보고 startup() 에서 `UPDATE customers SET tier='일반' WHERE tier='신규'`
→ 점수 1~24점 고객(운영 11곳)이 켤 때 '일반' ↔ 24시간 재계산에 '신규' 를 되풀이(운영 기록 1,265번).

실행: python _검증/test_customer_tier_z1156_20261011.py   (기본 python 3.12)
§1 자동 산정 등급표(진짜 함수)   §2 startup() 에 등급 일괄 수정이 없다   §3 배포 전 검사기 + 되돌림
"""
import io
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "deploy"))
from app import customer_tier as CT   # noqa: E402
import check_standards as CS          # noqa: E402

OK = FAIL = 0


def check(cond, what):
    global OK, FAIL
    if cond:
        OK += 1
        print("  ✅", what)
    else:
        FAIL += 1
        print("  ❌", what)


print("\n§1 자동 산정 등급표 — customer_tier.score_to_tier (대표 지시 v5H58)")
for sc, days, want in [(100, 1, "VIP"), (70, 1, "VIP"), (69, 1, "주요"), (50, 1, "주요"), (49, 1, "일반"),
                       (25, 1, "일반"), (24, 1, "신규"), (18, 1, "신규"), (1, 1, "신규"),
                       (0, 30, "신규"), (0, 400, "휴면"), (0, None, "휴면")]:
    check(CT.score_to_tier(sc, days) == want, "점수 %s · 비활성 %s일 → %s" % (sc, days, want))
got = {CT.score_to_tier(s, d) for s in range(101) for d in (None, 0, 30, 400)}
check(got == {"VIP", "주요", "일반", "신규", "휴면"}, "나오는 등급 = VIP·주요·일반·신규·휴면 5개 (「신규」는 정식 등급)")

print("\n§2 앱 시작 함수 startup() — 고객 등급을 일괄로 고치지 않는다")
msrc = io.open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
ln0, body = CS._py_top_func(msrc, "startup")
check(body is not None and len(body.splitlines()) > 100, "startup() 원문을 뽑았다(%s줄)" % (len(body.splitlines()) if body else 0))
code = "\n".join(l for l in (body or "").splitlines() if not l.strip().startswith("#"))
check("UPDATE customers SET tier" not in code, "startup() 에 `UPDATE customers SET tier` 가 없다")
check("[TIER-FIX]" not in code, "옛 「[TIER-FIX] … 정리 11건」 기록 줄이 없다")
check("refresh_all_customer_tiers" in code, "기동 직후 자동 재계산(refresh_all_customer_tiers)은 그대로 있다")
check("z1156" in body, "뺀 자리에 왜 뺐는지 설명이 있다(z1156)")

print("\n§3 배포 전 검사기 — check_customer_tier")
check(CS.check_customer_tier([]) == [], "지금 코드: 위반 0")
OLD_BLOCK = ('''    # v5H181 (2026-05-06): customers.tier='신규' 비표준 → '일반' 으로 정리
    try:
        with db_session() as c:
            _r = c.execute("UPDATE customers SET tier='일반' WHERE tier='신규'")
            if _r.rowcount:
                print(f"[TIER-FIX] customers.tier='신규' → '일반' 정리 {_r.rowcount}건")
    except Exception as _e:
        print(f"[TIER-FIX ERR] {_e}")
''')
ANCHOR = "    # z1156 (대표 2026-10-11 「신규 유지」): 여기 있던 v5H181 기동 정리"
REL = ["app/main.py", "app/customer_tier.py"]
_root = CS.ROOT
tmp = tempfile.mkdtemp(prefix="z1156chk_")


def fresh():
    shutil.rmtree(tmp, ignore_errors=True)
    for r in REL:
        os.makedirs(os.path.dirname(os.path.join(tmp, r)), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, r), os.path.join(tmp, r))


def edit(rel, old, new):
    p = os.path.join(tmp, rel)
    s = io.open(p, encoding="utf-8", newline="").read().replace("\r\n", "\n")
    assert s.count(old) == 1, (rel, s.count(old))
    io.open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new))


def run():
    CS.ROOT = tmp
    return CS.check_customer_tier([])


try:
    fresh()
    edit("app/main.py", ANCHOR, OLD_BLOCK + ANCHOR)
    hits = run()
    marks = {m.lstrip()[0] for _, _, m in hits}
    check({"①", "②"} <= marks, "되돌림 「v5H181 기동 정리를 다시 넣음」 → ①(일괄 덮어쓰기)·②(기동 때 수정) 로 잡힘 (%d건)" % len(hits))
    fresh()
    io.open(os.path.join(tmp, "app", "new_module.py"), "w", encoding="utf-8").write(
        'def f(c):\n    c.execute("UPDATE customers SET tier=? WHERE tier IN (\'신규\',\'휴면\')", ("일반",))\n')
    hits = run()
    check(any(m.lstrip().startswith("①") and "new_module" in p for p, _, m in hits),
          "다른 파일에서 등급을 일괄로 바꿔 써도 ① 로 잡힘")
    fresh()
    io.open(os.path.join(tmp, "app", "new_module.py"), "w", encoding="utf-8").write(
        "# 예전엔 UPDATE customers SET tier='일반' WHERE tier='신규' 를 켤 때 돌렸다\n"
        'def g(c, d):\n    c.execute("UPDATE customers SET name=?, tier=?, note=? WHERE id=?", d)\n')
    check(run() == [], "주석의 옛 SQL · 한 곳(id)만 고치는 UPDATE 는 위반 아님")
    fresh()
    edit("app/customer_tier.py", '    if score >= 25: return "일반"\n    return "신규"',
         '    return "일반"')
    hits = run()
    check(any(m.lstrip().startswith("③") for _, _, m in hits), "되돌림 「자동 산정에서 신규를 없앰」 → ③ 으로 잡힘(대표 결정 없이 등급 체계가 바뀌면)")
finally:
    CS.ROOT = _root
    shutil.rmtree(tmp, ignore_errors=True)

print("\n" + "=" * 60)
print("결과: 통과 %d · 실패 %d" % (OK, FAIL))
sys.exit(1 if FAIL else 0)
