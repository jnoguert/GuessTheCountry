"""Leaderboard API tests: submission validation, identity protection,
and today/all-time rankings."""
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

import app.leaderboard_db as db
from app.main import app


TODAY = datetime.now(timezone.utc).date().isoformat()


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Point the leaderboard at a throwaway database
    monkeypatch.setattr(db, 'DB_FILE', str(tmp_path / 'leaderboard.db'))
    return TestClient(app)


def submit(client, username='player1', token='secret-token-1', puzzle_id=TODAY,
           score=100, guesses=1, unlocks=0, won=True):
    return client.post('/api/scores', json={
        'username': username, 'token': token, 'puzzle_id': puzzle_id,
        'score': score, 'guesses': guesses, 'unlocks': unlocks, 'won': won,
    })


class TestSubmission:
    def test_valid_submission(self, client):
        assert submit(client).status_code == 201

    def test_score_must_match_rules(self, client):
        # 0 unlocks + win on 1st guess = 100, not 999
        res = submit(client, score=999)
        assert res.status_code == 400

    def test_score_with_hints_and_wrong_guesses(self, client):
        # 2 unlocks (50 base), won on 3rd guess (2 wrong = -20) -> 30
        res = submit(client, score=30, guesses=3, unlocks=2)
        assert res.status_code == 201

    def test_loss_scores_zero(self, client):
        assert submit(client, score=0, guesses=5, won=False).status_code == 201
        assert submit(client, username='p2', token='secret-token-2',
                      score=50, guesses=5, won=False).status_code == 400

    def test_only_today_accepted(self, client):
        res = submit(client, puzzle_id='2020-01-01')
        assert res.status_code == 400

    def test_invalid_username_rejected(self, client):
        assert submit(client, username='x').status_code == 400
        assert submit(client, username='bad name!').status_code == 400

    def test_duplicate_submission_rejected(self, client):
        assert submit(client).status_code == 201
        assert submit(client).status_code == 409

    def test_username_protected_by_token(self, client):
        assert submit(client, username='alice', token='alice-secret').status_code == 201
        # Someone else trying to post as alice with a different token
        res = submit(client, username='alice', token='mallory-secret')
        assert res.status_code == 409

    def test_username_case_insensitive_claim(self, client):
        assert submit(client, username='Alice', token='alice-secret').status_code == 201
        res = submit(client, username='alice', token='other-secret')
        assert res.status_code == 409


class TestRankings:
    def test_today_ranking_ordered_by_score(self, client):
        submit(client, username='gold', token='secret-token-g', score=100, guesses=1, unlocks=0)
        submit(client, username='silver', token='secret-token-s', score=70, guesses=1, unlocks=1)
        submit(client, username='bronze', token='secret-token-b', score=0, guesses=5, won=False)

        res = client.get('/api/leaderboard/today')
        assert res.status_code == 200
        names = [e['username'] for e in res.json()]
        assert names == ['gold', 'silver', 'bronze']

    def test_alltime_aggregates_scores(self, client):
        submit(client, username='ana', token='secret-token-a', score=100, guesses=1, unlocks=0)
        submit(client, username='bob', token='secret-token-o', score=30, guesses=3, unlocks=2)

        res = client.get('/api/leaderboard/alltime')
        assert res.status_code == 200
        top = res.json()[0]
        assert top['username'] == 'ana'
        assert top['total_score'] == 100
        assert top['wins'] == 1
        assert top['games'] == 1

    def test_empty_leaderboard(self, client):
        assert client.get('/api/leaderboard/today').json() == []
        assert client.get('/api/leaderboard/alltime').json() == []
