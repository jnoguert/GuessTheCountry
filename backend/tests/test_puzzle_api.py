"""API-level tests: full HTTP round trips through FastAPI, playing whole
games on simulated days via the ?day= parameter."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client(fake_loader):
    return TestClient(app)


def _guess(client, lang, puzzle_id, number, text):
    res = client.post('/api/guess', json={
        'lang': lang,
        'puzzle_id': puzzle_id,
        'guess_number': number,
        'guess_text': text,
    })
    assert res.status_code == 200, res.text
    return res.json()


class TestPuzzleEndpoint:
    def test_returns_only_first_paragraph(self, client):
        res = client.get('/api/puzzle/en', params={'day': 1})
        assert res.status_code == 200
        data = res.json()
        assert data['max_guesses'] == 5
        assert len(data['paragraphs']) == 1  # never leak the rest up front

    def test_simulated_days_change_the_puzzle(self, client):
        id1 = client.get('/api/puzzle/en', params={'day': 1}).json()['puzzle_id']
        id2 = client.get('/api/puzzle/en', params={'day': 2}).json()['puzzle_id']
        assert id1 == '2026-01-02'
        assert id2 == '2026-01-03'

    def test_unknown_language_404(self, client):
        res = client.get('/api/puzzle/de', params={'day': 1})
        assert res.status_code == 404


class TestGuessFlow:
    def test_win_on_first_guess(self, client):
        pid = client.get('/api/puzzle/en', params={'day': 1}).json()['puzzle_id']
        result = _guess(client, 'en', pid, 1, 'France')
        assert result['correct'] is True
        assert result['game_over'] is True
        assert result['answer']['name'] == 'France'
        assert result['answer']['iso2'] == 'FR'

    def test_wrong_guess_reveals_next_paragraph(self, client):
        pid = client.get('/api/puzzle/en', params={'day': 1}).json()['puzzle_id']
        result = _guess(client, 'en', pid, 1, 'Germany')
        assert result['correct'] is False
        assert result['game_over'] is False
        assert result['next_paragraph']  # the second paragraph
        assert result['answer'] is None  # answer must not leak mid-game

    def test_full_losing_game(self, client):
        pid = client.get('/api/puzzle/en', params={'day': 1}).json()['puzzle_id']
        for n in range(1, 5):
            result = _guess(client, 'en', pid, n, 'Germany')
            assert result['game_over'] is False, f'guess {n} ended the game early'
            assert result['next_paragraph']
        # 5th wrong guess ends the game and reveals the answer
        result = _guess(client, 'en', pid, 5, 'Germany')
        assert result['game_over'] is True
        assert result['next_paragraph'] is None
        assert result['answer']['name'] == 'France'

    def test_win_on_last_guess(self, client):
        pid = client.get('/api/puzzle/en', params={'day': 1}).json()['puzzle_id']
        for n in range(1, 5):
            _guess(client, 'en', pid, n, 'Germany')
        result = _guess(client, 'en', pid, 5, 'France')
        assert result['correct'] is True
        assert result['game_over'] is True

    def test_guess_checked_against_its_own_day(self, client):
        # A guess for day 1's puzzle id is evaluated against day 1's country
        # even if "today" is a different day (midnight rollover safety)
        pid_day1 = client.get('/api/puzzle/en', params={'day': 1}).json()['puzzle_id']
        pid_day2 = client.get('/api/puzzle/en', params={'day': 2}).json()['puzzle_id']
        assert _guess(client, 'en', pid_day1, 1, 'France')['correct']
        assert _guess(client, 'en', pid_day2, 1, 'Spain')['correct']

    def test_accents_and_case_accepted(self, client):
        pid = client.get('/api/puzzle/es', params={'day': 2}).json()['puzzle_id']
        assert _guess(client, 'es', pid, 1, 'espana')['correct']

    def test_alias_accepted(self, client):
        pid = client.get('/api/puzzle/en', params={'day': 2}).json()['puzzle_id']
        assert _guess(client, 'en', pid, 1, 'Kingdom of Spain')['correct']

    def test_invalid_puzzle_id_rejected(self, client):
        res = client.post('/api/guess', json={
            'lang': 'en', 'puzzle_id': 'not-a-date',
            'guess_number': 1, 'guess_text': 'France',
        })
        assert res.status_code == 400


class TestCountriesEndpoint:
    def test_lists_countries_sorted(self, client):
        res = client.get('/api/countries/en')
        assert res.status_code == 200
        names = [c['name'] for c in res.json()]
        assert names == sorted(names)
        assert 'France' in names

    def test_localized_names(self, client):
        res = client.get('/api/countries/ca')
        names = [c['name'] for c in res.json()]
        assert 'França' in names
        assert 'Espanya' in names
