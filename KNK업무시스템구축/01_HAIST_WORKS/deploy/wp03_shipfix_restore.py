# -*- coding: utf-8 -*-
"""WP-03 23대 출하 보정 — **범위 제한 복구 스크립트** (승인서 §5.2)

[승인서 `CHATGPT_WP03_23대_출하보정_최종실행승인_2026-07-26.md`]
  §5.1 실행 전 **범용 되돌리기 버튼은 만들지 않는다.**
  §5.2 복구수단은 ① 보정 직전 운영 DB 전체 백업 ② 23대의 전·후 이력을 이용한
       **범위 제한 복구 스크립트** 두 가지다.
       "복구 스크립트는 운영에서 처음 시험하지 않는다" → 반드시 백업 사본에서 리허설한 뒤 쓴다.

⭐ 설계 원칙
  · **스냅샷이 단일 근거**다. 보정 이력(old_*/new_*)만으로는 confirmed_by·confirmed_at 등
    되돌릴 값이 전부 담기지 않으므로, 실행 직전에 대상 프로젝트의 **모든 행 전체 칸**을 뜬다.
  · 범위는 오직 **스냅샷에 들어 있는 행**뿐이다. 다른 프로젝트·다른 표는 절대 건드리지 않는다.
  · 기본은 **미리보기(dry-run)**. `--apply` 를 붙여야 실제로 쓴다.
  · 감사기록(project_unit_audit)은 **지우지 않는다**. 보정도 복구도 사실이므로 둘 다 남긴다.
    되돌리며 지운 보정 이력 행은 `<스냅샷>.restorelog.json` 에 원문 그대로 보관한다.

사용법 (01_HAIST_WORKS 루트에서)
    python deploy/wp03_shipfix_restore.py snapshot --db data/knk.db --project 821 --out snap.json
    python deploy/wp03_shipfix_restore.py verify   --db data/knk.db --snapshot snap.json
    python deploy/wp03_shipfix_restore.py restore  --db data/knk.db --snapshot snap.json \
                                                   --reason "..." --actor 85 --apply
    python deploy/wp03_shipfix_restore.py compare  --db work.db --base pristine.db
"""
import argparse
import json
import os
import sqlite3
import sys

# ── 되돌릴 표와 그 범위 ────────────────────────────────────────────────────────
#   {표이름: 범위 SQL}  — :units 는 대상 호기 id 목록, :pid 는 프로젝트 id 로 치환된다.
#   ⛔ 여기 없는 표는 스냅샷도 복구도 하지 않는다(= 절대 건드리지 않는다).
SCOPED_TABLES = (
    ("project_units", "id IN ({units})"),
    ("project_unit_identifier_history", "project_unit_id IN ({units})"),
    ("project_unit_order_links", "project_unit_id IN ({units})"),
    ("project_unit_relations", "source_unit_id IN ({units}) OR result_unit_id IN ({units})"),
    ("project_unit_status_backfill", "project_id = {pid} OR project_unit_id IN ({units})"),
    ("project_unit_candidate_skips", "project_id = {pid}"),
)
# 감사기록은 복구 대상이 아니다(지우지 않는다). 몇 번까지가 보정 전이었는지만 기록해 둔다.
AUDIT_TABLE = "project_unit_audit"


def _conn(path, readonly=False):
    if readonly:
        c = sqlite3.connect("file:%s?mode=ro" % path.replace("?", "%3f"), uri=True)
    else:
        c = sqlite3.connect(path, timeout=30.0)
        c.execute("PRAGMA foreign_keys=ON")
    c.row_factory = sqlite3.Row
    return c


def _has(c, table):
    return bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                          (table,)).fetchone())


def _cols(c, table):
    return [r[1] for r in c.execute("PRAGMA table_info(%s)" % table).fetchall()]


def _where(tpl, units, pid):
    ulist = ",".join(str(int(x)) for x in units) or "-1"
    return tpl.format(units=ulist, pid=int(pid))


