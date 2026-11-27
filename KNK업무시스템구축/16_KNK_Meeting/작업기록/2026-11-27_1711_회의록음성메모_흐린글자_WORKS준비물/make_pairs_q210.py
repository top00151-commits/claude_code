# -*- coding: utf-8 -*-
"""z1210 전후 사진 나란히 — shots/before_<테마>/ 와 shots/after_<테마>/ 의 같은 장면을 왼쪽(전)·오른쪽(후)로 붙여 shots/pairs/ 에.
사용: py -3.12 make_pairs_q210.py"""
import os
import sys
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "shots")
OUT = os.path.join(S, "pairs")
os.makedirs(OUT, exist_ok=True)
SCENES = ["한눈에보기", "회의록상세_정리있음", "회의록상세_베트남", "음성메모_이미지카드", "음성메모상세_정리있음", "회의록목록", "음성메모목록"]
n = 0
for sc in SCENES:
    for th in ("clear", "soft", "dark"):
        for w in (1440, 390):
            fn = "%s_%s_%d.png" % (sc, th, w)
            a, b = os.path.join(S, "before_" + th, fn), os.path.join(S, "after_" + th, fn)
            if not (os.path.exists(a) and os.path.exists(b)):
                continue
            ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
            gap = 16
            im = Image.new("RGB", (ia.width + ib.width + gap, max(ia.height, ib.height) + 24), (128, 128, 128))
            im.paste(ia, (0, 24)); im.paste(ib, (ia.width + gap, 24))
            d = ImageDraw.Draw(im)
            d.text((6, 5), "BEFORE (acee2489)  %s  %s  %d" % (sc.encode("ascii", "ignore").decode() or "", th, w), fill=(255, 255, 255))
            d.text((ia.width + gap + 6, 5), "AFTER (z1210)", fill=(255, 255, 255))
            im.save(os.path.join(OUT, "전후_" + fn))
            n += 1
print("나란히 사진", n, "장 →", OUT)
