# -*- coding: utf-8 -*-
"""회의록이 없어진 뒤 서버에 남은 녹음 폴더(고아) 정리 — 운영 서버(/opt/knk_haist)에서 실행
  기본(인자 없음) = **목록만** 보여 준다(아무것도 안 지움) · 실제로 지우려면 `--go`
  🔴 지우는 것: `meeting_audio/meeting_<번호>/` 중 그 번호의 회의록이 **DB 에 없는** 폴더만
  🔴 안 지우는 것: `_share`(아직 어느 회의인지 정해지지 않은 파일) · 이름 모양이 다른 폴더 · 회의록이 살아 있는 폴더 · 폴더 아닌 것
사용: /opt/knk_haist/.venv/bin/python purge_orphan_audio.py [--go]"""
import os
import shutil
import sqlite3
import sys

GO = "--go" in sys.argv[1:]
BASE = "meeting_audio"
DB = "file:data/knk.db?mode=ro"

c = sqlite3.connect(DB, uri=True, timeout=5)
live = {int(r[0]) for r in c.execute("SELECT id FROM meetings")}
assert live, "회의록이 한 건도 안 읽힘 — 안전을 위해 중지(DB 경로 확인)"
print("회의록 살아 있는 것: %d건" % len(live))

rows, skip = [], []
for name in sorted(os.listdir(BASE)):
    p = os.path.join(BASE, name)
    if not os.path.isdir(p):
        skip.append((name, "폴더 아님"))
        continue
    if not name.startswith("meeting_"):
        skip.append((name, "이름 모양이 다름(예: _share)"))
        continue
    try:
        mid = int(name.split("_", 1)[1])
    except ValueError:
        skip.append((name, "번호가 아님"))
        continue
    if mid in live:
        skip.append((name, "회의록 살아 있음"))
        continue
    files = [os.path.join(r, f) for r, _d, fs in os.walk(p) for f in fs]
    size = 0
    for f in files:
        try:
            size += os.path.getsize(f)
        except OSError:
            pass
    rows.append((name, p, mid, len(files), size))

print("\n── 지울 것(회의록 없는 녹음 폴더) %d개" % len(rows))
tot = 0
for name, _p, mid, n, size in rows:
    tot += size
    print("   %-16s 회의번호 %-5s 파일 %-3d %8.2fMB" % (name, mid, n, size / 1048576))
print("   합계 %.1fMB" % (tot / 1048576))
print("\n── 건드리지 않는 것 %d개" % len(skip))
for name, why in skip:
    print("   %-16s %s" % (name, why))

if not GO:
    print("\n(목록만 봤습니다 — 실제로 지우려면 --go)")
    sys.exit(0)

print("\n── 지우는 중(--go)")
done = done_b = 0
for name, p, _mid, n, size in rows:
    try:
        shutil.rmtree(p)
        done += 1
        done_b += size
        print("   지움 %-16s 파일 %-3d %8.2fMB" % (name, n, size / 1048576))
    except Exception as e:
        print("   ⚠ 실패 %-16s %s: %s" % (name, type(e).__name__, str(e)[:120]))
left = [d for d in sorted(os.listdir(BASE)) if os.path.isdir(os.path.join(BASE, d))]
print("\n지운 폴더 %d개 · %.1fMB · 남은 폴더 %d개(%s)" % (done, done_b / 1048576, len(left), ", ".join(left[:6]) + (" …" if len(left) > 6 else "")))
