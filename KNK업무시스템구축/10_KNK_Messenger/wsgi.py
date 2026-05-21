"""WSGI 진입점 (운영 배포용).

gunicorn -k eventlet -w 1 wsgi:app
또는
gunicorn -k eventlet -w 1 wsgi:application

운영에서는 KNK_MSG_ENV=production 으로 실행해야 보안헤더·HTTPS·CORS가 켜집니다.
"""
# eventlet monkey_patch — 다른 import 보다 먼저 실행해야 함 (2026-05-20 대표 지시).
# 이게 없으면 sqlite3·socket·ssl 등이 sync(blocking) 동작 → eventlet 의 동시성 이점 무효.
# 75명 동시 파일 업로드 시 사실상 직렬 처리되어 30s timeout 직격 가능.
# gunicorn 의 eventlet worker 도 monkey_patch 를 하지만, app 모듈 import 가 끝난 후라
# 이미 unpatched 상태로 import 된 sqlite3 등이 영향 받음 → 여기서 가장 먼저 patch.
import eventlet
eventlet.monkey_patch()

import os

# wsgi 로드 시 init_db가 한 번 실행되도록 보장
from app import (
    app, socketio, init_db, UPLOAD_DIR,
    _start_calendar_worker, _start_project_history_worker, _start_backup_worker,
)

os.makedirs(UPLOAD_DIR, exist_ok=True)
init_db()
_start_calendar_worker()  # 60초마다 캘린더→상태 자동 전환
_start_project_history_worker()  # 24시간마다 모든 아이템 방 이력 자동 생성
_start_backup_worker()  # 매일 새벽 3시(KST) 자동 백업 (대표 지시 2026-05-19)

# gunicorn이 찾는 두 이름 모두 노출
application = app
