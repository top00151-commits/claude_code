# -*- coding: utf-8 -*-
"""WP-01 운영 잠금 상태 점검 — 배포 전/후 증빙 (ERP 게이트 v4 §7-7)

쓰는 법 (운영 컨테이너에서 1회):
    python deploy/check_wp01_locks.py

무엇을 보나:
  · 잠금 스위치 목록은 app/database.py 의 WP01_LOCK_SWITCHES 한 곳에서 읽는다(소스 파싱 —
    앱을 import 하지 않으므로 DB·서버에 아무 영향 없음).
  · 지금 셸 환경 + 컨테이너 1번 프로세스(/proc/1/environ)를 함께 확인한다.
    앱은 1번 프로세스(supervisord)의 환경을 물려받으므로 실제 서버 상태에 가깝다.

결과: 전부 '잠김'이어야 정상. 하나라도 '열림'이면 종료코드 1 (배포 전 제거 대상).
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # 01_HAIST_WORKS


def switch_names() -> list:
    """app/database.py 의 WP01_LOCK_SWITCHES 값을 구문분석으로 읽는다.
    (정규식으로 괄호를 세면 주석 안의 괄호에 걸려 목록이 잘린다 — 실제로 한 번 겪음)"""
    src = open(os.path.join(ROOT, "app", "database.py"), encoding="utf-8").read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "WP01_LOCK_SWITCHES":
                    return list(ast.literal_eval(node.value))
    print("!! app/database.py 에서 WP01_LOCK_SWITCHES 를 찾지 못했습니다 — 목록 정의가 바뀌었는지 확인하세요.")
    raise SystemExit(2)


def pid1_env() -> dict:
    """컨테이너 1번 프로세스의 환경변수 (리눅스에서만 · 실패하면 빈 값)."""
    try:
        raw = open("/proc/1/environ", "rb").read().decode("utf-8", "replace")
    except Exception:
        return {}
    out = {}
    for part in raw.split("\0"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def main() -> int:
    names = switch_names()
    p1 = pid1_env()
    print("=" * 66)
    print(" WP-01 위험 경로 잠금 상태 (값이 '1'이면 열림 = 위험)")
    print("=" * 66)
    opened = []
    for n in names:
        here = os.environ.get(n)
        there = p1.get(n)
        is_open = (here == "1") or (there == "1")
        if is_open:
            opened.append(n)
        state = "열림 ⚠" if is_open else "잠김"
        detail = f"셸={here or '-'} / 서버프로세스={there if p1 else '(확인 불가)'}"
        print(f"  {state:6s}  {n:34s}  {detail}")
    print("-" * 66)
    if not p1:
        print(" ※ /proc/1/environ 을 읽지 못했습니다(윈도우·권한). 서버에서 다시 실행하세요.")
    if opened:
        print(f" 결과: 열려 있는 스위치 {len(opened)}개 — {', '.join(opened)}")
        print(" 배포 전에 제거하고 서비스를 재시작하세요.")
        return 1
    print(f" 결과: {len(names)}개 전부 잠김 — 정상")
    return 0


if __name__ == "__main__":
    sys.exit(main())
