# -*- coding: utf-8 -*-
"""이음 i18n.js 에서 ko↔vi 짝을 뽑아 용어집을 만든다.
   🔵 두 앱이 같은 말을 쓰게 하려는 것 — 내가 새로 지어내지 않는다.
   🔴 이음 코드는 **읽기만** 한다(세션 10 소유)."""
import io
import json
import os
import re

SRC = r"C:/Users/top00/JR/Claude 코드/KNK업무시스템구축/10_KNK_Messenger/static/js/i18n.js"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glossary_vi.json")
t = io.open(SRC, encoding="utf-8").read()


def block(lang):
    """lang: { ... } 한 덩어리를 중괄호 짝을 세어 잘라낸다."""
    m = re.search(r"(?<![A-Za-z0-9_])" + lang + r"\s*:\s*\{", t)
    if not m:
        return ""
    i = m.end() - 1
    depth, j, instr, q, esc = 0, i, False, "", False
    while j < len(t):
        c = t[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == q:
                instr = False
        else:
            if c in "\"'`":
                instr, q = True, c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return t[i:j + 1]
        j += 1
    return ""


KV = re.compile(r"[\"']([A-Za-z0-9_.]+)[\"']\s*:\s*[\"'](([^\"'\\]|\\.)*)[\"']")


def pairs(b):
    d = {}
    for m in KV.finditer(b):
        k, v = m.group(1), m.group(2)
        try:
            v = v.encode().decode("unicode_escape").encode("latin1").decode("utf-8")
        except Exception:
            v = v.replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"')
        d[k] = v
    return d


ko = pairs(block("ko"))
vi = pairs(block("vi"))
print("이음 키: ko %d · vi %d" % (len(ko), len(vi)))

gl = {}
for k, kv in ko.items():
    vv = vi.get(k)
    if vv and kv.strip() and vv.strip() and kv.strip() != vv.strip():
        gl[kv.strip()] = vv.strip()
print("ko→vi 짝: %d개" % len(gl))

mt = {k: v for k, v in gl.items() if any(
    w in k for w in ("회의", "녹음", "회의록", "참석", "종료", "정리", "메모", "음성"))}
print("회의·녹음 관련 짝: %d개" % len(mt))
io.open(OUT, "w", encoding="utf-8").write(json.dumps(gl, ensure_ascii=False, indent=1))
print("저장:", OUT)
print()
print("── 쓸모 있어 보이는 것 20개 ──")
for k in sorted(mt, key=len, reverse=True)[:20]:
    print("  %-34s → %s" % (k[:34], mt[k][:60]))
