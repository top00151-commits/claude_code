#!/usr/bin/env python3
"""KNK Messenger load test client (2026-05-20)

Phase 3 - 75 concurrent users + file upload measurement.

Requirements:
- admin (ceo role) account credentials
- Server endpoints: /api/admin/load_test/setup, /cleanup, /status

Usage:
  python load_test_client.py \\
    --base https://haist.knknara.co.kr/msg \\
    --admin-username admin@example.com \\
    --admin-password "password" \\
    --count 75 \\
    --scenarios "5:1,5:5,5:20,5:75,30:75,100:75"

scenarios format: 'fileMB:concurrentUsers' comma separated
"""
import argparse
import concurrent.futures as _cf
import csv
import os
import sys
import time
import urllib3
from typing import List, Tuple

try:
    import requests
except ImportError:
    print("pip install requests required")
    sys.exit(1)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIRM_TOKEN = "I_UNDERSTAND_LOAD_TEST"


def make_dummy_file(size_mb: int) -> bytes:
    return os.urandom(size_mb * 1024 * 1024)


def login(base: str, username: str, password: str, verify: bool = False) -> requests.Session:
    s = requests.Session()
    s.verify = verify
    r = s.post(f"{base}/login",
               data={"username": username, "password": password},
               allow_redirects=False, timeout=30)
    if r.status_code in (302, 303):
        return s
    if "session" in s.cookies:
        return s
    raise RuntimeError(f"login failed ({username}): status={r.status_code}")


def setup_load_test(admin: requests.Session, base: str, count: int) -> dict:
    r = admin.post(f"{base}/api/admin/load_test/setup",
                   json={"count": count, "confirm_token": CONFIRM_TOKEN},
                   timeout=120)
    r.raise_for_status()
    return r.json()


def cleanup_load_test(admin: requests.Session, base: str) -> dict:
    r = admin.post(f"{base}/api/admin/load_test/cleanup",
                   json={"confirm_token": CONFIRM_TOKEN},
                   timeout=300)
    r.raise_for_status()
    return r.json()


def upload_file(session: requests.Session, base: str, room_id: int,
                filename: str, data: bytes) -> Tuple[float, int, str]:
    start = time.perf_counter()
    try:
        r = session.post(
            f"{base}/api/upload",
            files={"file": (filename, data, "application/octet-stream")},
            data={"room_id": str(room_id)},
            timeout=600,
        )
        elapsed = time.perf_counter() - start
        msg = "OK" if r.status_code == 200 else r.text[:200]
        return elapsed, r.status_code, msg
    except Exception as e:
        elapsed = time.perf_counter() - start
        return elapsed, -1, str(e)[:200]


def run_concurrent(sessions: List[requests.Session], base: str, room_id: int,
                   size_mb: int, n_users: int) -> List[Tuple[float, int, str]]:
    file_data = make_dummy_file(size_mb)
    selected = sessions[:n_users]
    results = []
    # .dwg = CAD drawing, allowed by server (ALLOWED_FILE_EXT) and matches the
    # "large drawing/CAD" usage pattern the load test simulates.
    with _cf.ThreadPoolExecutor(max_workers=n_users) as ex:
        futures = [
            ex.submit(upload_file, s, base, room_id,
                      f"loadtest_{i:03d}_{size_mb}mb.dwg", file_data)
            for i, s in enumerate(selected, 1)
        ]
        for f in _cf.as_completed(futures):
            results.append(f.result())
    return results


def report(results: List[Tuple[float, int, str]], scenario: str) -> dict:
    n = len(results)
    times = sorted(r[0] for r in results)
    ok = sum(1 for r in results if r[1] == 200)
    errors = n - ok
    p50 = times[n // 2] if n else 0
    p95 = times[min(n - 1, int(n * 0.95))] if n else 0
    p99 = times[min(n - 1, int(n * 0.99))] if n else 0
    p_max = times[-1] if n else 0
    print(f"\n=== {scenario} ===")
    print(f"  total {n}  | ok {ok}  | err {errors}  | rate {ok/n*100:.1f}%")
    print(f"  p50 {p50:.2f}s  p95 {p95:.2f}s  p99 {p99:.2f}s  max {p_max:.2f}s")
    fails = [r for r in results if r[1] != 200][:3]
    for f in fails:
        print(f"  fail status={f[1]}  msg={f[2][:100]}")
    return {
        "scenario": scenario, "total": n, "ok": ok, "errors": errors,
        "success_rate_pct": ok / n * 100 if n else 0,
        "p50_s": p50, "p95_s": p95, "p99_s": p99, "max_s": p_max,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--admin-username", required=True)
    ap.add_argument("--admin-password", required=True)
    ap.add_argument("--count", type=int, default=75)
    ap.add_argument("--scenarios", default="5:1,5:5,5:20,5:75,30:75,100:75")
    ap.add_argument("--no-cleanup", action="store_true")
    ap.add_argument("--verify-ssl", action="store_true", default=False)
    args = ap.parse_args()

    base = args.base.rstrip("/")
    print(f"[*] admin login - {args.admin_username}")
    admin = login(base, args.admin_username, args.admin_password, verify=args.verify_ssl)

    print(f"[*] /api/admin/load_test/setup count={args.count}")
    setup = setup_load_test(admin, base, args.count)
    room_id = setup["room_id"]
    users = setup["users"]
    print(f"    room_id={room_id}  users={len(users)}")

    print(f"[*] login each test account (parallel max=20)...")
    sessions: List[requests.Session] = []
    with _cf.ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(login, base, u["username"], u["password"], args.verify_ssl): u
                for u in users}
        for f in _cf.as_completed(futs):
            try:
                sessions.append(f.result())
            except Exception as e:
                print(f"    login fail: {e}")
    print(f"    login ok: {len(sessions)}/{len(users)}")
    if len(sessions) < len(users) * 0.9:
        print("    WARN login rate < 90% - aborting")
        if not args.no_cleanup:
            print("    calling cleanup...")
            cleanup_load_test(admin, base)
        return

    print(f"[*] running scenarios...")
    summary = []
    scenarios = [tuple(map(int, s.split(":"))) for s in args.scenarios.split(",")]
    for size_mb, n_users in scenarios:
        if n_users > len(sessions):
            n_users = len(sessions)
        print(f"\n>>> scenario: {size_mb}MB x {n_users} users")
        wall_start = time.perf_counter()
        results = run_concurrent(sessions, base, room_id, size_mb, n_users)
        wall = time.perf_counter() - wall_start
        r = report(results, f"{size_mb}MB x {n_users}")
        r["wall_clock_s"] = wall
        r["throughput_mbps"] = (size_mb * n_users) / wall if wall > 0 else 0
        print(f"  wall {wall:.1f}s  | throughput {r['throughput_mbps']:.1f}MB/s")
        summary.append(r)
        time.sleep(3)

    csv_path = f"loadtest_result_{int(time.time())}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        for row in summary:
            w.writerow(row)
    print(f"\n[*] result CSV: {csv_path}")

    if not args.no_cleanup:
        print(f"\n[*] cleanup...")
        c = cleanup_load_test(admin, base)
        print(f"    deleted users={c['deleted_users']}  rooms={c['deleted_rooms']}  "
              f"messages={c['deleted_messages']}  files={c['deleted_files']}")


if __name__ == "__main__":
    main()
