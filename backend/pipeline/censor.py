import re
import unicodedata
import json
import os
import random
from typing import Dict, List, Optional, Set
from .wikidata_core import fetch_wikidata_core
from .wikidata_lexical import fetch_wikidata_lexical
from .geo_adjectives import GEO_ADJECTIVES

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/raw')

# The starting clue is Wikipedia's whole intro (lede), often several hundred
# words - far too long to read as an opening hint. Keep whole sentences up to
# LEDE_MAX_CHARS (a couple of sentences) instead of a wall of text, but never
# stop below LEDE_MIN_CHARS: a one-line lede like "Malaysia is a country in
# Southeast Asia." would otherwise censor down to a uselessly short clue.
LEDE_MAX_CHARS = 260
LEDE_MIN_CHARS = 120

# Blurring block length: a censored block's size otherwise leaks the exact
# letter count of the hidden word, which is a huge tell (e.g. a 5-letter
# block for a country name narrows the guess enormously). Each block's
# length is shifted by 2-3 characters, direction picked at random, so the
# visible width no longer matches the real word.
BLOCK_LENGTH_JITTER_RANGE = (2, 3)


def fuzz_block_length(length: int, rng: random.Random) -> int:
    """Word length -> displayed block length, offset by 2-3 chars, never
    the true length and never below 1 character.

    The subtraction CAN exceed the word's own length - e.g. a 1-letter
    word minus 3, or a 3-letter word minus 3 landing on exactly 0. Naively
    clamping that to 1 would be wrong twice over: it can accidentally
    reproduce the true length (a 1-letter word minus anything, clamped to
    1, equals itself), and it silently shrinks the intended 2-3 character
    offset down to whatever's left. Instead, an underflow flips the whole
    offset to the positive direction, so the offset magnitude (2 or 3) is
    always preserved and the result never equals the input:
        length=1, magnitude=3  ->  1-3=-2 underflows  ->  1+3=4
        length=3, magnitude=3  ->  3-3=0  underflows  ->  3+3=6
        length=4, magnitude=3  ->  4-3=1  (no underflow, valid as-is)
    """
    delta = rng.randint(*BLOCK_LENGTH_JITTER_RANGE)
    if rng.random() < 0.5:
        delta = -delta
    fuzzed = length + delta
    if fuzzed < 1:
        fuzzed = length + abs(delta)
    return fuzzed


def _block(word: str, rng: random.Random) -> str:
    return '█' * fuzz_block_length(len(word), rng)


# Fixed seed: a full pipeline rebuild with unchanged inputs always produces
# byte-identical censored output, so re-runs don't cause spurious git diffs.
CENSOR_RNG_SEED = 20260120

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


# Split on the space after . ! ? only when the next sentence starts with a
# capital letter. This deliberately does NOT fire inside "103.000" (a digit
# follows the dot, not a capital) or after "s.", "aC" etc. (lowercase follows),
# which is exactly the punctuation a naive split on "." would mangle.
_SENTENCE_BOUNDARY = re.compile(r'(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ])', re.UNICODE)
# Zero-width / invisible chars (ZWSP, ZWNJ, ZWJ, word-joiner, BOM).
_ZERO_WIDTH = re.compile('[' + ''.join(map(chr, (0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF))) + ']')


def split_sentences(text: str) -> List[str]:
    # Wikipedia extracts leave zero-width chars (citation artifacts) glued right
    # after sentence-ending periods; they aren't \s, so they'd block the split
    # and swallow several sentences into one. Drop them first.
    text = _ZERO_WIDTH.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return [s for s in _SENTENCE_BOUNDARY.split(text) if s]


def trim_lede(text: str, max_chars: int = LEDE_MAX_CHARS,
              min_chars: int = LEDE_MIN_CHARS) -> str:
    """Shorten the intro paragraph to the first few whole sentences.

    Adds whole sentences until the clue is at least min_chars long, then keeps
    adding while they still fit inside max_chars. The first sentence is always
    kept, so the clue is never empty and never cut mid-sentence.
    """
    sentences = split_sentences(text)
    if not sentences:
        return text.strip()

    clue = sentences[0]
    for sentence in sentences[1:]:
        if len(clue) >= min_chars and len(clue) + 1 + len(sentence) > max_chars:
            break
        clue += ' ' + sentence
    return clue