# ══════════════════════════════════════════════════════════════════════════════
# snapshot — 실행 직전 전체 행 스냅샷
# ══════════════════════════════════════════════════════════════════════════════
def cmd_snapshot(a):
    c = _conn(a.db, readonly=True)
    units = [r[0] for r in c.execute(
        "SELECT id FROM project_units WHERE project_id=? ORDER BY id", (a.project,)).fetchall()]
    if not units:
        print("[중단] project_id %s 에 호기가 없습니다." % a.project)
        return 2
    proj = c.execute("SELECT id, mgmt_code, name FROM projects WHERE id=?",
                     (a.project,)).fetchone()
    snap = {
        "db": os.path.abspath(a.db),
        "project_id": a.project,
        "mgmt_code": proj["mgmt_code"] if proj else None,
        "unit_ids": units,
        "taken_at": c.execute("SELECT datetime('now','localtime')").fetchone()[0],
        "tables": {},
        "audit_max_id": 0,
    }
    for tbl, scope in SCOPED_TABLES:
        if not _has(c, tbl):
            snap["tables"][tbl] = {"missing": True, "cols": [], "rows": []}
            continue
        cols = _cols(c, tbl)
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM %s WHERE %s ORDER BY id" % (tbl, _where(scope, units, a.project)))]
        snap["tables"][tbl] = {"missing": False, "cols": cols, "rows": rows}
    if _has(c, AUDIT_TABLE):
        snap["audit_max_id"] = c.execute(
            "SELECT COALESCE(MAX(id),0) FROM %s" % AUDIT_TABLE).fetchone()[0]
    c.close()

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=1)
    print("== 스냅샷 저장 ==", a.out)
    print("  DB          :", snap["db"])
    print("  프로젝트    : %s (%s)" % (a.project, snap["mgmt_code"]))
    print("  대상 호기   : %d대  id %s ~ %s" % (len(units), units[0], units[-1]))
    print("  뜬 시각     :", snap["taken_at"])
    for tbl, _ in SCOPED_TABLES:
        t = snap["tables"][tbl]
        print("  %-34s %s" % (tbl, "표 없음" if t["missing"] else "%d행" % len(t["rows"])))
    print("  %-34s 마지막 id %s (복구 대상 아님)" % (AUDIT_TABLE, snap["audit_max_id"]))
    return 0


# ══════════════════════════════════════════════════════════════════════════════
# verify — 지금 DB 가 스냅샷과 같은가?
# ══════════════════════════════════════════════════════════════════════════════
def _diff(c, snap):
    """스냅샷 대비 지금 DB 의 차이. {표: {'update': [...], 'insert': [...], 'delete': [...]}}"""
    units, pid = snap["unit_ids"], snap["project_id"]
    out = {}
    for tbl, scope in SCOPED_TABLES:
        t = snap["tables"][tbl]
        if t["missing"] and not _has(c, tbl):
            continue
        now_rows = {}
        if _has(c, tbl):
            for r in c.execute("SELECT * FROM %s WHERE %s"
                               % (tbl, _where(scope, units, pid))):
                now_rows[r["id"]] = dict(r)
        snap_rows = {r["id"]: r for r in t["rows"]}
        upd, ins, dele = [], [], []
        for rid, want in snap_rows.items():
            have = now_rows.get(rid)
            if have is None:
                ins.append(want)
                continue
            changed = {k: (have.get(k), v) for k, v in want.items() if have.get(k) != v}
            if changed:
                upd.append({"id": rid, "fields": changed})
        for rid, have in now_rows.items():
            if rid not in snap_rows:
                dele.append(have)
        if upd or ins or dele:
            out[tbl] = {"update": upd, "insert": ins, "delete": dele}
    return out


def cmd_verify(a):
    snap = json.load(open(a.snapshot, encoding="utf-8"))
    c = _conn(a.db, readonly=True)
    d = _diff(c, snap)
    extra_audit = 0
    if _has(c, AUDIT_TABLE):
        extra_audit = c.execute("SELECT COUNT(*) FROM %s WHERE id>?" % AUDIT_TABLE,
                                (snap["audit_max_id"],)).fetchone()[0]
    c.close()
    print("== 스냅샷 대조 ==", a.db)
    print("  스냅샷      :", a.snapshot, "(", snap["taken_at"], ")")
    print("  대상 호기   : %d대" % len(snap["unit_ids"]))
    if not d:
        print("  결과        : ✅ 스냅샷과 **완전히 같음** (업무 데이터 차이 0)")
    for tbl, v in d.items():
        print("  %-34s 값다름 %d · 없어짐 %d · 새로생김 %d"
              % (tbl, len(v["update"]), len(v["insert"]), len(v["delete"])))
        for r in v["update"][:a.show]:
            for k, (nowv, wantv) in r["fields"].items():
                print("      id=%-6s %-22s 지금=%r  스냅샷=%r" % (r["id"], k, nowv, wantv))
        if len(v["update"]) > a.show:
            print("      ... 외 %d행" % (len(v["update"]) - a.show))
    print("  %-34s 보정 후 추가된 감사기록 %d건 (복구해도 남는다)" % (AUDIT_TABLE, extra_audit))
    return 0 if not d else 1


