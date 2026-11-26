# -*- coding: utf-8 -*-
"""메일 본문 정리 — ① 6개월 지난 본문 압축 · ② 같은 본문은 하나만 (대표 2026-11-23 「1번 2번 진행해」)
   ③ 11-26 대표 「1번 진행해」 — 받을 때·보낼 때 바로 압축(pack_now) · 밤 정리는 날짜 상관없이 모두(PACK_ALL)

까닭(11-23 실측 · 대표 메일함 8,036통): 본문 461MB → 한 통씩 압축하면 51.8MB(89%↓). 직원 160명이 쓰면 사내 공지·이음/웍스 알림이
      사람마다 같은 본문으로 겹쳐 쌓인다.

방법:
  · 대상 = 받은·보낸 메일(임시보관·예약 제외) 중 서식 본문(HTML)이 1KB 넘는 것 가운데
      ① 원래 날짜(sent_at · 없으면 받은 시각)가 6개월 지난 것  또는  ② 다른 메일(누구 것이든)과 HTML 이 똑같은 것
  · HTML 을 zlib 로 압축해 「본문 보관함」(mail_body_store · 내용 지문 sha256 하나에 한 벌)에 넣고 → **풀어 보아 원본과 같은지 확인한 뒤에만**
    메일의 body_html 칸을 비우고 html_sha 에 지문을 적는다(글 본문 body_text 는 그대로 — 찾기·미리 보기·답장이 그대로 돎)
  · 메일을 열면 get_mail 이 보관함에서 바로 풀어 돌려준다(1ms 안쪽)
  · 묶음(batch)마다 기록(mail_body_pack_log) → 되돌리기 = 그 묶음 메일의 HTML 을 다시 칸에 채움
  · 쓰기는 200통씩 짧게(로그인 등 다른 쓰기를 오래 막지 않게 · z521 교훈)
"""
import hashlib
import time
import zlib

MIN_BYTES = 1024
AGE_DAYS = 183
CHUNK = 200
# 11-26 대표 「1번 진행해」(운영 실측: 6개월 안 된 서식 본문 8,893통 464.6MB 가 그대로 · 압축분은 1,162.6→103.4MB)
#   ① LIVE_PACK = 받을 때·보낼 때 바로 압축(같은 본문이 보관함에 있으면 그 한 벌을 같이 씀)
#   ② PACK_ALL  = 밤 정리가 날짜와 상관없이 1KB 넘는 본문을 모두 압축(남아 있던 최근 본문 정리)
#   끄면(False) 11-23 규칙(6개월 지남 · 같은 본문)으로 돌아감 — 이미 압축된 메일은 그대로 열림
LIVE_PACK = True
PACK_ALL = True
_COLS_OK = set()
_CACHE = {}
_CACHE_MAX = 64


