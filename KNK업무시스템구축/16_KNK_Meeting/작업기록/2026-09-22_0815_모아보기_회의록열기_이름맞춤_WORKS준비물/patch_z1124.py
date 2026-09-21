# -*- coding: utf-8 -*-
"""z1124 — 「🗓 회의 카드 모아보기」 단추 이름 「📝 회의록 화면」 → 「📋 회의록 열기」 (대표 지시 2026-09-22 08시 「회의록 열기로 맞춰」)
  이음 회의 카드(v807 · 진행 중·정리 중·실패)와 같은 이름. 가는 곳·여는 방식은 그대로(이름만).
사용: py patch_z1124.py <앱 사본 폴더(app/ 가 들어 있는 곳)>
기준: 운영 z1123(meetings.html fdfe9416 = z1122 그대로)"""
import hashlib
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = sys.argv[1]
REL = "app/templates/meetings.html"
p = os.path.join(ROOT, REL)
raw = open(p, "rb").read()
h = hashlib.sha256(raw).hexdigest()[:8]
assert h == "fdfe9416", f"{REL} 기준이 다름: {h}"
s = raw.decode("utf-8")
assert "\r\n" not in s


def rep(s, old, new, name):
    n = s.count(old)
    assert n == 1, f"{name}: 기준 글 {n}곳(기대 1)"
    return s.replace(old, new)


s = rep(s,
        "        } else {\n"
        "          out += '<a class=\"mc-btn\" href=\"' + esc(mn.url) + '\">📝 회의록 화면</a>';\n"
        "        }\n",
        "        } else {\n"
        "          // z1124 (대표 지시 2026-09-22 「회의록 열기로 맞춰」): 이음 회의 카드(v807 · 진행 중·정리 중·실패)와 같은 이름 — 가는 곳은 그대로\n"
        "          out += '<a class=\"mc-btn\" href=\"' + esc(mn.url) + '\">📋 회의록 열기</a>';\n"
        "        }\n",
        "단추 이름")
s = rep(s,
        "    // z1122: 카드 빈 곳 = 그 카드의 회의록 단추(이어서 녹음·회의록 화면·회의록 보기)와 같게 — 이음 v817 과 같은 규칙.\n",
        "    // z1122: 카드 빈 곳 = 그 카드의 회의록 단추(이어서 녹음·회의록 열기·회의록 보기)와 같게 — 이음 v817 과 같은 규칙.\n",
        "주석")
assert "📝 회의록 화면" not in s and s.count("📋 회의록 열기") == 1
tmp = p + ".tmp_z1124"
with io.open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(s)
os.replace(tmp, p)
print("  [OK]", REL, "→", hashlib.sha256(s.encode("utf-8")).hexdigest()[:8])
