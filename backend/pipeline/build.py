import json
import os
import random
from datetime import datetime, timezone
from typing import Dict, List

from .wikidata_core import fetch_wikidata_core
from .wikidata_lexical import fetch_wikidata_lexical
from .wikipedia_fetch import fetch_all_wikipedia_articles
from .censor import censor_all_articles

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/raw')
DATA_DIR = os.path.join(os.path.dirname(__file__), '../data')
os.makedirs(DATA_DIR, exist_ok=True)


def load_pipeline_data():
    print("Loading pipeline data...")
    core_file = os.path.join(RAW_DATA_DIR, 'wikidata_stage_a.json')
    lexical_file = os.path.join(RAW_DATA_DIR, 'wikidata_lexical.json')

    with open(core_file, 'r', encoding='utf-8') as f:
        core = json.load(f)

    with open(lexical_file, 'r', encoding='utf-8') as f:
        lexical = json.load(f)

    return core, lexical


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
        iso2 = country_data.get('iso2', '')
        iso3 = country_data.get('iso3', '')
        cctld = country_data.get('cctld', '')

        i18n = {}
        for lang in ['en', 'ca', 'es']:
            lang_label = lexical.get(qid, {}).get('labels', {}).get(lang, {}).get('value', country_data.get('label', ''))
            capital_qid = country_data.get('capital')
            capital_label = ''
            if capital_qid and capital_qid in lexical:
                capital_label = lexical[capital_qid].get('labels', {}).get(lang, {}).get('value', '')

            wiki_key = f'{qid}_{lang}'
            paragraphs = articles.get(wiki_key, [])

            if paragraphs or True:
                censored_data = censored.get(qid, {}).get(lang, {})
                censored_paragraphs = censored_data.get('paragraphs', [])

                i18n[lang] = {
                    'name': lang_label,
                    'capital': capital_label,
                    'paragraphs': censored_paragraphs[:5] if censored_paragraphs else [],
                    'aliases': []
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


def build_daily_order():
    print("Building daily order...")

    countries_file = os.path.join(DATA_DIR, 'countries.json')
    with open(countries_file, 'r', encoding='utf-8') as f:
        countries = json.load(f)

    qids = list(countries.keys())
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
    build_countries_json()

    print("\nStage 5: Building daily rotation order...")
    build_daily_order()

    print("\n=== Build complete! ===\n")


if __name__ == '__main__':
    build_all()
