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
    entity = lexical.get(qid, {})

    # Self name + aliases
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

                # Add demonyms of border countries (with inflected forms)
                for dem in border_entity.get('demonyms', {}).get(lang, []):
                    terms.update(expand_demonym(dem, lang))

        # Own demonyms (with inflected forms)
        for dem in entity.get('demonyms', {}).get(lang, []):
            terms.update(expand_demonym(dem, lang))

    return terms


def create_censor_regex(terms: Set[str], lang: str) -> str:
    if not terms:
        return None

    normalized = {normalize_text(t) for t in terms if normalize_text(t)}
    # Longest-first so multi-word terms match before their substrings
    terms_list = sorted(normalized, key=lambda x: (-len(x.split()), -len(x)))

    escaped = [re.escape(t) for t in terms_list]

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


# ---------------------------------------------------------------------------
# Proper-noun censorship: black out every toponym / proper name
# ---------------------------------------------------------------------------
# Capitalized words that are NOT proper nouns and must survive (per language).
PROPER_NOUN_WHITELIST = {
    'en': {
        'January', 'February', 'March', 'April', 'May', 'June', 'July',
        'August', 'September', 'October', 'November', 'December',
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
        'Saturday', 'Sunday',
    },
    'ca': set(),   # months/days are lowercase in Catalan
    'es': set(),   # months/days are lowercase in Spanish
}

# Harmless all-caps abbreviations that carry no geographic clue.
ACRONYM_WHITELIST = {'GDP', 'PPP', 'HDI', 'GNI', 'UTC', 'TV', 'DNA', 'AD', 'BC', 'CE', 'BCE'}

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ſ]+", re.UNICODE)


def _is_capitalized(word: str) -> bool:
    return word[0].isupper() and not word.isupper()


def _is_acronym(word: str) -> bool:
    return len(word) >= 2 and word.isupper()


def _sentence_starts(text: str) -> Set[int]:
    """Offsets of words that begin a sentence (capitalization there is
    not evidence of a proper noun)."""
    starts = set()
    for m in _WORD_RE.finditer(text):
        prefix = text[:m.start()].rstrip()
        if not prefix or prefix[-1] in '.!?«"\'()[]':
            starts.add(m.start())
    return starts


def collect_proper_nouns(paragraphs, lang: str) -> Set[str]:
    """Words seen capitalized mid-sentence anywhere in the article are
    proper nouns; this also lets us censor them at sentence starts."""
    whitelist = PROPER_NOUN_WHITELIST.get(lang, set())
    known: Set[str] = set()
    for text in paragraphs:
        starts = _sentence_starts(text)
        for m in _WORD_RE.finditer(text):
            word = m.group(0)
            if m.start() in starts:
                continue
            if _is_capitalized(word) and word not in whitelist:
                known.add(word)
    return known


def censor_proper_nouns(text: str, lang: str, known: Set[str]) -> str:
    """Black out every capitalized mid-sentence word, every known proper
    noun (even sentence-initial), and non-whitelisted acronyms."""
    whitelist = PROPER_NOUN_WHITELIST.get(lang, set())
    starts = _sentence_starts(text)

    def replace(m):
        word = m.group(0)
        if _is_acronym(word):
            return word if word in ACRONYM_WHITELIST else '█' * len(word)
        if not _is_capitalized(word) or word in whitelist:
            return word
        if m.start() in starts and word not in known:
            return word  # plain sentence-initial capitalization
        return '█' * len(word)

    return _WORD_RE.sub(replace, text)


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
                # Pass 1: censor known terms (names, borders, demonyms...)
                censored = [censor_paragraph(p, pattern) for p in paragraphs]
                # Pass 2: censor every remaining proper noun / toponym
                known_proper = collect_proper_nouns(censored, lang)
                censored = [censor_proper_nouns(p, lang, known_proper) for p in censored]

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
