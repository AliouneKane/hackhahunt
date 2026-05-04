import psycopg2
import psycopg2.pool
import os
from datetime import datetime
from typing import Optional

_pool: psycopg2.pool.SimpleConnectionPool | None = None


def _get_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.SimpleConnectionPool(1, 5, os.getenv("DATABASE_URL"))
    return _pool


def get_connection():
    return _get_pool().getconn()


def release_connection(conn):
    _get_pool().putconn(conn)


def _fetchall_dict(cursor) -> list:
    if cursor.description is None:
        return []
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _fetchone_dict(cursor) -> Optional[dict]:
    if cursor.description is None:
        return None
    cols = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    return dict(zip(cols, row)) if row else None


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS hackathons (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            source TEXT,
            theme TEXT,
            format TEXT,
            location TEXT,
            prize_1st TEXT,
            prize_2nd TEXT,
            prize_3rd TEXT,
            prize_min_fcfa INTEGER,
            language TEXT,
            deadline TEXT,
            duration TEXT,
            level TEXT,
            score INTEGER,
            discord_message_id TEXT,
            posted_at TEXT,
            status TEXT DEFAULT 'active',
            discord_posted_at TEXT,
            archived_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS interests (
            id SERIAL PRIMARY KEY,
            hackathon_id INTEGER NOT NULL,
            discord_user_id TEXT NOT NULL,
            discord_username TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hackathon_id, discord_user_id),
            FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id SERIAL PRIMARY KEY,
            hackathon_id INTEGER NOT NULL,
            voter_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hackathon_id, voter_id, target_id),
            FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id SERIAL PRIMARY KEY,
            hackathon_id INTEGER NOT NULL,
            channel_id TEXT,
            channel_name TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id SERIAL PRIMARY KEY,
            team_id INTEGER NOT NULL,
            discord_user_id TEXT NOT NULL,
            UNIQUE(team_id, discord_user_id),
            FOREIGN KEY(team_id) REFERENCES teams(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS welcomed (
            id SERIAL PRIMARY KEY,
            discord_user_id TEXT UNIQUE NOT NULL,
            welcomed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    release_connection(conn)
    print("✅ Base de données initialisée")


# ── Hackathons ────────────────────────────────────────────────────────────────
def insert_hackathon(data: dict) -> Optional[int]:
    conn = get_connection()
    c = conn.cursor()
    try:
        title = (data.get("title") or "").strip()
        if title:
            c.execute(
                "SELECT id FROM hackathons WHERE LOWER(TRIM(title)) = LOWER(%s)",
                (title,),
            )
            if c.fetchone():
                return None

        c.execute(
            """
            INSERT INTO hackathons
            (title, url, source, theme, format, location, prize_1st, prize_2nd,
             prize_3rd, prize_min_fcfa, language, deadline, duration, level, score, posted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                data.get("title"),
                data.get("url"),
                data.get("source"),
                data.get("theme"),
                data.get("format"),
                data.get("location"),
                data.get("prize_1st"),
                data.get("prize_2nd"),
                data.get("prize_3rd"),
                data.get("prize_min_fcfa", 0),
                data.get("language"),
                data.get("deadline"),
                data.get("duration"),
                data.get("level"),
                data.get("score"),
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        row = c.fetchone()
        return row[0] if row else None
    except psycopg2.IntegrityError:
        conn.rollback()
        return None
    finally:
        release_connection(conn)


def update_message_id(hackathon_id: int, message_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE hackathons SET discord_message_id = %s, discord_posted_at = %s WHERE id = %s",
        (message_id, datetime.now().isoformat(), hackathon_id),
    )
    conn.commit()
    release_connection(conn)


def get_active_hackathons() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM hackathons WHERE status = 'active' ORDER BY score DESC")
    rows = _fetchall_dict(c)
    release_connection(conn)
    return rows


def get_unposted_hackathons(limit: int = 10) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM hackathons WHERE discord_message_id IS NULL AND status = 'active' ORDER BY score DESC, id ASC LIMIT %s",
        (limit,),
    )
    rows = _fetchall_dict(c)
    release_connection(conn)
    return rows


def get_posted_hackathons() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM hackathons WHERE discord_message_id IS NOT NULL AND discord_message_id != 'duplicate_skipped' AND status = 'active'"
    )
    rows = _fetchall_dict(c)
    release_connection(conn)
    return rows


def delete_hackathon(hackathon_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM hackathons WHERE id = %s", (hackathon_id,))
    conn.commit()
    release_connection(conn)


def archive_hackathon(hackathon_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE hackathons SET status = 'archived', archived_at = %s WHERE id = %s",
        (datetime.now().isoformat(), hackathon_id),
    )
    conn.commit()
    release_connection(conn)


def get_stats() -> dict:
    conn = get_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("SELECT COUNT(*) FROM hackathons WHERE status = 'active'")
    total_active = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM hackathons WHERE status = 'active' AND discord_message_id IS NULL")
    total_pending = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM hackathons WHERE status = 'active' AND discord_message_id IS NOT NULL")
    total_posted = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM hackathons WHERE status = 'archived'")
    total_archived = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM hackathons WHERE posted_at LIKE %s", (f"{today}%",))
    scraped_today = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM hackathons WHERE discord_posted_at LIKE %s", (f"{today}%",))
    posted_today = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM hackathons WHERE archived_at LIKE %s", (f"{today}%",))
    archived_today = c.fetchone()[0]

    release_connection(conn)
    return {
        "total_active": total_active,
        "total_pending": total_pending,
        "total_posted": total_posted,
        "total_archived": total_archived,
        "scraped_today": scraped_today,
        "posted_today": posted_today,
        "archived_today": archived_today,
    }


def get_hackathon_by_title(title: str) -> Optional[dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM hackathons WHERE LOWER(TRIM(title)) = LOWER(%s) AND status = 'active'",
        (title,),
    )
    row = _fetchone_dict(c)
    release_connection(conn)
    return row


def get_hackathon_by_message(message_id: str) -> Optional[dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM hackathons WHERE discord_message_id = %s", (message_id,))
    row = _fetchone_dict(c)
    release_connection(conn)
    return row


# ── Intérêts ─────────────────────────────────────────────────────────────────
def add_interest(hackathon_id: int, user_id: str, username: str):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO interests (hackathon_id, discord_user_id, discord_username) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (hackathon_id, user_id, username),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
    finally:
        release_connection(conn)


def remove_interest(hackathon_id: int, user_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "DELETE FROM interests WHERE hackathon_id = %s AND discord_user_id = %s",
        (hackathon_id, user_id),
    )
    conn.commit()
    release_connection(conn)


def get_interested_users(hackathon_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT discord_user_id, discord_username FROM interests WHERE hackathon_id = %s",
        (hackathon_id,),
    )
    rows = _fetchall_dict(c)
    release_connection(conn)
    return rows


# ── Votes de matchmaking ──────────────────────────────────────────────────────
def add_vote(hackathon_id: int, voter_id: str, target_id: str):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO votes (hackathon_id, voter_id, target_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (hackathon_id, voter_id, target_id),
        )
        conn.commit()
    except psycopg2.IntegrityError:
        conn.rollback()
    finally:
        release_connection(conn)


def check_mutual_match(hackathon_id: int, user_a: str, user_b: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM votes WHERE hackathon_id=%s AND voter_id=%s AND target_id=%s",
        (hackathon_id, user_a, user_b),
    )
    a_voted_b = c.fetchone()
    c.execute(
        "SELECT 1 FROM votes WHERE hackathon_id=%s AND voter_id=%s AND target_id=%s",
        (hackathon_id, user_b, user_a),
    )
    b_voted_a = c.fetchone()
    release_connection(conn)
    return bool(a_voted_b and b_voted_a)


def get_user_votes(hackathon_id: int, voter_id: str) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT target_id FROM votes WHERE hackathon_id=%s AND voter_id=%s",
        (hackathon_id, voter_id),
    )
    rows = c.fetchall()
    release_connection(conn)
    return [r[0] for r in rows]


# ── Équipes ───────────────────────────────────────────────────────────────────
def create_team(
    hackathon_id: int, member_ids: list, channel_id: str, channel_name: str
) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO teams (hackathon_id, channel_id, channel_name) VALUES (%s, %s, %s) RETURNING id",
        (hackathon_id, channel_id, channel_name),
    )
    team_id = c.fetchone()[0]
    for uid in member_ids:
        c.execute(
            "INSERT INTO team_members (team_id, discord_user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (team_id, uid),
        )
    conn.commit()
    release_connection(conn)
    return team_id


def get_user_team(hackathon_id: int, user_id: str) -> Optional[dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT t.* FROM teams t
        JOIN team_members tm ON t.id = tm.team_id
        WHERE t.hackathon_id = %s AND tm.discord_user_id = %s
        """,
        (hackathon_id, user_id),
    )
    row = _fetchone_dict(c)
    release_connection(conn)
    return row


def get_team_members(team_id: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT discord_user_id FROM team_members WHERE team_id = %s", (team_id,))
    rows = c.fetchall()
    release_connection(conn)
    return [r[0] for r in rows]


def get_open_teams(hackathon_id: int, max_size: int) -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT t.id, t.channel_id, t.channel_name, COUNT(tm.id) as member_count
        FROM teams t
        JOIN team_members tm ON t.id = tm.team_id
        WHERE t.hackathon_id = %s AND t.status = 'active'
        GROUP BY t.id
        HAVING COUNT(tm.id) < %s
        """,
        (hackathon_id, max_size),
    )
    rows = _fetchall_dict(c)
    release_connection(conn)
    return rows


# ── Bienvenue ─────────────────────────────────────────────────────────────────
def is_welcomed(user_id: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM welcomed WHERE discord_user_id = %s", (user_id,))
    row = c.fetchone()
    release_connection(conn)
    return row is not None


def mark_welcomed(user_id: str):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO welcomed (discord_user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (user_id,),
        )
        conn.commit()
    finally:
        release_connection(conn)


def get_not_welcomed_user_ids() -> list:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT discord_user_id FROM welcomed")
    rows = c.fetchall()
    release_connection(conn)
    return [r[0] for r in rows]


if __name__ == "__main__":
    init_db()
