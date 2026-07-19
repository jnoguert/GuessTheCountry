from datetime import datetime, timezone, timedelta
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


def puzzle_id_for_day(day_index: int) -> str:
    return (EPOCH_DATE + timedelta(days=day_index)).date().isoformat()


def _has_all_languages(country: Dict[str, Any]) -> bool:
    i18n = country.get('i18n', {})
    return all(i18n.get(lang, {}).get('paragraphs') for lang in LANGUAGES)


def _has_language(country: Dict[str, Any], lang: str) -> bool:
    return bool(country.get('i18n', {}).get(lang, {}).get('paragraphs'))


def get_daily_country(day_index: Optional[int] = None,
                      lang: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Deterministically pick the country for a given day (default: today).

    Preference order, walking forward from the day's slot so every player
    gets the same answer:
      1. First country with content in ALL languages (consistent puzzle
         across languages).
      2. If none exists (partial dataset), first country with content in
         the requested language.
    """
    loader = get_loader()
    if not loader.daily_order:
        return None

    if day_index is None:
        day_index = today_day_index()

    n = len(loader.daily_order)

    for offset in range(n):
        qid = loader.daily_order[(day_index + offset) % n]
        country = loader.get_country(qid)
        if country and _has_all_languages(country):
            return {'qid': qid, **country}

    if lang:
        for offset in range(n):
            qid = loader.daily_order[(day_index + offset) % n]
            country = loader.get_country(qid)
            if country and _has_language(country, lang):
                return {'qid': qid, **country}

    return None


def get_todays_puzzle(lang: str, day_index: Optional[int] = None) -> Optional[Dict[str, Any]]:
    if day_index is None:
        day_index = today_day_index()

    country = get_daily_country(day_index, lang)
    if not country or not _has_language(country, lang):
        return None

    paragraphs = country['i18n'][lang].get('paragraphs', [])

    return {
        'puzzle_id': puzzle_id_for_day(day_index),
        'qid': country['qid'],
        'max_guesses': len(paragraphs),
        'paragraphs': paragraphs,
        'i18n': country['i18n'][lang],
    }


def check_guess(lang: str, guess_text: str,
                day_index: Optional[int] = None) -> Dict[str, Any]:
    country = get_daily_country(day_index, lang)
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
