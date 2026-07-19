"""SQLite storage for the generated countries dataset.

The pipeline writes the final dataset into data/countries.db so the
backend can load it locally without any external service.
"""
import sqlite3
import os
from typing import Dict, List

DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
DB_FILE = os.path.join(DATA_DIR, 'countries.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS countries (
    qid   TEXT PRIMARY KEY,
    iso2  TEXT,
    iso3  TEXT,
    cctld TEXT
);

CREATE TABLE IF NOT EXISTS country_i18n (
    qid     TEXT NOT NULL,
    lang    TEXT NOT NULL,
    name    TEXT NOT NULL,
    capital TEXT,
    PRIMARY KEY (qid, lang),
    FOREIGN KEY (qid) REFERENCES countries(qid)
);

CREATE TABLE IF NOT EXISTS aliases (
    qid   TEXT NOT NULL,
    lang  TEXT NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY (qid, lang, alias)
);

CREATE TABLE IF NOT EXISTS paragraphs (
    qid  TEXT NOT NULL,
    lang TEXT NOT NULL,
    idx  INTEGER NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (qid, lang, idx)
);

CREATE TABLE IF NOT EXISTS daily_order (
    position INTEGER PRIMARY KEY,
    qid      TEXT NOT NULL
);
"""


def write_database(countries: Dict, daily_order: List[str], db_file: str = DB_FILE):
    """Write the full dataset to SQLite, replacing any previous contents."""
    os.makedirs(os.path.dirname(db_file), exist_ok=True)

    conn = sqlite3.connect(db_file)
    try:
        conn.executescript(SCHEMA)
        # Full refresh: the dataset is small, simplest to rewrite
        conn.execute('DELETE FROM countries')
        conn.execute('DELETE FROM country_i18n')
        conn.execute('DELETE FROM aliases')
        conn.execute('DELETE FROM paragraphs')
        conn.execute('DELETE FROM daily_order')

        for qid, data in countries.items():
            conn.execute(
                'INSERT INTO countries (qid, iso2, iso3, cctld) VALUES (?, ?, ?, ?)',
                (qid, data.get('iso2', ''), data.get('iso3', ''), data.get('cctld', ''))
            )
            for lang, i18n in data.get('i18n', {}).items():
                conn.execute(
                    'INSERT INTO country_i18n (qid, lang, name, capital) VALUES (?, ?, ?, ?)',
                    (qid, lang, i18n.get('name', ''), i18n.get('capital', ''))
                )
                for alias in i18n.get('aliases', []):
                    conn.execute(
                        'INSERT OR IGNORE INTO aliases (qid, lang, alias) VALUES (?, ?, ?)',
                        (qid, lang, alias)
                    )
                for idx, text in enumerate(i18n.get('paragraphs', [])):
                    conn.execute(
                        'INSERT INTO paragraphs (qid, lang, idx, text) VALUES (?, ?, ?, ?)',
                        (qid, lang, idx, text)
                    )

        for position, qid in enumerate(daily_order):
            conn.execute(
                'INSERT INTO daily_order (position, qid) VALUES (?, ?)',
                (position, qid)
            )

        conn.commit()
    finally:
        conn.close()

    print(f"Saved SQLite database to {db_file}")


def read_database(db_file: str = DB_FILE):
    """Load the dataset back into the in-memory dict shape the app uses."""
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        countries: Dict = {}
        for row in conn.execute('SELECT * FROM countries'):
            countries[row['qid']] = {
                'iso2': row['iso2'],
                'iso3': row['iso3'],
                'cctld': row['cctld'],
                'i18n': {}
            }

        for row in conn.execute('SELECT * FROM country_i18n'):
            countries[row['qid']]['i18n'][row['lang']] = {
                'name': row['name'],
                'capital': row['capital'],
                'aliases': [],
                'paragraphs': []
            }

        for row in conn.execute('SELECT * FROM aliases'):
            i18n = countries.get(row['qid'], {}).get('i18n', {}).get(row['lang'])
            if i18n is not None:
                i18n['aliases'].append(row['alias'])

        for row in conn.execute('SELECT * FROM paragraphs ORDER BY qid, lang, idx'):
            i18n = countries.get(row['qid'], {}).get('i18n', {}).get(row['lang'])
            if i18n is not None:
                i18n['paragraphs'].append(row['text'])

        daily_order = [
            row['qid']
            for row in conn.execute('SELECT qid FROM daily_order ORDER BY position')
        ]

        return countries, daily_order
    finally:
        conn.close()
