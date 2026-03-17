import sqlite3
import os
from datetime import datetime

DB_PATH = "hackahunt.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Table des hackathons scrapés
    c.execute("""
        CREATE TABLE IF NOT EXISTS hackathons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            status TEXT DEFAULT 'active'
        )
    """)

    # Table des intérêts (qui a cliqué 👍 sur quel hackathon)
    c.execute("""
        CREATE TABLE IF NOT EXISTS interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hackathon_id INTEGER NOT NULL,
            discord_user_id TEXT NOT NULL,
            discord_username TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hackathon_id, discord_user_id),
            FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
        )
    """)

    # Table des votes de matchmaking (A veut faire équipe avec B)
    c.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hackathon_id INTEGER NOT NULL,
            voter_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hackathon_id, voter_id, target_id),
            FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
        )
    """)

    # Table des équipes formées
    c.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hackathon_id INTEGER NOT NULL,
            channel_id TEXT,
            channel_name TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(hackathon_id) REFERENCES hackathons(id)
        )
    """)

    # Table des membres par équipe
    c.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            discord_user_id TEXT NOT NULL,
            UNIQUE(team_id, discord_user_id),
            FOREIGN KEY(team_id) REFERENCES teams(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Base de données initialisée")

# ── Hackathons ────────────────────────────────────────────────────────────────
def insert_hackathon(data: dict) -> int | None:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO hackathons
            (title, url, source, theme, format, location, prize_1st, prize_2nd,
             prize_3rd, prize_min_fcfa, language, deadline, duration, level, score, posted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("title"), data.get("url"), data.get("source"),
            data.get("theme"), data.get("format"), data.get("location"),
            data.get("prize_1st"), data.get("prize_2nd"), data.get("prize_3rd"),
            data.get("prize_min_fcfa", 0), data.get("language"),
            data.get("deadline"), data.get("duration"),
            data.get("level"), data.get("score"),
            datetime.now().isoformat()
        ))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        return None  # URL déjà existante → hackathon déjà en base
    finally:
        conn.close()

def update_message_id(hackathon_id: int, message_id: str):
    conn = get_connection()
    conn.execute(
        "UPDATE hackathons SET discord_message_id = ? WHERE id = ?",
        (message_id, hackathon_id)
    )
    conn.commit()
    conn.close()

def get_active_hackathons() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM hackathons WHERE status = 'active' ORDER BY score DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_hackathon_by_message(message_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM hackathons WHERE discord_message_id = ?", (message_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

# ── Intérêts ─────────────────────────────────────────────────────────────────
def add_interest(hackathon_id: int, user_id: str, username: str):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO interests (hackathon_id, discord_user_id, discord_username) VALUES (?, ?, ?)",
            (hackathon_id, user_id, username)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def remove_interest(hackathon_id: int, user_id: str):
    conn = get_connection()
    conn.execute(
        "DELETE FROM interests WHERE hackathon_id = ? AND discord_user_id = ?",
        (hackathon_id, user_id)
    )
    conn.commit()
    conn.close()

def get_interested_users(hackathon_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT discord_user_id, discord_username FROM interests WHERE hackathon_id = ?",
        (hackathon_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Votes de matchmaking ──────────────────────────────────────────────────────
def add_vote(hackathon_id: int, voter_id: str, target_id: str):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO votes (hackathon_id, voter_id, target_id) VALUES (?, ?, ?)",
            (hackathon_id, voter_id, target_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def check_mutual_match(hackathon_id: int, user_a: str, user_b: str) -> bool:
    conn = get_connection()
    a_voted_b = conn.execute(
        "SELECT 1 FROM votes WHERE hackathon_id=? AND voter_id=? AND target_id=?",
        (hackathon_id, user_a, user_b)
    ).fetchone()
    b_voted_a = conn.execute(
        "SELECT 1 FROM votes WHERE hackathon_id=? AND voter_id=? AND target_id=?",
        (hackathon_id, user_b, user_a)
    ).fetchone()
    conn.close()
    return bool(a_voted_b and b_voted_a)

def get_user_votes(hackathon_id: int, voter_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT target_id FROM votes WHERE hackathon_id=? AND voter_id=?",
        (hackathon_id, voter_id)
    ).fetchall()
    conn.close()
    return [r["target_id"] for r in rows]

# ── Équipes ───────────────────────────────────────────────────────────────────
def create_team(hackathon_id: int, member_ids: list, channel_id: str, channel_name: str) -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO teams (hackathon_id, channel_id, channel_name) VALUES (?, ?, ?)",
        (hackathon_id, channel_id, channel_name)
    )
    team_id = c.lastrowid
    for uid in member_ids:
        c.execute(
            "INSERT OR IGNORE INTO team_members (team_id, discord_user_id) VALUES (?, ?)",
            (team_id, uid)
        )
    conn.commit()
    conn.close()
    return team_id

def get_user_team(hackathon_id: int, user_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("""
        SELECT t.* FROM teams t
        JOIN team_members tm ON t.id = tm.team_id
        WHERE t.hackathon_id = ? AND tm.discord_user_id = ?
    """, (hackathon_id, user_id)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_team_members(team_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT discord_user_id FROM team_members WHERE team_id = ?", (team_id,)
    ).fetchall()
    conn.close()
    return [r["discord_user_id"] for r in rows]

def get_open_teams(hackathon_id: int, max_size: int) -> list:
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.id, t.channel_id, t.channel_name, COUNT(tm.id) as member_count
        FROM teams t
        JOIN team_members tm ON t.id = tm.team_id
        WHERE t.hackathon_id = ? AND t.status = 'active'
        GROUP BY t.id
        HAVING member_count < ?
    """, (hackathon_id, max_size)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    init_db()