def ensure(c):
    try:
        k = c.execute("PRAGMA database_list").fetchone()[2] or ""
    except Exception:
        k = ""
    if k and k in _COLS_OK:
        return
    have = {r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()}
    for col, ddl in (("html_sha", "ALTER TABLE mail_messages ADD COLUMN html_sha TEXT DEFAULT ''"),
                     ("sent_at", "ALTER TABLE mail_messages ADD COLUMN sent_at TEXT DEFAULT ''")):
        if col not in have:
            try:
                c.execute(ddl)
                have.add(col)
            except Exception as e:
                print("[MAIL-BODY-PACK] 칸 만들기 실패(%s): %s — 다음에 다시" % (col, str(e)[:120]), flush=True)
    c.execute("""CREATE TABLE IF NOT EXISTS mail_body_store (
        sha TEXT PRIMARY KEY, z BLOB NOT NULL, raw_len INTEGER, z_len INTEGER,
        created_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("""CREATE TABLE IF NOT EXISTS mail_body_pack_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, batch TEXT NOT NULL, mail_id INTEGER NOT NULL, sha TEXT NOT NULL,
        why TEXT, created_at TEXT DEFAULT (datetime('now','localtime')))""")
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_mail_body_pack_log_b ON mail_body_pack_log(batch)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_mailmsg_html_sha ON mail_messages(html_sha)")
    except Exception:
        pass
    if k and {"html_sha", "sent_at"} <= have:   # ⭐칸이 실제로 있을 때만 「끝남」(메모리 DB 는 기억 안 함)
        _COLS_OK.add(k)


def has_sent_at(c) -> bool:
    try:
        return "sent_at" in {r[1] for r in c.execute("PRAGMA table_info(mail_messages)").fetchall()}
    except Exception:
        return False


def unpack_html(c, sha):
    """보관함에서 HTML 을 꺼내 풂. 없으면 ''."""
    if not sha:
        return ""
    v = _CACHE.get(sha)
    if v is not None:
        return v
    try:
        r = c.execute("SELECT z FROM mail_body_store WHERE sha=?", (sha,)).fetchone()
    except Exception:
        return ""
    if not r:
        return ""
    try:
        v = zlib.decompress(r[0]).decode("utf-8")
    except Exception:
        return ""
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[sha] = v
    return v


def fill(c, d):
    """메일 dict 에 압축된 본문이 있으면 body_html 을 채워 돌려줌(get_mail 등에서)."""
    try:
        if d is not None and not (d.get("body_html") or "") and (d.get("html_sha") or ""):
            d["body_html"] = unpack_html(c, d["html_sha"])
    except Exception:
        pass
    return d


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def pack_now(c, mail_id, html) -> bool:
    """받을 때·보낼 때 바로(11-26) — 방금 저장한 메일 한 통의 HTML 을 보관함으로. 같은 본문이 이미 있으면 그 한 벌을 씀.
    ⭐풀어 보아 원본과 같을 때만 칸을 비움 · 실패하면 아무것도 안 바꾸고 False(메일은 원래 칸 그대로 · 밤 정리가 다시 봄).
    같은 연결(c) 안에서 돌아 메일 저장과 함께 확정됨. 기록(mail_body_pack_log)은 남기지 않음 — 밤 정리 「되돌리기」와 섞이지 않게."""
    if not LIVE_PACK or not html or not mail_id:
        return False
    try:
        b = html.encode("utf-8")
        if len(b) < MIN_BYTES:
            return False
        ensure(c)
        h = _sha(b)
        c.execute("SAVEPOINT mail_pack_now")
        try:
            ex = c.execute("SELECT z FROM mail_body_store WHERE sha=?", (h,)).fetchone()
            if ex:
                z = ex[0]
            else:
                z = zlib.compress(b, 9)
                c.execute("INSERT INTO mail_body_store(sha, z, raw_len, z_len) VALUES(?,?,?,?)", (h, z, len(b), len(z)))
            if zlib.decompress(z) != b:
                c.execute("ROLLBACK TO mail_pack_now")
                c.execute("RELEASE mail_pack_now")
                return False
            cur = c.execute("UPDATE mail_messages SET body_html='', html_sha=? WHERE id=? AND body_html=? "
                            "AND direction IN ('in','out')", (h, int(mail_id), html))
            if not cur.rowcount:
                c.execute("ROLLBACK TO mail_pack_now")
                c.execute("RELEASE mail_pack_now")
                return False
            c.execute("RELEASE mail_pack_now")
            return True
        except Exception:
            c.execute("ROLLBACK TO mail_pack_now")
            c.execute("RELEASE mail_pack_now")
            raise
    except Exception as e:
        print("[MAIL-BODY-PACK] 받을 때 압축 실패(본문은 원래 칸 그대로 · 밤 정리가 다시 봄): %s" % str(e)[:160], flush=True)
        return False


def _cut():
    from datetime import datetime, timedelta
    return (datetime.now() - timedelta(days=AGE_DAYS)).strftime("%Y-%m-%d %H:%M:%S")


def _scan(db_session):
    """1차 — 모든 받은·보낸 메일의 HTML 지문을 셈(같은 본문 찾기용). 반환 {sha: 개수}, 대상 후보 id 목록."""
    cnt = {}
    rows_meta = []
    last = 0
    while True:
        with db_session() as c:
            ensure(c)
            rs = c.execute("SELECT id, body_html, COALESCE(NULLIF(sent_at,''), received_at) AS t FROM mail_messages "
                           "WHERE id>? AND direction IN ('in','out') AND COALESCE(body_html,'')<>'' ORDER BY id LIMIT 500",
                           (last,)).fetchall()
        if not rs:
            break
        for r in rs:
            last = r["id"]
            b = (r["body_html"] or "").encode("utf-8")
            if len(b) < MIN_BYTES:
                continue
            h = _sha(b)
            cnt[h] = cnt.get(h, 0) + 1
            rows_meta.append((r["id"], h, len(b), r["t"] or ""))
    return cnt, rows_meta


def plan(db_session):
    """숫자만 — 정리하면 몇 통·얼마나 줄어드는지(압축 크기는 표본으로 짐작)."""
    cnt, meta = _scan(db_session)
    cut = _cut()
    old = [m for m in meta if m[3] < cut]
    dup = [m for m in meta if m[3] >= cut and cnt.get(m[1], 0) > 1]
    new = [m for m in meta if m[3] >= cut and cnt.get(m[1], 0) <= 1] if PACK_ALL else []   # 11-26 최근 본문도
    tgt = old + dup + new
    raw = sum(m[2] for m in tgt)
    uniq = {}
    for m in tgt:
        uniq.setdefault(m[1], m[2])
    with db_session() as c:
        ensure(c)
        packed_n = c.execute("SELECT COUNT(*) FROM mail_messages WHERE COALESCE(html_sha,'')<>''").fetchone()[0]
        st = c.execute("SELECT COUNT(*), COALESCE(SUM(raw_len),0), COALESCE(SUM(z_len),0) FROM mail_body_store").fetchone()
    return {"old_n": len(old), "dup_n": len(dup), "new_n": len(new), "pack_all": PACK_ALL, "mails": len(tgt), "raw": raw, "unique_raw": sum(uniq.values()),
            "unique_n": len(uniq), "already_packed": packed_n, "store_n": st[0], "store_raw": st[1], "store_z": st[2]}


def apply(db_session, prog=None):
    """정리 실행 — 묶음 번호와 숫자를 돌려줌."""
    cnt, meta = _scan(db_session)
    cut = _cut()
    tgt = [(m[0], m[1], "6개월 지남" if m[3] < cut else ("같은 본문" if cnt.get(m[1], 0) > 1 else "최근 본문")) for m in meta
           if PACK_ALL or m[3] < cut or cnt.get(m[1], 0) > 1]
    batch = time.strftime("%Y%m%d-%H%M%S")
    n = raw = zbytes_new = skipped = 0
    for i in range(0, len(tgt), CHUNK):
        part = tgt[i:i + CHUNK]
        with db_session() as c:
            ensure(c)
            for mid, h, why in part:
                r = c.execute("SELECT body_html FROM mail_messages WHERE id=?", (mid,)).fetchone()
                html = (r["body_html"] or "") if r else ""
                b = html.encode("utf-8")
                if not b or _sha(b) != h:
                    skipped += 1          # 그새 바뀜 — 건드리지 않음
                    continue
                ex = c.execute("SELECT z FROM mail_body_store WHERE sha=?", (h,)).fetchone()
                if ex:
                    z = ex[0]
                else:
                    z = zlib.compress(b, 9)
                    c.execute("INSERT INTO mail_body_store(sha, z, raw_len, z_len) VALUES(?,?,?,?)", (h, z, len(b), len(z)))
                    zbytes_new += len(z)
                if zlib.decompress(z) != b:   # ⭐풀어 보아 원본과 같을 때만 칸을 비움
                    skipped += 1
                    continue
                c.execute("UPDATE mail_messages SET body_html='', html_sha=? WHERE id=? AND body_html=?", (h, mid, html))
                c.execute("INSERT INTO mail_body_pack_log(batch, mail_id, sha, why) VALUES(?,?,?,?)", (batch, mid, h, why))
                n += 1
                raw += len(b)
        if prog:
            prog(min(i + CHUNK, len(tgt)), len(tgt))
    gc = gc_store(db_session)
    return {"batch": batch if n else "", "packed": n, "raw": raw, "z_new": zbytes_new, "skipped": skipped, "gc": gc}


def gc_store(db_session) -> int:
    """어느 메일도 쓰지 않는 보관함 본문 지우기(메일을 완전히 지운 뒤 남은 것)."""
    with db_session() as c:
        ensure(c)
        cur = c.execute("DELETE FROM mail_body_store WHERE sha NOT IN "
                        "(SELECT html_sha FROM mail_messages WHERE COALESCE(html_sha,'')<>'')")
        return cur.rowcount or 0


def undo(db_session, batch=None) -> int:
    """묶음 되돌리기(없으면 마지막 묶음) — HTML 을 다시 메일 칸에 채움. 되돌린 통수."""
    with db_session() as c:
        ensure(c)
        if not batch:
            r = c.execute("SELECT batch FROM mail_body_pack_log ORDER BY id DESC LIMIT 1").fetchone()
            if not r:
                return 0
            batch = r[0]
        rows = c.execute("SELECT mail_id, sha FROM mail_body_pack_log WHERE batch=?", (batch,)).fetchall()
    n = 0
    for i in range(0, len(rows), CHUNK):
        with db_session() as c:
            for x in rows[i:i + CHUNK]:
                html = unpack_html(c, x["sha"])
                if not html:
                    continue
                c.execute("UPDATE mail_messages SET body_html=?, html_sha='' WHERE id=? AND html_sha=?", (html, x["mail_id"], x["sha"]))
                n += 1
            c.execute("DELETE FROM mail_body_pack_log WHERE batch=? AND mail_id IN (%s)" % ",".join("?" * len(rows[i:i + CHUNK])),
                      [batch] + [x["mail_id"] for x in rows[i:i + CHUNK]])
    gc_store(db_session)
    _CACHE.clear()
    return n


def batches(c, limit=10):
    ensure(c)
    return [dict(r) for r in c.execute("SELECT batch, COUNT(*) AS n, MIN(created_at) AS at FROM mail_body_pack_log "
                                         "GROUP BY batch ORDER BY batch DESC LIMIT ?", (int(limit),)).fetchall()]
