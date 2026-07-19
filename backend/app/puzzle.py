from datetime import datetime, timezone
from typing import Optional, Dict, Any
import unicodedata
from .data_loader import get_loader


EPOCH_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def normalize_text(text: str) -> str:
    return unicodedata.normalize('NFC', text).lower().strip()


def today_day_index() -> int:
    now = datetime.now(timezone.utc)
    return (now.date() - EPOCH_DATE.date()).days


def get_todays_puzzle(lang: str) -> Optional[Dict[str, Any]]:
    loader = get_loader()
    day_index = today_day_index()
    qid = loader.get_daily_qid(day_index)

    if not qid:
        return None

    country = loader.get_country(qid)
    if not country or lang not in country.get('i18n', {}):
        return None

    puzzle_id = datetime.now(timezone.utc).date().isoformat()
    paragraphs = country['i18n'][lang].get('paragraphs', [])
    max_guesses = len(paragraphs)

    return {
        'puzzle_id': puzzle_id,
        'qid': qid,
        'max_guesses': max_guesses,
        'paragraphs': paragraphs,
        'i18n': country['i18n'][lang],
    }


def check_guess(lang: str, puzzle_id: str, guess_text: str) -> Dict[str, Any]:
    loader = get_loader()
    day_index = today_day_index()
    qid = loader.get_daily_qid(day_index)

    if not qid:
        return {'correct': False, 'error': 'No puzzle today'}

    country = loader.get_country(qid)
    if not country or lang not in country.get('i18n', {}):
        return {'correct': False, 'error': 'Language not available'}

    i18n_data = country['i18n'][lang]
    guess_norm = normalize_text(guess_text)

    # Check against country name
    if guess_norm == normalize_text(i18n_data.get('name', '')):
        return {'correct': True}

    # Check against aliases
    for alias in i18n_data.get('aliases', []):
        if guess_norm == normalize_text(alias):
            return {'correct': True}

    return {'correct': False}
