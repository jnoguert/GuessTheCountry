"""Tests for the censorship engine (pipeline/censor.py)."""
import random
import re
from pipeline.censor import (
    create_censor_regex, censor_paragraph, expand_demonym,
    collect_proper_nouns, censor_proper_nouns, censor_name_stems,
    fuzz_block_length, BLOCK_LENGTH_JITTER_RANGE,
)


def censor(terms, text):
    pattern = create_censor_regex(set(terms), 'en')
    return censor_paragraph(text, pattern)


class TestWordBoundaries:
    def test_niger_does_not_censor_inside_nigeria(self):
        result = censor(['Niger'], 'Nigeria and Niger are neighbours.')
        assert 'Nigeria' in result
        assert ' Niger ' not in result
        assert '█' in result  # block length is jittered, not necessarily 5

    def test_nigeria_does_not_censor_niger(self):
        result = censor(['Nigeria'], 'Nigeria and Niger are neighbours.')
        assert 'Niger are' in result
        assert 'Nigeria' not in result

    def test_possessive_form(self):
        result = censor(['France'], "France's economy is large.")
        assert 'France' not in result
        assert "'s economy" in result

    def test_catalan_elision(self):
        pattern = create_censor_regex({'Índia'}, 'ca')
        result = censor_paragraph("L'Índia és un país gran.", pattern)
        assert 'Índia' not in result
        assert "L'" in result


class TestLongestFirstOrdering:
    def test_multiword_term_censored_fully(self):
        # "United States of America" must not leave "of America" behind
        result = censor(['United States', 'United States of America'],
                        'The United States of America is large.')
        assert 'of America' not in result
        assert result.count('█') > 0

    def test_guinea_family(self):
        result = censor(['Guinea', 'Guinea-Bissau'],
                        'Guinea-Bissau borders Guinea.')
        # Both fully censored, nothing left over
        assert 'Guinea' not in result
        assert 'Bissau' not in result


class TestCensorShape:
    def test_per_word_blocks_preserved(self):
        result = censor(['United States'], 'The United States is big.')
        # Two words -> two blocks separated by a space
        assert '█' in result
        blocks = [t for t in result.split() if set(t) <= {'█'} or t.rstrip('.,') and set(t.rstrip('.,')) <= {'█'}]
        assert len(blocks) == 2

    def test_case_insensitive(self):
        result = censor(['France'], 'FRANCE, france and France.')
        assert 'france' not in result.lower()

    def test_no_terms_returns_text_unchanged(self):
        text = 'Nothing to censor here.'
        assert censor_paragraph(text, None) == text


class TestAccents:
    def test_accented_terms_censored(self):
        pattern = create_censor_regex({'España', 'Perú'}, 'es')
        result = censor_paragraph('España limita con Perú.', pattern)
        assert 'España' not in result
        assert 'Perú' not in result


def censor_all(paragraphs, lang='en'):
    known = collect_proper_nouns(paragraphs, lang)
    return [censor_proper_nouns(p, lang, known) for p in paragraphs]


class TestProperNounCensor:
    def test_region_names_censored(self):
        [result] = censor_all(['The region of Catalonia lies in the northeast.'])
        assert 'Catalonia' not in result
        assert 'region of' in result

    def test_historical_entities_censored(self):
        [result] = censor_all(['It was ruled by the count of Urgell for centuries.'])
        assert 'Urgell' not in result
        assert 'count of' in result

    def test_multiword_toponym(self):
        [result] = censor_all(['They crossed the Iberian Peninsula together.'])
        assert 'Iberian' not in result
        assert 'Peninsula' not in result

    def test_sentence_start_plain_words_survive(self):
        [result] = censor_all(['The kingdom grew. It became rich.'])
        assert 'The kingdom grew' in result
        assert 'It became rich' in result

    def test_sentence_start_known_proper_noun_censored(self):
        # "Catalonia" seen mid-sentence -> also censored at sentence start
        results = censor_all([
            'The area includes Catalonia and more.',
            'Catalonia is in the northeast.',
        ])
        assert all('Catalonia' not in r for r in results)

    def test_months_survive_in_english(self):
        [result] = censor_all(['The war ended in April after a long siege.'])
        assert 'April' in result

    def test_harmless_acronyms_survive(self):
        [result] = censor_all(['Its GDP per capita is high.'])
        assert 'GDP' in result

    def test_clueful_acronyms_censored(self):
        [result] = censor_all(['The country joined NATO and the EU together.'])
        assert 'NATO' not in result
        assert 'EU' not in result

    def test_people_names_censored(self):
        [result] = censor_all(['The dictatorship of Franco ended in 1975.'])
        assert 'Franco' not in result
        assert '1975' in result

    def test_spanish_toponyms(self):
        [result] = censor_all(
            ['El río Ebro pasa por Zaragoza y llega al Mediterráneo.'], lang='es')
        assert 'Ebro' not in result
        assert 'Zaragoza' not in result
        assert 'Mediterráneo' not in result
        assert 'río' in result

    def test_block_length_is_jittered_not_exact(self):
        # With the length obfuscation, the block for "Catalonia" (9 letters)
        # must NOT reveal the true 9-character width
        rng = random.Random(1)
        known = collect_proper_nouns(['They travelled to Catalonia quickly.'], 'en')
        result = censor_proper_nouns('They travelled to Catalonia quickly.', 'en', known, rng)
        block = re.search(r'█+', result).group(0)
        assert len(block) != len('Catalonia')


