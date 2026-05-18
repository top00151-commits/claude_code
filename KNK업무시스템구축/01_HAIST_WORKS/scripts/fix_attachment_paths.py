# -*- coding: utf-8 -*-
"""
v5H226z103 (2026-05-16) — 첨부 파일 경로 수정

원인: gen_test_attachments.py 가 data/uploads/parts/ 에 저장했으나
       main.py 의 _PARTS_UPLOAD_ROOT 는 01_HAIST_WORKS/uploads/parts/
       → 보안 검증 실패 → 다운로드/이미지 깨짐

조치: 폴더 이동 + DB file_path 일괄 갱신
"""
import os, sys, shutil, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # 01_HAIST_WORKS
SRC  = ROOT / "data" / "uploads" / "parts"
DST  = ROOT / "uploads" / "parts"

print(f"SRC: {SRC}")
print(f"DST: {DST}")
DST.parent.mkdir(parents=True, exist_ok=True)

# 1. 폴더 이동
moved = 0
if SRC.exists():
    DST.mkdir(parents=True, exist_ok=True)
    for entry in SRC.iterdir():
        target = DST / entry.name
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        shutil.move(str(entry), str(target))
        moved += 1
    # SRC 비어있으면 제거
    try:
        SRC.rmdir()
    except OSError:
        pass
    print(f"폴더 {moved}개 이동 완료")
else:
    print("SRC 없음 — 이미 이동됐거나 미생성")

# 2. DB UPDATE
DB = ROOT / "data" / "knk.db"
old_seg = os.sep.join(["01_HAIST_WORKS", "data", "uploads", "parts"])
new_seg = os.sep.join(["01_HAIST_WORKS", "uploads", "parts"])
print(f"OLD segment: {old_seg}")
print(f"NEW segment: {new_seg}")

con = sqlite3.connect(str(DB))
cur = con.cursor()
before = cur.execute(
    "SELECT COUNT(*) FROM part_attachments WHERE file_path LIKE ?",
    (f"%{old_seg}%",)
).fetchone()[0]
print(f"DB 갱신 대상: {before}건")

cur.execute(
    "UPDATE part_attachments SET file_path = REPLACE(file_path, ?, ?)",
    (old_seg, new_seg)
)
con.commit()
after = cur.execute(
    "SELECT COUNT(*) FROM part_attachments WHERE file_path LIKE ?",
    (f"%{old_seg}%",)
).fetchone()[0]
print(f"갱신 후 남은 잘못된 경로: {after}건")

# 3. 검증
print()
print("샘플 3건 검증:")
ok, fail = 0, 0
for row in cur.execute("SELECT id, file_path FROM part_attachments ORDER BY id"):
    if os.path.exists(row[1]):
        ok += 1
    else:
        fail += 1
        if fail <= 3:
            print(f"  [MISS] [{row[0]}] {row[1]}")

print(f"  존재: {ok}건  /  소실: {fail}건")
con.close()
