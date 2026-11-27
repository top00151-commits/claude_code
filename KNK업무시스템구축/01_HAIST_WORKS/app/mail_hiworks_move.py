# -*- coding: utf-8 -*-
"""하이웍스에서 옮겨 오기 — 11-27 대표 「최대한 쉽게 설명을 포함해서 만들어 · 직원들이 직접 내용 보고 쉽게 할 수 있도록 ·
자꾸 나한테 질문하게 하지 말고」

우리 메일은 하이웍스를 POP3 로 받는다 → 하이웍스 「받은 메일함」만 온다. 그래서
  · 하이웍스 「메일 자동분류」 규칙이 개인 메일함으로 바로 넣는 새 메일은 이음 메일에 안 온다
  · 하이웍스 개인 메일함에 든 옛 메일도 안 온다
이 화면 한 곳에서 직원이 혼자 끝낸다.
  ① 규칙 옮기기 — 하이웍스 자동분류 표를 복사해 붙여 넣으면 읽어서(parse_rules) 우리 규칙(보낸 사람 → 폴더)으로 바꿀 수 있는 것만
     미리 보기(preview_rules) → 사람이 체크하고 「확인한 규칙 저장」을 눌러야만 저장(save_rules) · ↺ 되돌리기(undo_rules)
  ② 하이웍스 규칙 지우기 — 안내만(화면에서 「지웠어요」 표시)
  ③ 옛 메일 올리기 — 하이웍스 「메일 백업」 파일(zip·eml·mbox · zip 안 zip 한 단계)을 조각으로 올림(begin/chunk) →
     파일 안의 메일함별 통수와 넣을 폴더 이름을 보여 줌(scan) → 사람이 폴더 이름을 확인하고 「넣기 시작」(start) →
     서버 뒤에서 한 통씩: 이미 있는 메일 = 같은 이름 폴더로 옮기기만(사람이 정한 자리·규칙이 다른 곳·지운 메일은 그대로) ·
     없는 메일 = 저장(AI·알림·자동 응답 없음 · 받은 때 = 원래 도착 시각) · 내 주소가 보낸 메일 = 보낸 메일함으로.
     멈추기·이어 하기(같은 파일을 다시 넣어도 두 번 안 들어감) · 끝나면 임시 파일 지움.
저장은 로그인한 사람 본인 메일함으로만. DB 를 잡은 채 파일을 오래 읽지 않는다(한 통 읽기 → 짧게 저장).
"""
from __future__ import annotations

import datetime as _dt
import email.utils as _eu
import json
import os
import re
import shutil
import threading
import time
import zipfile

# ─── 크기 한도 ─────────────────────────────────────────────────────
MAX_FILE = 4 * 1024 ** 3            # 파일 하나 최대 4GB(큰 메일함은 하이웍스에서 나눠 받기)
CHUNK_MAX = 16 * 1024 * 1024        # 조각 하나 최대(화면은 8MB 씩 보냄 — 중간 서버의 요청 한도 밑으로)
MAX_MSG_BYTES = 40 * 1024 * 1024    # 메일 한 통이 이보다 크면 넣지 않음(수만 알림)
MAX_RULE_TEXT = 2 * 1024 * 1024     # 붙여 넣은 글 최대
MAX_RULE_ROWS = 2000
KEEP_DAYS = 3                       # 다 못 넣은 임시 파일을 남겨 두는 날 수(이어 하기용) — 지나면 지움
STALE_MIN = 10
MAX_OPEN_UPLOADS = 30

# ─── ① 규칙 붙여넣기 해석 ───────────────────────────────────────────
_TARGETS = (
    ("from", ("보낸사람", "보낸사람주소", "보내는사람", "발신자", "발신인", "발신", "보낸이", "from", "sender")),
    ("to", ("받는사람", "받는사람주소", "수신자", "수신인", "수신", "받는이", "to", "받는사람/참조", "받는사람또는참조", "수신자/참조")),
    ("cc", ("참조", "cc", "참조자")),
    ("subject", ("제목", "메일제목", "subject")),
    ("body", ("본문", "내용", "메일본문", "body")),
    ("att", ("첨부파일", "첨부파일명", "첨부", "파일이름")),
    ("size", ("메일크기", "크기", "용량")),
)
_TARGET_NAME = {"from": "보낸 사람", "to": "받는 사람", "cc": "참조", "subject": "제목", "body": "본문",
                "att": "첨부파일", "size": "메일 크기"}
_CONDS = (   # 앞에서부터 맞춤(「포함하지 않음」을 「포함」보다 먼저)
    ("not", ("포함하지않음", "포함하지않는", "포함안함", "미포함", "불포함", "일치하지않음", "일치하지않는", "불일치", "같지않음", "다름",
             "notcontains", "doesnotcontain", "isnot")),
    ("eq", ("정확히일치", "완전일치", "일치함", "일치", "같음", "동일", "is", "equals")),
    ("has", ("을포함", "를포함", "포함함", "포함된", "포함", "contains")),
    ("start", ("으로시작", "로시작", "시작함", "시작", "startswith")),
    ("end", ("으로끝남", "로끝남", "끝남", "으로끝", "로끝", "끝", "endswith")),
)
_COND_NAME = {"eq": "일치", "has": "포함", "not": "포함하지 않음", "start": "시작", "end": "끝"}
_NOISE = {"분류대상", "분류조건", "조건내용", "이동할메일함", "이동메일함", "이동할편지함", "관리", "수정", "삭제", "수정삭제",
          "선택", "번호", "no", "순서", "순위", "사용", "사용여부", "사용중", "on", "off", "켜짐", "꺼짐", "□", "☐", "☑", "■", "✓", "v",
          "전체선택", "메일자동분류", "자동분류", "분류규칙", "규칙추가", "추가", "우선순위", "위로", "아래로", "▲", "▼", "↑", "↓"}
_NAV = {"처음", "이전", "다음", "마지막", "끝", "<", ">", "«", "»", "‹", "›", "<<", ">>", "...", "…", "◀", "▶", "first", "last", "prev", "next"}
_INBOX = {"inbox", "받은메일함", "받은편지함"}
_BAD_DEST = {"휴지통", "trash", "스팸메일함", "스팸편지함", "스팸", "spam", "junk", "정크메일", "삭제", "바로삭제", "영구삭제"}
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-']+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_RE_DOMAIN = re.compile(r"^@?((?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+[a-z]{2,})$")


def _nk(s) -> str:
    return re.sub(r"\s+", "", (s or "")).lower()


def _phrase_re(variants):
    alts = sorted({v for v in variants}, key=len, reverse=True)
    return "|".join(r"\s*".join(re.escape(ch) for ch in v) for v in alts)


_T_ALL = _phrase_re([v for _k, vs in _TARGETS for v in vs])
_C_ALL = _phrase_re([v for _k, vs in _CONDS for v in vs])
_RE_FULLROW = re.compile(r"^(?P<t>%s)\s*[:：]?\s+(?P<c>%s)\s+(?P<v>\S+)\s+(?P<f>.+?)(?:\s+수정)?(?:\s+삭제)?\s*$" % (_T_ALL, _C_ALL), re.I)
_RE_TC = re.compile(r"^(?P<t>%s)\s*[:：]?\s+(?P<c>%s)$" % (_T_ALL, _C_ALL), re.I)