# ---------------------------------------------------------------------------
# Phonetic / pronunciation stripping
# ---------------------------------------------------------------------------
# The opening parenthetical of a country article is a naming/pronunciation
# dump: IPA ("Islàndia (... IPA: [ˈistlant])"), English respellings ("Gabon
# ( gə-BON; ...)"), native scripts ("Rússia (rus: Россия ...)"), romanizations
# and audio links ("escolteu (?·pàg.)"). All of these spell out how the answer
# sounds or is written and make the first clue far too easy, so we remove them.

_IPA_MARKS = 'ˈˌːˑ'  # primary/secondary stress and length marks - IPA-only
# Non-Latin scripts used to gloss the native name (Cyrillic, Greek, CJK, ...).
_FOREIGN_SCRIPT = re.compile(
    '[Ͱ-Ͽ'   # Greek
    'Ѐ-ԯ'    # Cyrillic
    'Ա-֏'    # Armenian
    '֐-׿'    # Hebrew
    '؀-ۿ'    # Arabic
    'ऀ-ॿ'    # Devanagari
    '฀-๿'    # Thai
    'ᄀ-ᇿ'    # Hangul Jamo
    '぀-ヿ'    # Kana
    '㐀-鿿'    # CJK
    '가-힯]'   # Hangul syllables
)
# Labels that introduce a transcription, plus audio-link artifacts.
_PRON_LABEL = re.compile(
    r'\b(?:IPA|AFI|TR)\b:?'
    r'|\bpron(?:un|ún|ounc)\w*'
    r'|\bpinyin\b|\bromani[zst]\w*|\btransliter\w*|\btranscripci\w*'
    r'|\bescolt\w*|\bescuch\w*'
    r'|\(\?·[^)]*\)',
    re.IGNORECASE,
)
_BRACKETED = re.compile(r'\[[^\[\]]*\]')
# A /.../ pair is an IPA transcription only if it actually contains a phonetic
# character - guards against "1969/70" (single slash) and the like.
_SLASHED_IPA = re.compile(
    r'/(?=[^/\n]*[' + _IPA_MARKS + r'ɐ-ʯ̀-ͯ])[^/\n]{1,80}/'
)
# A run carrying an IPA stress/length mark - catches un-bracketed IPA ("AFI
# romɨˈni.a") that a malformed extract left outside its brackets.
_BARE_IPA = re.compile(
    r"[\w.'ɐ-ʯ̀-ͯ" + _IPA_MARKS + r']*'
    r'[' + _IPA_MARKS + r']'
    r"[\w.'ɐ-ʯ̀-ͯ" + _IPA_MARKS + r']*'
)


def _is_pron_parenthetical(content: str) -> bool:
    """A parenthetical is pronunciation/native-name clutter (not a factual
    aside like '(a 287 km)') if it carries a phonetic or foreign-script signal."""
    if any(mark in content for mark in _IPA_MARKS):
        return True
    if '[' in content or ']' in content:
        return True
    if _SLASHED_IPA.search(content):
        return True
    if _PRON_LABEL.search(content):
        return True
    if _FOREIGN_SCRIPT.search(content):
        return True
    return False


def _drop_pron_parentheticals(text: str) -> str:
    """Delete whole (possibly nested) parentheticals that are pronunciation or
    native-name clutter, keeping purely factual ones. An unbalanced '(' is left
    in place; the residual passes still scrub any phonetics inside it."""
    out = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == '(':
            depth, j = 0, i
            while j < n:
                if text[j] == '(':
                    depth += 1
                elif text[j] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j < n and depth == 0:  # matched close found
                if not _is_pron_parenthetical(text[i + 1:j]):
                    out.append(text[i:j + 1])
                i = j + 1
                continue
        out.append(text[i])
        i += 1
    return ''.join(out)


def _strip_unmatched(text: str, opener: str, closer: str) -> str:
    """Drop leftover unmatched brackets/parens (malformed source extracts and
    nested-markup remnants leave dangling ones behind)."""
    keep = [True] * len(text)
    stack = []
    for i, ch in enumerate(text):
        if ch == opener:
            stack.append(i)
        elif ch == closer:
            if stack:
                stack.pop()
            else:
                keep[i] = False  # closer with no opener
    for i in stack:
        keep[i] = False          # opener with no closer
    return ''.join(ch for ch, k in zip(text, keep) if k)


