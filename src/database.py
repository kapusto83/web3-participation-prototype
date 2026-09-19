import json
import sqlite3
import uuid
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "prototype.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def generate_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def init_db():
    with get_connection() as conn:

        # --------------------------------------------------
        # Participants
        # --------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                participant_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)

        # --------------------------------------------------
        # Sessions
        # --------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY (participant_id)
                    REFERENCES participants(participant_id)
            )
        """)

        # --------------------------------------------------
        # Reviews
        # --------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                content TEXT NOT NULL,
                qualified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id)
                    REFERENCES sessions(session_id),
                FOREIGN KEY (participant_id)
                    REFERENCES participants(participant_id)
            )
        """)

        # --------------------------------------------------
        # Events
        # --------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL,
                session_id TEXT,
                review_id TEXT,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (participant_id)
                    REFERENCES participants(participant_id)
            )
        """)

        # --------------------------------------------------
        # Wallet acknowledgements
        # --------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS acknowledgements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id TEXT NOT NULL,
                review_id TEXT NOT NULL,
                wallet_address TEXT NOT NULL,
                message TEXT NOT NULL,
                signature TEXT NOT NULL,
                acknowledged_at TEXT NOT NULL
            )
        """)

        conn.commit()


# --------------------------------------------------
# Participants
# --------------------------------------------------

def create_participant(created_at):
    participant_id = generate_id("P")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO participants (
                participant_id,
                created_at
            )
            VALUES (?, ?)
            """,
            (
                participant_id,
                created_at,
            ),
        )

        conn.commit()

    return participant_id


# --------------------------------------------------
# Sessions
# --------------------------------------------------

def create_session(participant_id, started_at):
    session_id = generate_id("S")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO sessions (
                session_id,
                participant_id,
                started_at
            )
            VALUES (?, ?, ?)
            """,
            (
                session_id,
                participant_id,
                started_at,
            ),
        )

        conn.commit()

    return session_id


def complete_session(session_id, completed_at):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET completed_at = ?
            WHERE session_id = ?
            """,
            (
                completed_at,
                session_id,
            ),
        )

        conn.commit()


# --------------------------------------------------
# Reviews
# --------------------------------------------------

def create_review(
    session_id,
    participant_id,
    content,
    qualified,
    created_at,
):
    review_id = generate_id("REV")

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO reviews (
                review_id,
                session_id,
                participant_id,
                content,
                qualified,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                session_id,
                participant_id,
                content,
                int(qualified),
                created_at,
            ),
        )

        conn.commit()

    return review_id


def review_exists_for_session(session_id):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT review_id
            FROM reviews
            WHERE session_id = ?
            LIMIT 1
            """,
            (session_id,),
        ).fetchone()

    return row is not None


# --------------------------------------------------
# Events
# --------------------------------------------------

def log_event(
    participant_id,
    event_type,
    timestamp,
    session_id=None,
    review_id=None,
    metadata=None,
):
    event_id = generate_id("EVT")

    metadata_json = None

    if metadata is not None:
        metadata_json = json.dumps(
            metadata,
            ensure_ascii=False,
        )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO events (
                event_id,
                participant_id,
                session_id,
                review_id,
                event_type,
                timestamp,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                participant_id,
                session_id,
                review_id,
                event_type,
                timestamp,
                metadata_json,
            ),
        )

        conn.commit()

    return event_id


# --------------------------------------------------
# Wallet acknowledgements
# --------------------------------------------------

def save_acknowledgement(
    participant_id,
    review_id,
    wallet_address,
    message,
    signature,
    acknowledged_at,
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO acknowledgements (
                participant_id,
                review_id,
                wallet_address,
                message,
                signature,
                acknowledged_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                participant_id,
                review_id,
                wallet_address,
                message,
                signature,
                acknowledged_at,
            ),
        )

        conn.commit()