class TestBlockLengthJitter:
    """The displayed block length must never equal the true word length -
    otherwise the player can count letters and drastically narrow guesses."""

    def test_never_matches_true_length(self):
        rng = random.Random(0)
        for word_len in range(1, 20):
            for _ in range(20):
                assert fuzz_block_length(word_len, rng) != word_len

    def test_offset_is_within_declared_range(self):
        rng = random.Random(7)
        word_len = 10
        for _ in range(200):
            length = fuzz_block_length(word_len, rng)
            offset = abs(length - word_len)
            assert offset in BLOCK_LENGTH_JITTER_RANGE

    def test_never_goes_below_one_character(self):
        rng = random.Random(3)
        for _ in range(200):
            assert fuzz_block_length(1, rng) >= 1
            assert fuzz_block_length(2, rng) >= 1

    def test_both_directions_occur(self):
        # Over many draws, the block must sometimes be longer and
        # sometimes shorter than the real word - not a one-way tell
        rng = random.Random(9)
        word_len = 8
        deltas = [fuzz_block_length(word_len, rng) - word_len for _ in range(200)]
        assert any(d > 0 for d in deltas)
        assert any(d < 0 for d in deltas)

    def test_same_seed_is_reproducible(self):
        lengths_a = [fuzz_block_length(8, random.Random(42)) for _ in range(10)]
        lengths_b = [fuzz_block_length(8, random.Random(42)) for _ in range(10)]
        assert lengths_a == lengths_b

    def test_applied_in_term_pass(self):
        rng = random.Random(5)
        pattern = create_censor_regex({'France'}, 'en')
        result = censor_paragraph('France is large.', pattern, rng)
        block = re.search(r'█+', result).group(0)
        assert len(block) != len('France')

    def test_applied_in_name_stem_pass(self):
        rng = random.Random(6)
        result = censor_name_stems('el estado austríaco moderno', {'austri'}, rng)
        block = re.search(r'█+', result).group(0)
        assert len(block) != len('austríaco')


class TestParenthesizedVariants:
    def test_word_after_open_paren_is_censored(self):
        # '(Afghānistān, ...)' must not escape as "sentence-initial"
        [result] = censor_all(['The name comes from (Afghānistān, land of hills).'])
        assert 'Afghānistān' not in result

    def test_transliterated_variant_censored(self):
        [result] = censor_all(['It was called (Espāña) in old records.'])
        assert 'Espāña' not in result


class TestNameStems:
    def test_catalan_derived_adjective(self):
        result = censor_name_stems("l'estat australià és gran", {'austra'})
        assert 'australià' not in result

    def test_spanish_derived_adjective(self):
        result = censor_name_stems('el estado austríaco moderno', {'austri'})
        assert 'austríaco' not in result

    def test_accent_insensitive_stem_match(self):
        result = censor_name_stems('la cultura búlgara', {'bulga'})
        assert 'búlgara' not in result

    def test_unrelated_words_survive(self):
        text = 'the australopithecus fossils were found'
        # stem from "Austria" must not censor unrelated science words
        result = censor_name_stems(text, {'austri'})
        assert result == text

    def test_no_stems_returns_unchanged(self):
        text = 'nothing here'
        assert censor_name_stems(text, set()) == text

    def test_compound_words_censored(self):
        result = censor_name_stems('els afrobolivians i la revolta lusobrasilera',
                                   {'boliv', 'brasi'})
        assert 'afrobolivians' not in result
        assert 'lusobrasilera' not in result

    def test_short_name_derivatives_censored(self):
        result = censor_name_stems('el territorio chadiano antiguo', {'chad'})
        assert 'chadiano' not in result

    def test_transliteration_with_extended_latin(self):
        # 'muqāṭarah' contains the stem 'qata' once accents are stripped;
        # the ṭ must not split the token
        result = censor_name_stems('a transaction known as muqāṭarah in markets', {'qata'})
        assert 'muqāṭarah' not in result

    def test_hyphenated_name_derivatives(self):
        result = censor_name_stems('el territori sud-africà i els sud-africans', {'sud-afr'})
        assert 'sud-africà' not in result
        assert 'sud-africans' not in result


class TestDemonymExpansion:
    def test_spanish_gender_and_plural(self):
        forms = expand_demonym('español', 'es')
        assert 'español' in forms

    def test_english_plural(self):
        forms = expand_demonym('German', 'en')
        assert 'German' in forms
        assert 'Germans' in forms

    def test_expanded_forms_are_censored(self):
        terms = set()
        for f in expand_demonym('español', 'es'):
            terms.add(f)
        pattern = create_censor_regex(terms, 'es')
        result = censor_paragraph('El pueblo español habla.', pattern)
        assert 'español' not in result