def _target_of(tok):
    k = _nk(tok).strip(":：")
    for key, vs in _TARGETS:
        if k in {_nk(v) for v in vs}:
            return key
    return None


def _cond_of(tok):
    k = _nk(tok).strip(":：")
    if not k:
        return None
    for key, vs in _CONDS:
        if k in {_nk(v) for v in vs}:
            return key
    return None


def _is_noise(tok) -> bool:
    k = _nk(tok)
    return (not k) or k in _NOISE or bool(re.fullmatch(r"\d{1,4}", k)) or bool(re.fullmatch(r"[\-–—|·•.,:;~]+", k))


def _nav_line(line) -> bool:
    ws = [w for w in re.split(r"\s+", line.strip()) if w]
    if not ws:
        return True
    if re.match(r"^(총|전체)\s*[:：]?\s*\d", line.strip()):
        return True
    return all((w.lower() in _NAV) or re.fullmatch(r"\d{1,4}", w) for w in ws)


def _cells(line):
    """한 줄 → 칸들. 탭·두 칸 이상 빈칸으로 나뉜 줄은 그대로 · 한 칸 빈칸뿐이면 「대상 조건 내용 메일함」 모양으로 읽어 봄."""
    line = line.strip().strip("​")
    if "\t" in line or re.search(r"\s{2,}", line):
        raw = [x.strip() for x in re.split(r"\t+|\s{2,}", line)]
    else:
        raw = [line]
    out = []
    for cell in raw:
        if not cell:
            continue
        m = _RE_FULLROW.match(cell)
        if m:
            out += [m.group("t"), m.group("c"), m.group("v"), m.group("f")]
            continue
        m = _RE_TC.match(cell)
        if m:
            out += [m.group("t"), m.group("c")]
            continue
        out.append(cell)
    return out


def _dest_path(s) -> list:
    """이동할 메일함 글 → 경로 조각. 「받은메일함 > 거래처 > 삼성」 → [거래처, 삼성]."""
    parts = [p.strip() for p in re.split(r"\s*(?:>|›|»|/|\\|→)\s*", (s or "").strip()) if p.strip()]
    parts = [re.sub(r"\s*\(\s*\d+\s*\)\s*$", "", p).strip() for p in parts]   # 「주간업무 (724)」 같은 숫자 꼬리
    parts = [p for p in parts if p]
    while parts and _nk(parts[0]) in _INBOX:
        parts = parts[1:]
    return parts[:3]


def parse_rules(text):
    """붙여 넣은 글 → (규칙 줄들, 건너뛴 글). 규칙 줄 = {target, cond, value, dest(경로), raw_t, raw_c}.
    같은 줄(대상·조건·내용·메일함이 모두 같음)은 한 번만."""
    text = (text or "")[:MAX_RULE_TEXT].replace("\r", "\n").replace(" ", " ").replace("　", " ")
    toks = []
    for line in text.split("\n"):
        if not line.strip() or _nav_line(line):
            continue
        for cell in _cells(line):
            if not _is_noise(cell):
                toks.append(cell)
    rows, left, seen = [], [], set()
    i = 0
    while i < len(toks):
        t = _target_of(toks[i])
        if t and i + 3 < len(toks):
            c = _cond_of(toks[i + 1])
            v, f = toks[i + 2], toks[i + 3]
            if c and not _target_of(v) and not _cond_of(v) and not _target_of(f) and not _cond_of(f):
                key = (t, c, v.strip().lower(), "/".join(_nk(p) for p in _dest_path(f)))
                if key not in seen:
                    seen.add(key)
                    rows.append({"target": t, "cond": c, "value": v.strip(), "dest": _dest_path(f), "dest_raw": f.strip(),
                                 "raw_t": toks[i].strip(), "raw_c": toks[i + 1].strip()})
                i += 4
                continue
            if not c and toks[i + 1].strip():
                # 조건 칸을 모르는 글 — 「옮길 수 없음(조건 모름)」으로 보여 줌
                c2 = toks[i + 1]
                if not _target_of(v) and not _target_of(f):
                    key = (t, "?" + _nk(c2), v.strip().lower(), "/".join(_nk(p) for p in _dest_path(f)))
                    if key not in seen:
                        seen.add(key)
                        rows.append({"target": t, "cond": "?", "value": v.strip(), "dest": _dest_path(f), "dest_raw": f.strip(),
                                     "raw_t": toks[i].strip(), "raw_c": c2.strip()})
                    i += 4
                    continue
        left.append(toks[i])
        i += 1
        if len(rows) >= MAX_RULE_ROWS:
            break
    return rows, left


def convert(r):
    """해석한 줄 → (kind, pattern, 이유). 옮길 수 없으면 kind=None · 이유에 쉬운 말."""
    t, c, v = r["target"], r["cond"], (r.get("value") or "").strip().strip("'\"<>[]()").strip()
    dest = r.get("dest") or []
    if not dest:
        if _nk(r.get("dest_raw")) in _INBOX:
            return None, "", "받은 메일함에 그대로 두는 규칙 — 옮길 필요 없음"
        return None, "", "옮길 메일함 이름이 없음"
    if _nk(dest[-1]) in _BAD_DEST or _nk(dest[0]) in _BAD_DEST:
        return None, "", "휴지통·스팸으로 보내는 규칙은 옮기지 않음 — 이음 메일의 「스팸·다시 안 받기」를 쓰세요"
    if t != "from":
        why = {"subject": "제목으로 나누는 규칙은 이음 메일에서 쓰지 않음(회신 메일까지 옮겨져서)",
               "to": "받는 사람으로 나누는 규칙은 이음 메일에 없음", "cc": "참조로 나누는 규칙은 이음 메일에 없음",
               "body": "본문 글자로 나누는 규칙은 이음 메일에 없음", "att": "첨부파일로 나누는 규칙은 이음 메일에 없음",
               "size": "메일 크기로 나누는 규칙은 이음 메일에 없음"}.get(t, "이음 메일에 없는 종류")
        return None, "", why
    if c == "?":
        return None, "", "조건 「%s」을(를) 알아보지 못함" % (r.get("raw_c") or "")[:20]
    if c == "not":
        return None, "", "「포함하지 않음」 규칙은 이음 메일에 없음"
    low = v.lower()
    m = _RE_EMAIL.search(low)
    full = m.group(0) if (m and (c in ("eq", "has", "start", "end"))) else ""
    if full and (c == "eq" or len(full) >= len(low) - 2):
        return "email", full, ""
    md = _RE_DOMAIN.match(low)
    if md and c in ("eq", "has", "end"):
        return "domain", md.group(1), ""
    if c == "eq":
        return None, "", "보낸 사람 이름으로 나누는 규칙은 옮길 수 없음(주소로만 나눌 수 있음)"
    return None, "", "주소 일부 글자로 나누는 규칙은 옮길 수 없음(주소 전체나 회사 주소 @회사.com 만 가능)"


