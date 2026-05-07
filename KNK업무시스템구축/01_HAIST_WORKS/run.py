#!/usr/bin/env python3
"""
HAIST WORKS - KNK 통합 업무 플랫폼
㈜케이엔케이 / HAIST Innovation
"""
import os
import sys
import uvicorn

# Windows 콘솔에서 유니코드 출력을 위해 UTF-8 강제
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    # v5H226f-2: 운영 모드 토글
    # KNK_MODE=prod  → reload off, host 127.0.0.1, workers 환경변수
    # 기본 (개발)    → reload on, host 0.0.0.0
    _mode = os.environ.get("KNK_MODE", "dev").lower()
    _is_prod = _mode in ("prod", "production")
    _host = os.environ.get("KNK_HOST", "127.0.0.1" if _is_prod else "0.0.0.0")
    _port = int(os.environ.get("KNK_PORT", "8081"))
    _workers = int(os.environ.get("KNK_WORKERS", "2" if _is_prod else "1"))
    print("=" * 60)
    print("  HAIST WORKS - KNK 통합 업무 플랫폼")
    print("  (주)케이엔케이 | HAIST Innovation")
    print("  Human & AI create the Best")
    print("=" * 60)
    print()
    print(f"  모드: {'운영' if _is_prod else '개발'}  (KNK_MODE={_mode})")
    print(f"  접속: http://{_host}:{_port}")
    print(f"  종료: Ctrl+C")
    print("=" * 60)
    if _is_prod:
        # 운영: reload off, workers 다중 (uvicorn 직접 호출은 string app path 필요)
        uvicorn.run("app.main:app", host=_host, port=_port,
                    reload=False, workers=_workers, log_level="info")
    else:
        # 개발: 기존 동작 그대로 (reload on)
        uvicorn.run("app.main:app", host=_host, port=_port, reload=True)
