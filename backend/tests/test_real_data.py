"""Data-quality checks against the real generated dataset.

These validate the actual countries.json / daily_order.json shipped with the
repo (the same data the frontend's game.json is built from). They are skipped
automatically when the dataset hasn't been built yet.
"""
import json
import os
import pytest

LANGUAGES = ('en', 'ca', 'es')
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
COUNTRIES_FILE = os.path.join(DATA_DIR, 'countries.json')
DAILY_ORDER_FILE = os.path.join(DATA_DIR, 'daily_order.json')

pytestmark = pytest.mark.skipif(
    not os.path.exists(COUNTRIES_FILE), reason='dataset not built yet'
)


@pytest.fixture(scope='module')
def dataset():
    with open(COUNTRIES_FILE, encoding='utf-8') as f:
        countries = json.load(f)
    with open(DAILY_ORDER_FILE, encoding='utf-8') as f:
        daily_order = json.load(f)
    return countries, daily_order


def _daily_qid(countries, daily_order, day_index):
    """Mirror of the client-side rotation (engine.ts getDailyCountry): from the
    day's slot, walk forward to the first country playable in every language."""
    n = len(daily_order)
    for offset in range(n):
        qid = daily_order[(day_index + offset) % n]
        c = countries.get(qid)
        if c and all(c['i18n'].get(lang, {}).get('paragraphs') for lang in LANGUAGES):
            return qid
    return None


def test_has_most_un_countries(dataset):
    countries, _ = dataset
    assert len(countries) >= 180


def test_daily_order_contains_exactly_the_playable_countries(dataset):
    countries, daily_order = dataset
    playable = {
        qid for qid, c in countries.items()
        if all(c['i18n'].get(lang, {}).get('paragraphs')
               for lang in ('en', 'ca', 'es'))
    }
    assert sorted(daily_order) == sorted(playable)


def test_enough_playable_countries(dataset):
    """The daily rotation only works if plenty of countries have content
    in every language."""
    countries, _ = dataset
    playable = [
        qid for qid, c in countries.items()
        if all(c['i18n'].get(lang, {}).get('paragraphs')
               for lang in ('en', 'ca', 'es'))
    ]
    assert len(playable) >= 100, f'only {len(playable)} fully playable countries'


def test_playable_countries_have_exactly_4_paragraphs(dataset):
    """1 starting paragraph + 3 hint unlocks = 4; the dataset must not
    ship a 5th fragment nobody can earn."""
    countries, daily_order = dataset
    for qid in daily_order:
        c = countries[qid]
        for lang in ('en', 'ca', 'es'):
            paragraphs = c['i18n'].get(lang, {}).get('paragraphs', [])
            assert len(paragraphs) == 4, f'{qid}/{lang} has {len(paragraphs)} paragraphs'
            for p in paragraphs:
                assert len(p) > 50, f'{qid}/{lang} has a suspiciously short paragraph'


def test_own_name_is_censored_in_paragraphs(dataset):
    """The country's own (normalized) name must never appear in its own
    censored paragraphs."""
    import unicodedata

    def norm(s):
        s = unicodedata.normalize('NFD', s)
        s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
        return s.casefold()

    countries, _ = dataset
    leaks = []
    for qid, c in countries.items():
        for lang in ('en', 'ca', 'es'):
            i18n = c['i18n'].get(lang, {})
            name = i18n.get('name', '')
            if not name or len(name) < 4:
                continue  # very short names can legitimately collide
            for i, p in enumerate(i18n.get('paragraphs', [])):
                if norm(name) in norm(p):
                    leaks.append(f'{qid}/{lang} paragraph {i} leaks "{name}"')
    assert not leaks, 'Name leaks found:\n' + '\n'.join(leaks[:20])


def test_playable_countries_have_capitals_in_every_language(dataset):
    """The result screen shows the capital; a playable country must never
    ship with a blank one (e.g. Nigeria's capital entity lacks en/ca
    labels on Wikidata itself - the build must fall back or patch)."""
    countries, daily_order = dataset
    missing = []
    for qid in daily_order:
        c = countries[qid]
        for lang in ('en', 'ca', 'es'):
            if not c['i18n'].get(lang, {}).get('capital'):
                missing.append(f"{qid} ({c['i18n']['en']['name']}) has no capital in {lang}")
    assert not missing, 'Blank capitals:\n' + '\n'.join(missing)


def test_playable_countries_have_iso2(dataset):
    """A blank iso2 breaks the flag emoji on the result screen and makes
    the country unmatchable on the Easy Mode map (found via Q756617
    'Kingdom of Denmark': Wikidata never attaches ISO codes to the
    sovereign-state entity distinct from the plain country entity)."""
    countries, daily_order = dataset
    missing = [
        f"{qid} ({countries[qid]['i18n']['en']['name']}) has no iso2"
        for qid in daily_order if not countries[qid].get('iso2')
    ]
    assert not missing, 'Blank iso2:\n' + '\n'.join(missing)


def test_denmark_short_form_guessable_in_every_language(dataset):
    """Regression for Q756617: its ca/es labels were the formal 'Regne/
    Reino de Dinamarca' with zero aliases, so the natural short guess
    'Dinamarca' would incorrectly fail even though the equivalent short
    English alias already existed."""
    countries, _ = dataset
    denmark = countries.get('Q756617')
    if denmark is None:
        pytest.skip('Denmark entity not present in this dataset')
    assert denmark['iso2'] == 'DK'
    expected_short_form = {'en': 'denmark', 'ca': 'dinamarca', 'es': 'dinamarca'}
    for lang, short in expected_short_form.items():
        i18n = denmark['i18n'][lang]
        names = {i18n['name'].casefold(), *(a.casefold() for a in i18n['aliases'])}
        assert short in names, f'{lang}: "{short}" not guessable ({names})'


def test_daily_order_is_shuffled(dataset):
    """The rotation must not be alphabetical/insertion order."""
    countries, daily_order = dataset
    assert daily_order != sorted(daily_order)
    assert daily_order != sorted(daily_order, key=lambda q: int(q[1:]))
    insertion_order = list(countries.keys())
    assert daily_order != insertion_order


def test_consecutive_days_are_varied(dataset):
    """A window of consecutive days must yield distinct, non-alphabetical
    countries once the dataset is complete."""
    countries, daily_order = dataset
    names = [
        countries[_daily_qid(countries, daily_order, day)]['i18n']['en']['name']
        for day in range(30)
    ]
    # 30 consecutive days: all distinct (rotation only holds playable
    # countries, so the skip-forward never causes back-to-back repeats)
    assert len(set(names)) == 30, f'answers repeat: {names}'
    # ...and not served in alphabetical order
    assert names != sorted(names)


def test_simulate_a_year_of_puzzles(dataset):
    """Every day for the next 365 days must resolve to a playable country."""
    countries, daily_order = dataset
    for day in range(365):
        qid = _daily_qid(countries, daily_order, day)
        assert qid is not None, f'day {day}: no playable country'
        for lang in LANGUAGES:
            assert countries[qid]['i18n'][lang]['paragraphs'], \
                f'day {day} ({lang}): no paragraphs'
