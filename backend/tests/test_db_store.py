"""SQLite storage round-trip tests."""
from pipeline.db_store import write_database, read_database


SAMPLE = {
    'Q1': {
        'iso2': 'FR', 'iso3': 'FRA', 'cctld': '.fr',
        'i18n': {
            'en': {'name': 'France', 'capital': 'Paris',
                   'aliases': ['French Republic'],
                   'paragraphs': ['First ████.', 'Second ████.']},
            'ca': {'name': 'França', 'capital': 'París',
                   'aliases': [], 'paragraphs': ['Primer ████.']},
        },
    },
    'Q2': {
        'iso2': 'ES', 'iso3': 'ESP', 'cctld': '.es',
        'i18n': {
            'en': {'name': 'Spain', 'capital': 'Madrid',
                   'aliases': [], 'paragraphs': []},
        },
    },
}


def test_roundtrip(tmp_path):
    db_file = str(tmp_path / 'test.db')
    write_database(SAMPLE, ['Q2', 'Q1'], db_file=db_file)

    countries, daily_order = read_database(db_file=db_file)

    assert daily_order == ['Q2', 'Q1']
    assert set(countries.keys()) == {'Q1', 'Q2'}
    fr = countries['Q1']
    assert fr['iso2'] == 'FR'
    assert fr['i18n']['en']['name'] == 'France'
    assert fr['i18n']['en']['aliases'] == ['French Republic']
    # Paragraph order must be preserved
    assert fr['i18n']['en']['paragraphs'] == ['First ████.', 'Second ████.']
    assert fr['i18n']['ca']['paragraphs'] == ['Primer ████.']


def test_rewrite_replaces_previous_content(tmp_path):
    db_file = str(tmp_path / 'test.db')
    write_database(SAMPLE, ['Q1'], db_file=db_file)
    smaller = {'Q1': SAMPLE['Q1']}
    write_database(smaller, ['Q1'], db_file=db_file)

    countries, daily_order = read_database(db_file=db_file)
    assert set(countries.keys()) == {'Q1'}
    assert daily_order == ['Q1']
