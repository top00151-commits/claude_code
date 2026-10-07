# -*- coding: utf-8 -*-
"""z1142 비교 — 같은 5분(조용한 앞구간 3:00~8:00)을 다섯 가지 소리 품질로 받아쓴다.
🔴 운영 DB·코드는 건드리지 않는다(AI 키만 앱이 쓰는 길로 읽는다 · 찍지 않는다).
결과는 /tmp/z1142/out_*.txt"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "/opt/knk_haist")
os.chdir("/opt/knk_haist")
from app import ai_client

D = "/tmp/z1142"
FILES = [
    ("A_now32k", "A_now32k.mp3", "지금 그대로 (16kHz 32kbps)"),
    ("B_96k", "B_96k.mp3", "덜 누르기 (16kHz 96kbps)"),
    ("C_96k_loudnorm", "C_96k_loudnorm.mp3", "음량 맞추기 (96kbps + loudnorm)"),
    ("D_96k_dynaudnorm", "D_96k_dynaudnorm.mp3", "작은 소리 끌어올림 (96kbps + dynaudnorm)"),
    ("E_original", "E_original.m4a", "원본 그대로 (48kHz 256kbps)"),
]

print("모델 = %s / 폴백 = %s" % (ai_client.STT_MODEL, ai_client.STT_FALLBACK_MODEL))
print("키 있나 = %s" % bool(ai_client._key_for("openai")))   # 값은 찍지 않는다
for name, fn, desc in FILES:
    p = os.path.join(D, fn)
    if not os.path.exists(p):
        print("%-18s 파일 없음" % name)
        continue
    t0 = time.time()
    ok, txt = ai_client.ai_transcribe(p, "")
    el = time.time() - t0
    with open(os.path.join(D, "out_%s.txt" % name), "w", encoding="utf-8") as f:
        f.write(txt if ok else "[실패] " + txt)
    print("%-18s %-4s %6.1f초  %5d자  | %s" % (name, "OK" if ok else "실패", el, len(txt), desc))
print("끝")
