#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KNK 메신저 — 베타 테스트 데이터 초기화 (전사 배포 직전 1회용)

대표 지시 2026-05-21 확정 범위:
  [삭제]  모든 메시지·방(1:1/그룹/프로젝트/채널)·요청·프로젝트(items)·업로드 파일·
          읽음표시·반응/확인/별표/번역/AI요약/프로젝트이력·푸시구독·로그인세션(active_sessions)
  [유지]  직원 계정(users) · 프로필 사진(avatars/) · 스키마 마이그레이션 기록(app_migrations)
          · 사용자 상태(user_statuses) · 캘린더(user_calendar_events)
  [자동복구] KNK WORLD/본사/베트남 채널 + 각자 "📝 내 메모" → 서버 재시작 시 자동 재생성

안전장치:
  · 기본은 '미리보기(dry-run)' — 무엇이 지워질지 건수만 보여주고 실제 삭제 안 함.
  · 실제 삭제는 --confirm 플래그를 줘야 실행.
  · 삭제 직전 DB 를 data/backups/ 에 자동 백업(타임스탬프).

사용법:
  미리보기:   python3 deploy/reset_beta_data.py
  실제 실행:  python3 deploy/reset_beta_data.py --confirm

실행 후 반드시 서버를 재시작하세요 (자동 채널·내 메모 재생성).
"""
import os
import sys
import shutil
import sqlite3
from datetime import datetime, timezone

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(APP_DIR, "data", "messenger.db")
UPLOAD_DIR = os.path.join(APP_DIR, "data", "uploads")
BACKUP_DIR = os.path.join(APP_DIR, "data", "backups")
KEEP_UPLOAD_SUBDIRS = {"avatars"}   # 프로필 사진은 보존

# 비울 테이블 — 의존성 순서(자식 먼저). users / app_migrations / user_statuses /
# user_calendar_events 는 의도적으로 제외(유지).
WIPE_TABLES = [
    "message_reactions",
    "message_acks",
    "message_stars",
    "attachment_versions",
    "message_translations",
    "ai_summaries",
    "project_history",
    "requests",
    "items",
    "room_aliases",
    "messages",
    "room_members",
    "rooms",
    "push_subscriptions",
    "active_sessions",
]
KEEP_TABLES = ["users", "app_migrations", "user_statuses", "user_calendar_events"]


def _table_exists(cur, name):
    r = cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name=?", (name,)
    ).fetchone()
    return r is not None


def _count(cur, name):
    if not _table_exists(cur, name):
        return None
    try:
        return cur.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    except Exception:
        return None


def _upload_stats():
    """avatars/ 를 제외한 업로드 항목 수·용량."""
    n_files = 0
    n_bytes = 0
    targets = []
    if not os.path.isdir(UPLOAD_DIR):
        return targets, n_files, n_bytes
    for entry in os.listdir(UPLOAD_DIR):
        if entry in KEEP_UPLOAD_SUBDIRS:
            continue
        path = os.path.join(UPLOAD_DIR, entry)
        targets.append(path)
        if os.path.isfile(path):
            n_files += 1
            try:
                n_bytes += os.path.getsize(path)
            except OSError:
                pass
        elif os.path.isdir(path):
            for root, _dirs, files in os.walk(path):
                for f in files:
                    n_files += 1
                    try:
                        n_bytes += os.path.getsize(os.path.join(root, f))
                    except OSError:
                        pass
    return targets, n_files, n_bytes


def _fmt_size(b):
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def preview():
    print("=" * 56)
    print("  KNK 메신저 — 베타 데이터 초기화 [미리보기]")
    print("=" * 56)
    print(f"  DB:      {DB_PATH}")
    print(f"  uploads: {UPLOAD_DIR}")
    print()
    if not os.path.exists(DB_PATH):
        print(f"  [오류] DB 파일 없음: {DB_PATH}")
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    print("  [삭제 예정]")
    total = 0
    for t in WIPE_TABLES:
        c = _count(cur, t)
        if c is None:
            print(f"    - {t:<22} (테이블 없음 — 건너뜀)")
        else:
            total += c
            print(f"    - {t:<22} {c:>7} 행")
    print(f"    {'합계':<22} {total:>7} 행")
    print()
    print("  [유지]")
    for t in KEEP_TABLES:
        c = _count(cur, t)
        if c is not None:
            print(f"    - {t:<22} {c:>7} 행 (보존)")
    con.close()
    _targets, nf, nb = _upload_stats()
    print()
    print(f"  [업로드 파일 삭제 예정] {nf} 개 / {_fmt_size(nb)}  (avatars/ 프로필 사진은 보존)")
    print()
    print("  ※ 실제로 지우려면:  python3 deploy/reset_beta_data.py --confirm")
    print("=" * 56)


FTS_TRIGGERS = ("messages_ai", "messages_ad", "messages_au")
# init_db 와 동일한 FTS 트리거 정의 — 초기화 후 즉시 복구해 DB 를 정상 상태로.
FTS_TRIGGER_SQL = """
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
END;
CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content) VALUES('delete', old.id, old.content);
    INSERT INTO messages_fts(rowid, content) VALUES (new.id, new.content);
