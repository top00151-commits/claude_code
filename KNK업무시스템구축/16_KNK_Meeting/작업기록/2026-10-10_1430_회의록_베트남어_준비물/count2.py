# -*- coding: utf-8 -*-
"""다시 센다 — 따옴표/태그 모양에 기대지 말고 **한글 덩어리**를 센다.
   주석은 뺀다(사람이 안 보는 글). 결과를 과장도 축소도 하지 않는다."""
import os
import re
import subprocess

B = "KNK업무시스템구축/01_HAIST_WORKS/app/templates/"
FILES = ["meeting_form.html", "meetings.html"]
# 한글이 섞인 덩어리(한글·영문·숫자·기호가 이어지는 한 토막)
CHUNK = re.compile(r"[^\n<>'\"]*[가-힣][^\n<>'\"]*")
HAN = re.compile(r"[가-힣]")


def blob(p):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    r = subprocess.run(["git", "-c", "core.quotepath=false", "cat-file", "blob",
                        "origin/main:" + B + p], capture_output=True, env=env)
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""


def strip_comments(t):
    out, inblock = [], False
    for ln in t.splitlines():
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
        # 줄 끝 한줄주석(// …) — 따옴표 안이 아닌 것만 대충 거른다
        if "//" in ln and ln.count('"') % 2 == 0 and ln.count("'") % 2 == 0:
            ln = ln.split("//")[0]
        out.append(ln)
    return "\n".join(out)


tot_chunks = 0
tot_chars = 0
for f in FILES:
    raw = blob(f)
    t = strip_comments(raw)
    chunks = [c.strip() for c in CHUNK.findall(t)]
    chunks = [c for c in chunks if HAN.search(c) and len(c) >= 2]
    uniq = sorted(set(chunks))
    han_chars = len(HAN.findall(t))
    raw_han = len(HAN.findall(raw))
    print("── %s ──" % f)
    print("   한글 글자 : 주석 뺀 뒤 **%d자** (주석 포함 %d자 · 주석이 %d자)"
          % (han_chars, raw_han, raw_han - han_chars))
    print("   번역할 덩어리 : **%d개**(서로 다른 것) · 나온 횟수 %d번" % (len(uniq), len(chunks)))
    print("   길이별 : 10자 미만 %d · 10~30자 %d · 30자 이상 %d"
          % (len([x for x in uniq if len(x) < 10]),
             len([x for x in uniq if 10 <= len(x) < 30]),
             len([x for x in uniq if len(x) >= 30])))
    tot_chunks += len(uniq)
    tot_chars += han_chars
    print()
print("합계: 서로 다른 덩어리 **%d개** · 한글 **%d자**" % (tot_chunks, tot_chars))
