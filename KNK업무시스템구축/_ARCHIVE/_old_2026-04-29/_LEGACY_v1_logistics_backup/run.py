#!/usr/bin/env python3
"""
㈜케이엔케이 KNK 물류허브
HAIST Innovation
"""
import os
import uvicorn

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("=" * 60)
    print("  ㈜케이엔케이 KNK 물류허브")
    print("  HAIST Innovation | Human & AI create the Best")
    print("=" * 60)
    print()
    print("  접속: http://localhost:8081")
    print("  종료: Ctrl+C")
    print("=" * 60)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8081, reload=True)