def _tidy_spacing(text: str) -> str:
    text = re.sub(r'\(\s*[,;:]?\s*\)', '', text)   # empty / near-empty parens
    text = re.sub(r'\(\s+', '(', text)              # space just inside "("
    text = re.sub(r'\s+([,;:.)])', r'\1', text)     # space before punctuation
    text = re.sub(r'([,;:])(?:\s*[,;:])+', r'\1', text)  # doubled separators
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def strip_phonetics(text: str) -> str:
    """Remove IPA, respellings, native-script glosses, romanizations and audio
    links so the opening clue can't be read off phonetically."""
    text = _ZERO_WIDTH.sub('', text)
    text = _drop_pron_parentheticals(text)
    # Iterate so nested markup remnants ("[[X]]" -> "[]" -> "") fully collapse.
    while True:
        stripped = _BRACKETED.sub('', text)
        if stripped == text:
            break
        text = stripped
    text = _SLASHED_IPA.sub('', text)
    text = _BARE_IPA.sub('', text)
    text = _PRON_LABEL.sub('', text)
    text = _strip_unmatched(text, '(', ')')
    text = _strip_unmatched(text, '[', ']')
    return _tidy_spacing(text)


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

        # Languages spoken there: names are lowercase in es/ca ("catalán",
        # "euskera") so the proper-noun pass misses them; they also inflect
        # like demonyms ("catalanes"), hence the expansion.
        for lang_qid in country.get('languages', []):
            lang_entity = lexical.get(lang_qid, {})
            label = lang_entity.get('labels', {}).get(lang, {}).get('value', '')
            if label:
                terms.update(expand_demonym(label, lang))
            for alias in lang_entity.get('aliases', {}).get(lang, []):
                val = alias.get('value', '')
                if val and '(' not in val:
                    terms.update(expand_demonym(val, lang))

        # Currency ("peseta", "danish krone" -> already partly covered by
        # demonyms, but the noun itself can be a giveaway too)
        currency_qid = country.get('currency')
        if currency_qid and currency_qid in lexical:
            cur_entity = lexical[currency_qid]
            label = cur_entity.get('labels', {}).get(lang, {}).get('value', '')
            if label:
                terms.add(label)

    return terms


def build_global_geo_terms(lang: str, core: Dict, lexical: Dict) -> Set[str]:
    """Geographic/nationality terms to censor in EVERY article, regardless of
    which country it is.

    Two sources, both giveaways when they appear in someone else's article:
      * the demonym of ANY country (not just neighbours) - build_censor_terms
        only covers borders, so a mention of a far-away nation's people leaks;
      * the curated continent/region/nationality adjective list, which fills
        the large gaps in Wikidata's Catalan/Spanish demonym coverage.
    """
    terms: Set[str] = set(GEO_ADJECTIVES.get(lang, []))

    for qid in core:
        entity = lexical.get(qid, {})
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


def censor_paragraph(text: str, pattern: str, rng: Optional[random.Random] = None) -> str:
    if not pattern:
        return text
    rng = rng or random.Random()

    def replace_match(match):
        words = match.group(0).split()
        return ' '.join(_block(w, rng) for w in words)

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

# Letters incl. Latin Extended Additional (ṭ, ā... used in transliterations);
# hyphenated compounds ("sud-africà") are one token so name stems match them.
_LETTERS = r"A-Za-zÀ-ÖØ-öø-ÿĀ-ſḀ-ỿ"
_WORD_RE = re.compile(rf"[{_LETTERS}]+(?:-[{_LETTERS}]+)*", re.UNICODE)


def _is_capitalized(word: str) -> bool:
    return word[0].isupper() and not word.isupper()


def _is_acronym(word: str) -> bool:
    return len(word) >= 2 and word.isupper()


def _sentence_starts(text: str) -> Set[int]:
    """Offsets of words that begin a sentence (capitalization there is
    not evidence of a proper noun). Only true sentence enders count:
    an opening parenthesis or quote is NOT a sentence start, otherwise
    '(Afghānistān, ...)' style variants would escape censorship."""
    starts = set()
    for m in _WORD_RE.finditer(text):
        prefix = text[:m.start()].rstrip()
        if not prefix or prefix[-1] in '.!?':
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


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize('NFD', text)
    return ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')


