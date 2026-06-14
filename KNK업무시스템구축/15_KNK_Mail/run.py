# -*- coding: utf-8 -*-
"""KNK Eum MAIL 독립 기동 엔트리.

로컬 실행:  python run.py
   또는    uvicorn app.main:app --host 127.0.0.1 --port 8201
환경변수:
   KNK_MAIL_PORT (기본 8201) / KNK_MAIL_HOST (기본 127.0.0.1)
   KNK_MAIL_DEV_LOGIN=1  → 로컬 개발 로그인 우회 활성(운영 금지)
"""
import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("KNK_MAIL_HOST", "127.0.0.1"),
        port=int(os.environ.get("KNK_MAIL_PORT", "8201")),
        reload=False,
    )
