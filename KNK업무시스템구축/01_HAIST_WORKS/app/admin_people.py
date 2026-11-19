# -*- coding: utf-8 -*-
"""z1191z83 2단계 — 관리 화면 다시 짜기 (대표 2026-11-19)

대표: 「관리 항목에 들어가면 관리자, 권한 위임 … 쓰기가 상당히 어려워. 관리자라고 생각하고 권한을 부여하고 넘기고
       등록하고 새로 만들고 하는 실무 담당자 입장에서 다시 정리」
대표 고름(11-19): 권한 넘기기 = 담당 교체 + 기간 맡기기 둘 다 · 맡기는 동안 보낸 사람 권한은 그대로 ·
                  관리자 권한(역할 관리자·임원·대표)은 대표만 줄 수 있다.

화면
  /admin                 관리 홈 — 사람 찾기 · 하려는 일 카드 · 최근 바뀐 권한 · 점검·위험 도구(접어 둠)
  /admin/staff           직원 목록(찾기 · 본사/법인 · 재직/잠금)
  /admin/staff/{uid}     직원 한 사람 — 할 수 있는 것이 한 장에(센터 4칸 · 담당 사업부 · 역할 · 부서 · 재직/잠금)
                         민감 정보(매출금액·구매단가·구매처)는 **부서 규칙에서 온다** → 이유만 보여 주고 부서 화면으로 안내
  /admin/handover        권한 넘기기 — 담당 교체(계속) · 기간 맡기기(끝나면 저절로 원래대로)
  /admin/depts           부서 — 팀장 · 본사/법인 · 인원 · 부서별 민감 정보 보기

권한 판단 함수(main.py can_view_sales 등)는 **안 바꾼다** — 같은 칸(users.can_*·biz_divs·role·team_id·is_active)을 고칠 뿐.
바뀐 것은 전부 user_history(사람 수정·일괄 설정과 같은 기록)에 남긴다.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

# 넘기기·복사할 수 있는 칸(관리자 권한·역할은 제외 — 대표만)
FLAGS = (("can_view_sales", "매출영업센터 보기"), ("can_use_sales", "매출영업센터 등록·수정"),
         ("can_view_logistics", "자재구매센터 보기"), ("can_use_logistics", "자재구매센터 등록·수정"))
BIZ = (("T", "검사기"), ("M", "자동화"), ("L", "라이프밸류"), ("E", "기타"))
ITEM_LABEL = dict(FLAGS)
ITEM_LABEL.update({"biz:" + k: "담당 사업부 · " + v for k, v in BIZ})
ITEMS = [k for k, _ in FLAGS] + ["biz:" + k for k, _ in BIZ]
ROLE_LABEL = {"member": "일반 직원", "leader": "팀장", "executive": "임원", "admin": "관리자", "ceo": "대표"}
ROLE_ORDER = ("member", "leader", "executive", "admin", "ceo")
CEO_ONLY_ROLES = ("executive", "admin", "ceo")   # 대표 11-19 「대표만」 — 이 역할로 주거나 빼는 것은 대표 계정만
TICK_SECS = 300


def _biz_set(v):
    return {x.strip().upper() for x in str(v or "").split(",") if x.strip()}


def _biz_str(s):
    return ",".join(k for k, _ in BIZ if k in s)


def _items_of(row):
    """사람 한 명이 가진 넘길 수 있는 칸 목록"""
    out = [f for f, _ in FLAGS if row.get(f)]
    out += ["biz:" + k for k, _ in BIZ if k in _biz_set(row.get("biz_divs"))]
    return out


def _corp(row):
    return "법인" if ((row.get("team_entity") or row.get("entity")) == "VN" or row.get("team_id") == 12) else "본사"


def register_admin_people(app, d):
    """main.py 가 부른다. d = 도우미 묶음(dict)."""
    ctx, require, db_session = d["ctx"], d["require"], d["db_session"]
    kst_now, nas_quiet = d["kst_now"], d["nas_quiet"]
    locked_for_role, imply = d["locked_for_role"], d["imply"]
    can_view_field, load_policy, field_labels = d["can_view_field"], d["load_policy"], d["field_labels"]
    can_view_work_patterns = d["can_view_work_patterns"]

    with db_session() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS perm_handover (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,                -- transfer(담당 교체) | delegate(기간 맡기기)
            from_user INTEGER NOT NULL, to_user INTEGER NOT NULL,
            items_json TEXT NOT NULL,          -- 넘긴 칸
            added_json TEXT,                   -- 받은 사람에게 실제로 더해진 칸(맡기기 끝날 때 이것만 뺀다)
            removed_json TEXT,                 -- 담당 교체 때 보낸 사람에게서 뺀 칸
            starts_at TEXT, ends_at TEXT,      -- 한국 시각 'YYYY-MM-DD HH:MM'
            status TEXT NOT NULL,              -- done | pending | active | ended
            note TEXT, created_by INTEGER, created_at TEXT DEFAULT (datetime('now','+9 hours')),
            ended_at TEXT, ended_by INTEGER, end_note TEXT)""")

    # ───────────────────────── 공용 ─────────────────────────
    def _is_vn_actor(u):
        return (u.get("entity") == "VN") or u.get("team_id") == 12

    def _fmt_local(kst_str, u):
        """저장(한국 시각) → 보는 사람 시각(본사 +9 · 법인 +7). KNK 시간대 표준."""
        if not kst_str:
            return ""
        try:
            t = datetime.strptime(kst_str[:16], "%Y-%m-%d %H:%M")
        except ValueError:
            return kst_str
        if _is_vn_actor(u):
            t -= timedelta(hours=2)
        return t.strftime("%m-%d %H:%M")

    def _to_kst(local_str, u):
        """입력(보는 사람 시각 'YYYY-MM-DDTHH:MM') → 한국 시각 문자열. 못 읽으면 None"""
        s = (local_str or "").strip().replace("T", " ")[:16]
        try:
            t = datetime.strptime(s, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
        if _is_vn_actor(u):
            t += timedelta(hours=2)
        return t.strftime("%Y-%m-%d %H:%M")

    def _user(c, uid):
        r = c.execute("SELECT u.*, t.name AS team_name, t.entity AS team_entity FROM users u "
                      "LEFT JOIN teams t ON t.id=u.team_id WHERE u.id=?", (uid,)).fetchone()
        return dict(r) if r else None

    def _hist(c, uid, actor, field, ov, nv, note):
        c.execute("INSERT INTO user_history(user_id, changed_by, field, old_value, new_value, note) VALUES(?,?,?,?,?,?)",
                  (uid, actor, field, ov, nv, note))

    def _set_items(c, uid, actor, items, on, note):
        """칸들을 켜거나 끈다(이미 그 값이면 건너뜀) — 실제로 바뀐 칸 목록을 돌려준다. 바뀐 것은 기록."""
        row = _user(c, uid)
        changed = []
        biz = _biz_set(row.get("biz_divs"))
        biz0 = set(biz)
        for it in items:
            if it.startswith("biz:"):
                k = it[4:]
                if on and k not in biz:
                    biz.add(k); changed.append(it)
                elif not on and k in biz:
                    biz.discard(k); changed.append(it)
            elif it in ITEM_LABEL:
                cur = 1 if row.get(it) else 0
                if cur != (1 if on else 0):
                    c.execute(f"UPDATE users SET {it}=? WHERE id=?", (1 if on else 0, uid))
                    _hist(c, uid, actor, ITEM_LABEL[it], "켬" if cur else "끔", "켬" if on else "끔", note)
                    changed.append(it)
        if biz != biz0:
            c.execute("UPDATE users SET biz_divs=? WHERE id=?", (_biz_str(biz), uid))
            _hist(c, uid, actor, "담당 사업부", "·".join(v for k, v in BIZ if k in biz0) or "공통",
                  "·".join(v for k, v in BIZ if k in biz) or "공통", note)
        return changed

    def _expand_add(items):
        """등록·수정을 주면 보기도 함께(판단 함수·저장 규칙과 같다)"""
        s = list(items)
        for use, view in (("can_use_sales", "can_view_sales"), ("can_use_logistics", "can_view_logistics")):
            if use in s and view not in s:
                s.insert(s.index(use), view)
        return s

    def _expand_remove(items):
        """보기를 빼면 등록·수정도 함께 빠진다"""
        s = list(items)
        for use, view in (("can_use_sales", "can_view_sales"), ("can_use_logistics", "can_view_logistics")):
            if view in s and use not in s:
                s.append(use)
        return s

    # ───────────────────── 기간 맡기기 시작·끝 ─────────────────────
    def run_due(now=None):
        """시작할 맡기기는 시작하고, 끝난 맡기기는 받은 사람에게 더했던 칸만 뺀다. NAS 백업 시간(월 02:00~07:30)엔 미룬다."""
        if nas_quiet():
            return {"skipped": "nas_quiet"}
        now_s = (now or kst_now()).strftime("%Y-%m-%d %H:%M")
        done = {"started": 0, "ended": 0}
        with db_session() as c:
            for r in [dict(x) for x in c.execute(
                    "SELECT * FROM perm_handover WHERE kind='delegate' AND status='pending' AND starts_at<=? ORDER BY id", (now_s,))]:
                if c.execute("UPDATE perm_handover SET status='active' WHERE id=? AND status='pending'", (r["id"],)).rowcount != 1:
                    continue
                if r["ends_at"] and r["ends_at"] <= now_s:     # 시작도 전에 끝난 것 — 아무것도 안 더함
                    c.execute("UPDATE perm_handover SET status='ended', added_json='[]', ended_at=?, end_note=? WHERE id=?",
                              (now_s, "시작 전에 끝남", r["id"]))
                    continue
                to = _user(c, r["to_user"])
                if not to or not to.get("is_active"):
                    c.execute("UPDATE perm_handover SET status='ended', added_json='[]', ended_at=?, end_note=? WHERE id=?",
                              (now_s, "받는 사람이 없거나 잠김", r["id"]))
                    continue
                added = _set_items(c, r["to_user"], None, _expand_add(json.loads(r["items_json"])), True,
                                   "기간 맡기기 시작 #%d (%s까지)" % (r["id"], r["ends_at"]))
                c.execute("UPDATE perm_handover SET added_json=? WHERE id=?", (json.dumps(added), r["id"]))
                done["started"] += 1
            for r in [dict(x) for x in c.execute(
                    "SELECT * FROM perm_handover WHERE kind='delegate' AND status='active' AND ends_at<=? ORDER BY id", (now_s,))]:
                _end(c, r, None, "기간 끝", now_s)
                done["ended"] += 1
        return done

    def _end(c, r, actor, why, now_s):
        if c.execute("UPDATE perm_handover SET status='ended', ended_at=?, ended_by=?, end_note=? WHERE id=? AND status='active'",
                     (now_s, actor, why, r["id"])).rowcount != 1:
            return []
        added = json.loads(r.get("added_json") or "[]")
        # 같은 사람에게 아직 진행 중인 다른 맡기기가 같은 칸을 맡기고 있으면 남기고, 그 칸을 그 맡기기 몫으로 옮긴다
        #   (그 맡기기가 끝날 때 빠지게 — 안 옮기면 영영 남는다)
        others = [dict(o) for o in c.execute("SELECT id, items_json, added_json FROM perm_handover WHERE kind='delegate' "
                                             "AND status='active' AND to_user=? AND id<>? ORDER BY ends_at DESC, id DESC",
                                             (r["to_user"], r["id"]))]
        rm = []
        for x in added:
            o = next((o for o in others if x in _expand_add(json.loads(o["items_json"] or "[]"))), None)
            if o is None:
                rm.append(x)
                continue
            oa = json.loads(o["added_json"] or "[]")
            if x not in oa:
                oa.append(x)
                o["added_json"] = json.dumps(oa)
                c.execute("UPDATE perm_handover SET added_json=? WHERE id=?", (o["added_json"], o["id"]))
        to = _user(c, r["to_user"]) or {}
        # 보기를 빼려는데 등록·수정이 남아 있으면 보기도 남긴다(등록·수정 = 보기 포함)
        for use, view in (("can_use_sales", "can_view_sales"), ("can_use_logistics", "can_view_logistics")):
            if view in rm and use not in rm and to.get(use):
                rm.remove(view)
        return _set_items(c, r["to_user"], actor, rm, False, "기간 맡기기 끝 #%d (%s)" % (r["id"], why))

    def _tick():
        try:
            run_due()
        except Exception as e:   # 기록만 하고 다음 번에 다시
            print(f"[z83 handover] 맡기기 점검 실패: {e}")
        t = threading.Timer(TICK_SECS, _tick); t.daemon = True; t.start()

    @app.on_event("startup")
    def _z83_start_tick():
        t = threading.Timer(60, _tick); t.daemon = True; t.start()
        print("[z83 handover] 기간 맡기기 점검 5분마다(월 02:00~07:30 미룸)")

    # ───────────────────────── 관리 홈 ─────────────────────────
    @app.get("/admin", response_class=HTMLResponse)
    async def admin_home(req: Request):
        u = require(req, ["admin", "ceo"])
        if not u:
            return RedirectResponse("/login", 303)
        try:
            run_due()
        except Exception as e:
            print(f"[z83 handover] {e}")
        with db_session() as c:
            n_active = c.execute("SELECT COUNT(*) FROM users WHERE COALESCE(is_active,1)=1").fetchone()[0]
            n_locked = c.execute("SELECT COUNT(*) FROM users WHERE COALESCE(is_active,1)=0").fetchone()[0]
            n_teams = c.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
            n_deleg = c.execute("SELECT COUNT(*) FROM perm_handover WHERE kind='delegate' AND status IN ('active','pending')").fetchone()[0]
            recent = [dict(r) for r in c.execute(
                "SELECT h.*, a.name AS target_name, a.id AS target_id, b.name AS actor_name FROM user_history h "
                "LEFT JOIN users a ON a.id=h.user_id LEFT JOIN users b ON b.id=h.changed_by "
                "WHERE h.field NOT IN ('비밀번호') ORDER BY h.id DESC LIMIT 8")]
        for r in recent:
            r["when"] = (r.get("changed_at") or "")[5:16]
        return ctx(req, "admin_home.html", user=u, active="admin", n_active=n_active, n_locked=n_locked,
                   n_teams=n_teams, n_deleg=n_deleg, recent=recent, is_ceo=(u.get("role") == "ceo"),
                   can_work_patterns=can_view_work_patterns(u))

    # ───────────────────────── 직원 목록 ─────────────────────────
    @app.get("/admin/staff", response_class=HTMLResponse)
    async def admin_staff(req: Request, q: str = "", corp: str = "", state: str = "active"):
        u = require(req, ["admin", "ceo"])
        if not u:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            rows = [dict(r) for r in c.execute(
                "SELECT u.id, u.name, u.name_vi, u.employee_no, u.login_id, u.role, u.rank, u.is_active, u.team_id, u.entity, "
                "u.can_view_sales, u.can_use_sales, u.can_view_logistics, u.can_use_logistics, u.biz_divs, "
                "t.name AS team_name, t.entity AS team_entity FROM users u LEFT JOIN teams t ON t.id=u.team_id "
                "ORDER BY CASE WHEN (COALESCE(t.entity,'')='VN' OR u.team_id=12) THEN 1 ELSE 0 END, "
                "COALESCE(t.display_order, 9999), t.name, CAST(u.employee_no AS INTEGER), u.employee_no, u.id")]
        qq = q.strip().lower()
        out, cnt = [], {"kr": 0, "vn": 0, "locked": 0}
        for r in rows:
            r["corp"] = _corp(r)
            act = bool(r.get("is_active", 1))
            if act:
                cnt["vn" if r["corp"] == "법인" else "kr"] += 1
            else:
                cnt["locked"] += 1
            if state == "locked" and act or state != "locked" and not act:
                continue
            if corp == "kr" and r["corp"] != "본사" or corp == "vn" and r["corp"] != "법인":
                continue
            if qq and not any(qq in str(r.get(k) or "").lower() for k in ("name", "name_vi", "employee_no", "login_id", "team_name")):
                continue
            r["role_lbl"] = ROLE_LABEL.get(r.get("role") or "member", r.get("role") or "")
            lk = locked_for_role(r.get("role"))
            on = {f for f, _ in FLAGS if r.get(f) or f in lk}
            r["chips"] = [("매출 등록·수정" if "can_use_sales" in on else "매출 보기") if "can_view_sales" in on or "can_use_sales" in on else "",
                          ("자재 등록·수정" if "can_use_logistics" in on else "자재 보기") if "can_view_logistics" in on or "can_use_logistics" in on else ""]
            r["chips"] = [x for x in r["chips"] if x]
            r["role_fixed"] = bool(lk)
            r["biz_lbl"] = "·".join(v for k, v in BIZ if k in _biz_set(r.get("biz_divs")))
            out.append(r)
        return ctx(req, "admin_staff.html", user=u, active="admin", rows=out, q=q, corp=corp, state=state, cnt=cnt)

    # ───────────────────────── 직원 한 사람 ─────────────────────────
    def _person_view(c, p, viewer):
        policy = load_policy(c)
        role = p.get("role") or "member"
        lk = locked_for_role(role)
        sens = []
        for cat, lbl in field_labels.items():
            ok = can_view_field(p, cat, policy) if p.get("is_active", 1) else False
            if role in ("ceo", "executive"):
                why = "역할(%s)로 항상 보임" % ROLE_LABEL[role]
            elif ok and p.get("team_id") in (policy.get(cat) or set()):
                why = "부서 규칙 · %s" % (p.get("team_name") or "")
            elif ok:
                why = "관리자 + 센터 보기"
            else:
                why = "이 사람 부서(%s)는 안 보임" % (p.get("team_name") or "부서 없음")
            sens.append({"cat": cat, "label": lbl, "ok": ok, "why": why})
        return {"role": role, "locked": sorted(lk), "sens": sens}

    @app.get("/admin/staff/{uid:int}", response_class=HTMLResponse)
    async def admin_person(req: Request, uid: int):
        u = require(req, ["admin", "ceo"])
        if not u:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            p = _user(c, uid)
            if not p:
                return RedirectResponse("/admin/staff", 303)
            pv = _person_view(c, p, u)
            teams = [dict(r) for r in c.execute("SELECT id, name, entity FROM teams ORDER BY "
                                                "CASE WHEN COALESCE(entity,'')='VN' THEN 1 ELSE 0 END, display_order, name")]
            hist = [dict(r) for r in c.execute(
                "SELECT h.*, b.name AS actor_name FROM user_history h LEFT JOIN users b ON b.id=h.changed_by "
                "WHERE h.user_id=? ORDER BY h.id DESC LIMIT 30", (uid,))]
            staff = [dict(r) for r in c.execute(
                "SELECT u.id, u.name, u.employee_no, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id "
                "WHERE COALESCE(u.is_active,1)=1 AND u.id<>? ORDER BY u.name", (uid,))]
            deleg = [dict(r) for r in c.execute(
                "SELECT h.*, f.name AS from_name, t.name AS to_name FROM perm_handover h LEFT JOIN users f ON f.id=h.from_user "
                "LEFT JOIN users t ON t.id=h.to_user WHERE h.kind='delegate' AND h.status IN ('active','pending') "
                "AND (h.from_user=? OR h.to_user=?) ORDER BY h.id DESC", (uid, uid))]
        for h in hist:
            h["when"] = (h.get("changed_at") or "")[:16]
        for g in deleg:
            g["until"] = _fmt_local(g.get("ends_at"), u)
            g["items_lbl"] = " · ".join(ITEM_LABEL.get(x, x) for x in json.loads(g["items_json"] or "[]"))
        cur = {f: (1 if p.get(f) else 0) for f, _ in FLAGS}
        cur.update({"biz_divs": _biz_str(_biz_set(p.get("biz_divs"))), "role": pv["role"],
                    "team_id": p.get("team_id") or "", "is_active": 1 if p.get("is_active", 1) else 0})
        is_ceo = u.get("role") == "ceo"
        target_ceo = pv["role"] == "ceo"
        role_opts = [r for r in ROLE_ORDER if is_ceo or r in ("member", "leader")]
        if not is_ceo and pv["role"] in CEO_ONLY_ROLES:
            role_note = "%s 역할은 대표만 바꿀 수 있습니다" % ROLE_LABEL[pv["role"]]
        elif uid == u.get("id"):
            role_note = "내 역할·잠금은 스스로 바꿀 수 없습니다"
        else:
            role_note = "" if is_ceo else "관리자·임원·대표 역할은 대표만 줄 수 있습니다"
        can_role = (uid != u.get("id")) and (is_ceo or pv["role"] not in CEO_ONLY_ROLES)
        can_lock = (uid != u.get("id")) and (is_ceo or pv["role"] not in CEO_ONLY_ROLES)
        read_only = target_ceo and not is_ceo
        return ctx(req, "admin_person.html", user=u, active="admin", p=p, pv=pv, cur=cur, teams=teams, hist=hist,
                   staff=staff, deleg=deleg, flags=FLAGS, bizs=BIZ, role_label=ROLE_LABEL, role_opts=role_opts,
                   can_role=can_role, can_lock=can_lock, role_note=role_note, read_only=read_only, corp=_corp(p))

    @app.get("/admin/staff/{uid:int}/like")
    async def admin_person_like(req: Request, uid: int, src: int = 0):
        """「○○○과 똑같이」 — 그 사람의 센터 4칸·담당 사업부 값(역할·관리자 권한은 복사하지 않는다)"""
        u = require(req, ["admin", "ceo"])
        if not u:
            return JSONResponse({"ok": False, "msg": "로그인이 필요합니다"}, 401)
        with db_session() as c:
            s = _user(c, src)
        if not s:
            return JSONResponse({"ok": False, "msg": "그 직원을 찾지 못했습니다"}, 404)
        vals = {f: (1 if s.get(f) else 0) for f, _ in FLAGS}
        vals["biz_divs"] = _biz_str(_biz_set(s.get("biz_divs")))
        return JSONResponse({"ok": True, "name": s.get("name"), "team": s.get("team_name") or "",
                             "role_lbl": ROLE_LABEL.get(s.get("role") or "member", ""), "vals": vals})

    @app.post("/admin/staff/{uid:int}/save")
    async def admin_person_save(req: Request, uid: int):
        u = require(req, ["admin", "ceo"])
        if not u:
            return JSONResponse({"ok": False, "msg": "로그인이 필요합니다"}, 401)
        try:
            body = await req.json()
            old, new = body.get("old") or {}, body.get("new") or {}
        except Exception:
            return JSONResponse({"ok": False, "msg": "보낸 값을 읽지 못했습니다"}, 400)
        is_ceo = u.get("role") == "ceo"
        me = u.get("id")
        with db_session() as c:
            p = _user(c, uid)
            if not p:
                return JSONResponse({"ok": False, "msg": "그 직원을 찾지 못했습니다"}, 404)
            prole = p.get("role") or "member"
            dbv = {f: (1 if p.get(f) else 0) for f, _ in FLAGS}
            dbv.update({"biz_divs": _biz_str(_biz_set(p.get("biz_divs"))), "role": prole,
                        "team_id": str(p.get("team_id") or ""), "is_active": 1 if p.get("is_active", 1) else 0})
            # 화면을 연 뒤 다른 사람이 먼저 바꿨으면 멈춘다(덮어쓰기 방지)
            for k, v in dbv.items():
                if k in old and str(old[k] if old[k] is not None else "") != str(v):
                    return JSONResponse({"ok": False, "msg": "화면을 연 뒤 다른 사람이 이 직원을 먼저 바꿨습니다. 새로고침한 뒤 다시 해 주세요."}, 409)
            if prole == "ceo" and not is_ceo:
                return JSONResponse({"ok": False, "msg": "대표 계정은 대표만 바꿀 수 있습니다"}, 403)
            nrole = new.get("role", prole) or prole
            if nrole not in ROLE_LABEL:
                return JSONResponse({"ok": False, "msg": "모르는 역할입니다"}, 400)
            if nrole != prole:
                if uid == me:
                    return JSONResponse({"ok": False, "msg": "내 역할은 스스로 바꿀 수 없습니다"}, 403)
                if not is_ceo and (nrole in CEO_ONLY_ROLES or prole in CEO_ONLY_ROLES):
                    return JSONResponse({"ok": False, "msg": "관리자·임원·대표 역할은 대표만 주거나 뺄 수 있습니다"}, 403)
            nact = 1 if str(new.get("is_active", dbv["is_active"])) in ("1", "True", "true") else 0
            if nact != dbv["is_active"]:
                if uid == me:
                    return JSONResponse({"ok": False, "msg": "내 계정은 스스로 잠글 수 없습니다"}, 403)
                if not is_ceo and prole in CEO_ONLY_ROLES:
                    return JSONResponse({"ok": False, "msg": "관리자·임원·대표 계정 잠금은 대표만 할 수 있습니다"}, 403)
            nteam = str(new.get("team_id", dbv["team_id"]) or "")
            if nteam and not c.execute("SELECT 1 FROM teams WHERE id=?", (nteam,)).fetchone():
                return JSONResponse({"ok": False, "msg": "모르는 부서입니다"}, 400)
            fv = imply({f: (1 if str(new.get(f, dbv[f])) in ("1", "True", "true") else 0) for f, _ in FLAGS})
            nbiz = _biz_str(_biz_set(new.get("biz_divs", dbv["biz_divs"])))
            note = "관리 화면"
            n = 0
            on = [f for f, _ in FLAGS if fv[f] and not dbv[f]] + ["biz:" + k for k in _biz_set(nbiz) - _biz_set(dbv["biz_divs"])]
            off = [f for f, _ in FLAGS if not fv[f] and dbv[f]] + ["biz:" + k for k in _biz_set(dbv["biz_divs"]) - _biz_set(nbiz)]
            n += len(_set_items(c, uid, me, on, True, note))
            n += len(_set_items(c, uid, me, off, False, note))
            if nrole != prole:
                c.execute("UPDATE users SET role=? WHERE id=?", (nrole, uid))
                _hist(c, uid, me, "역할", ROLE_LABEL[prole], ROLE_LABEL[nrole], note); n += 1
            if nteam != dbv["team_id"]:
                tn = {str(r[0]): r[1] for r in c.execute("SELECT id, name FROM teams")}
                c.execute("UPDATE users SET team_id=? WHERE id=?", (nteam or None, uid))
                _hist(c, uid, me, "부서", tn.get(dbv["team_id"]) or "없음", tn.get(nteam) or "없음", note + " · 부서 이동"); n += 1
            if nact != dbv["is_active"]:
                c.execute("UPDATE users SET is_active=? WHERE id=?", (nact, uid))
                _hist(c, uid, me, "재직", "재직" if dbv["is_active"] else "잠금", "재직" if nact else "잠금", note + (" · 잠금 풀기" if nact else " · 퇴사·잠금")); n += 1
        return JSONResponse({"ok": True, "n": n, "msg": ("%d가지 바꿨습니다" % n) if n else "바뀐 것이 없습니다"})

    # ───────────────────────── 권한 넘기기 ─────────────────────────
    def _plan(c, kind, frm, to, items, remove_from_sender):
        f, t = _user(c, frm), _user(c, to)
        if not f or not t:
            return None, "보내는 사람·받는 사람을 골라 주세요"
        if frm == to:
            return None, "보내는 사람과 받는 사람이 같습니다"
        if not t.get("is_active", 1):
            return None, "받는 사람이 잠긴 계정입니다"
        have = set(_items_of(f))
        items = [x for x in ITEMS if x in items]
        if not items:
            return None, "넘길 것을 하나 이상 골라 주세요"
        bad = [x for x in items if x not in have]
        if bad:
            return None, "보내는 사람에게 없는 것: " + ", ".join(ITEM_LABEL[x] for x in bad)
        give = _expand_add(items)
        t_have = set(_items_of(t)) | set(locked_for_role(t.get("role")))
        added = [x for x in give if x not in t_have]
        already = [x for x in give if x in t_have]
        removed = _expand_remove(items) if (kind == "transfer" and remove_from_sender) else []
        return {"from": f, "to": t, "items": items, "added": added, "already": already, "removed": removed}, ""

    def _plan_json(pl):
        lab = lambda xs: [ITEM_LABEL[x] for x in xs]
        return {"from": pl["from"]["name"], "to": pl["to"]["name"], "added": lab(pl["added"]),
                "already": lab(pl["already"]), "removed": lab(pl["removed"])}

    @app.get("/admin/handover", response_class=HTMLResponse)
    async def admin_handover(req: Request, frm: int = 0):
        u = require(req, ["admin", "ceo"])
        if not u:
            return RedirectResponse("/login", 303)
        try:
            run_due()
        except Exception as e:
            print(f"[z83 handover] {e}")
        with db_session() as c:
            staff = [dict(r) for r in c.execute(
                "SELECT u.id, u.name, u.employee_no, u.role, u.can_view_sales, u.can_use_sales, u.can_view_logistics, "
                "u.can_use_logistics, u.biz_divs, t.name AS team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id "
                "WHERE COALESCE(u.is_active,1)=1 ORDER BY u.name")]
            live = [dict(r) for r in c.execute(
                "SELECT h.*, f.name AS from_name, t.name AS to_name FROM perm_handover h LEFT JOIN users f ON f.id=h.from_user "
                "LEFT JOIN users t ON t.id=h.to_user WHERE h.kind='delegate' AND h.status IN ('active','pending') ORDER BY h.ends_at")]
            past = [dict(r) for r in c.execute(
                "SELECT h.*, f.name AS from_name, t.name AS to_name FROM perm_handover h LEFT JOIN users f ON f.id=h.from_user "
                "LEFT JOIN users t ON t.id=h.to_user WHERE h.status IN ('done','ended') ORDER BY h.id DESC LIMIT 10")]
        for s in staff:
            s["items"] = _items_of(s)
        for g in live + past:
            g["items_lbl"] = " · ".join(ITEM_LABEL.get(x, x) for x in json.loads(g["items_json"] or "[]"))
            g["since"], g["until"] = _fmt_local(g.get("starts_at"), u), _fmt_local(g.get("ends_at"), u)
            g["ended"] = _fmt_local(g.get("ended_at"), u)
            g["created"] = _fmt_local((g.get("created_at") or "")[:16], u)
        now = kst_now()
        if _is_vn_actor(u):
            now -= timedelta(hours=2)
        return ctx(req, "admin_handover.html", user=u, active="admin", staff=staff, live=live, past=past, frm=frm,
                   item_label=ITEM_LABEL, items_all=ITEMS, now_local=now.strftime("%Y-%m-%dT%H:%M"),
                   tz_lbl=("베트남 시각" if _is_vn_actor(u) else "한국 시각"))

    async def _read(req):
        try:
            b = await req.json()
        except Exception:
            return None
        return b

    @app.post("/admin/handover/preview")
    async def admin_handover_preview(req: Request):
        u = require(req, ["admin", "ceo"])
        if not u:
            return JSONResponse({"ok": False, "msg": "로그인이 필요합니다"}, 401)
        b = await _read(req) or {}
        with db_session() as c:
            pl, err = _plan(c, b.get("kind"), int(b.get("from") or 0), int(b.get("to") or 0), b.get("items") or [], bool(b.get("remove")))
        if not pl:
            return JSONResponse({"ok": False, "msg": err})
        return JSONResponse(dict(_plan_json(pl), ok=True))

    @app.post("/admin/handover/apply")
    async def admin_handover_apply(req: Request):
        u = require(req, ["admin", "ceo"])
        if not u:
            return JSONResponse({"ok": False, "msg": "로그인이 필요합니다"}, 401)
        b = await _read(req) or {}
        kind = b.get("kind")
        if kind not in ("transfer", "delegate"):
            return JSONResponse({"ok": False, "msg": "담당 교체·기간 맡기기 가운데 골라 주세요"})
        me = u.get("id")
        now_s = kst_now().strftime("%Y-%m-%d %H:%M")
        with db_session() as c:
            pl, err = _plan(c, kind, int(b.get("from") or 0), int(b.get("to") or 0), b.get("items") or [], bool(b.get("remove")))
            if not pl:
                return JSONResponse({"ok": False, "msg": err})
            fn, tn = pl["from"]["name"], pl["to"]["name"]
            if kind == "transfer":
                note = "담당 교체 %s → %s" % (fn, tn)
                added = _set_items(c, pl["to"]["id"], me, pl["added"], True, note)
                removed = _set_items(c, pl["from"]["id"], me, pl["removed"], False, note) if pl["removed"] else []
                c.execute("INSERT INTO perm_handover(kind, from_user, to_user, items_json, added_json, removed_json, starts_at, status, note, created_by) "
                          "VALUES('transfer',?,?,?,?,?,?,'done',?,?)",
                          (pl["from"]["id"], pl["to"]["id"], json.dumps(pl["items"]), json.dumps(added), json.dumps(removed), now_s,
                           (b.get("note") or "")[:200], me))
                msg = "%s에게 %d가지를 넘겼습니다" % (tn, len(added)) + (" · %s에게서 %d가지를 뺐습니다" % (fn, len(removed)) if removed else "")
                return JSONResponse({"ok": True, "msg": msg})
            st = _to_kst(b.get("starts") or "", u) or now_s
            en = _to_kst(b.get("ends") or "", u)
            if not en:
                return JSONResponse({"ok": False, "msg": "끝나는 날짜·시각을 넣어 주세요"})
            if en <= st or en <= now_s:
                return JSONResponse({"ok": False, "msg": "끝나는 때는 시작보다, 그리고 지금보다 뒤여야 합니다"})
            c.execute("INSERT INTO perm_handover(kind, from_user, to_user, items_json, starts_at, ends_at, status, note, created_by) "
                      "VALUES('delegate',?,?,?,?,?,'pending',?,?)",
                      (pl["from"]["id"], pl["to"]["id"], json.dumps(pl["items"]), st, en, (b.get("note") or "")[:200], me))
        res = run_due()
        when = "지금부터" if st <= now_s else (_fmt_local(st, u) + "부터")
        tail = " (월요일 새벽 백업 시간이라 07:30 뒤에 시작합니다)" if res.get("skipped") and st <= now_s else ""
        return JSONResponse({"ok": True, "msg": "%s에게 %s %s까지 맡겼습니다. 끝나면 저절로 원래대로 돌아갑니다.%s" % (tn, when, _fmt_local(en, u), tail)})

    @app.post("/admin/handover/{hid:int}/end")
    async def admin_handover_end(req: Request, hid: int):
        u = require(req, ["admin", "ceo"])
        if not u:
            return JSONResponse({"ok": False, "msg": "로그인이 필요합니다"}, 401)
        now_s = kst_now().strftime("%Y-%m-%d %H:%M")
        with db_session() as c:
            r = c.execute("SELECT * FROM perm_handover WHERE id=? AND kind='delegate'", (hid,)).fetchone()
            if not r:
                return JSONResponse({"ok": False, "msg": "그 맡기기를 찾지 못했습니다"}, 404)
            r = dict(r)
            if r["status"] == "pending":
                c.execute("UPDATE perm_handover SET status='ended', added_json='[]', ended_at=?, ended_by=?, end_note=? WHERE id=? AND status='pending'",
                          (now_s, u.get("id"), "시작 전에 취소", hid))
                return JSONResponse({"ok": True, "msg": "시작 전에 취소했습니다"})
            if r["status"] != "active":
                return JSONResponse({"ok": False, "msg": "이미 끝난 맡기기입니다"})
            rm = _end(c, r, u.get("id"), "일찍 끝냄", now_s)
        return JSONResponse({"ok": True, "msg": "끝냈습니다 · 받은 사람에게서 %d가지를 원래대로 돌렸습니다" % len(rm)})

    # ───────────────────────── 부서 ─────────────────────────
    @app.get("/admin/depts", response_class=HTMLResponse)
    async def admin_depts(req: Request):
        u = require(req, ["admin", "ceo"])
        if not u:
            return RedirectResponse("/login", 303)
        with db_session() as c:
            policy = load_policy(c)
            teams = [dict(r) for r in c.execute(
                "SELECT t.*, l.name AS leader_name, p.name AS parent_name, "
                "(SELECT COUNT(*) FROM users x WHERE x.team_id=t.id AND COALESCE(x.is_active,1)=1) AS n "
                "FROM teams t LEFT JOIN users l ON l.id=t.leader_id LEFT JOIN teams p ON p.id=t.parent_team_id "
                "ORDER BY CASE WHEN COALESCE(t.entity,'')='VN' THEN 1 ELSE 0 END, t.display_order, t.name")]
        for t in teams:
            t["corp"] = "법인" if (t.get("entity") == "VN" or t.get("id") == 12) else "본사"
            t["sens"] = [lbl for cat, lbl in field_labels.items() if t["id"] in (policy.get(cat) or set())]
        return ctx(req, "admin_depts.html", user=u, active="admin", teams=teams)

    return {"run_due": run_due}
