"""KNK 브랜드 정의 검사 — brand.json · knk-brand.css · assets 가 서로 맞는지 본다.

쓰는 법:  python check_brand.py
끝나면 첫 줄에 ✅(모두 맞음) 또는 ❌(틀린 곳 목록)를 찍는다.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    try:  # 윈도우 콘솔(cp949)에서도 한글·✅ 가 깨지지 않게
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    errs = []
    with open(os.path.join(HERE, "brand.json"), encoding="utf-8") as f:
        b = json.load(f)
    with open(os.path.join(HERE, "knk-brand.css"), encoding="utf-8") as f:
        css = f.read()

    # 1) 색: brand.json 과 knk-brand.css 가 같은가
    pairs = {"--knk-brand-red": b["colors"]["red"]["screen"],
             "--knk-brand-gray": b["colors"]["gray"]["screen"],
             "--knk-brand-black": b["colors"]["black"]["screen"],
             "--knk-brand-ink": b["colors"]["ink"]["screen"]}
    for name, val in pairs.items():
        m = re.search(re.escape(name) + r":\s*(#[0-9A-Fa-f]{6})", css)
        if not m or m.group(1).upper() != val.upper():
            errs.append(f"색 다름: {name} css={m.group(1) if m else '없음'} json={val}")

    # 2) 로고 파일: 시그니처마다 SVG 5색판 + PNG 2색판
    variants = list(b["variants"].keys())
    for s in b["signatures"]:
        for v in variants:
            p = os.path.join(HERE, "assets", "logo", "svg", f"{s['id']}_{v}.svg")
            if not os.path.exists(p):
                errs.append(f"SVG 없음: {s['id']}_{v}.svg")
            else:
                with open(p, encoding="utf-8") as f:
                    fills = {x.upper() for x in re.findall(r'fill="(#[0-9a-fA-F]{6})"', f.read())}
                want = {b["variants"][v]["symbol"].upper(), b["variants"][v]["text"].upper()}
                if not fills <= want:
                    errs.append(f"색판 색 다름: {s['id']}_{v}.svg {sorted(fills - want)}")
        for v in ("full", "white"):
            if not os.path.exists(os.path.join(HERE, "assets", "logo", "png", f"{s['id']}_{v}.png")):
                errs.append(f"PNG 없음: {s['id']}_{v}.png")

    # 3) 바탕 규칙과 색판 규칙이 서로 맞는가
    for bg, allowed in b["backgrounds"].items():
        if not isinstance(allowed, list):
            continue
        for v in allowed:
            if bg not in b["variants"][v]["on"]:
                errs.append(f"바탕 규칙 어긋남: {bg} 바탕에 {v} 허용인데 variants.{v}.on 에 {bg} 없음")

    # 4) 패턴 파일
    for c in ("red", "white", "gray"):
        if not os.path.exists(os.path.join(HERE, "assets", "pattern", f"knk-pattern-tile_{c}.png")):
            errs.append(f"패턴 없음: knk-pattern-tile_{c}.png")

    # 5) 역사: 날짜 순서
    dates = [h["date"] for h in b["history"]]
    if dates != sorted(dates):
        errs.append("역사 날짜 순서가 어긋남")

    if errs:
        print(f"❌ 틀린 곳 {len(errs)}개")
        for e in errs:
            print("  -", e)
        return 1
    n = len(b["signatures"])
    print(f"✅ 모두 맞음 — 로고 {n}가지 × SVG {len(variants)}색판 · PNG 2색판 · 패턴 3색 · 색 4개 · 역사 {len(dates)}줄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