# ─── 폴더 찾기·만들기(①·③ 같은 방식) ──────────────────────────────
def find_folder(c, uid, parts):
    """경로 → 있는 폴더 키(f<id> 또는 부서 t<id>) 또는 ''. 맨 위부터 이름대로 · 없으면 이름 하나짜리는 같은 이름 폴더가 하나뿐일 때 그것."""
    from . import mail_folders as MF
    from .mail_import_outlook import norm_name, name_map
    MF.ensure(c)
    parts = [p for p in (parts or []) if p][:3]
    if not parts:
        return ""
    parent, key = None, ""
    for depth, nm in enumerate(parts):
        rows = c.execute("SELECT id, name, kind FROM mail_folders WHERE user_id=? AND "
                         + ("parent_id=?" if parent else "parent_id IS NULL"), ((uid, parent) if parent else (uid,))).fetchall()
        hit = [r for r in rows if norm_name(r["name"]) == norm_name(nm)]
        if not hit:
            key = ""
            break
        if depth == 0 and hit[0]["kind"] == "staff" and len(parts) > 1:
            key = ""
            break
        parent, key = hit[0]["id"], "f%d" % hit[0]["id"]
    if key:
        return key
    ks = name_map(c, uid).get(norm_name(parts[-1]), [])
    return ks[0] if len(ks) == 1 else ""


def folder_label(c, uid, key):
    from . import mail_folders as MF
    if not key:
        return ""
    if key.startswith("f") and key[1:].isdigit():
        names, cur = [], int(key[1:])
        for _ in range(4):
            r = c.execute("SELECT name, parent_id FROM mail_folders WHERE id=? AND user_id=?", (cur, uid)).fetchone()
            if not r:
                break
            names.insert(0, r["name"])
            if not r["parent_id"]:
                break
            cur = r["parent_id"]
        return " › ".join(names)
    if key.startswith("t"):
        for t in MF.teams(c):
            if "t%d" % t["id"] == key:
                return MF.folder_team_label(t)
    return ""


def get_or_make_folder(c, uid, parts, made=None):
    """있으면 그 폴더 · 없으면 맨 위부터 만듦(만든 폴더 번호는 made 에). 반환 키 또는 ''."""
    from . import mail_folders as MF
    from .mail_import_outlook import norm_name
    key = find_folder(c, uid, parts)
    if key:
        return key
    parts = [p for p in (parts or []) if p][:3]
    parent, key = None, ""
    for nm in parts:
        rows = c.execute("SELECT id, name, kind FROM mail_folders WHERE user_id=? AND "
                         + ("parent_id=?" if parent else "parent_id IS NULL"), ((uid, parent) if parent else (uid,))).fetchall()
        hit = [r for r in rows if norm_name(r["name"]) == norm_name(nm) and not (not parent and r["kind"] == "staff")]
        if hit:
            fid = hit[0]["id"]
        else:
            fid = MF.add_folder(c, uid, nm[:60], parent, "")
            if not fid:
                break
            if made is not None:
                made.append(fid)
        parent, key = fid, "f%d" % fid
    return key


# ─── ① 미리 보기 · 저장 · 되돌리기 ─────────────────────────────────
def _more_count(c, uid, kind, pat):
    return int(c.execute(
        "SELECT COUNT(*) FROM mail_messages WHERE user_id=? AND direction='in' AND is_deleted=0 "
        "AND COALESCE(is_blocked,0)=0 AND COALESCE(fd_pin,'')='' AND " +
        ("lower(from_email)=?" if kind == "email" else "lower(from_email) LIKE ?"),
        (uid, pat if kind == "email" else "%@" + pat)).fetchone()[0] or 0)


def preview_rules(c, uid, text) -> dict:
    """붙여 넣은 글 → 화면 줄들(저장 안 함). 줄 = {id, who, cond, value, dest, folder, folder_new, ok, why, status, other_folder,
    more, checked}. status: new(새로) · have(이미 있음) · other(다른 폴더로 가는 규칙 있음) · dup(위 줄과 같은 보낸 사람) · no(옮길 수 없음)."""
    from . import mail_folders as MF
    MF.ensure(c)
    rows, left = parse_rules(text)
    out, used = [], set()
    for i, r in enumerate(rows):
        kind, pat, why = convert(r)
        d = {"n": i + 1, "who": _TARGET_NAME.get(r["target"], r["raw_t"]), "cond": _COND_NAME.get(r["cond"], r.get("raw_c") or ""),
             "value": r["value"][:200], "dest": " › ".join(r["dest"]) or r.get("dest_raw", "")[:100],
             "ok": bool(kind), "why": why, "kind": kind or "", "pattern": pat, "folder": "", "folder_new": False,
             "status": "no", "other_folder": "", "more": 0, "checked": False}
        d["id"] = "%s|%s|%s" % (kind or "x", pat or _nk(r["value"]), "/".join(_nk(p) for p in r["dest"]))
        if kind:
            key = find_folder(c, uid, r["dest"])
            d["folder"] = folder_label(c, uid, key) if key else " › ".join(r["dest"])
            d["folder_new"] = not key
            tg = [h["target"] for h in c.execute("SELECT target FROM mail_move_rules WHERE user_id=? AND kind=? AND pattern=? "
                                                  "ORDER BY id DESC", (uid, kind, pat)).fetchall()]
            if (kind, pat) in used:
                d["status"] = "dup"
            elif key and key in tg:
                d["status"] = "have"
            elif tg:
                d["status"] = "other"
                t0 = tg[0]
                d["other_folder"] = folder_label(c, uid, t0) or ("일반" if t0 == "gen" else "다른 곳")
            else:
                d["status"] = "new"
            used.add((kind, pat))
            d["more"] = _more_count(c, uid, kind, pat)
            d["checked"] = d["status"] == "new"
        out.append(d)
    n_ok = len([x for x in out if x["ok"]])
    return {"ok": True, "rows": out, "n_rows": len(out), "n_ok": n_ok, "n_no": len(out) - n_ok,
            "left": [x[:80] for x in left[:200]], "n_left": len(left)}


def save_rules(c, uid, text, picked, past) -> dict:
    """체크한 줄만 저장. 화면이 보낸 번호는 지금 다시 읽은 미리 보기에 있는 것만 받음.
    past=True = 지난 메일도 이 규칙대로(언제부터 = 처음부터) · False = 지금부터 오는 메일만."""
    from . import mail_folders as MF
    pv = preview_rules(c, uid, text)
    by = {r["id"]: r for r in pv["rows"]}
    rows, _left = parse_rules(text)
    raw_by = {}
    for r in rows:
        kind, pat, _w = convert(r)
        if kind:
            raw_by.setdefault("%s|%s|%s" % (kind, pat, "/".join(_nk(p) for p in r["dest"])), r)
    since = "" if past else c.execute("SELECT datetime('now','localtime')").fetchone()[0]
    undo = {"add": [], "del": [], "pins": [], "mkfolder": []}
    saved, have, skip, dup = 0, 0, 0, 0
    done_pat = set()
    for pid in picked or []:
        x = by.get(pid)
        r = raw_by.get(pid)
        if not x or not x["ok"] or not r:
            skip += 1
            continue
        if x["status"] == "have":
            have += 1
            continue
        if (x["kind"], x["pattern"]) in done_pat:
            dup += 1
            continue
        key = get_or_make_folder(c, uid, r["dest"], undo["mkfolder"])
        if not key:
            skip += 1
            continue
        MF._put_rule(c, uid, x["kind"], x["pattern"], key, since, undo)
        done_pat.add((x["kind"], x["pattern"]))
        saved += 1
    batch = ""
    if saved:
        batch = "hwm%d" % int(time.time() * 1000)
        MF._save_undo(c, uid, undo, batch)
        MF._set_flag(c, uid, "hwm_rules", json.dumps({"at": c.execute("SELECT datetime('now','localtime')").fetchone()[0],
                                                    "n": saved, "batch": batch, "made": len(undo["mkfolder"]),
                                                    "past": bool(past)}, ensure_ascii=False))
        MF._CACHE.pop(uid, None)
    return {"ok": True, "saved": saved, "have": have, "skipped": skip, "dup": dup, "made": len(undo["mkfolder"]), "batch": batch}


