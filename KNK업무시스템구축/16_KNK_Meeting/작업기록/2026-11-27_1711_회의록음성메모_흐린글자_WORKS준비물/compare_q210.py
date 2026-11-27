# -*- coding: utf-8 -*-
"""z1210 전후 비교 — result_<before>_*.json 과 result_<after>_*.json 을 합쳐 기준 미달·더 나빠진 글자를 센다.
사용: py -3.12 compare_q210.py <전 이름> [후 이름]   (예: before after)
· 원인 나눔: 공용 틀(세션 01 · 본문 main 밖 상단바·왼쪽 메뉴) / 꺼진 단추 / 큰 글자 / 이 화면
· 결과: compare_<전>_<후>.json + 화면에 표
"""
import glob
import io
import json
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    items, errs, pages = [], [], 0
    for p in sorted(glob.glob(os.path.join(HERE, "result_%s_*.json" % name))):
        d = json.load(io.open(p, encoding="utf-8"))
        items += d["items"]; errs += d["errors"]; pages += d["pages"]
    return items, errs, pages


def cls(i):
    if not i.get("inmain"):
        return "공용 틀(세션01)"
    if i.get("dis"):
        return "꺼진 단추"
    return "이 화면"


def key(i):
    return (i["scene"], i["theme"], i["w"], i["p"], i["t"], i["kind"])


def summary(items, title):
    bad = [i for i in items if i["cr"] < i["need"]]
    print("── %s: 글자 %d · 기준 미달 %d" % (title, len(items), len(bad)))
    c = Counter((cls(i), i["theme"]) for i in bad)
    for k, v in sorted(c.items()):
        print("   %s · %s: %d" % (k[0], k[1], v))
    g = defaultdict(list)
    for i in bad:
        g[(cls(i), i["p"].split(">")[-1], i["c"], i["t"][:18])].append(i)
    rows = sorted(g.items(), key=lambda kv: -len(kv[1]))
    for (c0, sel, col, txt), L in rows:
        crs = sorted(x["cr"] for x in L)
        th = sorted({x["theme"] for x in L})
        sc = sorted({x["scene"] for x in L})
        print("   [%s] %s · %s · 「%s」 × %d · %.2f~%.2f · %s · 바탕 %s · %s" % (c0, sel, col, txt, len(L), crs[0], crs[-1], "/".join(th),
                                                                       L[0]["bg"], ",".join(sc[:4]) + ("…" if len(sc) > 4 else "")))
    return bad


bn = sys.argv[1]
an = sys.argv[2] if len(sys.argv) > 2 else None
B, be, bp = load(bn)
print("전: 화면 %d · 화면 오류 %d" % (bp, len(be)))
bb = summary(B, "전 " + bn)
out = {"before": {"pages": bp, "items": len(B), "bad": len(bb), "errors": be}}
if an:
    A, ae, ap = load(an)
    print("후: 화면 %d · 화면 오류 %d" % (ap, len(ae)))
    ab = summary(A, "후 " + an)
    bm = {key(i): i for i in B}
    am = {key(i): i for i in A}
    common = set(bm) & set(am)
    worse = [(bm[k], am[k]) for k in common if am[k]["cr"] < bm[k]["cr"] - 0.05 and am[k]["cr"] < 7]
    print("── 같은 글자 %d 비교 · 더 나빠진 글자(0.05 넘게 낮아짐) %d" % (len(common), len(worse)))
    for b, a in sorted(worse, key=lambda x: x[1]["cr"])[:40]:
        print("   ▼", a["scene"], a["theme"], a["w"], a["p"].split(">")[-1], "「%s」" % a["t"][:20], b["cr"], "→", a["cr"])
    fixed = [(bm[k], am[k]) for k in common if bm[k]["cr"] < bm[k]["need"] <= am[k]["cr"]]
    print("── 기준 미달 → 통과로 바뀐 글자 %d" % len(fixed))
    only_b = len(set(bm) - set(am)); only_a = len(set(am) - set(bm))
    print("── 한쪽에만 있는 글자: 전만 %d · 후만 %d" % (only_b, only_a))
    newbad = [am[k] for k in set(am) - set(bm) if am[k]["cr"] < am[k]["need"]]
    print("── 후에만 있는 글자 중 기준 미달 %d" % len(newbad))
    for a in newbad[:20]:
        print("   ＋", a["scene"], a["theme"], a["w"], a["p"].split(">")[-1], "「%s」" % a["t"][:20], a["cr"])
    out["after"] = {"pages": ap, "items": len(A), "bad": len(ab), "errors": ae}
    out["compare"] = {"common": len(common), "worse": len(worse), "fixed": len(fixed), "only_before": only_b, "only_after": only_a,
                      "new_bad_only_after": len(newbad),
                      "by_class_before": dict(Counter(cls(i) for i in bb)), "by_class_after": dict(Counter(cls(i) for i in ab)),
                      "by_theme_before": dict(Counter(i["theme"] for i in bb)), "by_theme_after": dict(Counter(i["theme"] for i in ab)),
                      "worse_list": [{"scene": a["scene"], "theme": a["theme"], "w": a["w"], "p": a["p"], "t": a["t"], "before": b["cr"], "after": a["cr"]} for b, a in worse]}
    io.open(os.path.join(HERE, "compare_%s_%s.json" % (bn, an)), "w", encoding="utf-8", newline="").write(json.dumps(out, ensure_ascii=False, indent=1))
