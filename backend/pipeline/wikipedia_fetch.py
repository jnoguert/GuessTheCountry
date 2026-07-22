import requests
import json
import os
import re
import time
from typing import Dict, List, Tuple
from .wikidata_core import fetch_wikidata_core
from .wikidata_lexical import fetch_wikidata_lexical

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/raw')
os.makedirs(RAW_DATA_DIR, exist_ok=True)

SECTION_STOPLIST = {
    'en': {'See also', 'References', 'Notes', 'External links', 'Further reading', 'Bibliography', 'Gallery', 'Citations'},
    'ca': {'Vegeu també', 'Referències', 'Bibliografia', 'Enllaços externs', 'Notes'},
    'es': {'Véase también', 'Referencias', 'Bibliografía', 'Enlaces externos', 'Notas'}
}

LANGUAGES = ['en', 'ca', 'es']
LANG_CODES = {'en': 'en', 'ca': 'ca', 'es': 'es'}


def load_core_and_lexical() -> Tuple[Dict, Dict]:
    core_file = os.path.join(RAW_DATA_DIR, 'wikidata_stage_a.json')
    lexical_file = os.path.join(RAW_DATA_DIR, 'wikidata_lexical.json')

    if os.path.exists(core_file):
        with open(core_file, 'r', encoding='utf-8') as f:
            core = json.load(f)
    else:
        core = fetch_wikidata_core()

    if os.path.exists(lexical_file):
        with open(lexical_file, 'r', encoding='utf-8') as f:
            lexical = json.load(f)
    else:
        lexical = fetch_wikidata_lexical()

    return core, lexical


def get_wikipedia_title(lang: str, qid: str, lexical: Dict) -> str:
    if qid not in lexical:
        return None

    entity = lexical[qid]
    sitelinks = entity.get('sitelinks', {})

    lang_map = {'en': 'enwiki', 'ca': 'cawiki', 'es': 'eswiki'}
    wiki_key = lang_map.get(lang)

    if wiki_key in sitelinks:
        return sitelinks[wiki_key].get('title')

    return None


def fetch_wikipedia_extract(lang: str, title: str, max_retries: int = 3) -> Tuple[str, str]:
    lang_code = LANG_CODES[lang]
    url = f'https://{lang_code}.wikipedia.org/w/api.php'

    params = {
        'action': 'query',
        'titles': title,
        'prop': 'extracts|revisions',
        'explaintext': 1,
        'exsectionformat': 'wiki',
        'rvprop': 'ids',
        'redirects': 1,
        'format': 'json',
        'formatversion': 2
    }

    headers = {'User-Agent': 'Redactica/1.0'}

    # Exponential backoff with retries
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()

            data = response.json()
            pages = data.get('query', {}).get('pages', [])

            if not pages:
                return None, None

            page = pages[0]
            extract = page.get('extract', '')
            revid = page.get('lastrevid', '')

            return extract, revid
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Too Many Requests
                wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                print(f"    Rate limited. Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                raise

    return None, None


def split_into_paragraphs(text: str) -> List[Tuple[str, str]]:
    section_pattern = r'^={2,}\s*(.+?)\s*=+$'
    lines = text.split('\n')

    sections = []
    current_section = ('', [])

    for line in lines:
        match = re.match(section_pattern, line)
        if match:
            if current_section[1]:
                sections.append((current_section[0], '\n'.join(current_section[1])))
            heading = match.group(1).strip()
            current_section = (heading, [])
        else:
            current_section[1].append(line)

    if current_section[1]:
        sections.append((current_section[0], '\n'.join(current_section[1])))

    result = []
    for section_name, section_body in sections:
        paragraphs = section_body.split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if len(para) > 150 and len(para.split()) > 20:
                result.append((section_name, para))

    return result


def extract_paragraphs(lang: str, text: str) -> List[str]:
    paragraphs = split_into_paragraphs(text)
    stoplist = SECTION_STOPLIST.get(lang, set())

    result = []
    for section_name, para_text in paragraphs:
        if section_name and section_name in stoplist:
            continue
        if para_text:
            result.append(para_text)
            if len(result) >= 5:
                break

    return result[:5] if result else []


def fetch_all_wikipedia_articles():
    print("Fetching Wikipedia articles...")
    core, lexical = load_core_and_lexical()

    articles = {}
    for lang in LANGUAGES:
        lang_dir = os.path.join(RAW_DATA_DIR, f'wikipedia_{lang}')
        os.makedirs(lang_dir, exist_ok=True)

        for qid, country_data in core.items():
            # Skip if already cached from a previous run with usable content
            cache_file = os.path.join(lang_dir, f'{qid}.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                if cached.get('paragraphs'):
                    articles[f'{qid}_{lang}'] = cached['paragraphs']
                    continue

            title = get_wikipedia_title(lang, qid, lexical)
            if not title:
                print(f"  No title found for {qid} in {lang}")
                continue

            # Rate limiting: pace requests to respect Wikipedia's limits
            time.sleep(1.5)

            try:
                extract, revid = fetch_wikipedia_extract(lang, title)
                if extract:
                    paragraphs = extract_paragraphs(lang, extract)

                    cache = {
                        'qid': qid,
                        'lang': lang,
                        'title': title,
                        'paragraphs': paragraphs,
                        'revid': revid,
                        'source_text': extract[:500]  # Store first 500 chars as ref
                    }

                    cache_file = os.path.join(lang_dir, f'{qid}.json')
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(cache, f, ensure_ascii=False, indent=2)

                    articles[f'{qid}_{lang}'] = paragraphs
                    print(f"  {qid} ({lang}): {len(paragraphs)} paragraphs")
                else:
                    print(f"  No extract for {qid} in {lang}")
            except Exception as e:
                print(f"  Error fetching {qid} ({lang}): {e}")

    return articles


if __name__ == '__main__':
    fetch_all_wikipedia_articles()
