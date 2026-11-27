# -*- coding: utf-8 -*-
"""z1206 — 음성 메모 정리 단추 「✏ 고치기」 → 「✏ 수정하기」 (대표 2026-11-04 「음성메모도 수정하기로 변경」 · 11-27 「올려」)
사용: py edit06.py <앱 폴더(app/ 가 들어 있는 곳)>   · 줄 끝 원본 그대로(newline="")
 · templates/voice_note_form.html : 단추 한 줄
 · voice_note_vi.py               : 베트남어 사전 열쇠 한 줄(번역 「✏ Sửa」 그대로)
 (11-04 판은 임시 폴더 정리로 지워져 11-27 에 같은 내용으로 다시 씀)"""
import io
import os
import sys

root = sys.argv[1]


def swap(rel, old, new):
    p = os.path.join(root, "app", rel)
    s = io.open(p, "r", encoding="utf-8", newline="").read()
    if new in s:
        print("STOP: 이미 바뀜", rel); sys.exit(2)
    assert s.count(old) == 1, ("자리", rel, s.count(old))
    s = s.replace(old, new, 1)
    tmp = p + ".tmp06"
    io.open(tmp, "w", encoding="utf-8", newline="").write(s)
    os.replace(tmp, p)
    print("OK", rel)


swap(os.path.join("templates", "voice_note_form.html"),
     "{{ vnt('✏ 고치기', lang)|safe }}</button>",
     "{{ vnt('✏ 수정하기', lang)|safe }}</button>")
swap("voice_note_vi.py",
     '"✏ 고치기": "✏ Sửa",',
     '"✏ 수정하기": "✏ Sửa",   # z1206 (대표 2026-11-04 「음성메모도 수정하기로 변경」) — 번역은 그대로')
