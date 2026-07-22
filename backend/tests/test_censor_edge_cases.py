"""Tests for the censorship engine (pipeline/censor.py)."""
import random
import re
from pipeline.censor import (
    create_censor_regex, censor_paragraph, expand_demonym,
    collect_proper_nouns, censor_proper_nouns, censor_name_stems,
    fuzz_block_length, BLOCK_LENGTH_JITTER_RANGE,
    split_sentences, trim_lede, build_global_geo_terms,
    strip_phonetics, LEDE_MAX_CHARS, LEDE_MIN_CHARS,
)
from pipeline.geo_adjectives import GEO_ADJECTIVES


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

    def test_subtracting_more_than_word_length_is_safe(self):
        """Exhaustive (not sampled) check of every case where the negative
        offset would exceed the word's own length - e.g. a 1-letter word
        minus 3, or a 3-letter word minus 3 landing on exactly 0. Each
        combination is forced directly rather than hoping random sampling
        stumbles onto it."""

        class ForcedRng:
            """Stand-in for random.Random that forces a specific
            (magnitude, sign) pair instead of sampling one."""
            def __init__(self, magnitude, negative):
                self.magnitude, self.negative = magnitude, negative

            def randint(self, a, b):
                return self.magnitude

            def random(self):
                return 0.1 if self.negative else 0.9  # < 0.5 triggers "negative"

        for word_len in range(1, 8):  # covers every case magnitude >= word_len
            for magnitude in BLOCK_LENGTH_JITTER_RANGE:  # 2, 3
                rng = ForcedRng(magnitude, negative=True)
                result = fuzz_block_length(word_len, rng)
                assert result >= 1, (
                    f'word_len={word_len} magnitude={magnitude}: '
                    f'got non-positive length {result}'
                )
                assert result != word_len, (
                    f'word_len={word_len} magnitude={magnitude}: '
                    f'result {result} leaks the true length'
                )

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


class TestStripPhonetics:
    def test_removes_ipa_naming_parenthetical(self):
        text = "Islàndia (en islandès, Ísland; IPA: [ˈistlant]) és un estat insular."
        result = strip_phonetics(text)
        assert 'ˈistlant' not in result
        assert '[' not in result and ']' not in result
        assert result == 'Islàndia és un estat insular.'

    def test_keeps_factual_parentheticals_and_dates(self):
        text = 'Les illes són Grimsey (a 287 km) i altres. El 1969/70 va nevar.'
        result = strip_phonetics(text)
        assert '(a 287 km)' in result   # factual aside survives
        assert '1969/70' in result      # a single-slash date is not IPA

    def test_removes_slashed_ipa(self):
        result = strip_phonetics('Canadá (AFI: /ˈkænədə/) es un país.')
        assert 'kænədə' not in result
        assert '/' not in result
        assert result == 'Canadá es un país.'

    def test_removes_english_respelling_and_pronunciation_label(self):
        result = strip_phonetics(
            'Gabon ( gə-BON; French pronunciation: [ɡabɔ̃] ), officially a republic.')
        assert 'gə-BON' not in result
        assert 'pronunciation' not in result
        assert 'ɡabɔ̃' not in result

    def test_removes_native_script_gloss(self):
        result = strip_phonetics('Rússia (rus: Россия, [rɐˈsʲijə]) és un estat.')
        assert 'Россия' not in result
        assert result == 'Rússia és un estat.'

    def test_removes_audio_link_artifact(self):
        result = strip_phonetics('La Xina (en pinyin: Zhonghua pronunciació (?·pàg.)) és extensa.')
        assert '?·pàg' not in result
        assert 'pinyin' not in result

    def test_removes_bare_ipa_left_by_malformed_extract(self):
        # No brackets around the transcription, and an unclosed paren
        result = strip_phonetics('Romania (escrit en romanès, AFI romɨˈni.a és un estat.')
        assert 'romɨˈni' not in result
        assert result.count('(') == result.count(')')  # no dangling paren

    def test_collapses_nested_bracket_remnants(self):
        assert strip_phonetics('given to [[Margrave]] in 976.') == 'given to in 976.'


class TestSentenceSplitting:
    def test_does_not_split_on_thousands_separator(self):
        # "103.000" must stay in one piece - the dot is followed by a digit
        sents = split_sentences('Té una superfície de 103.000 km². És gran.')
        assert sents == ['Té una superfície de 103.000 km².', 'És gran.']

    def test_does_not_split_before_lowercase(self):
        # A dot before a lowercase word (e.g. "s. xix") is not a boundary
        sents = split_sentences('Va passar al s. xix a la regió.')
        assert sents == ['Va passar al s. xix a la regió.']

    def test_strips_zero_width_chars_blocking_a_boundary(self):
        # Citation artifacts glue a zero-width space right after the period;
        # without stripping it the two sentences would fuse into one.
        text = 'És un país.​ El clima és fred.'
        assert split_sentences(text) == ['És un país.', 'El clima és fred.']


