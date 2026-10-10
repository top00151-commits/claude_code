# -*- coding: utf-8 -*-
"""번역할 글을 줄번호와 함께 뽑는다. 이음 용어집에 **똑같은 글**이 있으면 그 베트남어를 붙여 준다."""
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
B = "KNK업무시스템구축/01_HAIST_WORKS/app/templates/"
F = sys.argv[1] if len(sys.argv) > 1 else "meetings.html"
GL = json.load(io.open(os.path.join(HERE, "glossary_vi.json"), encoding="utf-8"))
HAN = re.compile(r"[가-힣]")
CHUNK = re.compile(r"[^\n<>'\"]*[가-힣][^\n<>'\"]*")

env = dict(os.environ)
env["MSYS_NO_PATHCONV"] = "1"
r = subprocess.run(["git", "-c", "core.quotepath=false", "cat-file", "blob",
                    "origin/main:" + B + F], capture_output=True, env=env)
t = r.stdout.decode("utf-8", "replace")
io.open(os.path.join(HERE, F), "w", encoding="utf-8", newline="").write(t)

inblock = False
seen = {}
for n, ln in enumerate(t.splitlines(), 1):
    s = ln.strip()
    if inblock:
        if "*/" in s:
            inblock = False
        continue
    if s.startswith("{#") or s.startswith("<!--") or s.startswith("//"):
        continue
    if s.startswith("/*"):
        if "*/" not in s:
            inblock = True
        continue
    for c in CHUNK.findall(ln):
        c = c.strip()
        if len(c) >= 2 and HAN.search(c):
            seen.setdefault(c, []).append(n)

hit = 0
print("# %s — 서로 다른 글 %d개" % (F, len(seen)))
print("# 표시: [줄] 한국어   ||  이음에 같은 글이 있으면 → 베트남어")
for c, lines in sorted(seen.items(), key=lambda x: x[1][0]):
    vi = GL.get(c)
    if vi:
        hit += 1
    print("[%s] %s%s" % (",".join(map(str, lines[:3])), c, ("   ||→ " + vi) if vi else ""))
print("\n# 이음에 그대로 있던 것: %d개 / %d" % (hit, len(seen)))