def build_name_stems(qid: str, lang: str, core: Dict, lexical: Dict) -> Set[str]:
    """Normalized prefixes of the country's own single-word names/aliases.

    Languages derive lowercase adjectives from country names ('Austràlia'
    -> 'australià', 'Austria' -> 'austríaco'); when Wikidata lacks that
    demonym, exact term matching misses them. Any word starting with one
    of these stems is a giveaway inside the country's own article, so
    over-matching here is safe by design.
    """
    entity = lexical.get(qid, {})
    words = set()

    label = entity.get('labels', {}).get(lang, {}).get('value', '')
    if label:
        words.add(label)
    for alias in entity.get('aliases', {}).get(lang, []):
        val = alias.get('value', '')
        if val and '(' not in val:
            words.add(val)

    stems = set()
    for word in words:
        # Single-word names only: components of multi-word names
        # ("United", "States") are common words and would over-censor.
        if ' ' in word.strip() or len(word) < 4:
            continue
        normalized = _strip_accents(word).casefold()
        stems.add(normalized[:max(4, len(normalized) - 3)])
    return stems


def censor_name_stems(text: str, stems: Set[str], rng: Optional[random.Random] = None) -> str:
    """Black out any word derived from the country's own name.

    Substring (not prefix) matching so compounds are caught too:
    'afrobolivians', 'lusobrasilera'. Over-censoring an occasional
    unrelated word inside the country's own article is acceptable.
    """
    if not stems:
        return text
    rng = rng or random.Random()

    def replace(m):
        word = m.group(0)
        normalized = _strip_accents(word).casefold()
        if any(stem in normalized for stem in stems):
            return _block(word, rng)
        return word

    return _WORD_RE.sub(replace, text)


def censor_proper_nouns(text: str, lang: str, known: Set[str], rng: Optional[random.Random] = None) -> str:
    """Black out every capitalized mid-sentence word, every known proper
    noun (even sentence-initial), and non-whitelisted acronyms."""
    whitelist = PROPER_NOUN_WHITELIST.get(lang, set())
    starts = _sentence_starts(text)
    rng = rng or random.Random()

    def replace(m):
        word = m.group(0)
        if _is_acronym(word):
            return word if word in ACRONYM_WHITELIST else _block(word, rng)
        if not _is_capitalized(word) or word in whitelist:
            return word
        if m.start() in starts and word not in known:
            return word  # plain sentence-initial capitalization
        return _block(word, rng)

    return _WORD_RE.sub(replace, text)


def censor_all_articles():
    print("Building censorship regexes and censoring articles...")
    core, lexical = load_data()
    rng = random.Random(CENSOR_RNG_SEED)

    censored_articles = {}
    langs = ['en', 'ca', 'es']

    # Same for every country in a language, so compute the (large) set once.
    global_geo_terms = {lang: build_global_geo_terms(lang, core, lexical) for lang in langs}

    for qid in core.keys():
        censored_articles[qid] = {}

        for lang in langs:
            terms = build_censor_terms(qid, lang, core, lexical) | global_geo_terms[lang]
            pattern = create_censor_regex(terms, lang)

            wiki_data_file = os.path.join(RAW_DATA_DIR, f'wikipedia_{lang}', f'{qid}.json')
            if os.path.exists(wiki_data_file):
                with open(wiki_data_file, 'r', encoding='utf-8') as f:
                    wiki_data = json.load(f)

                paragraphs = wiki_data.get('paragraphs', [])
                # Strip IPA / pronunciation guides / native-script glosses first
                # (they spell out the answer), then trim the intro paragraph to
                # a couple of sentences so the opening clue isn't a wall of text.
                paragraphs = [strip_phonetics(p) for p in paragraphs]
                if paragraphs:
                    paragraphs = [trim_lede(paragraphs[0])] + list(paragraphs[1:])
                # Pass 1: censor known terms (names, borders, demonyms...)
                censored = [censor_paragraph(p, pattern, rng) for p in paragraphs]
                # Pass 2: censor every remaining proper noun / toponym
                known_proper = collect_proper_nouns(censored, lang)
                censored = [censor_proper_nouns(p, lang, known_proper, rng) for p in censored]
                # Pass 3: censor lowercase words derived from the name
                # ('australià', 'austríaco') that passes 1-2 can miss
                stems = build_name_stems(qid, lang, core, lexical)
                censored = [censor_name_stems(p, stems, rng) for p in censored]

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
