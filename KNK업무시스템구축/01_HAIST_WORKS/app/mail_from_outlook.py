# -*- coding: utf-8 -*-
"""아웃룩에서 보낸 사람 채우기 — 11-25 대표 「예전 아웃룩에 남아있는데 어떻게 전달하지?」

까닭: 보낸 사람 주소가 빈 대표 메일 243통(6~11월)은 하이웍스 원본(받은편지함 424통 · 11월만)에도, 본문 단서에도 없음.
      대표 PC 의 예전 아웃룩에 원본이 남아 있음 → 아웃룩에서 **4칸만**(Message-ID · 보낸 사람 주소 · 이름 · 받은 시각) 뽑은
      CSV(deploy/outlook_from_export.ps1) 를 관리자 화면에 올리면, Message-ID 로 정확히 맞춰 보낸 사람을 채운다.

· 맞추기 = 저장된 「같은 메일」 판정값(dedup_hash = Message-ID 해시 · mail_store._dedup_hash) — 대상은 mail_from_refill.targets 와 같은 조건(내 메일만)
· 채우기 = 되돌림 표 mail_from_refill_bak(묶음 outlook-…) · fd_key 비움(폴더 다시 나눔) · 원본 주소이므로 「🔎 추정」 표시(mail_from_guessed)는 지움
· 올린 파일은 디스크에 저장하지 않음(메모리에서만) · 돌려주는 값·로그 = 숫자만(주소·이름 안 찍음)
"""
import csv
import io
import time

MAX_BYTES = 20 * 1024 * 1024

# CSV 머리 이름(한·영 모두 받음)
_COL_MID = ("message_id", "message-id", "messageid", "메시지id", "메일id")
_COL_ADDR = ("from_email", "sender_email", "from", "보낸사람주소", "주소")
_COL_NAME = ("from_name", "sender_name", "name", "보낸사람이름", "이름")


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp949"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "replace")


def _norm_key(k) -> str:
    return (k or "").strip().strip("﻿").lower().replace(" ", "")


def parse_csv(raw: bytes) -> dict:
    """CSV → {"rows": 줄 수, "with_mid": Message-ID 있는 줄, "items": {dedup_hash: (이름, 주소)}}. 주소에 @ 없는 줄은 items 에 안 넣음."""
    from .mail_store import _dedup_hash
    txt = _decode(raw)
    rd = csv.DictReader(io.StringIO(txt))
    keys = {_norm_key(k): k for k in (rd.fieldnames or [])}

    def col(cands):
        for c in cands:
            if c in keys:
                return keys[c]
        return None
    kmid, kaddr, kname = col(_COL_MID), col(_COL_ADDR), col(_COL_NAME)
    rows = with_mid = 0
    items = {}
    if not kmid:
        return {"rows": 0, "with_mid": 0, "items": {}, "bad_header": True}
    for r in rd:
        rows += 1
        mid = (r.get(kmid) or "").strip().strip("<>").strip()
        if not mid:
            continue
        with_mid += 1
        ad = (r.get(kaddr) or "").strip().strip("<>").strip() if kaddr else ""
        nm = (r.get(kname) or "").strip() if kname else ""
        if "@" not in ad or len(ad) > 254 or any(ch in ad for ch in " \t\r\n,;"):
            continue
        h = _dedup_hash(mid, "", "", "")
        if h not in items:
            items[h] = (nm[:200], ad.lower())
    return {"rows": rows, "with_mid": with_mid, "items": items, "bad_header": False}


def run(c, user_id, raw: bytes, dry: bool = True) -> dict:
    """셈만(dry) 또는 채우기. 돌려주는 값 = 숫자만."""
    from . import mail_from_refill as R
    R.ensure(c)
    p = parse_csv(raw)
    t = R.targets(c, user_id)
    by_hash = t["by_hash"]
    hit = {by_hash[h]: v for h, v in p["items"].items() if h in by_hash}
    out = {"rows": p["rows"], "with_mid": p["with_mid"], "usable": len(p["items"]),
           "targets": len(by_hash) + t["nohash"], "matched": len(hit), "filled": 0,
           "bad_header": p.get("bad_header", False)}
    if not dry and hit:
        batch = "outlook-" + time.strftime("%Y%m%d-%H%M%S")
        n = 0
        for mid, (nm, ad) in hit.items():
            r = c.execute("SELECT from_email, from_name FROM mail_messages WHERE id=? AND user_id=? "
                          "AND (COALESCE(from_email,'')='' OR instr(from_email,'@')=0)", (int(mid), int(user_id))).fetchone()
            if not r:
                continue
            old_nm = (r["from_name"] or "").strip()
            old_ad = (r["from_email"] or "").strip()
            # 주소 칸에 이름이 들어 있던 메일 = 그 글자를 이름으로(아웃룩 이름이 비었을 때)
            new_nm = nm or old_nm or old_ad
            c.execute("INSERT INTO mail_from_refill_bak(batch, user_id, mail_id, old_from_email, old_from_name, new_from_email, new_from_name) "
                      "VALUES(?,?,?,?,?,?,?)", (batch, int(user_id), int(mid), r["from_email"], r["from_name"], ad, new_nm))
            c.execute("UPDATE mail_messages SET from_email=?, from_name=?, fd_key='' WHERE id=? AND user_id=?",
                      (ad, new_nm, int(mid), int(user_id)))
            try:   # 원본 주소 → 「🔎 추정」 표시 지움
                c.execute("DELETE FROM mail_from_guessed WHERE mail_id=?", (int(mid),))
            except Exception:
                pass
            n += 1
        out["filled"] = n
        out["batch"] = batch
    t2 = R.targets(c, user_id)
    out["left"] = len(t2["by_hash"]) + t2["nohash"]
    return out


def undo(c, user_id) -> int:
    """마지막 outlook- 묶음만 되돌림(그 뒤 다시 바뀐 메일은 그대로)."""
    from . import mail_from_refill as R
    R.ensure(c)
    r = c.execute("SELECT batch FROM mail_from_refill_bak WHERE user_id=? AND batch LIKE 'outlook-%' ORDER BY id DESC LIMIT 1",
                  (int(user_id),)).fetchone()
    if not r:
        return 0
    n = 0
    for b in c.execute("SELECT * FROM mail_from_refill_bak WHERE user_id=? AND batch=?", (int(user_id), r["batch"])).fetchall():
        n += c.execute("UPDATE mail_messages SET from_email=?, from_name=?, fd_key='' WHERE id=? AND user_id=? AND from_email=?",
                       (b["old_from_email"] or "", b["old_from_name"] or "", b["mail_id"], int(user_id), b["new_from_email"])).rowcount
    c.execute("DELETE FROM mail_from_refill_bak WHERE user_id=? AND batch=?", (int(user_id), r["batch"]))
    return n
