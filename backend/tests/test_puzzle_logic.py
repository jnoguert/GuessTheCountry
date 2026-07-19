"""Unit tests for daily puzzle selection and guess checking.

All tests use the in-memory fake_loader fixture (see conftest.py) and pass
explicit day indices, so they simulate arbitrary days deterministically.
"""
from app import puzzle


class TestNormalize:
    def test_case_insensitive(self):
        assert puzzle.normalize_text('SPAIN') == puzzle.normalize_text('spain')

    def test_accent_insensitive(self):
        assert puzzle.normalize_text('España') == puzzle.normalize_text('Espana')
        assert puzzle.normalize_text('França') == puzzle.normalize_text('Franca')

    def test_whitespace_trimmed(self):
        assert puzzle.normalize_text('  France  ') == 'france'


class TestDailySelection:
    def test_skips_country_without_content(self, fake_loader):
        # Day 0 lands on Q_BROKEN (no ca/es paragraphs) -> must skip to Q_FR
        country = puzzle.get_daily_country(day_index=0)
        assert country['qid'] == 'Q_FR'

    def test_different_days_give_different_countries(self, fake_loader):
        c1 = puzzle.get_daily_country(day_index=1)
        c2 = puzzle.get_daily_country(day_index=2)
        assert c1['qid'] == 'Q_FR'
        assert c2['qid'] == 'Q_ES'

    def test_same_day_is_deterministic(self, fake_loader):
        assert puzzle.get_daily_country(day_index=7)['qid'] == \
               puzzle.get_daily_country(day_index=7)['qid']

    def test_rotation_wraps_around(self, fake_loader):
        n = len(fake_loader.daily_order)
        assert puzzle.get_daily_country(day_index=2)['qid'] == \
               puzzle.get_daily_country(day_index=2 + n)['qid']

    def test_same_answer_across_languages(self, fake_loader):
        # Every language must get the same country on the same day
        qids = {
            puzzle.get_todays_puzzle(lang, day_index=0)['qid']
            for lang in ('en', 'ca', 'es')
        }
        assert len(qids) == 1

    def test_every_simulated_day_is_playable(self, fake_loader):
        # Simulate a year of days: there must always be a puzzle with
        # paragraphs in every language
        for day in range(365):
            for lang in ('en', 'ca', 'es'):
                p = puzzle.get_todays_puzzle(lang, day_index=day)
                assert p is not None, f'day {day} lang {lang} has no puzzle'
                assert p['paragraphs'], f'day {day} lang {lang} has no paragraphs'

    def test_puzzle_id_matches_day(self, fake_loader):
        p = puzzle.get_todays_puzzle('en', day_index=0)
        assert p['puzzle_id'] == '2026-01-01'
        p31 = puzzle.get_todays_puzzle('en', day_index=31)
        assert p31['puzzle_id'] == '2026-02-01'


class TestCheckGuess:
    def test_correct_name(self, fake_loader):
        # Day 1 -> Q_FR
        assert puzzle.check_guess('en', 'France', day_index=1)['correct']

    def test_correct_name_case_and_accents(self, fake_loader):
        assert puzzle.check_guess('ca', 'franca', day_index=1)['correct']
        assert puzzle.check_guess('es', 'FRANCIA', day_index=1)['correct']

    def test_alias_matches(self, fake_loader):
        assert puzzle.check_guess('en', 'French Republic', day_index=1)['correct']

    def test_wrong_guess(self, fake_loader):
        assert not puzzle.check_guess('en', 'Germany', day_index=1)['correct']

    def test_other_days_answer_does_not_match(self, fake_loader):
        # Spain is day 2's answer, not day 1's
        assert not puzzle.check_guess('en', 'Spain', day_index=1)['correct']
        assert puzzle.check_guess('en', 'Spain', day_index=2)['correct']
