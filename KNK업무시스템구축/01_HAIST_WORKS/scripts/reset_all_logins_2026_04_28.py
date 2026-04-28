"""
2026-04-28 대표 지시 — 전 직원 login_id (한글→로마자 첫글자) + 비번 knk1234 일괄 리셋.
사용: cd 01_HAIST_WORKS && python scripts/reset_all_logins_2026_04_28.py [--apply]
DRY-RUN 기본. --apply 전달 시 실제 UPDATE.
"""
import sys, os, sqlite3, hashlib, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB   = ROOT / "data" / "knk.db"
OUT  = ROOT / "_전직원_로그인계정_2026-04-28.csv"

# 초성 19개 (김→k 등 KNK 관습 우선)
CHO = ['k','k','n','d','d','r','m','b','p','s','s','','j','j','c','k','t','p','h']
# ㅇ-초성일 때 중성 첫글자 매핑 (실용 영문 표기)
JUNG = ['a','a','y','y','e','e','y','y','o','w','w','o','y','u','w','w','w','y','u','i','i']

# 자주 쓰이는 surname 의 관습 표기 (ㅇ 시작 surname)
SURNAME_HACK = {
    '이': 'l', '임': 'l', '안': 'a', '오': 'o', '우': 'w', '윤': 'y',
    '양': 'y', '유': 'y', '엄': 'e', '여': 'y', '연': 'y', '염': 'y',
    '원': 'w', '위': 'w', '왕': 'w', '예': 'y', '온': 'o',
}

def syl_to_roman(syl: str, is_first: bool) -> str:
    """한 음절(syllable) → 로마자 첫 1글자."""
    if not syl: return ''
    if is_first and syl in SURNAME_HACK:
        return SURNAME_HACK[syl]
    code = ord(syl) - 0xAC00
    if not (0 <= code <= 11171):
        # 한글 음절 아님 → ASCII 첫글자
        c = syl[0].lower()
        return c if c.isalpha() else ''
    cho_idx = code // (21 * 28)
    jung_idx = (code % (21 * 28)) // 28
    initial = CHO[cho_idx]
    if initial:
        return initial
    # ㅇ 초성 → 중성 첫글자
    return JUNG[jung_idx]

def name_to_id(name: str) -> str:
    """한글 이름 → 로마자 약자 (예: 김정락→kjr · 안지연→ajy)."""
    s = name.strip()
    if not s: return 'user'
    # 영문 이름이면 lowercase ASCII 만 추출
    if all(ord(c) < 128 for c in s):
        return ''.join(c for c in s.lower() if c.isalnum())[:8] or 'user'
    out = []
    for i, c in enumerate(s):
        if c in (' ', '·', '.', ','): continue
        r = syl_to_roman(c, i == 0)
        if r: out.append(r)
    return ''.join(out) or 'user'

def hash_pw(pw: str) -> str:
    return hashlib.sha256(("knk-haist-" + pw).encode()).hexdigest()

def main():
    apply = '--apply' in sys.argv
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, name, login_id, role, team_id FROM users WHERE is_active=1 ORDER BY id"
    ).fetchall()
    teams = {r[0]: r[1] for r in con.execute("SELECT id, name FROM teams").fetchall()}

    NEW_PW = "knk1234"
    new_pw_hash = hash_pw(NEW_PW)

    # 1) 신규 id 생성 + 충돌 해결
    used = set()
    plan = []  # (uid, name, old_id, new_id, team_name, role)
    # admin 계정은 'admin' 그대로 유지
    for r in rows:
        old_id = r['login_id']
        if r['name'] == '시스템관리자' or old_id == 'admin':
            new_id = 'admin'
        else:
            base = name_to_id(r['name'])
            new_id = base
            n = 2
            while new_id in used:
                new_id = f"{base}{n}"
                n += 1
        used.add(new_id)
        plan.append((r['id'], r['name'], old_id, new_id,
                     teams.get(r['team_id'], '-'), r['role']))

    # 2) 출력
    print(f"=== {'APPLY' if apply else 'DRY-RUN'} · 84명 일괄 리셋 ===")
    print(f"비밀번호: {NEW_PW} (hash: sha256('knk-haist-...'))")
    print(f"{'ID':>3} {'팀':<14} {'역할':<10} {'이름':<10} {'OLD':<14} → NEW")
    print('-' * 80)
    for uid, name, old, new, team, role in plan:
        marker = '*' if old != new else ' '
        print(f"{uid:>3} {team:<14} {role:<10} {name:<10} {old:<14} → {new}{marker}")

    # 3) CSV 출력 (배포용)
    if apply:
        with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['id', '팀', '역할', '이름', '로그인ID', '비밀번호'])
            for uid, name, old, new, team, role in plan:
                w.writerow([uid, team, role, name, new, NEW_PW])
        print(f"\n[CSV 저장] {OUT}")

    # 4) UPDATE
    if apply:
        for uid, name, old, new, team, role in plan:
            con.execute(
                "UPDATE users SET login_id=?, password=? WHERE id=?",
                (new, new_pw_hash, uid)
            )
        con.commit()
        print(f"\n[DB 갱신] {len(plan)}명 login_id + password 업데이트 완료.")
    else:
        print("\n[DRY-RUN] 실제 적용은 --apply 전달.")
    con.close()

if __name__ == '__main__':
    main()
