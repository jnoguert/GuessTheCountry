import re
import unicodedata
import json
import os
from typing import Dict, List, Set
from .wikidata_core import fetch_wikidata_core
from .wikidata_lexical import fetch_wikidata_lexical

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/raw')

SUFFIX_TABLES = {
    'es': [
        {'-o': ['-o', '-a', '-os', '-as']},
        {'-és': ['-és', '-esa', '-eses']},
        {'-á': ['-á', '-ana', '-anes']},
        {'-ín': ['-ín', '-ina', '-ines']},
        {'-ense': ['-ense', '-ense', '-enses']},
    ],
    'ca': [
        {'-è': ['-è', '-a', '-es']},
        {'-à': ['-à', '-ana', '-anes']},
        {'-ès': ['-ès', '-esa', '-eses']},
        {'-enc': ['-enc', '-enca', '-encs', '-encas']},
    ],
    'en': []
}


def normalize_text(text: str) -> str:
    return unicodedata.normalize('NFC', text)


def expand_demonym(base_form: str, lang: str) -> List[str]:
    if lang == 'en':
        return [base_form, base_form + 's']

    forms = [base_form]
    suffix_rules = SUFFIX_TABLES.get(lang, [])

    for rule_dict in suffix_rules:
        for suffix, expansions in rule_dict.items():
            if base_form.endswith(suffix[1:]):
                stem = base_form[:-len(suffix)+1]
                for exp in expansions:
                    exp_suffix = exp[1:]
                    forms.append(stem + exp_suffix)

    return list(set(forms))


def load_data():
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


def build_censor_terms(qid: str, lang: str, core: Dict, lexical: Dict) -> Set[str]:
    terms = set()

    # Self name + aliases
    if qid in lexical:
        entity = lexical[qid]
        if lang in entity.get('labels', {}):
            terms.add(entity['labels'][lang].get('value', ''))

        if lang in entity.get('aliases', {}):
            for alias in entity['aliases'][lang]:
                val = alias.get('value', '')
                if '(' not in val:
                    terms.add(val)

    # Capital
    if qid in core:
        country = core[qid]
        capital_qid = country.get('capital')
        if capital_qid and capital_qid in lexical:
            capital_entity = lexical[capital_qid]
            if lang in capital_entity.get('labels', {}):
                terms.add(capital_entity['labels'][lang].get('value', ''))

        # Highest point
        hp_qid = country.get('highest_point')
        if hp_qid and hp_qid in lexical:
            hp_entity = lexical[hp_qid]
            if lang in hp_entity.get('labels', {}):
                terms.add(hp_entity['labels'][lang].get('value', ''))

        # Border countries + their demonyms
        for border_qid in country.get('borders', []):
            if border_qid in lexical:
                border_entity = lexical[border_qid]
                if lang in border_entity.get('labels', {}):
                    terms.add(border_entity['labels'][lang].get('value', ''))

                # Add demonyms of border countries
                if 'demonyms' in border_entity and lang in border_entity.get('demonyms', {}):
                    for dem in border_entity['demonyms'][lang]:
                        terms.add(dem)

        # Own demonyms
        if 'demonyms' in entity and lang in entity.get('demonyms', {}):
            for dem in entity['demonyms'][lang]:
                terms.add(dem)

    return terms


def create_censor_regex(terms: Set[str], lang: str) -> str:
    if not terms:
        return None

    terms_list = list(terms)
    terms_list = [normalize_text(t) for t in terms_list]
    terms_list = [t for t in terms_list if t]
    terms_list = sorted(terms_list, key=lambda x: (-len(x.split()), -len(x)))

    escaped = [re.escape(t) for t in terms_list]
    escaped = list(set(escaped))

    if not escaped:
        return None

    pattern = r'\b(' + '|'.join(escaped) + r')\b'
    return pattern


def censor_paragraph(text: str, pattern: str) -> str:
    if not pattern:
        return text

    def replace_match(match):
        words = match.group(0).split()
        return ' '.join(['█' * len(w) for w in words])

    return re.sub(pattern, replace_match, text, flags=re.IGNORECASE | re.UNICODE)


def censor_all_articles():
    print("Building censorship regexes and censoring articles...")
    core, lexical = load_data()

    censored_articles = {}
    langs = ['en', 'ca', 'es']

    for qid in core.keys():
        censored_articles[qid] = {}

        for lang in langs:
            terms = build_censor_terms(qid, lang, core, lexical)
            pattern = create_censor_regex(terms, lang)

            wiki_data_file = os.path.join(RAW_DATA_DIR, f'wikipedia_{lang}', f'{qid}.json')
            if os.path.exists(wiki_data_file):
                with open(wiki_data_file, 'r', encoding='utf-8') as f:
                    wiki_data = json.load(f)

                paragraphs = wiki_data.get('paragraphs', [])
                censored = [censor_paragraph(p, pattern) for p in paragraphs]

                censored_articles[qid][lang] = {
                    'paragraphs': censored,
                    'original_count': len(paragraphs),
                    'censored_count': len(censored)
                }

                if censored:
                    print(f"  {qid} ({lang}): {len(censored)} censored paragraphs")

    return censored_articles


if __name__ == '__main__':
    censor_all_articles()
