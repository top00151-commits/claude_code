# WORKS DB 사본 더미 정리 (2026-10-11 · 대표 선택 「9/2 이후 + 기능별 최신 1개」)
#
#   남김: 자동 직원 동기화(04:10) 사본 전부 · 2026-09-02 이후 사본 전부 · 그 이전은 만든 기능마다 최신 1개(기록용)
#   지움: 그 밖의 사본(약 108개 · 69GB) + 빅터가 9/10 뜬 사본 2개 + 빅터가 남긴 빈 보조 파일(-shm/-wal)
#   손대지 않음: 운영 DB · WP-03 사본 2개
#
# 그냥 실행하면 **확인만** 합니다(아무것도 지우지 않음).
# 실제로 지우려면 뒤에 -Apply 를 붙이세요.
#
#   확인 :  powershell -ExecutionPolicy Bypass -File "이 파일"
#   적용 :  powershell -ExecutionPolicy Bypass -File "이 파일" -Apply
param([switch]$Apply)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$mode = "CHECK"
if ($Apply) { $mode = "APPLY" }

Write-Host ""
Write-Host "=== WORKS DB 사본 정리 ($mode) ===" -ForegroundColor Cyan
Write-Host ""

$py = @'
# -*- coding: utf-8 -*-
# WORKS DB 사본 더미 정리 (2026-10-11 · 대표 선택 「9/2 이후 + 기능별 최신 1개」)
#   남기는 것: ① 자동 직원 동기화(04:10) 사본 전부 ② 2026-09-02 이후 사본 전부
#             ③ 2026-09-02 이전 사본은 「만든 기능」마다 가장 최근 1개(기록용)
#   지우는 것: 그 밖의 사본 + 빅터가 남긴 빈 보조 파일(-shm/-wal) + 빅터가 9/10 뜬 사본 2개(knk_pre_z1097*)
#   손대지 않는 것: 운영 DB(knk.db*) · WP-03 사본 2개(knk_wp03_*.db — 담당 확인 전)
#   CHECK = 목록만(아무것도 안 지움) · APPLY = 지움
import os, sys, datetime, shutil

MODE = sys.argv[1] if len(sys.argv) > 1 else "CHECK"
B = "/opt/knk_haist/data/backups"
D = "/opt/knk_haist/data"
CUT = datetime.datetime(2026, 9, 2).timestamp()      # 서버 시각(KST) 2026-09-02 00:00
AUTO = "자동 직원동기화(04:10)"
AUX = ("-shm", "-wal", "-journal")
LIVE = {os.path.join(D, n) for n in ("knk.db", "knk.db-wal", "knk.db-shm", "knk.db-journal")}
MINE = [os.path.join(D, n) for n in ("knk_pre_z1097_20260910.db", "knk_pre_z1097b_20260910.db")]
MINE_AUX = [os.path.join(D, n) for n in ("knk_wp03_shipfix_pre_20260726.db-shm", "knk_wp03_shipfix_pre_20260726.db-wal")]


def kind_of(f):
    if f.startswith("knk.db.bak_autoempsync"):
        return AUTO
    if f.startswith("knk.db.bak_empsync"):
        return "수동 직원동기화"
    if f.startswith("knk.db.bak_retire"):
        return "수주·프로젝트 폐기"
    if f.startswith("knk.db.bak_resetgrp"):
        return "데이터 그룹 비우기"
    if f.startswith("knk.db.bak_resetdiv") or f.startswith("knk.db.bak_reset") or f.startswith("knk.db.bak_co_reset"):
        return "초기화"
    return "1회성"


def gb(b):
    return "%.2fGB" % (b / 1e9)


def day(t):
    return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


def open_paths():
    s = set()
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        fd = "/proc/%s/fd" % pid
        try:
            for n in os.listdir(fd):
                try:
                    s.add(os.readlink(os.path.join(fd, n)))
                except OSError:
                    pass
        except OSError:
            pass
    return s


def plan():
    main, aux = [], []
    for f in sorted(os.listdir(B)):
        p = os.path.join(B, f)
        if not os.path.isfile(p):
            continue
        st = os.stat(p)
        if f.endswith(AUX):
            aux.append((p, st.st_size))
        else:
            main.append({"p": p, "f": f, "k": kind_of(f), "b": st.st_size, "t": st.st_mtime})
    old = {}
    for x in main:
        if x["t"] < CUT and x["k"] != AUTO:
            old.setdefault(x["k"], []).append(x)
    keep_old = {k: max(v, key=lambda x: x["t"])["p"] for k, v in old.items()}
    keep, dele = [], []
    for x in main:
        if x["k"] == AUTO or x["t"] >= CUT or x["p"] == keep_old.get(x["k"]):
            keep.append(x)
        else:
            dele.append(x)
    for p in MINE_AUX:
        if os.path.isfile(p):
            aux.append((p, os.path.getsize(p)))
    mine = [(p, os.path.getsize(p)) for p in MINE if os.path.isfile(p)]
    return main, keep, dele, aux, mine