class TestTrimLede:
    # Many full sentences, ~1200 chars total - longer than LEDE_MAX_CHARS so
    # the default trim genuinely has to drop the tail.
    LEDE = (
        "Islàndia és un estat insular situat al nord de l'oceà. "
        'El 2021 tenia una població estimada de 376.000 habitants. '
        'La capital i ciutat més gran concentra dos terços de la població. '
        'És un territori volcànicament i geològicament molt actiu. '
        "Té nombroses glaceres, rius i deserts a l'interior del país. "
        'El clima és temperat malgrat la seva alta latitud septentrional. '
        "La seva economia depèn de la pesca i de l'energia geotèrmica. "
        'Els primers pobladors van arribar fa més de mil anys. '
        'Durant segles va formar part de dues monarquies veïnes. '
        'Avui és una república amb un alt nivell de desenvolupament humà. '
        'El paisatge combina fiords, altiplans i grans camps de lava. '
        'El turisme ha esdevingut un pilar econòmic les darreres dècades. '
        'La xarxa de carreteres principals envolta tota la línia de costa. '
        "L'interior, en canvi, només és accessible amb vehicles preparats. "
        'La densitat de població és de les més baixes del continent. '
        "Bona part de l'electricitat prové de fonts renovables. "
        'Les seves aigües són riques en peix i altres recursos marins. '
        'El país manté una llarga tradició literària i cultural. '
        'Les nits amb sol de mitjanit atrauen molts visitants a l\'estiu.'
    )

    def test_keeps_whole_sentences_within_budget(self):
        clue = trim_lede(self.LEDE, max_chars=70, min_chars=0)
        # No sentence is cut mid-way: the clue ends on a full stop
        assert clue.endswith('.')
        assert len(clue) <= 70
        assert clue.startswith("Islàndia és un estat insular situat al nord de l'oceà.")

    def test_first_sentence_always_kept_even_if_over_budget(self):
        long_first = 'A' * 400 + '. Second one here.'
        clue = trim_lede(long_first, max_chars=100, min_chars=0)
        assert clue == 'A' * 400 + '.'

    def test_min_chars_floor_pulls_in_more_sentences(self):
        # A short opening sentence must not yield a tiny clue: with a small
        # budget the floor is what forces the second sentence to be included.
        text = 'Malàisia és un país. Es compon de tretze estats i tres territoris.'
        short_only = trim_lede(text, max_chars=25, min_chars=0)
        floored = trim_lede(text, max_chars=25, min_chars=40)
        assert short_only == 'Malàisia és un país.'
        assert len(floored) > len(short_only)

    def test_real_lede_is_shortened(self):
        clue = trim_lede(self.LEDE)
        assert len(clue) < len(self.LEDE)
        assert clue.endswith('.')
        assert LEDE_MIN_CHARS <= len(clue) <= LEDE_MAX_CHARS + 200


class TestGeoAdjectives:
    def test_curated_catalan_adjectives_censored(self):
        terms = build_global_geo_terms('ca', {}, {})
        pattern = create_censor_regex(terms, 'ca')
        text = 'un estat insular europeu, el capità noruec i la monarquia danesa'
        result = censor_paragraph(text, pattern)
        for leak in ('europeu', 'noruec', 'danesa'):
            assert leak not in result

    def test_curated_spanish_adjectives_censored(self):
        terms = build_global_geo_terms('es', {}, {})
        pattern = create_censor_regex(terms, 'es')
        result = censor_paragraph('el imperialismo británico y los portugueses', pattern)
        assert 'británico' not in result
        assert 'portugueses' not in result

    def test_english_has_no_curated_list(self):
        # English demonyms are capitalized -> covered by the proper-noun pass
        assert GEO_ADJECTIVES['en'] == []

    def test_includes_every_country_demonym_not_just_borders(self):
        # A far-away (non-bordering) country's demonym still gets pulled in
        core = {'Q99': {}}
        lexical = {'Q99': {'demonyms': {'ca': ['japonès']}}}
        terms = build_global_geo_terms('ca', core, lexical)
        assert 'japonès' in terms

    def test_common_geo_words_survive(self):
        # Words we deliberately dropped from the list must NOT be censored
        terms = build_global_geo_terms('ca', {}, {})
        pattern = create_censor_regex(terms, 'ca')
        result = censor_paragraph('un clima oceànic i un alfabet llatí', pattern)
        assert 'oceànic' in result
        assert 'llatí' in result


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
