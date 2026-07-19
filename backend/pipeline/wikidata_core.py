import requests
import json
import os
from typing import Dict, List

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/raw')
os.makedirs(RAW_DATA_DIR, exist_ok=True)

SPARQL_ENDPOINT = 'https://query.wikidata.org/sparql'

COUNTRY_QUERY = """
SELECT ?country ?countryLabel ?capital ?highestPoint ?iso2 ?iso3 ?cctld ?currency
       (GROUP_CONCAT(DISTINCT ?border; separator="|") AS ?borders)
       (GROUP_CONCAT(DISTINCT ?language; separator="|") AS ?languages)
WHERE {
  ?country wdt:P31/wdt:P279* wd:Q3624078 .
  ?country p:P463 ?memberStmt .
  ?memberStmt ps:P463 wd:Q1065 .
  MINUS { ?memberStmt pq:P582 ?end . }
  OPTIONAL { ?country wdt:P36 ?capital }
  OPTIONAL { ?country wdt:P610 ?highestPoint }
  OPTIONAL { ?country wdt:P297 ?iso2 }
  OPTIONAL { ?country wdt:P298 ?iso3 }
  OPTIONAL { ?country wdt:P78 ?cctld }
  OPTIONAL { ?country wdt:P38 ?currency }
  OPTIONAL { ?country wdt:P47 ?border }
  OPTIONAL { ?country (wdt:P37|wdt:P2936) ?language }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
GROUP BY ?country ?countryLabel ?capital ?highestPoint ?iso2 ?iso3 ?cctld ?currency
ORDER BY ?countryLabel
"""


def fetch_wikidata_core(force: bool = False) -> Dict:
    output_file = os.path.join(RAW_DATA_DIR, 'wikidata_stage_a.json')
    if not force and os.path.exists(output_file):
        print("Core country data already cached, skipping fetch.")
        with open(output_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    print("Fetching core country data from Wikidata...")
    headers = {
        'User-Agent': 'GuessTheCountry/1.0 (https://github.com/yourusername/guess-the-country)',
        'Accept': 'application/sparql-results+json'
    }

    response = requests.get(
        SPARQL_ENDPOINT,
        params={'query': COUNTRY_QUERY},
        headers=headers,
        timeout=60
    )
    response.raise_for_status()

    data = response.json()
    countries = {}

    for binding in data.get('results', {}).get('bindings', []):
        qid = binding['country']['value'].split('/')[-1]
        borders = binding.get('borders', {}).get('value', '').split('|') if binding.get('borders', {}).get('value') else []
        languages = binding.get('languages', {}).get('value', '').split('|') if binding.get('languages', {}).get('value') else []

        countries[qid] = {
            'label': binding.get('countryLabel', {}).get('value', ''),
            'capital': binding.get('capital', {}).get('value', '').split('/')[-1] if binding.get('capital') else None,
            'highest_point': binding.get('highestPoint', {}).get('value', '').split('/')[-1] if binding.get('highestPoint') else None,
            'iso2': binding.get('iso2', {}).get('value', ''),
            'iso3': binding.get('iso3', {}).get('value', ''),
            'cctld': binding.get('cctld', {}).get('value', ''),
            'currency': binding.get('currency', {}).get('value', '').split('/')[-1] if binding.get('currency') else None,
            'borders': [b.split('/')[-1] for b in borders if b],
            'languages': [l.split('/')[-1] for l in languages if l]
        }

    output_file = os.path.join(RAW_DATA_DIR, 'wikidata_stage_a.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(countries, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(countries)} countries to {output_file}")
    return countries


if __name__ == '__main__':
    fetch_wikidata_core()
