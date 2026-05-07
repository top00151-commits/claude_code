"""WSGI 진입점 (운영 배포용).

gunicorn -k eventlet -w 1 wsgi:app
또는
gunicorn -k eventlet -w 1 wsgi:application

운영에서는 KNK_MSG_ENV=production 으로 실행해야 보안헤더·HTTPS·CORS가 켜집니다.
"""
import os

# wsgi 로드 시 init_db가 한 번 실행되도록 보장
from app import app, socketio, init_db, UPLOAD_DIR

os.makedirs(UPLOAD_DIR, exist_ok=True)
init_db()

# gunicorn이 찾는 두 이름 모두 노출
application = app
