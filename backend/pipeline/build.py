import json
import os
import random
from datetime import datetime, timezone
from typing import Dict, List

from .wikidata_core import fetch_wikidata_core
from .wikidata_lexical import fetch_wikidata_lexical, clean_aliases
from .wikipedia_fetch import fetch_all_wikipedia_articles
from .censor import censor_all_articles
from .db_store import write_database

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/raw')
DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
os.makedirs(DATA_DIR, exist_ok=True)

# 1 starting paragraph + 3 hint unlocks = 4 paragraphs max per game,
# so the dataset ships exactly 4 (the raw cache keeps 5 as spare).
PARAGRAPHS_PER_COUNTRY = 4


def load_pipeline_data():
    print("Loading pipeline data...")
    core_file = os.path.join(RAW_DATA_DIR, 'wikidata_stage_a.json')
    lexical_file = os.path.join(RAW_DATA_DIR, 'wikidata_lexical.json')

    with open(core_file, 'r', encoding='utf-8') as f:
        core = json.load(f)

    with open(lexical_file, 'r', encoding='utf-8') as f:
        lexical = json.load(f)

    return core, lexical


# Manual fixes for gaps in Wikidata itself (e.g. Nigeria's capital entity
# has no en/ca label at the source). Keyed by country QID, then language.
CAPITAL_LABEL_PATCHES = {
    'Q1033': {'en': 'Abuja', 'ca': 'Abuja'},
}


def _capital_label(country_qid: str, capital_qid: str, lang: str, lexical: Dict) -> str:
    """Capital display name with fallbacks: manual patch -> requested
    language -> English -> any label Wikidata has."""
    patched = CAPITAL_LABEL_PATCHES.get(country_qid, {}).get(lang)
    if patched:
        return patched

    labels = lexical.get(capital_qid, {}).get('labels', {})
    for candidate in (lang, 'en'):
        if candidate in labels:
            return labels[candidate].get('value', '')
    if labels:
        return next(iter(labels.values())).get('value', '')
    return ''


# Manual fixes for whole-country data gaps caused by Wikidata modeling a
# country as a separate "sovereign state" entity distinct from the common
# "country" entity (e.g. Denmark's UN seat is modeled under Q756617
# "Kingdom of Denmark" rather than Q35 "Denmark"). That entity has no
# ISO 3166 codes attached at all (blank flag emoji, unmatchable on the
# Easy Mode map), and its ca/es labels are the formal long form with no
# short-form alias, so natural guesses like "Dinamarca" would fail even
# though the equivalent short-form alias already exists in English.
COUNTRY_OVERRIDES = {
    'Q756617': {
        'iso2': 'DK',
        'iso3': 'DNK',
        'name': {'en': 'Denmark', 'ca': 'Dinamarca', 'es': 'Dinamarca'},
        'extra_aliases': {
            'en': ['Kingdom of Denmark'],
            'ca': ['Regne de Dinamarca'],
            'es': ['Reino de Dinamarca'],
        },
    },
}


def load_cached_articles():
    print("Loading cached Wikipedia articles...")
    articles = {}

    for lang in ['en', 'ca', 'es']:
        lang_dir = os.path.join(RAW_DATA_DIR, f'wikipedia_{lang}')
        if os.path.exists(lang_dir):
            for qid_file in os.listdir(lang_dir):
                if qid_file.endswith('.json'):
                    qid = qid_file[:-5]
                    filepath = os.path.join(lang_dir, qid_file)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        key = f'{qid}_{lang}'
                        articles[key] = data.get('paragraphs', [])

    return articles


def build_countries_json():
    print("Building countries.json...")

    core, lexical = load_pipeline_data()
    censored = censor_all_articles()
    articles = load_cached_articles()

    countries = {}

    for qid, country_data in core.items():
        override = COUNTRY_OVERRIDES.get(qid, {})
        iso2 = override.get('iso2') or country_data.get('iso2', '')
        iso3 = override.get('iso3') or country_data.get('iso3', '')
        cctld = country_data.get('cctld', '')

        i18n = {}
        for lang in ['en', 'ca', 'es']:
            entity = lexical.get(qid, {})
            lang_label = override.get('name', {}).get(lang) or \
                entity.get('labels', {}).get(lang, {}).get('value', country_data.get('label', ''))
            capital_qid = country_data.get('capital')
            capital_label = ''
            if capital_qid:
                capital_label = _capital_label(qid, capital_qid, lang, lexical)

            # Aliases let guesses like "USA" or "Estats Units" match
            aliases = clean_aliases(entity.get('aliases', {}).get(lang, []))
            aliases.extend(override.get('extra_aliases', {}).get(lang, []))

            censored_data = censored.get(qid, {}).get(lang, {})
            censored_paragraphs = censored_data.get('paragraphs', [])

            i18n[lang] = {
                'name': lang_label,
                'capital': capital_label,
                'paragraphs': censored_paragraphs[:PARAGRAPHS_PER_COUNTRY] if censored_paragraphs else [],
                'aliases': aliases
            }

        countries[qid] = {
            'iso2': iso2,
            'iso3': iso3,
            'cctld': cctld,
            'i18n': i18n
        }

    countries_file = os.path.join(DATA_DIR, 'countries.json')
    with open(countries_file, 'w', encoding='utf-8') as f:
        json.dump(countries, f, ensure_ascii=False, indent=2)

    print(f"Saved countries.json with {len(countries)} countries")
    return countries


