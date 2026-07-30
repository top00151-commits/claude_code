# -*- coding: utf-8 -*-
"""WP-04 B-0 — BOM 현행 **읽기 전용** 실측
근거: 대표/게이트 승인 `CHATGPT_WP04_B0실측승인_및_A단계_사용자검증결정_2026-07-31_0038.md` §3

⛔ §3.2 금지 절대준수 — 아래를 **한 글자도 출력하지 않는다**:
   품명·품번·고객명·협력사명·담당자명 / 단가·금액·거래내용 / 메시지·메모·비고 원문 /
   첨부 내용 / 개별 행 원문 / 개인정보·비밀번호·토큰
   → 이 스크립트는 **집계 숫자와 스키마 이름만** 출력한다.
⛔ 쓰기 없음(SELECT·PRAGMA 만) · mode=ro · 재시작 없음 · 마이그레이션 없음.

§3.1 허용 조회 9종을 순서대로 수행한다.
"""
import sqlite3
import sys
import time

DB = sys.argv[1] if len(sys.argv) > 1 else "/opt/knk_haist/data/knk.db"
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
q = con.execute
T0 = time.time()

BOM_TABLES = ("bom_uploads", "bom_items", "bom_item_history")


def head(t):
    print("\n" + "=" * 74)
    print(f" {t}")
    print("=" * 74)


def exists(name, kind="table"):
    return bool(q("SELECT 1 FROM sqlite_master WHERE type=? AND name=?", (kind, name)).fetchone())


def cnt(sql, args=()):
    try:
        return q(sql, args).fetchone()[0]
    except Exception as e:
        return f"(조회불가: {type(e).__name__})"


print("=" * 74)
print(" WP-04 B-0 — BOM 현행 읽기 전용 실측")
print("=" * 74)
print(f" DB          : {DB} (mode=ro)")
print(f" 시작        : (호출 셸에서 기록)")
print(" 출력 원칙   : 집계 숫자 + 스키마 이름만. 개별 행·품명·금액·개인정보 없음.")

# ── ① 스키마: 표·열·PK·FK·인덱스·뷰·트리거 ────────────────────────────────
head("① BOM 관련 스키마 — 존재 여부와 개수")
for t in BOM_TABLES:
    if not exists(t):
        print(f"  {t:20s} ❌ 없음")
        continue
    cols = q(f"PRAGMA table_info({t})").fetchall()
    pk = [c["name"] for c in cols if c["pk"]]
    fks = q(f"PRAGMA foreign_key_list({t})").fetchall()
    idx = q(f"PRAGMA index_list({t})").fetchall()
    print(f"  {t:20s} ✅ 열 {len(cols):2d}개 · PK {pk} · FK {len(fks)}개 · 인덱스 {len(idx)}개")
    for f in fks:
        print(f"       └ FK  {f['from']} → {f['table']}.{f['to']}")
    for i in idx:
        print(f"       └ IDX {i['name']}")

nv = cnt("SELECT COUNT(*) FROM sqlite_master WHERE type='view' AND name LIKE '%bom%'")
nt = cnt("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE '%bom%'")
print(f"\n  BOM 관련 뷰 {nv}개 · 트리거 {nt}개")

# ── ② 표별 전체 행 수 ────────────────────────────────────────────────────
head("② 표별 전체 행 수")
for t in BOM_TABLES:
    print(f"  {t:20s} {cnt(f'SELECT COUNT(*) FROM {t}'):>8}행")

# ── ③ 상태별·연도별·프로젝트 상태별 집계 ─────────────────────────────────
head("③ 상태별 · 연도별 · 프로젝트 상태별 집계")
print("  [bom_items.status]")
for r in q("SELECT COALESCE(status,'(빈칸)') k, COUNT(*) n FROM bom_items GROUP BY k ORDER BY n DESC"):
    print(f"     {r['k']:<14} {r['n']:>7}")
print("  [bom_items.item_type]")
for r in q("SELECT COALESCE(item_type,'(빈칸)') k, COUNT(*) n FROM bom_items GROUP BY k ORDER BY n DESC"):
    print(f"     {r['k']:<14} {r['n']:>7}")
print("  [bom_items.order_status] — 발주 진행 표시")
for r in q("SELECT COALESCE(order_status,'(빈칸)') k, COUNT(*) n FROM bom_items GROUP BY k ORDER BY n DESC"):
    print(f"     {r['k']:<14} {r['n']:>7}")
print("  [bom_uploads 연도별]")
for r in q("SELECT substr(created_at,1,4) y, COUNT(*) n FROM bom_uploads GROUP BY y ORDER BY y"):
    print(f"     {r['y'] or '(빈칸)':<14} {r['n']:>7}")
