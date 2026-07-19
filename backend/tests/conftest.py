import pytest
import app.data_loader as dl


def _make_i18n(name: str, capital: str, aliases=None, n_paragraphs: int = 5):
    return {
        'name': name,
        'capital': capital,
        'aliases': aliases or [],
        'paragraphs': [f'Censored paragraph {i} about ████.' for i in range(n_paragraphs)],
    }


FAKE_COUNTRIES = {
    # Missing ca/es content on purpose: daily selection must skip it
    'Q_BROKEN': {
        'iso2': 'XX', 'iso3': 'XXX', 'cctld': '.xx',
        'i18n': {
            'en': _make_i18n('Brokenland', 'Nowhere'),
            'ca': {'name': 'Brokenlàndia', 'capital': 'Enlloc', 'aliases': [], 'paragraphs': []},
            'es': {'name': 'Brokenlandia', 'capital': 'Ninguna', 'aliases': [], 'paragraphs': []},
        },
    },
    'Q_FR': {
        'iso2': 'FR', 'iso3': 'FRA', 'cctld': '.fr',
        'i18n': {
            'en': _make_i18n('France', 'Paris', ['French Republic']),
            'ca': _make_i18n('França', 'París', ['República Francesa']),
            'es': _make_i18n('Francia', 'París', ['República Francesa']),
        },
    },
    'Q_ES': {
        'iso2': 'ES', 'iso3': 'ESP', 'cctld': '.es',
        'i18n': {
            'en': _make_i18n('Spain', 'Madrid', ['Kingdom of Spain']),
            'ca': _make_i18n('Espanya', 'Madrid', ['Regne d\'Espanya']),
            'es': _make_i18n('España', 'Madrid', ['Reino de España']),
        },
    },
}

FAKE_DAILY_ORDER = ['Q_BROKEN', 'Q_FR', 'Q_ES']


@pytest.fixture
def fake_loader(monkeypatch):
    """Install an in-memory dataset so tests never touch disk or network."""
    loader = dl.DataLoader.__new__(dl.DataLoader)
    loader.countries = FAKE_COUNTRIES
    loader.daily_order = FAKE_DAILY_ORDER
    monkeypatch.setattr(dl, '_loader', loader)
    return loader
