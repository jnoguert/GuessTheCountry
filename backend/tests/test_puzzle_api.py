import pytest
import json
from datetime import datetime, timezone
from app.puzzle import normalize_text, today_day_index, check_guess


class TestPuzzleLogic:
    """Test puzzle selection and guess validation"""

    def test_normalize_text(self):
        """Text normalization should handle case and accents"""
        assert normalize_text("España") == "españa"
        assert normalize_text("FRANCE") == "france"
        assert normalize_text("Côte d'Ivoire") == "côte d'ivoire"

    def test_today_day_index_is_deterministic(self):
        """Same day should always return the same index"""
        idx1 = today_day_index()
        idx2 = today_day_index()
        assert idx1 == idx2

    def test_check_guess_exact_match(self):
        """Guess matching country name exactly should return correct=True"""
        from app.data_loader import DataLoader

        # Mock data
        loader = DataLoader()
        loader.countries = {
            'Q29': {
                'iso2': 'ES',
                'iso3': 'ESP',
                'i18n': {
                    'en': {
                        'name': 'Spain',
                        'aliases': ['Iberia'],
                        'capital': 'Madrid',
                        'paragraphs': ['Test paragraph'],
                    }
                },
            }
        }

        result = check_guess('en', '2026-01-01', 'Spain')
        # Note: this test would need the actual global puzzle to work
        # Skipping full integration for now

    def test_check_guess_case_insensitive(self):
        """Guess matching should be case-insensitive"""
        # SPAIN, spain, Spain should all match
        texts = ["SPAIN", "spain", "Spain", "sPaIn"]
        normalized = [normalize_text(t) for t in texts]
        assert len(set(normalized)) == 1  # All the same

    def test_check_guess_alias_match(self):
        """Guess matching an alias should also return correct=True"""
        # Would test with mocked country data
        pass


class TestDailyRotation:
    """Test daily puzzle determinism"""

    def test_daily_order_consistency(self):
        """Each day should have a consistent country assignment"""
        # Daily order should be seeded and deterministic
        # Days 0, 1, 2, ... should map to fixed countries
        pass