print("  [bom_uploads.mode]")
for r in q("SELECT COALESCE(mode,'(빈칸)') k, COUNT(*) n FROM bom_uploads GROUP BY k ORDER BY n DESC"):
    print(f"     {r['k']:<14} {r['n']:>7}")
print("  [BOM 보유 프로젝트의 projects.status 별 프로젝트 수]")
for r in q("SELECT COALESCE(p.status,'(빈칸)') k, COUNT(DISTINCT p.id) n"
           " FROM projects p WHERE EXISTS(SELECT 1 FROM bom_items b WHERE b.project_id=p.id)"
           " GROUP BY k ORDER BY n DESC"):
    print(f"     {r['k']:<14} {r['n']:>7}")

# ── ④ 필수 연결키 NULL/비NULL ────────────────────────────────────────────
head("④ 필수 연결키 NULL · 비NULL 건수와 비율")


def nullrate(table, col):
    tot = cnt(f"SELECT COUNT(*) FROM {table}")
    if not isinstance(tot, int) or tot == 0:
        print(f"  {table}.{col:<18} 행 없음")
        return
    nul = cnt(f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL")
    print(f"  {table}.{col:<18} 전체 {tot:>7} · NULL {nul:>6} ({nul*100.0/tot:5.1f}%) · 비NULL {tot-nul:>7}")


for c in ("project_id", "part_id", "first_upload_id", "last_upload_id", "part_no_norm"):
    nullrate("bom_items", c)
for c in ("project_id", "uploaded_by", "source_filename", "sheet_names"):
    nullrate("bom_uploads", c)
for c in ("item_id", "project_id", "upload_id", "changed_by"):
    nullrate("bom_item_history", c)

print("\n  [참조 무결성 — 끊어진 연결 건수]")
print(f"     bom_items → projects 없음      : {cnt('SELECT COUNT(*) FROM bom_items b LEFT JOIN projects p ON p.id=b.project_id WHERE p.id IS NULL')}")
print(f"     bom_uploads → projects 없음    : {cnt('SELECT COUNT(*) FROM bom_uploads u LEFT JOIN projects p ON p.id=u.project_id WHERE p.id IS NULL')}")
print(f"     bom_item_history → bom_items 없음: {cnt('SELECT COUNT(*) FROM bom_item_history h LEFT JOIN bom_items b ON b.id=h.item_id WHERE b.id IS NULL')}")

# ── ⑤ 프로젝트별 BOM 존재 여부 집계 ──────────────────────────────────────
head("⑤ 프로젝트별 BOM 존재 여부")
print(f"  전체 프로젝트                : {cnt('SELECT COUNT(*) FROM projects')}")
print(f"  BOM 품목이 있는 프로젝트     : {cnt('SELECT COUNT(DISTINCT project_id) FROM bom_items')}")
print(f"  업로드 기록이 있는 프로젝트  : {cnt('SELECT COUNT(DISTINCT project_id) FROM bom_uploads')}")
_act_prj = cnt("SELECT COUNT(DISTINCT project_id) FROM bom_items WHERE status='활성'")
print(f"  활성 BOM 품목이 있는 프로젝트: {_act_prj}")
print("\n  [프로젝트당 활성 BOM 품목 수 구간별 프로젝트 수]")
for r in q("SELECT CASE WHEN n=0 THEN '0' WHEN n<=50 THEN '1~50' WHEN n<=200 THEN '51~200'"
           "        WHEN n<=500 THEN '201~500' ELSE '501+' END band, COUNT(*) c FROM ("
           "  SELECT project_id, COUNT(*) n FROM bom_items WHERE status='활성' GROUP BY project_id"
           ") GROUP BY band ORDER BY c DESC"):
    print(f"     {r['band']:<10} {r['c']:>5} 프로젝트")
print("\n  [프로젝트당 업로드 차수(version_no) 최댓값 분포]")
for r in q("SELECT mx, COUNT(*) c FROM (SELECT project_id, MAX(version_no) mx FROM bom_uploads GROUP BY project_id)"
           " GROUP BY mx ORDER BY mx"):
    print(f"     v{r['mx']:<9} {r['c']:>5} 프로젝트")

# ── ⑥ 업로드 파일 중복 여부 집계 ─────────────────────────────────────────
head("⑥ 업로드 파일 중복 여부 (건수만 · 파일명 출력 안 함)")
_dupc = cnt("SELECT COUNT(*) FROM (SELECT project_id, source_filename FROM bom_uploads"
            " WHERE COALESCE(source_filename,'')<>'' GROUP BY project_id, source_filename HAVING COUNT(*)>1)")
print(f"  같은 프로젝트에 같은 파일명이 2회 이상 올라간 조합 수 : {_dupc}")
_dupr = cnt("SELECT COALESCE(SUM(n),0) FROM (SELECT COUNT(*) n FROM bom_uploads"
            " WHERE COALESCE(source_filename,'')<>'' GROUP BY project_id, source_filename HAVING COUNT(*)>1)")
print(f"  그 조합에 속한 업로드 행 수                            : {_dupr}")
_multi = cnt("SELECT COUNT(*) FROM bom_uploads WHERE sheet_names LIKE '%,%'")
print(f"  적용 시트가 2개 이상인 업로드 수                        : {_multi}")

# ── ⑦ 외부 Revision 자동 식별 집계 ───────────────────────────────────────
head("⑦ 외부 Revision 표기 — 자동 식별 집계 (파일명 원문 출력 안 함)")
tot_u = cnt("SELECT COUNT(*) FROM bom_uploads")
pat_r = cnt(r"SELECT COUNT(*) FROM bom_uploads WHERE source_filename LIKE '%-R_' OR source_filename LIKE '%-R_.%' OR source_filename LIKE '%_R_%'")
pat_ver = cnt(r"SELECT COUNT(*) FROM bom_uploads WHERE UPPER(source_filename) LIKE '%VER%'")
pat_rev = cnt(r"SELECT COUNT(*) FROM bom_uploads WHERE UPPER(source_filename) LIKE '%REV%'")
no_name = cnt("SELECT COUNT(*) FROM bom_uploads WHERE COALESCE(source_filename,'')=''")
print(f"  업로드 전체                         : {tot_u}")
print(f"  파일명에 'R숫자' 형태 포함           : {pat_r}")
print(f"  파일명에 'VER' 포함                  : {pat_ver}")
print(f"  파일명에 'REV' 포함                  : {pat_rev}")
print(f"  파일명 자체가 비어 있음              : {no_name}")
print("  ⚠ 위는 **파일명 패턴 집계**일 뿐이다. '자동인식 실패'와 '외부 Revision 표기 없음'은")
print("     파일명만으로 구분할 수 없다 — 사람 확인이 필요하다(B-P0-3).")

# ── ⑧ 초기 Release 대상 후보 ─────────────────────────────────────────────
head("⑧ 활성·종료 프로젝트별 초기 Release 대상 후보 건수")
for r in q("SELECT COALESCE(p.status,'(빈칸)') st, COUNT(DISTINCT p.id) prj,"
           " SUM((SELECT COUNT(*) FROM bom_items b WHERE b.project_id=p.id AND b.status='활성')) items"
           " FROM projects p WHERE EXISTS(SELECT 1 FROM bom_items b2 WHERE b2.project_id=p.id AND b2.status='활성')"
           " GROUP BY st ORDER BY prj DESC"):
    print(f"  {r['st']:<14} 프로젝트 {r['prj']:>4} · 활성 BOM 품목 {r['items']:>7}")

# ── ⑨ BOM ↔ 구매요청·발주 연결 ───────────────────────────────────────────
head("⑨ 현재 BOM 과 구매요청·발주 연결 여부 집계")
_ord = cnt("SELECT COUNT(*) FROM bom_items WHERE COALESCE(order_status,'미발주')<>'미발주'")
print(f"  bom_items.order_status 가 '미발주' 아닌 행 : {_ord}")
print(f"  review_flag(발주 후 변경) = 1 인 행        : {cnt('SELECT COUNT(*) FROM bom_items WHERE COALESCE(review_flag,0)=1')}")
print(f"  bom_uploads.ordered_warn 합계              : {cnt('SELECT COALESCE(SUM(ordered_warn),0) FROM bom_uploads')}")
if exists("po_item_project_links"):
    print(f"  BOM 보유 프로젝트 중 발주 연결이 있는 수   : "
          f"{cnt('SELECT COUNT(DISTINCT l.project_id) FROM po_item_project_links l WHERE EXISTS(SELECT 1 FROM bom_items b WHERE b.project_id=l.project_id)')}")
else:
    print("  po_item_project_links 표 없음")
print(f"  bom_items.part_id 연결(자재 마스터) 있는 행: {cnt('SELECT COUNT(*) FROM bom_items WHERE part_id IS NOT NULL')}")

con.close()
print("\n" + "=" * 74)
print(f" 조회 끝 — SELECT·PRAGMA 만 수행. 쓰기·삭제·보정 없음. 소요 {time.time()-T0:.1f}초")
print("=" * 74)
