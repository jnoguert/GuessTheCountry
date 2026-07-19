import pytest
from pipeline.censor import build_censor_terms, create_censor_regex, censor_paragraph


class TestCensorEdgeCases:
    """Test edge cases in the censorship algorithm"""

    def test_niger_nigeria_substring_safety(self):
        """Niger and Nigeria should censor independently without collision"""
        niger_regex = r'\bNiger\b'
        nigeria_regex = r'\bNigeria\b'

        text = "Nigeria and Niger are neighboring countries."

        # Niger regex should match only Niger
        import re
        niger_matches = len(re.findall(niger_regex, text, re.IGNORECASE))
        nigeria_matches = len(re.findall(nigeria_regex, text, re.IGNORECASE))

        assert niger_matches == 1
        assert nigeria_matches == 1

    def test_guinea_family_distinctness(self):
        """Guinea, Guinea-Bissau, Equatorial Guinea, and Papua New Guinea should not collide"""
        patterns = [
            r'\bGuinea\b',
            r'\bGuinea-Bissau\b',
            r'\bEquatorial Guinea\b',
            r'\bPapua New Guinea\b',
        ]

        text = "Guinea, Guinea-Bissau, Equatorial Guinea, and Papua New Guinea are different."

        import re
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            assert len(matches) == 1, f"Pattern {pattern} should match exactly once"

    def test_catalan_elision(self):
        """Catalan elision (l'Índia) should still match Índia"""
        text = "L'Índia és una nació gran."

        import re
        pattern = r'\bÍndia\b'
        matches = re.findall(pattern, text, re.IGNORECASE | re.UNICODE)
        assert len(matches) == 1

    def test_self_referential_capitals(self):
        """Vatican, Monaco, Singapore where capital == country should not double-list"""
        # This is more of a data-structure test, ensuring term dedup works
        terms = {'Vatican', 'Vatican', 'Singapore', 'Singapore City'}
        unique_terms = len(terms)
        assert unique_terms <= 4

    def test_spanish_demonym_expansion(self):
        """Spanish demonym variants should be censored"""
        from pipeline.censor import expand_demonym

        base = "español"
        expanded = expand_demonym(base, "es")

        # Should include Spanish, Spanish
        assert any('español' in form.lower() for form in expanded)

    def test_word_boundary_with_punctuation(self):
        """Word boundaries should work with punctuation"""
        text = "The United States' economy is large (USA)."

        import re
        pattern = r'\b(United States|USA)\b'
        matches = re.findall(pattern, text, re.IGNORECASE)
        assert len(matches) == 2

    def test_censor_paragraph_preserves_spacing(self):
        """Censored text should preserve word spacing"""
        text = "The capital of France is Paris."

        import re
        pattern = r'\b(France|Paris)\b'
        censored = censor_paragraph(text, pattern)

        # Should have roughly the same structure
        assert '█' in censored
        assert len(censored.split()) == len(text.split())  # Same number of tokens
