# -*- coding: utf-8 -*-
"""메일 용량 재기 (대표 2026-11-23 「중복 메일도 용량을 차지하는지 · 오래된 메일은 최대한 압축해 보관할 방법 · 160명이면 서버 부담」)

숫자만 잰다 — 저장·변경·바깥 전송 없음 · 제목·내용·주소는 돌려주지 않음.
  ① 내 메일(대표): 기간(6개월 안 · 6~12개월 · 12개월 넘음) × 종류(스팸 · 광고·알림 · 내부 업무(제작요청·발주·구매·가공·진행 등) ·
     내부 기타 · 거래처·기타)별 통수 · 본문 크기 · 「한 통씩 압축」 크기(zlib) · 첨부(논리 크기 · 실제 파일 크기)
  ② 6개월 넘은 메일을 「월별 묶음」으로 강하게 압축(lzma)하면 얼마인지 — 실제로 압축해 봄(달마다 앞 2MB 까지 · 나머지는 같은 비율로 셈)
  ③ 첨부 — 압축이 되는 종류만 실제로 압축해 봄(표본 · 최대 400개 · 300MB)
  ④ 서버 전체(관리자): DB 파일 · 첨부 폴더 크기 · 모든 사람 본문 중 「같은 내용 본문」이 차지하는 크기(전사 공지처럼 여러 명이 받은 메일)
읽기는 500통씩 짧게 나눠서(쓰기를 오래 막지 않게 · WAL).
"""
import hashlib
import lzma
import os
import re
import threading
import time
import zlib

_LOCK = threading.Lock()

AGES = (("a6", "6개월 안"), ("a12", "6~12개월"), ("old", "12개월 넘음"))
KINDS = (("spam", "스팸·차단"), ("bulk", "광고·뉴스레터·자동 알림"), ("work", "내부 업무(제작요청·발주·구매·가공·진행 등)"),
         ("internal", "내부 기타"), ("partner", "거래처·기타"))
WORK_WORDS = ("제작요청", "제작 요청", "발주", "구매", "가공", "진행", "입고", "출고", "출하", "납품", "작업지시", "요청")
_AD_SUBJ = re.compile(r"[\(\[（]\s*(광고|AD)\s*[\)\]）]", re.I)
_UNSUB = ("수신거부", "수신 거부", "수신을 원치", "수신을 원하지", "구독 취소", "구독취소", "unsubscribe", "opt-out", "opt out")
# 이미 압축된 형식(다시 압축해도 거의 안 줄어듦)
_PACKED = re.compile(r"^(image/(jpeg|jpg|png|gif|webp|heic)|video/|audio/|application/(pdf|zip|x-zip|x-7z|x-rar|vnd\.rar|gzip|x-gzip|"
                     r"vnd\.openxmlformats|vnd\.oasis|vnd\.android|x-msdownload|octet-stream))", re.I)
ATT_SAMPLE_MAX = 400
ATT_SAMPLE_BYTES = 300 * 1024 * 1024
MONTH_SAMPLE = 2 * 1024 * 1024      # 달·묶음마다 앞 2MB 를 실제로 압축해 비율을 잼
MONTH_MEM_MAX = 64 * 1024 * 1024    # 모아 둔 표본이 이만큼 넘으면 가장 큰 것부터 먼저 압축해 비움(서버 메모리 보호)
CHUNK = 500


def _empty():
    return {"n": 0, "body": 0, "body_z": 0, "att_n": 0, "att_logical": 0, "att_shas": set()}


def _kind(r, robot_re, internal_fn):
    if int(r["is_blocked"] or 0):
        return "spam"
    addr = (r["from_email"] or "").lower()
    subj = r["subject"] or ""
    inner = (r["direction"] == "out") or internal_fn(addr)
    if inner:
        return "work" if any(w in subj for w in WORK_WORDS) else "internal"
    local = addr.split("@")[0] if "@" in addr else addr
    tail = (r["body_text"] or "")[-2500:].lower()
    if _AD_SUBJ.search(subj) or any(u in tail for u in _UNSUB) or (local and robot_re.match(local)):
        return "bulk"
    return "partner"


def _age(ts, cut6, cut12):
    t = ts or ""
    if t >= cut6:
        return "a6"
    if t >= cut12:
        return "a12"
    return "old"


def _dir_size(path):
    total = n = 0
    for root, _d, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
                n += 1
            except Exception:
                pass
    return total, n


