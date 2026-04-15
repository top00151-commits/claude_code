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
    print("=" * 60)
    print("  HAIST WORKS - KNK 통합 업무 플랫폼")
    print("  (주)케이엔케이 | HAIST Innovation")
    print("  Human & AI create the Best")
    print("=" * 60)
    print()
    print("  접속: http://localhost:8081")
    print("  종료: Ctrl+C")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8081, reload=True)