# ══════════════════════════════════════════════════════════════════════════════
# restore — 범위 제한 복구
# ══════════════════════════════════════════════════════════════════════════════
def cmd_restore(a):
    snap = json.load(open(a.snapshot, encoding="utf-8"))
    live = os.path.basename(a.db) == "knk.db"
    if a.apply and live and not a.allow_live:
        print("[중단] 운영 DB(knk.db) 에 쓰려면 --allow-live 를 함께 지정하세요.")
        return 2
    if a.apply and not (a.reason or "").strip():
        print("[중단] 복구 사유(--reason)를 반드시 적으세요.")
        return 2

    c = _conn(a.db)
    d = _diff(c, snap)
    print("== 범위 제한 복구 %s ==" % ("실행" if a.apply else "미리보기(dry-run)"))
    print("  DB          :", os.path.abspath(a.db))
    print("  스냅샷      : %s (%s)" % (a.snapshot, snap["taken_at"]))
    print("  범위        : project_id %s · 호기 %d대 · 표 %d개"
          % (snap["project_id"], len(snap["unit_ids"]), len(SCOPED_TABLES)))
    if not d:
        print("  결과        : 되돌릴 것이 없습니다(이미 스냅샷 상태).")
        c.close()
        return 0

    plan = []
    for tbl, v in d.items():
        print("  %-34s 값되돌림 %d · 다시넣기 %d · 지우기 %d"
              % (tbl, len(v["update"]), len(v["insert"]), len(v["delete"])))
        plan.append((tbl, v))
    if not a.apply:
        print("\n  ⚠ 미리보기입니다. 실제로 되돌리려면 --apply 를 붙이세요.")
        for tbl, v in plan:
            for r in v["update"][:a.show]:
                for k, (nowv, wantv) in r["fields"].items():
                    print("    %s id=%-6s %-20s %r → %r" % (tbl, r["id"], k, nowv, wantv))
        c.close()
        return 0

    log = {"db": os.path.abspath(a.db), "snapshot": os.path.abspath(a.snapshot),
           "reason": a.reason.strip(), "actor_id": a.actor, "deleted": {}, "restored": {}}
    try:
        c.execute("BEGIN IMMEDIATE")
        for tbl, v in plan:
            cols = snap["tables"][tbl]["cols"] or _cols(c, tbl)
            # ① 보정이 새로 만든 행 지우기 (원문은 로그에 보관)
            if v["delete"]:
                log["deleted"].setdefault(tbl, []).extend(v["delete"])
                c.executemany("DELETE FROM %s WHERE id=?" % tbl,
                              [(r["id"],) for r in v["delete"]])
            # ② 값이 바뀐 행 되돌리기 — 스냅샷의 **모든 칸**을 그대로 쓴다
            if v["update"]:
                setc = [k for k in cols if k != "id"]
                sql = "UPDATE %s SET %s WHERE id=?" % (
                    tbl, ", ".join("%s=?" % k for k in setc))
                rows = {r["id"]: r for r in snap["tables"][tbl]["rows"]}
                params = []
                for r in v["update"]:
                    want = rows[r["id"]]
                    params.append([want.get(k) for k in setc] + [r["id"]])
                c.executemany(sql, params)
                log["restored"].setdefault(tbl, []).extend(
                    [{"id": r["id"], "fields": {k: list(x) for k, x in r["fields"].items()}}
                     for r in v["update"]])
            # ③ 사라진 행 다시 넣기(있어서는 안 될 일이지만 방어)
            if v["insert"]:
                sql = "INSERT INTO %s (%s) VALUES (%s)" % (
                    tbl, ",".join(cols), ",".join("?" * len(cols)))
                c.executemany(sql, [[r.get(k) for k in cols] for r in v["insert"]])
                log["restored"].setdefault(tbl, []).append({"reinserted": len(v["insert"])})
        # ④ 복구 자체를 감사기록에 남긴다(지우지 않고 **더한다**)
        if _has(c, AUDIT_TABLE):
            c.execute(
                "INSERT INTO %s (actor_id, actor_name, action, target, note, created_at) "
                "VALUES (?,?,?,?,?, datetime('now','localtime'))" % AUDIT_TABLE,
                (a.actor, a.actor_name or "", "status_backfill_restore",
                 "project#%s" % snap["project_id"],
                 "[범위 제한 복구] 스냅샷 %s 로 되돌림 · 호기 %d대 · 사유: %s"
                 % (snap["taken_at"], len(snap["unit_ids"]), a.reason.strip())))
        c.commit()
    except Exception as e:
        c.rollback()
        c.close()
        print("  [실패·전체 취소]", e)
        return 3

    logpath = a.snapshot + ".restorelog.json"
    with open(logpath, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)
    left = _diff(c, snap)
    c.close()
    print("  복구 로그   :", logpath)
    print("  복구 후 대조: %s" % ("✅ 스냅샷과 완전히 같음"
                                  if not left else "❌ 아직 차이 %d표" % len(left)))
    return 0 if not left else 1