def run(db_session, user_id, whole=False, prog=None):
    """재기 본체(오래 걸릴 수 있음 — 뒤에서 돌림). 반환 = 숫자만."""
    from . import mail_cleanup as _mc
    from datetime import datetime, timedelta
    t0 = time.time()
    now = datetime.now()
    cut6 = (now - timedelta(days=183)).strftime("%Y-%m-%d %H:%M:%S")
    cut12 = (now - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
    cells = {(a, k): _empty() for a, _ in AGES for k, _ in KINDS}
    months = {}            # (YYYY-MM, 묶음 종류) -> {"buf": 앞 2MB, "full": 전체 바이트, "ratio": 압축 비율(재고 나면)}
    mem = [0]

    def _fin(m):
        if m["ratio"] is None and m["buf"]:
            m["ratio"] = len(lzma.compress(bytes(m["buf"]), preset=6)) / float(len(m["buf"]))
            m["sampled"] = len(m["buf"])
            mem[0] -= len(m["buf"])
            m["buf"] = bytearray()
    hdr_bytes = 0
    att_rows = {}          # sha -> (size, mime) — 내 메일에 붙은 실제 파일
    with db_session() as c:
        mx = c.execute("SELECT COALESCE(MAX(id),0) FROM mail_messages WHERE user_id=?", (int(user_id),)).fetchone()[0]
        total_rows = c.execute("SELECT COUNT(*) FROM mail_messages WHERE user_id=?", (int(user_id),)).fetchone()[0]
    last = 0
    done = 0
    while last < mx:
        with db_session() as c:
            rows = c.execute(
                "SELECT id, direction, from_email, subject, body_text, body_html, received_at, COALESCE(is_blocked,0) AS is_blocked "
                "FROM mail_messages WHERE user_id=? AND id>? AND direction IN ('in','out') ORDER BY id LIMIT ?",
                (int(user_id), last, CHUNK)).fetchall()
            if not rows:
                break
            ids = [r["id"] for r in rows]
            q = ",".join("?" * len(ids))
            atts = {}
            for a in c.execute("SELECT mail_id, size, mime, sha256, path, data IS NOT NULL AS has_blob FROM mail_attachments "
                               "WHERE mail_id IN (" + q + ")", ids).fetchall():
                atts.setdefault(a["mail_id"], []).append(dict(a))
            try:
                hdr_bytes += c.execute("SELECT COALESCE(SUM(length(hdr)),0) FROM mail_raw_headers WHERE mail_id IN (" + q + ")", ids).fetchone()[0] or 0
            except Exception:
                pass
        for r in rows:
            last = r["id"]
            body = ((r["body_text"] or "") + "\x00" + (r["body_html"] or "")).encode("utf-8", "replace")
            a = _age(r["received_at"], cut6, cut12)
            k = _kind(r, _mc._RE_ROBOT, _mc.is_internal)
            cell = cells[(a, k)]
            cell["n"] += 1
            cell["body"] += len(body)
            cell["body_z"] += len(zlib.compress(body, 6))
            for at in atts.get(r["id"], []):
                cell["att_n"] += 1
                cell["att_logical"] += int(at["size"] or 0)
                if at["sha256"]:
                    cell["att_shas"].add(at["sha256"])
                    att_rows[at["sha256"]] = (int(at["size"] or 0), (at["mime"] or "").lower(), at["path"] or "")
            if a != "a6":
                grp = "bulk" if k in ("spam", "bulk", "work") else "keep"
                key = ((r["received_at"] or "")[:7], grp)
                m = months.get(key)
                if m is None:
                    m = months[key] = {"buf": bytearray(), "full": 0, "ratio": None, "sampled": 0}
                m["full"] += len(body)
                if m["ratio"] is None and len(m["buf"]) < MONTH_SAMPLE:
                    add = body[:MONTH_SAMPLE - len(m["buf"])]
                    m["buf"] += add
                    mem[0] += len(add)
                    if mem[0] > MONTH_MEM_MAX:
                        _fin(max(months.values(), key=lambda x: len(x["buf"])))
            done += 1
        if prog:
            prog(done, total_rows)
    # ② 월별 묶음 압축(실제로 lzma)
    m_raw = m_xz = m_sampled = 0
    for m in months.values():
        _fin(m)
        if m["ratio"] is None:
            continue
        m_sampled += m["sampled"]
        m_raw += m["full"]
        m_xz += int(m["full"] * m["ratio"])
    # ③ 첨부 — 압축이 되는 종류만 실제로 압축해 봄
    comp_cand = [(sha, sz, mime, p) for sha, (sz, mime, p) in att_rows.items() if not _PACKED.match(mime or "")]
    packed_bytes = sum(sz for sha, (sz, mime, p) in att_rows.items() if _PACKED.match(mime or ""))
    s_raw = s_z = s_n = 0
    for sha, sz, mime, p in sorted(comp_cand, key=lambda x: x[1]):
        if s_n >= ATT_SAMPLE_MAX or s_raw >= ATT_SAMPLE_BYTES:
            break
        try:
            with open(p, "rb") as f:
                data = f.read()
        except Exception:
            continue
        s_raw += len(data)
        s_z += len(lzma.compress(data, preset=6))
        s_n += 1
    comp_bytes = sum(x[1] for x in comp_cand)

    def _pub(cell):
        phys = sum(att_rows.get(s, (0,))[0] for s in cell["att_shas"])
        return {"n": cell["n"], "body": cell["body"], "body_z": cell["body_z"], "att_n": cell["att_n"],
                "att_logical": cell["att_logical"], "att_physical": phys}
    out = {"cells": {"%s|%s" % (a, k): _pub(cells[(a, k)]) for a, _ in AGES for k, _ in KINDS},
           "ages": [list(x) for x in AGES], "kinds": [list(x) for x in KINDS],
           "rows": done, "hdr_bytes": hdr_bytes,
           "month_bundle": {"raw": m_raw, "xz": m_xz, "sampled": m_sampled, "groups": len(months)},
           "att": {"unique_files": len(att_rows), "unique_bytes": sum(v[0] for v in att_rows.values()),
                   "packed_bytes": packed_bytes, "compressible_bytes": comp_bytes,
                   "sample_n": s_n, "sample_raw": s_raw, "sample_xz": s_z}}
    if whole:
        out["server"] = _whole(db_session)
    out["secs"] = round(time.time() - t0, 1)
    out["at"] = now.strftime("%Y-%m-%d %H:%M")
    return out


def _whole(db_session):
    """서버 전체(관리자) — DB 파일·첨부 폴더 크기 · 모든 사람 본문 중 같은 내용이 겹친 크기(숫자만)."""
    from .database import DB_PATH
    from .mail_store import _att_dir
    out = {}
    try:
        out["db_file"] = os.path.getsize(DB_PATH)
        for ext in ("-wal",):
            if os.path.exists(DB_PATH + ext):
                out["db_wal"] = os.path.getsize(DB_PATH + ext)
    except Exception:
        pass
    out["att_dir"], out["att_files"] = _dir_size(_att_dir())
    seen = {}
    total = dup = rows = 0
    users = set()
    last = 0
    while True:
        with db_session() as c:
            rs = c.execute("SELECT id, user_id, body_text, body_html FROM mail_messages WHERE id>? AND direction IN ('in','out') "
                           "ORDER BY id LIMIT ?", (last, CHUNK)).fetchall()
        if not rs:
            break
        for r in rs:
            last = r["id"]
            b = ((r["body_text"] or "") + "\x00" + (r["body_html"] or "")).encode("utf-8", "replace")
            if len(b) < 2:
                continue
            h = hashlib.sha1(b).digest()
            rows += 1
            total += len(b)
            users.add(r["user_id"])
            if h in seen:
                dup += len(b)
            else:
                seen[h] = 1
    out.update({"mail_rows": rows, "body_total": total, "body_dup": dup, "users": len(users)})
    return out


def _job_path(user_id):
    from .database import DB_PATH
    return os.path.join(os.path.dirname(DB_PATH), ".mail_storage_%d.json" % int(user_id))


def _job_write(user_id, d):
    import json
    p = _job_path(user_id)
    tmp = p + ".tmp%d" % os.getpid()
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, p)
    except Exception as e:
        print("[MAIL-STORAGE] 상태 파일 못 씀: %s" % str(e)[:120], flush=True)


