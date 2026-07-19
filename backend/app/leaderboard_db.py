"""SQLite persistence for usernames and daily scores.

Kept in its own database file (not countries.db, which the pipeline
rewrites on every rebuild) so player data survives dataset updates.
"""
import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Dict, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DB_FILE = os.path.join(DATA_DIR, 'leaderboard.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL UNIQUE COLLATE NOCASE,
    token_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scores (
    user_id    INTEGER NOT NULL REFERENCES users(id),
    puzzle_id  TEXT NOT NULL,
    score      INTEGER NOT NULL,
    guesses    INTEGER NOT NULL,
    unlocks    INTEGER NOT NULL,
    won        INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (user_id, puzzle_id)
);

CREATE INDEX IF NOT EXISTS idx_scores_puzzle ON scores(puzzle_id, score DESC);
"""


def _connect(db_file: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_file or DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class UsernameTaken(Exception):
    """Username exists and the presented token doesn't match."""


class AlreadySubmitted(Exception):
    """This user already submitted a score for this puzzle."""


def submit_score(username: str, token: str, puzzle_id: str, score: int,
                 guesses: int, unlocks: int, won: bool,
                 db_file: Optional[str] = None) -> None:
    conn = _connect(db_file)
    try:
        row = conn.execute(
            'SELECT id, token_hash FROM users WHERE username = ?', (username,)
        ).fetchone()

        if row is None:
            cur = conn.execute(
                'INSERT INTO users (username, token_hash, created_at) VALUES (?, ?, ?)',
                (username, _hash_token(token), _now())
            )
            user_id = cur.lastrowid
        elif row['token_hash'] != _hash_token(token):
            raise UsernameTaken(username)
        else:
            user_id = row['id']

        try:
            conn.execute(
                'INSERT INTO scores (user_id, puzzle_id, score, guesses, unlocks, won, created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                (user_id, puzzle_id, score, guesses, unlocks, int(won), _now())
            )
        except sqlite3.IntegrityError:
            raise AlreadySubmitted(f'{username}/{puzzle_id}')

        conn.commit()
    finally:
        conn.close()


def leaderboard_today(puzzle_id: str, limit: int = 50,
                      db_file: Optional[str] = None) -> List[Dict]:
    conn = _connect(db_file)
    try:
        rows = conn.execute(
            'SELECT u.username, s.score, s.guesses, s.unlocks, s.won '
            'FROM scores s JOIN users u ON u.id = s.user_id '
            'WHERE s.puzzle_id = ? '
            'ORDER BY s.score DESC, s.guesses ASC, s.created_at ASC '
            'LIMIT ?',
            (puzzle_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def leaderboard_alltime(limit: int = 50,
                        db_file: Optional[str] = None) -> List[Dict]:
    conn = _connect(db_file)
    try:
        rows = conn.execute(
            'SELECT u.username, '
            '       SUM(s.score)  AS total_score, '
            '       SUM(s.won)    AS wins, '
            '       COUNT(*)      AS games '
            'FROM scores s JOIN users u ON u.id = s.user_id '
            'GROUP BY s.user_id '
            'ORDER BY total_score DESC, wins DESC, games ASC '
            'LIMIT ?',
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