def rules_state(c, uid) -> dict:
    """마지막 저장 정보 + 지금 ↺ 되돌리기가 되는지(그 뒤 다른 옮기기를 했으면 안 됨)."""
    from . import mail_folders as MF
    MF.ensure(c)
    try:
        st = json.loads(MF._flag(c, uid, "hwm_rules") or "{}")
    except Exception:
        st = {}
    try:
        u = json.loads(MF._flag(c, uid, "move_undo") or "{}")
    except Exception:
        u = {}
    st["can_undo"] = bool(st.get("batch")) and u.get("batch") == st.get("batch") and not st.get("undone")
    return st


def undo_rules(c, uid) -> dict:
    from . import mail_folders as MF
    st = rules_state(c, uid)
    if not st.get("can_undo"):
        return {"ok": False, "message": "되돌릴 수 없습니다 — 그 뒤에 다른 옮기기를 했거나 이미 되돌렸습니다. "
                                        "「폴더 관리」 화면의 규칙 목록에서 하나씩 지울 수 있습니다."}
    u = json.loads(MF._flag(c, uid, "move_undo") or "{}")
    keep = []
    for fid in list(u.get("mkfolder") or []):
        # 그사이 ③에서 메일을 넣은 폴더는 남김(메일이 자동 분류로 흩어지지 않게)
        if c.execute("SELECT 1 FROM mail_messages WHERE user_id=? AND fd_pin=? LIMIT 1", (uid, "f%d" % int(fid))).fetchone():
            keep.append(fid)
    if keep:
        u["mkfolder"] = [f for f in u["mkfolder"] if f not in keep]
        MF._set_flag(c, uid, "move_undo", json.dumps(u, ensure_ascii=False))
    n = MF.move_undo(c, uid)
    st.update(undone=True)
    st.pop("can_undo", None)
    MF._set_flag(c, uid, "hwm_rules", json.dumps(st, ensure_ascii=False))
    return {"ok": True, "n": n, "kept_folders": len(keep)}


# ─── ③ 파일 올리기 ────────────────────────────────────────────────
_RUNNING = {}
_RUN_LOCK = threading.Lock()
_COUNTS = ("total", "done", "saved", "moved", "already", "kept", "other", "sent", "failed", "big")