def _job_read(user_id):
    import json
    try:
        with open(_job_path(user_id), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def start(db_session, user_id, whole=False):
    """뒤에서 재기 시작. 일꾼이 둘이라 진행 상황·결과는 데이터 폴더 파일에(어느 일꾼에 물어도 같은 답).
    이미 도는 중(1분 안에 소식 있음)이면 새로 시작하지 않음."""
    with _LOCK:
        cur = _job_read(user_id) or {}
        if cur.get("state") == "running" and time.time() - float(cur.get("beat") or 0) < 60:
            return cur
        j = {"state": "running", "done": 0, "total": 0, "beat": time.time()}
        _job_write(user_id, j)

    def prog(d, t):
        j.update(done=d, total=t, beat=time.time())
        _job_write(user_id, j)

    def work():
        try:
            res = run(db_session, user_id, whole, prog)
            _job_write(user_id, {"state": "done", "done": j["done"], "total": j["total"], "beat": time.time(), "result": res})
        except Exception as e:
            err = "%s: %s" % (type(e).__name__, str(e)[:200])
            _job_write(user_id, {"state": "error", "error": err, "beat": time.time()})
            print("[MAIL-STORAGE] 재기 실패 user=%s: %s" % (user_id, err), flush=True)
    threading.Thread(target=work, daemon=True).start()
    return j


def status(user_id):
    j = _job_read(user_id) or {"state": "none"}
    if j.get("state") == "running" and time.time() - float(j.get("beat") or 0) > 300:
        j = {"state": "error", "error": "재는 중에 멈췄습니다(서버 다시 시작 등) — 다시 눌러 주세요"}
    return j
