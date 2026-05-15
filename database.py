import psycopg2
import psycopg2.pool
import os
import threading
import concurrent.futures
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Optional

# Hard timeout côté Python (les keepalives libpq ne sont pas honorés sur macOS,
# une conn zombie peut hang ~10 min sinon)
_DB_TIMEOUT_SECONDS = 20
_db_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=10, thread_name_prefix="db-worker"
)

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
_pool_lock = threading.Lock()


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = psycopg2.pool.ThreadedConnectionPool(
                    1,
                    10,
                    os.getenv("DATABASE_URL"),
                    connect_timeout=5,
                    # Probes TCP agressifs : conn morte détectée en ~16s au lieu de 60s+
                    keepalives=1,
                    keepalives_idle=10,
                    keepalives_interval=3,
                    keepalives_count=2,
                    # Côté serveur : aucune requête ne peut dépasser 15s
                    options="-c statement_timeout=15000",
                )
    return _pool


def _reset_pool():
    """Ferme et détruit le pool actuel — utile après un changement réseau."""
    global _pool
    with _pool_lock:
        old = _pool
        _pool = None
    if old is not None:
        try:
            old.closeall()
        except Exception:
            pass


def _retry(func):
    """Exécute la fonction DB dans un thread dédié avec un hard timeout. Réessaie une fois sur erreur/timeout (le pool est reset entre 2 tentatives)."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exc: Optional[Exception] = None
        for attempt in range(2):
            future = _db_executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=_DB_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError as e:
                # On abandonne le thread (il finira en arrière-plan, conn sera GC) et on retente sur du frais.
                last_exc = TimeoutError(
                    f"DB call '{func.__name__}' timed out after {_DB_TIMEOUT_SECONDS}s"
                )
                _reset_pool()
            except (
                psycopg2.OperationalError,
                psycopg2.InterfaceError,
                psycopg2.DatabaseError,
            ) as e:
                last_exc = e
        if last_exc:
            raise last_exc
        return None  # unreachable

    return wrapper


@contextmanager
def _db():
    """Ouvre une connexion fraîche par appel. Plus de pool = plus de conns zombies sur macOS.
    Neon utilise un pooler côté serveur (URL contient 'pooler'), donc l'overhead reste faible (~500ms).
    Le pooler Neon n'accepte PAS `options=-c statement_timeout` au startup → on le set après."""
    conn = psycopg2.connect(
        os.getenv("DATABASE_URL"),
        connect_timeout=5,
    )
    try:
        with conn.cursor() as c:
            c.execute("SET statement_timeout = 15000")
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


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
    with _db() as conn:
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
    print("✅ Base de données initialisée")


# ── Hackathons ────────────────────────────────────────────────────────────────
@_retry
def insert_hackathon(data: dict) -> Optional[int]:
    with _db() as conn:
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
                    data.get("title"), data.get("url"), data.get("source"),
                    data.get("theme"), data.get("format"), data.get("location"),
                    data.get("prize_1st"), data.get("prize_2nd"), data.get("prize_3rd"),
                    data.get("prize_min_fcfa", 0), data.get("language"),
                    data.get("deadline"), data.get("duration"), data.get("level"),
                    data.get("score"), datetime.now().isoformat(),
                ),
            )
            conn.commit()
            row = c.fetchone()
            return row[0] if row else None
        except psycopg2.IntegrityError:
            conn.rollback()
            return None


@_retry
def update_message_id(hackathon_id: int, message_id: str):
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE hackathons SET discord_message_id = %s, discord_posted_at = %s WHERE id = %s",
            (message_id, datetime.now().isoformat(), hackathon_id),
        )
        conn.commit()


@_retry
def get_active_hackathons() -> list:
    with _db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM hackathons WHERE status = 'active' ORDER BY score DESC")
        return _fetchall_dict(c)


@_retry
def get_unposted_hackathons(limit: int = 10) -> list:
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM hackathons WHERE discord_message_id IS NULL AND status = 'active' ORDER BY score DESC, id ASC LIMIT %s",
            (limit,),
        )
        return _fetchall_dict(c)


@_retry
def get_posted_hackathons() -> list:
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM hackathons WHERE discord_message_id IS NOT NULL AND discord_message_id != 'duplicate_skipped' AND status = 'active'"
        )
        return _fetchall_dict(c)


@_retry
def delete_hackathon(hackathon_id: int):
    with _db() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM hackathons WHERE id = %s", (hackathon_id,))
        conn.commit()


@_retry
def archive_hackathon(hackathon_id: int):
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE hackathons SET status = 'archived', archived_at = %s WHERE id = %s",
            (datetime.now().isoformat(), hackathon_id),
        )
        conn.commit()