def _load_plain_paragraphs(qid: str, lang: str) -> List[str]:
    """Original (uncensored) paragraphs from the raw Wikipedia cache,
    revealed to the player once the game is over."""
    cache_file = os.path.join(RAW_DATA_DIR, f'wikipedia_{lang}', f'{qid}.json')
    if not os.path.exists(cache_file):
        return []
    with open(cache_file, 'r', encoding='utf-8') as f:
        return json.load(f).get('paragraphs', [])[:PARAGRAPHS_PER_COUNTRY]


def build_frontend_game_json(countries: Dict, daily_order: List[str]):
    """Export the dataset for the fully client-side build (GitHub Pages).

    Slimmed: unplayable countries keep only their names/aliases (needed
    for the autocomplete) since they can never be the daily answer, and
    fields the frontend never reads are dropped. Playable countries also
    carry the uncensored text ('plain') shown after the game ends.
    """
    frontend_public = os.path.join(os.path.dirname(__file__), '../../frontend/public')
    os.makedirs(frontend_public, exist_ok=True)

    slim = {}
    for qid, country in countries.items():
        playable = _is_playable(country)
        slim[qid] = {
            'iso2': country.get('iso2', ''),
            'i18n': {
                lang: {
                    'name': i18n.get('name', ''),
                    'capital': i18n.get('capital', ''),
                    'aliases': i18n.get('aliases', []),
                    'paragraphs': i18n.get('paragraphs', []) if playable else [],
                    'plain': _load_plain_paragraphs(qid, lang) if playable else [],
                }
                for lang, i18n in country.get('i18n', {}).items()
            },
        }

    game = {
        'epoch': '2026-01-01',
        'dailyOrder': daily_order,
        'countries': slim,
    }

    game_file = os.path.join(frontend_public, 'game.json')
    with open(game_file, 'w', encoding='utf-8') as f:
        json.dump(game, f, ensure_ascii=False, separators=(',', ':'))

    size_kb = os.path.getsize(game_file) // 1024
    print(f"Saved frontend game.json ({size_kb} KB)")


def _is_playable(country: Dict) -> bool:
    return all(country.get('i18n', {}).get(lang, {}).get('paragraphs')
               for lang in ('en', 'ca', 'es'))


def build_daily_order():
    print("Building daily order...")

    countries_file = os.path.join(DATA_DIR, 'countries.json')
    with open(countries_file, 'r', encoding='utf-8') as f:
        countries = json.load(f)

    # Only fully playable countries enter the rotation; otherwise the
    # runtime skip-forward makes consecutive days repeat the same answer.
    qids = [qid for qid, c in countries.items() if _is_playable(c)]
    skipped = len(countries) - len(qids)
    if skipped:
        print(f"  {skipped} countries lack full content and are excluded from the rotation")
    random.seed(42)
    random.shuffle(qids)

    daily_order_file = os.path.join(DATA_DIR, 'daily_order.json')
    with open(daily_order_file, 'w', encoding='utf-8') as f:
        json.dump(qids, f, ensure_ascii=False, indent=2)

    print(f"Saved daily_order.json with {len(qids)} countries in daily rotation")
    return qids


def build_all():
    print("\n=== Starting full build pipeline ===\n")

    print("Stage 1: Fetching core Wikidata...")
    fetch_wikidata_core()

    print("\nStage 2: Fetching lexical Wikidata...")
    fetch_wikidata_lexical()

    print("\nStage 3: Fetching Wikipedia articles...")
    fetch_all_wikipedia_articles()

    print("\nStage 4: Building countries.json...")
    countries = build_countries_json()

    print("\nStage 5: Building daily rotation order...")
    daily_order = build_daily_order()

    print("\nStage 6: Writing SQLite database...")
    write_database(countries, daily_order)

    print("\nStage 7: Exporting frontend game.json...")
    build_frontend_game_json(countries, daily_order)

    print("\n=== Build complete! ===\n")


if __name__ == '__main__':
    build_all()
