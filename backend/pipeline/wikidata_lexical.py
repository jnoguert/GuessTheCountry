import requests
import json
import os
import re
from typing import Dict, List, Set
from .wikidata_core import fetch_wikidata_core

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/raw')

API_ENDPOINT = 'https://www.wikidata.org/w/api.php'


def load_or_fetch_core() -> Dict:
    core_file = os.path.join(RAW_DATA_DIR, 'wikidata_stage_a.json')
    if os.path.exists(core_file):
        with open(core_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return fetch_wikidata_core()


def collect_qids(countries: Dict) -> Set[str]:
    qids = set(countries.keys())
    for qid, data in countries.items():
        if data.get('capital'):
            qids.add(data['capital'])
        if data.get('highest_point'):
            qids.add(data['highest_point'])
        if data.get('currency'):
            qids.add(data['currency'])
        qids.update(data.get('borders', []))
    return qids


def batch_fetch_entities(qids: List[str], languages: List[str] = ['en', 'ca', 'es']) -> Dict:
    print(f"Fetching lexical data for {len(qids)} entities...")
    headers = {
        'User-Agent': 'GuessTheCountry/1.0 (https://github.com/yourusername/guess-the-country)'
    }

    entities = {}
    batch_size = 50

    for i in range(0, len(qids), batch_size):
        batch = qids[i:i + batch_size]
        params = {
            'action': 'wbgetentities',
            'ids': '|'.join(batch),
            'props': 'labels|aliases|sitelinks|descriptions',
            'languages': '|'.join(languages),
            'sitefilter': 'enwiki|cawiki|eswiki',
            'format': 'json',
            'formatversion': 2
        }

        response = requests.get(API_ENDPOINT, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        batch_data = response.json().get('entities', {})
        entities.update(batch_data)

    # Also fetch demonyms per language (P1549)
    for lang in languages:
        demonyms = fetch_demonyms_for_countries(list(countries.keys()), lang)
        for qid, dem_list in demonyms.items():
            if qid in entities:
                if 'demonyms' not in entities[qid]:
                    entities[qid]['demonyms'] = {}
                entities[qid]['demonyms'][lang] = dem_list

    return entities


def fetch_demonyms_for_countries(country_qids: List[str], lang: str) -> Dict[str, List[str]]:
    sparql_query = f"""
    SELECT ?country ?demonym
    WHERE {{
      ?country wdt:P31/wdt:P279* wd:Q3624078 ;
               wdt:P1549 ?demonym .
      FILTER(LANG(?demonym) = "{lang}")
      FILTER(?country IN ({','.join(['wd:' + qid for qid in country_qids])}))
    }}
    """

    headers = {
        'User-Agent': 'GuessTheCountry/1.0',
        'Accept': 'application/sparql-results+json'
    }

    response = requests.get(
        'https://query.wikidata.org/sparql',
        params={'query': sparql_query},
        headers=headers,
        timeout=30
    )
    response.raise_for_status()

    result = {}
    for binding in response.json().get('results', {}).get('bindings', []):
        qid = binding['country']['value'].split('/')[-1]
        demonym = binding.get('demonym', {}).get('value', '')
        if demonym:
            if qid not in result:
                result[qid] = []
            result[qid].append(demonym)

    return result


def clean_aliases(aliases: List[Dict]) -> List[str]:
    cleaned = []
    for alias in aliases:
        text = alias.get('value', '')
        if text and '(' not in text and not has_non_latin(text):
            cleaned.append(text)
    return cleaned


def has_non_latin(text: str) -> bool:
    return bool(re.search(r'[^\w\s\-\'À-ÿ]', text, re.UNICODE))


def fetch_wikidata_lexical():
    countries = load_or_fetch_core()
    all_qids = list(collect_qids(countries))

    entities = batch_fetch_entities(all_qids)

    output_file = os.path.join(RAW_DATA_DIR, 'wikidata_lexical.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)

    print(f"Saved lexical data for {len(entities)} entities to {output_file}")
    return entities


if __name__ == '__main__':
    fetch_wikidata_lexical()