def ensure(c):
    try:
        from .mail_store import _ensure_security_cols
        _ensure_security_cols(c)
    except Exception:
        pass
    from . import mail_hiworks_folders as MHW
    MHW.ensure(c)   # 규칙 후보(mail_hw_items)를 같이 씀
    c.execute("""CREATE TABLE IF NOT EXISTS mail_hwm_files(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT DEFAULT '',
        size INTEGER DEFAULT 0,
        received INTEGER DEFAULT 0,
        tmp TEXT DEFAULT '',
        state TEXT DEFAULT 'uploading',
        groups TEXT DEFAULT '[]',
        plan TEXT DEFAULT '{}',
        bad TEXT DEFAULT '[]',
        pos INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0, done INTEGER DEFAULT 0, saved INTEGER DEFAULT 0, moved INTEGER DEFAULT 0,
        already INTEGER DEFAULT 0, kept INTEGER DEFAULT 0, other INTEGER DEFAULT 0, sent INTEGER DEFAULT 0,
        failed INTEGER DEFAULT 0, big INTEGER DEFAULT 0,
        cur TEXT DEFAULT '', msg TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        last_at TEXT DEFAULT (datetime('now','localtime')))""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_mailhwm_user ON mail_hwm_files(user_id, id)")


def tmp_root():
    from .database import DB_PATH
    return os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "mail_hwm_tmp")


def _tmp_path(uid, fid):
    d = os.path.join(tmp_root(), str(int(uid)))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "%d.part" % int(fid))


def _rm_tmp(path):
    if not path:
        return
    d = os.path.dirname(path)
    base = os.path.basename(path)
    try:
        for fn in os.listdir(d):
            if fn == base or fn.startswith(base + "."):
                try:
                    os.remove(os.path.join(d, fn))
                except Exception:
                    pass
    except Exception:
        pass


def _row(c, uid, fid):
    r = c.execute("SELECT * FROM mail_hwm_files WHERE id=? AND user_id=?", (int(fid), uid)).fetchone()
    return dict(r) if r else None


def cleanup_old(c, uid=None):
    """이어 하기용으로 남긴 임시 파일 — KEEP_DAYS 가 지나면 지움(메일은 그대로)."""
    ensure(c)
    q = ("SELECT id, user_id, tmp FROM mail_hwm_files WHERE state IN ('uploading','uploaded','scanned','stopped','failed') "
         "AND last_at < datetime('now','localtime', ?)")
    args = ["-%d days" % KEEP_DAYS]
    if uid:
        q += " AND user_id=?"
        args.append(uid)
    n = 0
    for r in c.execute(q, args).fetchall():
        if r["user_id"] in _RUNNING:
            continue
        _rm_tmp(r["tmp"])
        c.execute("UPDATE mail_hwm_files SET state='expired', tmp='', msg=? WHERE id=?",
                  ("%d일이 지나 올린 파일을 지웠습니다 — 필요하면 다시 올려 주세요(이미 넣은 메일은 그대로)" % KEEP_DAYS, r["id"]))
        n += 1
    return n


def begin(c, uid, name, size) -> dict:
    """올리기 시작 — 같은 이름·크기로 올리다 만 파일이 있으면 그 자리부터(이어 올리기)."""
    from .mail_import_outlook import disk_state, DISK_MIN_FREE
    ensure(c)
    name = os.path.basename((name or "").replace("\\", "/")).strip()[:200] or "하이웍스 백업"
    try:
        size = int(size)
    except Exception:
        size = -1
    if size <= 0:
        return {"ok": False, "message": "빈 파일입니다. 하이웍스에서 다시 받아 주세요."}
    if size > MAX_FILE:
        return {"ok": False, "message": "파일이 너무 큽니다(최대 %dGB). 하이웍스 「메일 백업」에서 메일함을 하나씩 나눠 받아 주세요." % (MAX_FILE // 1024 ** 3)}
    low = name.lower()
    if low.endswith((".msg", ".pst", ".ost")):
        return {"ok": False, "message": "아웃룩 파일(.msg·.pst)은 여기서 읽지 못합니다 — 「아웃룩 옛 메일 가져오기」를 써 주세요."}
    if low.endswith((".xls", ".xlsx", ".csv", ".pdf", ".hwp", ".doc", ".docx", ".jpg", ".png", ".exe")):
        return {"ok": False, "message": "메일 백업 파일이 아닙니다. 하이웍스 「메일 백업」에서 받은 파일(.zip · .eml · .mbox)을 올려 주세요."}
    r = c.execute("SELECT * FROM mail_hwm_files WHERE user_id=? AND name=? AND size=? AND state='uploading' ORDER BY id DESC LIMIT 1",
                  (uid, name, size)).fetchone()
    if r and r["tmp"] and os.path.isfile(r["tmp"]):
        got = os.path.getsize(r["tmp"])
        if got != r["received"]:
            c.execute("UPDATE mail_hwm_files SET received=? WHERE id=?", (got, r["id"]))
        return {"ok": True, "id": r["id"], "received": got, "resumed": True}
    d = disk_state()
    if (not d.get("ok", True)) or (d.get("free") and d["free"] < size * 3 + DISK_MIN_FREE):
        return {"ok": False, "message": "서버 남은 공간이 모자랍니다. 빅터(관리팀)에게 알려 주세요."}
    if c.execute("SELECT COUNT(*) FROM mail_hwm_files WHERE user_id=? AND state='uploading'", (uid,)).fetchone()[0] >= MAX_OPEN_UPLOADS:
        return {"ok": False, "message": "올리다 만 파일이 너무 많습니다. 화면을 새로 고치고 하나씩 올려 주세요."}
    same = c.execute("SELECT id FROM mail_hwm_files WHERE user_id=? AND name=? AND size=? AND state='done' ORDER BY id DESC LIMIT 1",
                     (uid, name, size)).fetchone()
    fid = c.execute("INSERT INTO mail_hwm_files(user_id, name, size) VALUES(?,?,?)", (uid, name, size)).lastrowid
    p = _tmp_path(uid, fid)
    open(p, "wb").close()
    c.execute("UPDATE mail_hwm_files SET tmp=? WHERE id=?", (p, fid))
    return {"ok": True, "id": fid, "received": 0, "resumed": False, "same_done": bool(same)}


def chunk_target(c, uid, fid, off):
    """조각 받기 전 확인 → (경로, 지금까지 받은 크기, 전체 크기, 안내). 위치가 다르면 받은 크기만 돌려줌(화면이 거기서 다시)."""
    ensure(c)
    r = _row(c, uid, fid)
    if not r or r["state"] != "uploading" or not r["tmp"]:
        return None, 0, 0, "올리기를 다시 시작해 주세요(파일을 다시 골라 주세요)."
    got = os.path.getsize(r["tmp"]) if os.path.isfile(r["tmp"]) else -1
    if got < 0:
        return None, 0, 0, "올리던 파일이 서버에 없습니다. 파일을 다시 골라 주세요."
    if int(off) != got:
        return None, got, r["size"], "where"
    return r["tmp"], got, r["size"], ""


def chunk_done(c, uid, fid, got):
    c.execute("UPDATE mail_hwm_files SET received=?, last_at=datetime('now','localtime') WHERE id=? AND user_id=?", (got, fid, uid))
    r = _row(c, uid, fid)
    if r and got >= r["size"]:
        c.execute("UPDATE mail_hwm_files SET state='uploaded' WHERE id=?", (fid,))
        return True
    return False


# ─── 파일 안 읽기 ─────────────────────────────────────────────────
_RE_MBOX_SEP = re.compile(rb"^From \S+.*\d{1,2}:\d{2}")
_RE_HDR = re.compile(rb"^[!-9;-~]{1,60}:[ \t]")
_RE_HDR_ANY = re.compile(rb"(?im)^(received|return-path|from|subject|date|message-id|mime-version|delivered-to|to|content-type)[ \t]*:")
_SKIP_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}


def _zname(info):
    """zip 안 이름 — 윈도에서 만든 한글 이름(cp949)도 바르게."""
    n = info.filename
    if not (info.flag_bits & 0x800):
        try:
            b = n.encode("cp437")
            for enc in ("utf-8", "cp949"):
                try:
                    return b.decode(enc)
                except Exception:
                    continue
        except Exception:
            pass
    return n


def sniff(head: bytes) -> str:
    """앞 몇 KB → 'mbox' | 'eml' | 'zip' | ''."""
    h = (head or b"").lstrip(b"\xef\xbb\xbf")
    if h[:4] == b"PK\x03\x04":
        return "zip"
    if h.startswith(b"From "):
        return "mbox"
    first = h.split(b"\n", 1)[0]
    if _RE_HDR.match(first) and _RE_HDR_ANY.search(h[:8192]):
        return "eml"
    return ""


def _iter_mbox(fobj, limit=MAX_MSG_BYTES):
    """mbox 를 한 통씩 → bytes 또는 None(너무 큼). 「>From 」 앞 > 하나는 뗌."""
    buf, size, big, started, prev_blank = [], 0, False, False, True
    for line in fobj:
        if line.startswith(b"From ") and (prev_blank or _RE_MBOX_SEP.match(line) or not started):
            if started:
                yield None if big else b"".join(buf)
            buf, size, big, started = [], 0, False, True
            prev_blank = False
            continue
        if not started:
            prev_blank = not line.strip()
            continue
        if line.startswith(b">") and re.match(rb"^>+From ", line):
            line = line[1:]
        if not big:
            size += len(line)
            if size > limit:
                big, buf = True, []
            else:
                buf.append(line)
        prev_blank = not line.strip()
    if started:
        yield None if big else b"".join(buf)


def _count_mbox(fobj):
    n, prev_blank, started = 0, True, False
    for line in fobj:
        if line.startswith(b"From ") and (prev_blank or _RE_MBOX_SEP.match(line) or not started):
            n += 1
            started = True
        prev_blank = not line.strip()
    return n


def _base(name):
    b = os.path.basename(name.rstrip("/"))
    return re.sub(r"\.(zip|eml|mbox|mbx|mbs|txt|msg|emlx)$", "", b, flags=re.I)


def entries(path, name):
    """올린 파일 → [(gid, kind, opener, size, 표시 이름)] 정해진 순서 · 읽을 수 없는 것은 bad 로.
    kind: 'eml'(한 통) | 'mbox'(여러 통). opener() → 읽기 파일. gid = 메일함 경로(zip 안 폴더 / mbox 이름)."""
    with open(path, "rb") as f:
        head = f.read(16384)
    k = sniff(head)
    if k == "zip" or zipfile.is_zipfile(path):
        return _zip_entries(path, "", 0)
    if k == "mbox":
        return [("", "mbox", lambda: open(path, "rb"), os.path.getsize(path), name)], []
    if k == "eml" or name.lower().endswith(".eml"):
        return [("", "eml", lambda: open(path, "rb"), os.path.getsize(path), name)], []
    return [], [name]


def _zip_entries(path, prefix, depth):
    out, bad = [], []
    try:
        zf = zipfile.ZipFile(path)
    except Exception:
        return [], [prefix or os.path.basename(path)]
    infos = sorted(zf.infolist(), key=lambda i: _zname(i))
    for idx, info in enumerate(infos):
        if info.is_dir():
            continue
        nm = _zname(info).replace("\\", "/")
        if nm.startswith("__MACOSX/") or os.path.basename(nm).lower() in _SKIP_NAMES or os.path.basename(nm).startswith("._"):
            continue
        full = (prefix + "/" + nm) if prefix else nm
        d = os.path.dirname(full)
        low = nm.lower()
        try:
            with zf.open(info) as fz:
                head = fz.read(16384)
        except Exception:
            bad.append(full)
            continue
        k = sniff(head)
        if k == "zip" or low.endswith(".zip"):
            if depth >= 1:
                bad.append(full + " (zip 안 zip 안 zip)")
                continue
            sub = "%s.n%d" % (path, idx)
            try:
                if not os.path.isfile(sub):
                    with zf.open(info) as src, open(sub + ".w", "wb") as dst:
                        shutil.copyfileobj(src, dst, 1024 * 1024)
                    os.replace(sub + ".w", sub)
            except Exception:
                bad.append(full)
                continue
            o2, b2 = _zip_entries(sub, (d + "/" if d else "") + _base(nm), depth + 1)
            out += o2
            bad += b2
            continue
        if k == "mbox" or (not k and low.endswith((".mbox", ".mbx", ".mbs"))):
            gid = (d + "/" if d else "") + _base(nm)
            out.append((gid, "mbox", (lambda p=path, i=info: _zopen(p, i)), info.file_size, full))
            continue
        if k == "eml" or low.endswith(".eml"):
            out.append((d, "eml", (lambda p=path, i=info: _zopen(p, i)), info.file_size, full))
            continue
        bad.append(full)
    zf.close()
    return out, bad


class _ZOpen:
    """zip 안 파일을 열어 두는 동안 zip 도 열어 둠(닫을 때 같이)."""

    def __init__(self, path, info):
        self.zf = zipfile.ZipFile(path)
        self.f = self.zf.open(info)

    def __iter__(self):
        return iter(self.f)

    def read(self, n=-1):
        return self.f.read(n)

    def close(self):
        try:
            self.f.close()
        finally:
            self.zf.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _zopen(path, info):
    return _ZOpen(path, info)


def iter_mail(ents, skip_gids=()):
    """[(gid, raw 또는 None(너무 큼) 또는 b''(못 읽음))] — 정해진 순서로 한 통씩."""
    for gid, kind, opener, size, _nm in ents:
        if gid in skip_gids:
            continue
        if kind == "eml":
            if size > MAX_MSG_BYTES:
                yield gid, None
                continue
            try:
                with opener() as f:
                    yield gid, f.read(MAX_MSG_BYTES + 1)
            except Exception:
                yield gid, b""
            continue
        try:
            with opener() as f:
                for raw in _iter_mbox(f):
                    yield gid, raw
        except Exception:
            yield gid, b""


# ─── 폴더 이름 정하기 ──────────────────────────────────────────────
_RE_DATEISH = re.compile(r"(19|20)\d{2}[-_.년 ]?\d{1,2}[-_.월 ]?\d{1,2}일?|\d{6,}|\d{1,2}[:_]\d{2}([:_]\d{2})?")
_RE_WORDS = re.compile(r"메일\s*백업|백업\s*파일|백업|backup|mailbox|mail_?export|export|hiworks|하이웍스|다운로드|download", re.I)
_SYS_NOTE = {"보낸메일함": "sent", "보낸편지함": "sent", "sent": "sent", "sentitems": "sent", "sentmessages": "sent",
             "휴지통": "trash", "trash": "trash", "deleteditems": "trash",
             "스팸메일함": "spam", "스팸편지함": "spam", "스팸": "spam", "spam": "spam", "junk": "spam",
             "임시보관함": "draft", "drafts": "draft", "draft": "draft", "예약메일함": "draft"}


def clean_name(s) -> str:
    s = _base(s or "")
    s = _RE_EMAIL.sub(" ", s)
    s = _RE_WORDS.sub(" ", s)
    s = _RE_DATEISH.sub(" ", s)
    s = re.sub(r"\(\s*\d*\s*\)|\[\s*\]", " ", s)
    s = re.sub(r"[\s_]+", " ", s).strip(" -_.()[]~")
    return s[:60]


def _norm_parts(gid):
    ps = [p for p in (gid or "").split("/") if p.strip()]
    out = []
    for p in ps:
        if "@" in p and _RE_EMAIL.search(p) and len(clean_name(p)) < 2:
            continue
        if _nk(p) in _INBOX:
            out = []   # 받은메일함 앞(계정 이름 등)은 버리고 그 아래부터
            continue
        cp = clean_name(p)
        if cp:
            out.append(cp)
    return out


def suggest(groups, file_name):
    """메일함 경로들 → {gid: (폴더 경로 조각들, 안내 종류)}. 모두에 똑같이 붙은 앞부분(백업 폴더 이름 등)은 뗌."""
    parts = {g: _norm_parts(g) for g in groups}
    multi = [p for p in parts.values() if p]
    if len(multi) > 1:
        pre = 0
        while all(len(p) > pre + 1 for p in multi) and len({p[pre] for p in multi}) == 1:
            pre += 1
        parts = {g: (p[pre:] if len(p) > pre else p) for g, p in parts.items()}
    fallback = clean_name(file_name) or "하이웍스 옛 메일"
    out = {}
    for g in groups:
        p = parts[g]
        raw_last = _nk((g or "").split("/")[-1]) if g else ""
        note = _SYS_NOTE.get(_nk(p[-1]) if p else "") or _SYS_NOTE.get(raw_last) or ""
        if not p and g and raw_last in _INBOX:
            out[g] = ([], "inbox")
            continue
        out[g] = ((p or [fallback])[:3], note)
    return out


def scan(c_session, uid, fid) -> dict:
    """올린 파일 안을 보고 메일함별 통수·넣을 폴더 이름 후보를 적어 둠(파일 읽기는 DB 밖)."""
    with c_session() as c:
        ensure(c)
        r = _row(c, uid, fid)
    if not r:
        return {"ok": False, "message": "파일을 찾지 못했습니다."}
    if r["state"] not in ("uploaded", "scanned", "stopped"):
        return {"ok": False, "message": "아직 다 올라가지 않았습니다."}
    if not r["tmp"] or not os.path.isfile(r["tmp"]):
        return {"ok": False, "message": "올린 파일이 서버에 없습니다. 다시 올려 주세요."}
    try:
        ents, bad = entries(r["tmp"], r["name"])
    except Exception as e:
        ents, bad = [], [r["name"]]
        print("[MAIL-HWM] 파일 읽기 실패: %s" % type(e).__name__, flush=True)
    cnt, big, order = {}, {}, []
    for gid, kind, opener, size, _nm in ents:
        if gid not in cnt:
            cnt[gid], big[gid] = 0, 0
            order.append(gid)
        if kind == "eml":
            cnt[gid] += 1
            if size > MAX_MSG_BYTES:
                big[gid] += 1
        else:
            try:
                with opener() as f:
                    cnt[gid] += _count_mbox(f)
            except Exception:
                bad.append(_nm)
    sg = suggest(order, r["name"])
    groups = []
    for gid in order:
        if not cnt[gid]:
            continue
        parts, note = sg[gid]
        groups.append({"gid": gid, "label": gid or r["name"], "n": cnt[gid], "big": big[gid], "folder": " / ".join(parts),
                       "note": note, "use": note not in ("trash", "spam", "draft")})
    with c_session() as c:
        if not groups:
            c.execute("UPDATE mail_hwm_files SET state='failed', bad=?, msg=?, last_at=datetime('now','localtime') WHERE id=?",
                      (json.dumps(bad[:50], ensure_ascii=False),
                       "이 파일 안에서 메일을 찾지 못했습니다. 하이웍스 「메일 백업」에서 받은 파일인지 확인해 주세요(.zip · .eml · .mbox).", fid))
        else:
            c.execute("UPDATE mail_hwm_files SET state=CASE WHEN state='stopped' THEN 'stopped' ELSE 'scanned' END, groups=?, bad=?, "
                      "last_at=datetime('now','localtime') WHERE id=?",
                      (json.dumps(groups, ensure_ascii=False), json.dumps(bad[:50], ensure_ascii=False), fid))
        r = _row(c, uid, fid)
    return {"ok": bool(groups), "file": public(r), "message": "" if groups else r.get("msg")}


# ─── ③ 넣기(뒤에서) ───────────────────────────────────────────────
def _stale(t) -> bool:
    try:
        last = _dt.datetime.strptime((t.get("last_at") or "")[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return True
    return _dt.datetime.now() - last > _dt.timedelta(minutes=STALE_MIN)


def public(t) -> dict:
    """화면에 보낼 것(서버 경로 없음)."""
    if not t:
        return {}
    st = t.get("state")
    if st == "running" and t.get("user_id") not in _RUNNING and _stale(t):
        st = "lost"
    try:
        groups = json.loads(t.get("groups") or "[]")
    except Exception:
        groups = []
    try:
        plan = json.loads(t.get("plan") or "{}")
    except Exception:
        plan = {}
    try:
        bad = json.loads(t.get("bad") or "[]")
    except Exception:
        bad = []
    d = {k: int(t.get(k) or 0) for k in _COUNTS}
    d.update(id=t["id"], name=t.get("name") or "", size=int(t.get("size") or 0), received=int(t.get("received") or 0),
             state=st, groups=groups, plan=plan, bad=bad[:20], n_bad=len(bad), cur=t.get("cur") or "", msg=t.get("msg") or "",
             created_at=t.get("created_at") or "", last_at=t.get("last_at") or "")
    return d


def list_files(c, uid, limit=20):
    ensure(c)
    return [public(dict(r)) for r in c.execute(
        "SELECT * FROM mail_hwm_files WHERE user_id=? AND state<>'cancelled' ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()]


def _bump(c, fid, **kw):
    sets, args = ["last_at=datetime('now','localtime')"], []
    for k, v in kw.items():
        if k in _COUNTS or k == "pos":
            sets.append("%s=%s+?" % (k, k))
            args.append(int(v or 0))
        elif k in ("state", "cur", "msg"):
            sets.append("%s=?" % k)
            args.append((v or "")[:300])
    args.append(fid)
    c.execute("UPDATE mail_hwm_files SET " + ",".join(sets) + " WHERE id=?", args)


def is_running(uid) -> bool:
    with _RUN_LOCK:
        return uid in _RUNNING


def stop(c, uid) -> int:
    ensure(c)
    with _RUN_LOCK:
        ev = _RUNNING.get(uid)
        if ev:
            ev.set()
    return c.execute("UPDATE mail_hwm_files SET state='stopped', msg='멈추기를 눌러 멈췄습니다', last_at=datetime('now','localtime') "
                     "WHERE user_id=? AND state='running'", (uid,)).rowcount


def cancel(c, uid, fid) -> bool:
    """올린 파일 지우기(넣는 중이 아닐 때) — 이미 넣은 메일은 그대로."""
    ensure(c)
    r = _row(c, uid, fid)
    if not r or (r["state"] == "running" and uid in _RUNNING):
        return False
    _rm_tmp(r["tmp"])
    c.execute("UPDATE mail_hwm_files SET state=CASE WHEN state='done' THEN 'done' ELSE 'cancelled' END, tmp='' WHERE id=?", (fid,))
    return True


def start(db_session, uid, fid, plan, wait=False):
    """넣기 시작 → (ok, 안내). plan = {gid: '폴더 경로'(빈 글자 = 받은편지함 · 폴더 고정 안 함) 또는 None(넣지 않음)}."""
    with _RUN_LOCK:
        if uid in _RUNNING:
            return False, "이미 넣는 중입니다. 끝날 때까지 기다리시거나 「멈추기」를 눌러 주세요."
        ev = threading.Event()
        _RUNNING[uid] = ev
    try:
        with db_session() as c:
            ensure(c)
            r = _row(c, uid, fid)
            if not r or r["state"] not in ("scanned", "stopped", "running") or not r["tmp"] or not os.path.isfile(r["tmp"]):
                raise ValueError("파일이 준비되지 않았습니다. 다시 올려 주세요.")
            groups = json.loads(r["groups"] or "[]")
            clean = {}
            for g in groups:
                v = (plan or {}).get(g["gid"])   # 화면이 보낸 것만(없거나 null = 넣지 않음)
                if v is None:
                    continue
                v = re.sub(r"\s+", " ", str(v)).strip()[:180]
                clean[g["gid"]] = v
            if not clean:
                raise ValueError("넣을 메일함을 하나 이상 골라 주세요.")
            total = sum(g["n"] for g in groups if g["gid"] in clean)
            resume = r["state"] in ("stopped", "running") and json.loads(r["plan"] or "{}") == clean
            if resume:
                c.execute("UPDATE mail_hwm_files SET state='running', msg='', cur='', last_at=datetime('now','localtime') WHERE id=?", (fid,))
            else:
                c.execute("UPDATE mail_hwm_files SET state='running', plan=?, pos=0, total=?, done=0, saved=0, moved=0, already=0, kept=0, "
                          "other=0, sent=0, failed=0, big=0, msg='', cur='', last_at=datetime('now','localtime') WHERE id=?",
                          (json.dumps(clean, ensure_ascii=False), total, fid))
            path, name = r["tmp"], r["name"]
    except Exception:
        with _RUN_LOCK:
            _RUNNING.pop(uid, None)
        raise

    def _job():
        try:
            run(db_session, uid, fid, path, name, clean, ev)
        finally:
            with _RUN_LOCK:
                _RUNNING.pop(uid, None)
    if wait:
        _job()
    else:
        threading.Thread(target=_job, name="mail-hwm-%s" % uid, daemon=True).start()
    return True, ""


def _place_plain(c, uid, parsed, raw_len, fid):
    """폴더 고정 없이(받은편지함) — 있으면 그대로 · 없으면 저장."""
    from . import mail_store as MS
    from . import mail_hiworks_folders as MHW
    subject = (parsed.get("subject") or "(제목 없음)").strip()
    body = (parsed.get("text") or "").strip() or MS._html_to_text(parsed.get("html") or "")
    row = MHW._find(c, uid, MS._dedup_hash(parsed.get("message_id", ""), parsed.get("from_email", ""), subject, body))
    if row:
        return "already"
    mx = c.execute("SELECT COALESCE(MAX(id),0) FROM mail_messages").fetchone()[0] or 0
    mid, _o = _store_in(c, uid, parsed, raw_len)
    if not mid:
        return "failed"
    if mid <= mx:
        return "already"
    c.execute("UPDATE mail_messages SET is_read=1 WHERE id=? AND user_id=?", (mid, uid))
    return "saved"


def _store_in(c, uid, parsed, raw_len):
    from . import mail_store as MS
    return MS.store_inbound(
        c, to_email=(parsed.get("to_email") or ""), from_email=parsed.get("from_email", ""),
        from_name=parsed.get("from_name", ""), subject=parsed.get("subject", ""), text=parsed.get("text", ""),
        html=parsed.get("html", ""), cc=parsed.get("cc", ""), size=raw_len, owner_id=uid, run_ai=False,
        attachments=parsed.get("attachments"), message_id=parsed.get("message_id", ""), auth=parsed.get("auth"),
        reply_to=parsed.get("reply_to", ""), to_all=parsed.get("to_all", ""), raw_headers=parsed.get("raw_headers", ""),
        sent_at=parsed.get("sent_at", ""))


def _store_sent(c, uid, parsed, raw_len):
    """내 주소가 보낸 메일 → 보낸 메일함(이미 있으면 그대로)."""
    from . import mail_store as MS
    from . import mail_hiworks_folders as MHW
    subject = (parsed.get("subject") or "(제목 없음)").strip()
    body = (parsed.get("text") or "").strip() or MS._html_to_text(parsed.get("html") or "")
    h = MS._dedup_hash(parsed.get("message_id", ""), parsed.get("from_email", ""), subject, body)
    if MHW._find(c, uid, h):
        return "already"
    oid = MS.store_outbound(c, user_id=uid, from_email=parsed.get("from_email", ""), to_email=parsed.get("to_all") or parsed.get("to_email", ""),
                            subject=subject, body=body, from_name=parsed.get("from_name", ""), cc=parsed.get("cc", ""),
                            body_html=parsed.get("html", ""), size=raw_len)
    if not oid:
        return "failed"
    sets, args = ["dedup_hash=?"], [h]
    try:
        at = MS.arrival_at(parsed.get("raw_headers", ""), parsed.get("sent_at", ""))
    except Exception:
        at = ""
    if at:
        sets.append("received_at=?")
        args.append(at)
    c.execute("UPDATE mail_messages SET " + ",".join(sets) + " WHERE id=? AND user_id=?", args + [oid, uid])
    if parsed.get("attachments"):
        try:
            MS._save_attachments(c, oid, parsed["attachments"])
        except Exception as e:
            print("[MAIL-HWM] 보낸 메일 첨부 저장 건너뜀: %s" % type(e).__name__, flush=True)
    return "sent"


def run(db_session, uid, fid, path, name, plan, ev):
    from . import mail_store as MS
    from . import mail_hiworks_folders as MHW
    from .mail_import_outlook import disk_state
    state, msg = "done", ""
    try:
        with db_session() as c:
            r = _row(c, uid, fid)
            pos0 = int(r["pos"] or 0) if r else 0
            own = MHW.own_addresses(c, uid)
            keys = {}
            for gid, folder in plan.items():
                parts = [p.strip() for p in re.split(r"\s*(?:/|›|>)\s*", folder or "") if p.strip()][:3]
                keys[gid] = get_or_make_folder(c, uid, parts) if parts else ""
            ri = MHW._rules_of(c, uid)
            _bump(c, fid, cur="파일 읽는 중")
        ents, _bad = entries(path, name)
        ents = [e for e in ents if e[0] in plan]
        i = 0
        for gid, raw in iter_mail(ents):
            i += 1
            if i <= pos0:
                continue          # 이어 하기 — 앞에서 처리한 것은 건너뜀(읽기만)
            if ev.is_set():
                break
            if i % 50 == 0 and not disk_state().get("ok", True):
                state, msg = "stopped", "서버 남은 공간이 모자라 멈췄습니다(빅터에게 알려 주세요)"
                ev.set()
                break
            if raw is None:
                with db_session() as c:
                    _bump(c, fid, done=1, big=1, pos=1)
                continue
            try:
                parsed = MS.parse_raw_email(raw) if raw else {}
            except Exception:
                parsed = {}
            if parsed and not (parsed.get("from_email") or parsed.get("subject") or parsed.get("text") or parsed.get("html")):
                parsed = {}
            key = keys.get(gid, "")
            with db_session() as c:
                if not parsed:
                    _bump(c, fid, done=1, failed=1, pos=1)
                    continue
                try:
                    frm = (parsed.get("from_email") or "").strip().lower()
                    if frm and frm in own:
                        act = _store_sent(c, uid, parsed, len(raw))
                    elif key:
                        if parsed.get("message_id"):
                            row = MHW._find(c, uid, MS._dedup_hash(parsed["message_id"], "", "", ""))
                            if row:
                                act = MHW.place_existing(c, uid, row, key, ri, -int(fid))
                            else:
                                act, _m = MHW.store_new(c, uid, parsed, len(raw), {"seen": True, "idate": ""}, key, -int(fid), "")
                        else:
                            act, _m = MHW.store_new(c, uid, parsed, len(raw), {"seen": True, "idate": ""}, key, -int(fid), "")
                    else:
                        act = _place_plain(c, uid, parsed, len(raw), fid)
                except Exception as e:
                    print("[MAIL-HWM] 한 통 건너뜀: %s" % type(e).__name__, flush=True)
                    act = "failed"
                if act not in _COUNTS:
                    act = "failed"
                _bump(c, fid, done=1, pos=1, cur=gid or name, **{act: 1})
        if ev.is_set() and state == "done":
            state, msg = "stopped", msg or "멈추기를 눌러 멈췄습니다"
    except Exception as e:
        state, msg = "stopped", "읽다가 멈췄습니다(%s) — 「이어서 넣기」를 눌러 주세요" % type(e).__name__
        print("[MAIL-HWM] 멈춤: %s" % type(e).__name__, flush=True)
    finally:
        try:
            from . import mail_folders as MF
            MF._CACHE.pop(uid, None)
        except Exception:
            pass
        with db_session() as c:
            cur = c.execute("SELECT state FROM mail_hwm_files WHERE id=?", (fid,)).fetchone()
            if cur and cur["state"] == "stopped" and state == "done":
                state = "stopped"
            _bump(c, fid, state=state, cur="", msg=msg)
            if state == "done":
                c.execute("UPDATE mail_hwm_files SET tmp='' WHERE id=?", (fid,))
        if state == "done":
            _rm_tmp(path)
    print("[MAIL-HWM] user=%s file=%s %s" % (uid, fid, state), flush=True)