main, keep, dele, aux, mine = plan()

# ── 안전장치 ──
bad = [x["p"] for x in dele if x["p"] in LIVE or not x["p"].startswith(B + "/")]
bad += [p for p, _ in aux + mine if p in LIVE]
if bad:
    print("!! 운영 DB 가 지울 목록에 있습니다 — 멈춥니다:", bad)
    sys.exit(2)
if any(x["t"] >= CUT or x["k"] == AUTO for x in dele):
    print("!! 9월 2일 이후 사본이나 자동 사본이 지울 목록에 있습니다 — 멈춥니다")
    sys.exit(2)
if not (95 <= len(dele) <= 115):
    print("!! 지울 사본이 %d개 — 예상(약 108개)과 많이 다릅니다. 멈춥니다. 빅터에게 알려 주세요." % len(dele))
    sys.exit(2)

print("사본 전체 %d개 %s" % (len(main), gb(sum(x["b"] for x in main))))
print("")
print("[남길 것] %d개 %s" % (len(keep), gb(sum(x["b"] for x in keep))))
for x in sorted(keep, key=lambda x: x["t"]):
    tag = "기록용(9/2 이전 최신)" if (x["t"] < CUT and x["k"] != AUTO) else ""
    print("   %-16s %s  %7s  %s %s" % (x["k"], day(x["t"]), gb(x["b"]), x["f"], tag))
print("")
print("[지울 것] %d개 %s" % (len(dele), gb(sum(x["b"] for x in dele))))
by = {}
for x in dele:
    by.setdefault(x["k"], []).append(x)
for k, v in sorted(by.items(), key=lambda kv: -sum(x["b"] for x in kv[1])):
    print("   %-16s %3d개 %8s  %s ~ %s" % (k, len(v), gb(sum(x["b"] for x in v)),
                                        day(min(x["t"] for x in v))[:10], day(max(x["t"] for x in v))[:10]))
print("   + 빅터가 9/10 뜬 사본 %d개 %s : %s" % (len(mine), gb(sum(b for _, b in mine)), " · ".join(os.path.basename(p) for p, _ in mine)))
print("   + 빈 보조 파일(-shm/-wal) %d개 %d바이트" % (len(aux), sum(b for _, b in aux)))
print("")
print("손대지 않음: 운영 DB · WP-03 사본(data/knk_wp03_pre_20260725.db · data/knk_wp03_shipfix_pre_20260726.db)")
du0 = shutil.disk_usage(D)
print("디스크 여유: %s" % gb(du0.free))

if MODE != "APPLY":
    print("")
    print("확인만 했습니다. 아무것도 지우지 않았습니다.")
    print("실제로 지우려면 -Apply 를 붙여 다시 실행하세요.")
    sys.exit(0)

# ── 적용 ──
opened = open_paths()
n, freed, skipped = 0, 0, []
for x in dele:
    if x["p"] in opened:
        skipped.append(x["f"])
        continue
    os.remove(x["p"])
    n += 1
    freed += x["b"]
for p, b in mine:
    if p in opened:
        skipped.append(os.path.basename(p))
        continue
    os.remove(p)
    n += 1
    freed += b
na = 0
for p, b in aux:
    # 내용이 든 -wal 은 지우지 않는다(사본에 아직 안 들어간 내용일 수 있음) · 열려 있으면 지우지 않는다
    if p in opened or (p.endswith("-wal") and b > 0) or (p.endswith("-shm") and b > 65536):
        skipped.append(os.path.basename(p))
        continue
    os.remove(p)
    na += 1
_, keep2, dele2, aux2, mine2 = plan()
du1 = shutil.disk_usage(D)
print("")
print("지운 사본 : %d개 %s" % (n, gb(freed)))
print("지운 보조 파일 : %d개" % na)
print("건너뜀 : %d개 %s" % (len(skipped), " · ".join(skipped)))
print("남은 사본 : %d개 %s" % (len(keep2) + len(dele2), gb(sum(x["b"] for x in keep2 + dele2))))
print("남길 기준에 맞지 않는데 남은 것 : %d개" % len(dele2))
print("디스크 여유 : %s → %s" % (gb(du0.free), gb(du1.free)))
'@

# 파이프로 그냥 보내면 한글이 CP949 로 바뀌며 깨진다 → base64 로 실어 보낸다(z1132b 와 같은 방식)
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
ssh -p 32201 root@o.knknara.co.kr "echo $b64 | base64 -d > /tmp/_bakclean.py; python3 /tmp/_bakclean.py $mode; rm -f /tmp/_bakclean.py"

Write-Host ""
Write-Host "끝났습니다." -ForegroundColor Green
