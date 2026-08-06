"""Tests for BibTeX formatting."""

from openalexcli.formatters.bibtex import (
    _escape_latex,
    _generate_citation_key,
    _get_entry_type,
    _normalize_to_ascii,
    _reconstruct_abstract,
    format_bibtex,
    format_works_bibtex,
)


class TestNormalizeToAscii:
    def test_ascii_unchanged(self):
        assert _normalize_to_ascii("hello world") == "hello world"

    def test_unicode_normalized(self):
        assert _normalize_to_ascii("café") == "cafe"
        assert _normalize_to_ascii("naïve") == "naive"

    def test_accented_names(self):
        assert _normalize_to_ascii("José García") == "Jose Garcia"


class TestEscapeLatex:
    def test_ampersand(self):
        assert _escape_latex("Smith & Jones") == r"Smith \& Jones"

    def test_percent_and_dollar(self):
        assert _escape_latex("10% & $5") == r"10\% \& \$5"

    def test_underscore(self):
        assert _escape_latex("test_name") == r"test\_name"

    def test_hash(self):
        assert _escape_latex("#1") == r"\#1"

    def test_braces(self):
        assert _escape_latex("{test}") == r"\{test\}"

    def test_tilde_and_caret(self):
        assert _escape_latex("~x^2") == r"\textasciitilde{}x\textasciicircum{}2"

    def test_empty_string(self):
        assert _escape_latex("") == ""


class TestGenerateCitationKey:
    def test_standard_work(self):
        work = {
            "authorships": [{"author": {"display_name": "John Smith"}}],
            "publication_year": 2023,
            "title": "Attention Is All You Need",
        }
        assert _generate_citation_key(work) == "smith2023attention"

    def test_skips_stopwords(self):
        work = {
            "authorships": [{"author": {"display_name": "John Doe"}}],
            "publication_year": 2020,
            "title": "The Art of Programming",
        }
        assert _generate_citation_key(work) == "doe2020art"

    def test_no_author(self):
        work = {"authorships": [], "publication_year": 2023, "title": "Test"}
        assert _generate_citation_key(work) == "unknown2023test"

    def test_no_year(self):
        work = {
            "authorships": [{"author": {"display_name": "Jane Smith"}}],
            "title": "Timeless Work",
        }
        assert _generate_citation_key(work) == "smithndtimeless"

    def test_no_title(self):
        work = {
            "authorships": [{"author": {"display_name": "Jane Smith"}}],
            "publication_year": 2020,
        }
        assert _generate_citation_key(work) == "smith2020untitled"

    def test_unicode_author(self):
        work = {
            "authorships": [{"author": {"display_name": "José García"}}],
            "publication_year": 2020,
            "title": "Test Paper",
        }
        assert _generate_citation_key(work) == "garcia2020test"

    def test_multi_word_last_name(self):
        work = {
            "authorships": [{"author": {"display_name": "Vincent van Gogh"}}],
            "publication_year": 1888,
            "title": "Sunflowers",
        }
        assert _generate_citation_key(work) == "gogh1888sunflowers"

    def test_empty_work(self):
        assert _generate_citation_key({}) == "unknownnduntitled"


class TestReconstructAbstract:
    def test_basic_reconstruction(self):
        inverted_index = {"Hello": [0], "world": [1], "test": [2]}
        assert _reconstruct_abstract(inverted_index) == "Hello world test"

    def test_repeated_words(self):
        inverted_index = {"the": [0, 2], "cat": [1], "hat": [3]}
        assert _reconstruct_abstract(inverted_index) == "the cat the hat"

    def test_empty_input(self):
        assert _reconstruct_abstract(None) == ""
        assert _reconstruct_abstract({}) == ""

    def test_truncated_at_1000_chars(self):
        inverted_index = {"word": list(range(400))}
        abstract = _reconstruct_abstract(inverted_index)
        assert len(abstract) == 1000
        assert abstract.endswith("...")


