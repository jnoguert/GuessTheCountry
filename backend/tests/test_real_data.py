"""Data-quality checks against the real generated database.

These tests validate the actual countries.db shipped with the repo.
They are skipped automatically when the DB hasn't been built yet.
"""
import os
import pytest
from pipeline.db_store import read_database, DB_FILE

pytestmark = pytest.mark.skipif(
    not os.path.exists(DB_FILE), reason='countries.db not built yet'
)


@pytest.fixture(scope='module')
def dataset():
    return read_database()


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


def test_daily_order_is_shuffled(dataset):
    """The rotation must not be alphabetical/insertion order."""
    countries, daily_order = dataset
    assert daily_order != sorted(daily_order)
    assert daily_order != sorted(daily_order, key=lambda q: int(q[1:]))
    insertion_order = list(countries.keys())
    assert daily_order != insertion_order


def test_consecutive_days_are_varied(dataset, monkeypatch):
    """A window of consecutive days must yield distinct, non-alphabetical
    countries once the dataset is complete."""
    import app.data_loader as dl
    from app import puzzle

    countries, daily_order = dataset
    loader = dl.DataLoader.__new__(dl.DataLoader)
    loader.countries = countries
    loader.daily_order = daily_order
    monkeypatch.setattr(dl, '_loader', loader)

    start = puzzle.today_day_index()
    names = []
    for day in range(start, start + 30):
        country = puzzle.get_daily_country(day_index=day)
        assert country is not None
        names.append(country['i18n']['en']['name'])

    # 30 consecutive days: all distinct (rotation only holds playable
    # countries, so the skip-forward never causes back-to-back repeats)
    assert len(set(names)) == 30, f'answers repeat: {names}'
    # ...and not served in alphabetical order
    assert names != sorted(names)


def test_simulate_a_year_of_puzzles(dataset, monkeypatch):
    """Every day for the next 365 days must produce a playable puzzle."""
    import app.data_loader as dl
    from app import puzzle

    countries, daily_order = dataset
    loader = dl.DataLoader.__new__(dl.DataLoader)
    loader.countries = countries
    loader.daily_order = daily_order
    monkeypatch.setattr(dl, '_loader', loader)

    start = puzzle.today_day_index()
    for day in range(start, start + 365):
        for lang in ('en', 'ca', 'es'):
            p = puzzle.get_todays_puzzle(lang, day_index=day)
            assert p is not None, f'day {day} ({lang}): no puzzle'
            assert p['paragraphs'], f'day {day} ({lang}): no paragraphs'