@_retry
def get_stats() -> dict:
    with _db() as conn:
        c = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status = 'active') AS total_active,
                COUNT(*) FILTER (WHERE status = 'active' AND discord_message_id IS NULL) AS total_pending,
                COUNT(*) FILTER (WHERE status = 'active' AND discord_message_id IS NOT NULL) AS total_posted,
                COUNT(*) FILTER (WHERE status = 'archived') AS total_archived,
                COUNT(*) FILTER (WHERE posted_at LIKE %s) AS scraped_today,
                COUNT(*) FILTER (WHERE discord_posted_at LIKE %s) AS posted_today,
                COUNT(*) FILTER (WHERE archived_at LIKE %s) AS archived_today
            FROM hackathons
            """,
            (f"{today}%", f"{today}%", f"{today}%"),
        )
        row = c.fetchone()
        return {
            "total_active": row[0], "total_pending": row[1], "total_posted": row[2],
            "total_archived": row[3], "scraped_today": row[4],
            "posted_today": row[5], "archived_today": row[6],
        }


@_retry
def get_hackathon_by_title(title: str) -> Optional[dict]:
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM hackathons WHERE LOWER(TRIM(title)) = LOWER(%s) AND status = 'active'",
            (title,),
        )
        return _fetchone_dict(c)


@_retry
def get_hackathon_by_message(message_id: str) -> Optional[dict]:
    with _db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM hackathons WHERE discord_message_id = %s", (message_id,))
        return _fetchone_dict(c)


# ── Intérêts ─────────────────────────────────────────────────────────────────
@_retry
def add_interest(hackathon_id: int, user_id: str, username: str):
    with _db() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO interests (hackathon_id, discord_user_id, discord_username) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (hackathon_id, user_id, username),
            )
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()


@_retry
def remove_interest(hackathon_id: int, user_id: str):
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "DELETE FROM interests WHERE hackathon_id = %s AND discord_user_id = %s",
            (hackathon_id, user_id),
        )
        conn.commit()


@_retry
def get_interested_users(hackathon_id: int) -> list:
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT discord_user_id, discord_username FROM interests WHERE hackathon_id = %s",
            (hackathon_id,),
        )
        return _fetchall_dict(c)


# ── Votes de matchmaking ──────────────────────────────────────────────────────
@_retry
def add_vote(hackathon_id: int, voter_id: str, target_id: str):
    with _db() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO votes (hackathon_id, voter_id, target_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (hackathon_id, voter_id, target_id),
            )
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()


@_retry
def check_mutual_match(hackathon_id: int, user_a: str, user_b: str) -> bool:
    with _db() as conn:
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
        return bool(a_voted_b and b_voted_a)


@_retry
def get_user_votes(hackathon_id: int, voter_id: str) -> list:
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT target_id FROM votes WHERE hackathon_id=%s AND voter_id=%s",
            (hackathon_id, voter_id),
        )
        return [r[0] for r in c.fetchall()]


# ── Équipes ───────────────────────────────────────────────────────────────────
@_retry
def create_team(hackathon_id: int, member_ids: list, channel_id: str, channel_name: str) -> int:
    with _db() as conn:
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
        return team_id


@_retry
def get_user_team(hackathon_id: int, user_id: str) -> Optional[dict]:
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT t.* FROM teams t
            JOIN team_members tm ON t.id = tm.team_id
            WHERE t.hackathon_id = %s AND tm.discord_user_id = %s
            """,
            (hackathon_id, user_id),
        )
        return _fetchone_dict(c)


@_retry
def get_team_members(team_id: int) -> list:
    with _db() as conn:
        c = conn.cursor()
        c.execute("SELECT discord_user_id FROM team_members WHERE team_id = %s", (team_id,))
        return [r[0] for r in c.fetchall()]


@_retry
def get_open_teams(hackathon_id: int, max_size: int) -> list:
    with _db() as conn:
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
        return _fetchall_dict(c)


# ── Bienvenue ─────────────────────────────────────────────────────────────────
@_retry
def is_welcomed(user_id: str) -> bool:
    with _db() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM welcomed WHERE discord_user_id = %s", (user_id,))
        return c.fetchone() is not None


@_retry
def mark_welcomed(user_id: str):
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO welcomed (discord_user_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (user_id,),
        )
        conn.commit()


@_retry
def get_not_welcomed_user_ids() -> list:
    with _db() as conn:
        c = conn.cursor()
        c.execute("SELECT discord_user_id FROM welcomed")
        return [r[0] for r in c.fetchall()]


# ── Helpers Postgres pour les cogs (remplacent l'ancien db.get_connection() SQLite) ──
@_retry
def find_common_active_hackathon(user_a: str, user_b: str) -> Optional[dict]:
    """Hackathon actif où deux utilisateurs sont tous deux intéressés (le mieux noté)."""
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT h.* FROM hackathons h
            JOIN interests i1 ON h.id = i1.hackathon_id AND i1.discord_user_id = %s
            JOIN interests i2 ON h.id = i2.hackathon_id AND i2.discord_user_id = %s
            WHERE h.status = 'active'
            ORDER BY h.score DESC LIMIT 1
            """,
            (user_a, user_b),
        )
        return _fetchone_dict(c)


@_retry
def add_member_to_team(team_id: int, user_id: str):
    """Ajoute un membre à une équipe existante (idempotent)."""
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO team_members (team_id, discord_user_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (team_id, user_id),
        )
        conn.commit()


@_retry
def get_active_teams_for_hackathon(hackathon_id: int) -> list:
    """Liste les équipes actives d'un hackathon."""
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "SELECT * FROM teams WHERE hackathon_id = %s AND status = 'active'",
            (hackathon_id,),
        )
        return _fetchall_dict(c)


@_retry
def archive_hackathon_and_teams(hackathon_id: int):
    """Archive un hackathon et toutes les équipes associées."""
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE hackathons SET status = 'archived', archived_at = %s WHERE id = %s",
            (datetime.now().isoformat(), hackathon_id),
        )
        c.execute(
            "UPDATE teams SET status = 'archived' WHERE hackathon_id = %s",
            (hackathon_id,),
        )
        conn.commit()


@_retry
def get_user_active_team(user_id: str) -> Optional[dict]:
    """Équipe active la plus récente de l'utilisateur, avec titre du hackathon."""
    with _db() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT t.*, h.title AS hack_title FROM teams t
            JOIN team_members tm ON t.id = tm.team_id
            JOIN hackathons h ON t.hackathon_id = h.id
            WHERE tm.discord_user_id = %s AND t.status = 'active'
            ORDER BY t.created_at DESC LIMIT 1
            """,
            (user_id,),
        )
        return _fetchone_dict(c)


if __name__ == "__main__":
    init_db()