class TestGetEntryType:
    def test_journal_article(self):
        assert _get_entry_type({"type": "journal-article"}) == "article"
        assert _get_entry_type({"type": "article"}) == "article"

    def test_proceedings_article(self):
        assert _get_entry_type({"type": "proceedings-article"}) == "inproceedings"

    def test_book_types(self):
        assert _get_entry_type({"type": "book"}) == "book"
        assert _get_entry_type({"type": "book-chapter"}) == "incollection"

    def test_dissertation(self):
        assert _get_entry_type({"type": "dissertation"}) == "phdthesis"

    def test_preprint(self):
        assert _get_entry_type({"type": "preprint"}) == "unpublished"

    def test_report(self):
        assert _get_entry_type({"type": "report"}) == "techreport"

    def test_unknown_defaults_to_misc(self):
        assert _get_entry_type({"type": "peer-review"}) == "misc"
        assert _get_entry_type({}) == "misc"


class TestFormatBibtex:
    def test_full_article(self):
        work = {
            "title": "Test Paper",
            "authorships": [
                {"author": {"display_name": "Alice Smith"}},
                {"author": {"display_name": "Bob Jones"}},
            ],
            "publication_year": 2023,
            "type": "journal-article",
            "doi": "https://doi.org/10.1234/test",
            "id": "https://openalex.org/W123",
            "primary_location": {"source": {"display_name": "Nature"}},
            "biblio": {"volume": "42", "first_page": "1", "last_page": "10"},
        }
        bibtex = format_bibtex(work)

        assert "@article{smith2023test," in bibtex
        assert "title = {Test Paper}" in bibtex
        assert "author = {Alice Smith and Bob Jones}" in bibtex
        assert "year = 2023" in bibtex
        assert "journal = {Nature}" in bibtex
        assert "volume = 42" in bibtex
        assert "pages = 1--10" in bibtex
        assert "doi = 10.1234/test" in bibtex
        assert "url = https://openalex.org/W123" in bibtex

    def test_conference_paper_uses_booktitle(self):
        work = {
            "title": "Deep Learning Advances",
            "authorships": [{"author": {"display_name": "Jane Smith"}}],
            "publication_year": 2022,
            "type": "proceedings-article",
            "primary_location": {"source": {"display_name": "NeurIPS"}},
        }
        bibtex = format_bibtex(work)
        assert "@inproceedings{" in bibtex
        assert "booktitle = {NeurIPS}" in bibtex

    def test_other_type_uses_publisher(self):
        work = {
            "title": "A Book",
            "type": "book",
            "primary_location": {"source": {"display_name": "Springer"}},
        }
        bibtex = format_bibtex(work)
        assert "@book{" in bibtex
        assert "publisher = {Springer}" in bibtex

    def test_minimal_work(self):
        bibtex = format_bibtex({})
        assert bibtex.startswith("@misc{unknownnduntitled,")
        assert bibtex.endswith("}")

    def test_primary_location_none(self):
        work = {"title": "Orphan", "primary_location": None, "biblio": None}
        bibtex = format_bibtex(work)
        assert "title = {Orphan}" in bibtex
        assert "journal" not in bibtex

    def test_first_page_only(self):
        work = {"title": "T", "biblio": {"first_page": "e4375"}}
        bibtex = format_bibtex(work)
        assert "pages = e4375" in bibtex
        assert "--" not in bibtex

    def test_issue_maps_to_number(self):
        work = {"title": "T", "biblio": {"issue": "3"}}
        assert "number = 3" in format_bibtex(work)

    def test_escapes_special_chars_in_title(self):
        work = {"title": "100% Accuracy & More"}
        assert r"100\% Accuracy \& More" in format_bibtex(work)

    def test_abstract_included(self):
        work = {
            "title": "T",
            "abstract_inverted_index": {"Short": [0], "abstract": [1]},
        }
        assert "abstract = {Short abstract}" in format_bibtex(work)

    def test_no_trailing_comma_on_last_field(self):
        work = {"title": "Only Title"}
        lines = format_bibtex(work).splitlines()
        assert not lines[-2].endswith(",")


class TestFormatWorksBibtex:
    def test_multiple_works(self):
        works = [
            {"title": "First", "publication_year": 2020},
            {"title": "Second", "publication_year": 2021},
        ]
        output = format_works_bibtex(works)
        assert "@misc{unknown2020first," in output
        assert "@misc{unknown2021second," in output
        assert output.count("@misc") == 2
        assert "\n\n" in output

    def test_empty_list(self):
        assert format_works_bibtex([]) == ""
