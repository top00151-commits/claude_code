"""
👁 「이 사람들도 보기」 (2026-10-08 대표 지시) — meeting_viewers 새 표 (idempotent · CREATE TABLE IF NOT EXISTS)

대표 지시: 「회의록 공개범위 관련해서 회의설정시 참여자는 상관없이 공유가 되는데…
          회의 참석하지 않은 특정 인원들에게도 보일 수 있게 공개범위를 **직원 선택**이 가능하도록 했으면 좋겠어…
          만약 내가 회의 참석을 안 했는데 공개범위를 팀으로 한정하면 나는 볼 수 있는 방법이 없어」
대표 결정(2026-10-08):
  · 지금 공개 범위 5가지(비공개·팀·본사·법인·본사+법인)는 **그대로 두고** 「이 사람들도 보기」를 **더한다**
    → 「팀 공개 + 콕 집은 3명」처럼 겹쳐 쓸 수 있다
  · 그 명단을 고칠 수 있는 사람 = **회의록을 고칠 수 있는 사람**(작성자·이음 등록 담당·참석자·관리자/대표)
  · 고른 사람은 **보기만** 한다(고치기·지우기·녹음 권한은 그대로)

🔴 왜 meeting_attendees(참석자) 에 넣지 않았나:
  참석자 명단은 **저장할 때마다 참석자 글자에서 통째로 다시 만들어진다**(_sync_attendees 는 DELETE 후 INSERT).
  이음 참석자 명단 맞추기(z1134)도 같은 표를 덮어쓴다.
  거기에 열람자를 넣으면 ①다음 저장에 **소리 없이 사라지고** ②오지도 않은 사람이 **참석자로 기록**된다
  (회의록 양식·참석자 수·일일카드 배정까지 틀어진다).

칸:
  - meeting_id : 그 회의록(meetings.id)
  - user_id    : 볼 수 있게 해 준 직원(users.id) — 🔴 사람 참조는 항상 ID
  - added_by   : 누가 넣었는지(users.id) — 권한을 넓힌 기록은 남긴다
  - 한 회의에 같은 사람 두 번 = 기본키로 막는다

⚠ startup() 에서 1회 호출 · 기존 DB 에도 안전(새 표 하나) · 업무데이터는 건드리지 않는다.
"""
import sqlite3


def _has_table(c, t: str) -> bool:
    return bool(c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone())


SCHEMA_SQL = r"""
CREATE TABLE IF NOT EXISTS meeting_viewers (
    meeting_id  INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    added_by    INTEGER REFERENCES users(id),
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (meeting_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_meeting_viewers_user ON meeting_viewers(user_id, meeting_id);
"""


def migrate(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    made = []
    if not _has_table(c, "meeting_viewers"):
        made.append("meeting_viewers")
    c.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
    return {"added": made}


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    print(migrate(os.path.join(here, "..", "..", "data", "knk.db")))