# ══════════════════════════════════════════════════════════════════════════════
# compare — 두 DB 전체 표 대조 (범위 밖이 안 변했는지 증명)
# ══════════════════════════════════════════════════════════════════════════════
def cmd_compare(a):
    c = sqlite3.connect("file:%s?mode=ro" % a.db, uri=True)
    c.execute("ATTACH DATABASE ? AS base", (a.base,))
    tabs_m = {r[0] for r in c.execute(
        "SELECT name FROM main.sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'")}
    tabs_b = {r[0] for r in c.execute(
        "SELECT name FROM base.sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'")}
    ignore = set(a.ignore or [])
    print("== 전체 표 대조 ==")
    print("  대상 : %s" % a.db)
    print("  기준 : %s" % a.base)
    only_m, only_b = sorted(tabs_m - tabs_b), sorted(tabs_b - tabs_m)
    if only_m:
        print("  ⚠ 대상에만 있는 표:", only_m)
    if only_b:
        print("  ⚠ 기준에만 있는 표:", only_b)
    diffs, same, skipped = [], 0, []
    for t in sorted(tabs_m & tabs_b):
        if t in ignore:
            skipped.append(t)
            continue
        cm = [r[1] for r in c.execute("PRAGMA main.table_info(%s)" % t)]
        cb = [r[1] for r in c.execute("PRAGMA base.table_info(%s)" % t)]
        if cm != cb:
            diffs.append((t, "칸 구성이 다름", 0, 0))
            continue
        try:
            add = c.execute("SELECT COUNT(*) FROM (SELECT * FROM main.%s "
                            "EXCEPT SELECT * FROM base.%s)" % (t, t)).fetchone()[0]
            rem = c.execute("SELECT COUNT(*) FROM (SELECT * FROM base.%s "
                            "EXCEPT SELECT * FROM main.%s)" % (t, t)).fetchone()[0]
        except Exception as e:
            diffs.append((t, "대조 실패: %s" % e, 0, 0))
            continue
        if add or rem:
            diffs.append((t, "", add, rem))
        else:
            same += 1
    print("  같은 표      : %d개" % same)
    if skipped:
        print("  건너뛴 표    : %s (지시로 제외)" % ", ".join(skipped))
    if not diffs:
        print("  결과         : ✅ 제외한 표 말고는 **전부 완전히 동일**")
    for t, note, add, rem in diffs:
        print("  ❌ %-34s %s대상에만 %d행 · 기준에만 %d행"
              % (t, (note + " · ") if note else "", add, rem))
    c.close()
    return 0 if not diffs else 1


def main(argv=None):
    p = argparse.ArgumentParser(description="WP-03 23대 출하 보정 범위 제한 복구")
    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("snapshot", help="실행 직전 전체 행 스냅샷")
    s.add_argument("--db", required=True)
    s.add_argument("--project", type=int, required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(fn=cmd_snapshot)

    s = sub.add_parser("verify", help="지금 DB 가 스냅샷과 같은지 대조")
    s.add_argument("--db", required=True)
    s.add_argument("--snapshot", required=True)
    s.add_argument("--show", type=int, default=8)
    s.set_defaults(fn=cmd_verify)

    s = sub.add_parser("restore", help="범위 제한 복구(기본은 미리보기)")
    s.add_argument("--db", required=True)
    s.add_argument("--snapshot", required=True)
    s.add_argument("--reason", default="")
    s.add_argument("--actor", type=int, default=0)
    s.add_argument("--actor-name", default="")
    s.add_argument("--show", type=int, default=8)
    s.add_argument("--apply", action="store_true", help="실제로 되돌린다")
    s.add_argument("--allow-live", action="store_true", help="운영 knk.db 에 쓸 때 필수")
    s.set_defaults(fn=cmd_restore)

    s = sub.add_parser("compare", help="두 DB 전체 표 대조")
    s.add_argument("--db", required=True)
    s.add_argument("--base", required=True)
    s.add_argument("--ignore", nargs="*", default=[])
    s.set_defaults(fn=cmd_compare)

    a = p.parse_args(argv)
    if not getattr(a, "fn", None):
        p.print_help()
        return 2
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