END;
"""


def run_reset():
    if not os.path.exists(DB_PATH):
        print(f"[오류] DB 파일 없음: {DB_PATH}")
        sys.exit(1)

    # 1) 백업 — SQLite 백업 API (WAL 모드에서도 일관된 스냅샷 보장. raw 파일복사 X)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"messenger_before_reset_{stamp}.db")
    _src = sqlite3.connect(DB_PATH)
    _dst = sqlite3.connect(backup_path)
    try:
        with _dst:
            _src.backup(_dst)
    finally:
        _dst.close()
        _src.close()
    print(f"[1/4] 백업 완료(일관성 보장): {backup_path}")

    # 2) DB 비우기
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = OFF")  # 명시적 순서 삭제 — FK 의존 안 함
    cur = con.cursor()
    # FTS 동기화 트리거 일시 제거 — external-content FTS5 의 'delete' 트리거는 본문-인덱스
    # 정확매칭을 요구해 대량 삭제 시 취약. 트리거 끄고 비운 뒤 rebuild + 트리거 복구.
    for trg in FTS_TRIGGERS:
        cur.execute(f"DROP TRIGGER IF EXISTS {trg}")
    deleted = {}
    for t in WIPE_TABLES:
        if _table_exists(cur, t):
            before = _count(cur, t) or 0
            cur.execute(f"DELETE FROM {t}")
            deleted[t] = before
    # FTS 인덱스 재빌드 — 빈 messages 기준 → 빈 인덱스. 'rebuild' 는 content-매칭 불필요라 안전.
    try:
        if _table_exists(cur, "messages_fts"):
            cur.execute("INSERT INTO messages_fts(messages_fts) VALUES('rebuild')")
    except Exception as e:
        print(f"      (FTS rebuild 경고, 무시): {e}")
    # FTS 트리거 복구 (서버 재시작 없이도 정상 동작하도록)
    cur.executescript(FTS_TRIGGER_SQL)
    con.commit()
    print("[2/4] DB 비우기 완료:")
    for t, n in deleted.items():
        if n:
            print(f"        {t}: {n} 행 삭제")

    # 3) 공간 회수
    try:
        con.execute("VACUUM")
    except Exception as e:
        print(f"      (VACUUM 경고, 무시): {e}")
    con.close()
    print("[3/4] VACUUM (공간 회수) 완료")

    # 4) 업로드 파일 삭제 (avatars/ 제외)
    targets, nf, nb = _upload_stats()
    for path in targets:
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
        except Exception as e:
            print(f"      (파일 삭제 경고, 무시) {path}: {e}")
    print(f"[4/4] 업로드 파일 삭제 완료: {nf} 개 / {_fmt_size(nb)} (avatars/ 보존)")

    print()
    print("=" * 56)
    print("  ✅ 초기화 완료")
    print(f"     백업: {backup_path}")
    print("     ⚠️  서버를 재시작하세요 →")
    print("        자동 채널(KNK WORLD/본사/베트남) + 직원 멤버십 + 각자 📝내 메모 자동 재생성")
    print("=" * 56)


def main():
    confirm = "--confirm" in sys.argv
    if not confirm:
        preview()
        return
    print("=" * 56)
    print("  ⚠️  실제 삭제를 진행합니다 (--confirm). 백업 후 비웁니다.")
    print("=" * 56)
    run_reset()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
