import json
import os
from typing import Dict, List, Any, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
COUNTRIES_FILE = os.path.join(DATA_DIR, 'countries.json')
DAILY_ORDER_FILE = os.path.join(DATA_DIR, 'daily_order.json')


class DataLoader:
    def __init__(self):
        self.countries: Dict[str, Any] = {}
        self.daily_order: List[str] = []
        self.load()

    def load(self):
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
