from datetime import datetime, timezone
from typing import Optional, Dict, Any
import unicodedata
from .data_loader import get_loader


EPOCH_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
LANGUAGES = ['en', 'ca', 'es']


def normalize_text(text: str) -> str:
    """Casefold, trim and strip accents so 'España' == 'espana'."""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.casefold().strip()


def today_day_index() -> int:
    now = datetime.now(timezone.utc)
    return (now.date() - EPOCH_DATE.date()).days


def _has_content(country: Dict[str, Any]) -> bool:
    """A country is playable only if it has paragraphs in every language."""
    i18n = country.get('i18n', {})
    return all(i18n.get(lang, {}).get('paragraphs') for lang in LANGUAGES)


def get_daily_country() -> Optional[Dict[str, Any]]:
    """Deterministically pick today's country, skipping entries without
    content so every player gets the same, playable puzzle."""
    loader = get_loader()
    if not loader.daily_order:
        return None

    day_index = today_day_index()
    n = len(loader.daily_order)
    for offset in range(n):
        qid = loader.daily_order[(day_index + offset) % n]
        country = loader.get_country(qid)
        if country and _has_content(country):
            return {'qid': qid, **country}

    return None


def get_todays_puzzle(lang: str) -> Optional[Dict[str, Any]]:
    country = get_daily_country()
    if not country or lang not in country.get('i18n', {}):
        return None

    puzzle_id = datetime.now(timezone.utc).date().isoformat()
    paragraphs = country['i18n'][lang].get('paragraphs', [])

    return {
        'puzzle_id': puzzle_id,
        'qid': country['qid'],
        'max_guesses': len(paragraphs),
        'paragraphs': paragraphs,
        'i18n': country['i18n'][lang],
    }


def check_guess(lang: str, puzzle_id: str, guess_text: str) -> Dict[str, Any]:
    country = get_daily_country()
    if not country:
        return {'correct': False, 'error': 'No puzzle today'}

    if lang not in country.get('i18n', {}):
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
