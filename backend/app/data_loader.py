import json
import os
import sqlite3
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
DB_FILE = os.path.join(DATA_DIR, 'countries.db')
COUNTRIES_FILE = os.path.join(DATA_DIR, 'countries.json')
DAILY_ORDER_FILE = os.path.join(DATA_DIR, 'daily_order.json')


class DataLoader:
    def __init__(self):
        self.countries: Dict[str, Any] = {}
        self.daily_order: List[str] = []
        self.load()

    def load(self):
        if os.path.exists(DB_FILE):
            self._load_from_db()
        else:
            self._load_from_json()

    def _load_from_db(self):
        """Load the dataset from the local SQLite database."""
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        try:
            for row in conn.execute('SELECT * FROM countries'):
                self.countries[row['qid']] = {
                    'iso2': row['iso2'],
                    'iso3': row['iso3'],
                    'cctld': row['cctld'],
                    'i18n': {}
                }

            for row in conn.execute('SELECT * FROM country_i18n'):
                self.countries[row['qid']]['i18n'][row['lang']] = {
                    'name': row['name'],
                    'capital': row['capital'],
                    'aliases': [],
                    'paragraphs': []
                }

            for row in conn.execute('SELECT * FROM aliases'):
                i18n = self.countries.get(row['qid'], {}).get('i18n', {}).get(row['lang'])
                if i18n is not None:
                    i18n['aliases'].append(row['alias'])

            for row in conn.execute('SELECT * FROM paragraphs ORDER BY qid, lang, idx'):
                i18n = self.countries.get(row['qid'], {}).get('i18n', {}).get(row['lang'])
                if i18n is not None:
                    i18n['paragraphs'].append(row['text'])

            self.daily_order = [
                row['qid']
                for row in conn.execute('SELECT qid FROM daily_order ORDER BY position')
            ]
        finally:
            conn.close()

    def _load_from_json(self):
        """Fallback for environments where the DB hasn't been built yet."""
        if os.path.exists(COUNTRIES_FILE):
            with open(COUNTRIES_FILE, 'r', encoding='utf-8') as f:
                self.countries = json.load(f)

        if os.path.exists(DAILY_ORDER_FILE):
            with open(DAILY_ORDER_FILE, 'r', encoding='utf-8') as f:
                self.daily_order = json.load(f)

    def get_country(self, qid: str) -> Optional[Dict[str, Any]]:
        return self.countries.get(qid)

    def get_daily_qid(self, day_index: int) -> Optional[str]:
        if not self.daily_order:
            return None
        return self.daily_order[day_index % len(self.daily_order)]

    def get_all_countries_by_lang(self, lang: str) -> List[Dict[str, str]]:
        result = []
        for qid, country_data in self.countries.items():
            if lang in country_data.get('i18n', {}):
                i18n = country_data['i18n'][lang]
                result.append({
                    'name': i18n.get('name', ''),
                    'iso2': country_data.get('iso2', ''),
                    'aliases': i18n.get('aliases', [])
                })
        return sorted(result, key=lambda x: x['name'])


# Singleton instance
_loader = None


def get_loader() -> DataLoader:
    global _loader
    if _loader is None:
        _loader = DataLoader()
    return _loader
