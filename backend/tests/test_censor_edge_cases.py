"""Tests for the censorship engine (pipeline/censor.py)."""
from pipeline.censor import (
    create_censor_regex, censor_paragraph, expand_demonym,
    collect_proper_nouns, censor_proper_nouns,
)


def censor(terms, text):
    pattern = create_censor_regex(set(terms), 'en')
    return censor_paragraph(text, pattern)


class TestWordBoundaries:
    def test_niger_does_not_censor_inside_nigeria(self):
        result = censor(['Niger'], 'Nigeria and Niger are neighbours.')
        assert 'Nigeria' in result
        assert ' Niger ' not in result
        assert '█████' in result

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

    def test_block_length_matches_word(self):
        [result] = censor_all(['They travelled to Catalonia quickly.'])
        assert '█' * len('Catalonia') in result


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
