"""Tests for openalexcli CLI.

Covers:
- ID normalization for different entity types
- Parameter building (especially group_by edge cases)
- BibTeX formatting
- Abstract reconstruction from inverted index
"""

import pytest
from unittest.mock import Mock, patch

from openalexcli.api.client import OpenAlexAPI, DEFAULT_WORK_FIELDS
from openalexcli.formatters.bibtex import (
    format_bibtex,
    _generate_citation_key,
    _reconstruct_abstract,
    _escape_latex,
)
from openalexcli.formatters.json_fmt import format_json


# =============================================================================
# ID Normalization Tests
# =============================================================================

class TestWorkIdNormalization:
    """Test work ID normalization for various formats."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_openalex_id_unchanged(self):
        # OpenAlex IDs should pass through unchanged
        assert self.api._normalize_work_id("W2741809807") == "W2741809807"

    def test_openalex_url_stripped(self):
        # Full URLs should be stripped to just the ID
        assert self.api._normalize_work_id("https://openalex.org/W123") == "W123"

    def test_doi_with_prefix(self):
        # DOIs with doi: prefix
        assert self.api._normalize_work_id("doi:10.1234/test") == "doi:10.1234/test"

    def test_doi_bare(self):
        # Bare DOIs (starting with 10.) get prefix added
        assert self.api._normalize_work_id("10.1234/test") == "doi:10.1234/test"

    def test_pmid_normalized(self):
        # PubMed IDs should be lowercased
        assert self.api._normalize_work_id("PMID:12345") == "pmid:12345"


class TestAuthorIdNormalization:
    """Test author ID normalization."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_orcid_from_url(self):
        # ORCID URLs should be converted to orcid: format
        result = self.api._normalize_author_id("https://orcid.org/0000-0002-1825-0097")
        assert result == "orcid:0000-0002-1825-0097"

    def test_orcid_bare(self):
        # Bare ORCIDs (starting with 0000-) get prefix
        result = self.api._normalize_author_id("0000-0002-1825-0097")
        assert result == "orcid:0000-0002-1825-0097"


class TestInstitutionIdNormalization:
    """Test institution ID normalization."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_ror_from_url(self):
        # ROR URLs should be converted to ror: format
        result = self.api._normalize_institution_id("https://ror.org/03vek6s52")
        assert result == "ror:03vek6s52"


# =============================================================================
# Parameter Building Tests
# =============================================================================

class TestBuildParams:
    """Test _build_params handles group_by constraints correctly.

    OpenAlex API constraints:
    - group_by cannot be used with select
    - group_by only allows sort by 'key' or 'count'
    """

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_normal_search_includes_select(self):
        # Without group_by, select should be included
        params = self.api._build_params(
            search="test",
            select=["id", "title"],
            sort="cited_by_count:desc"
        )
        assert "select" in params
        assert params["select"] == "id,title"

    def test_group_by_excludes_select(self):
        # With group_by, select must be excluded (API constraint)
        params = self.api._build_params(
            search="test",
            select=["id", "title"],
            group_by="publication_year"
        )
        assert "select" not in params
        assert params["group_by"] == "publication_year"

    def test_group_by_overrides_invalid_sort(self):
        # group_by only allows sort by 'key' or 'count'
        params = self.api._build_params(
            group_by="type",
            sort="cited_by_count:desc"  # Invalid for group_by
        )
        # Should be replaced with valid sort
        assert params["sort"] == "count:desc"

    def test_group_by_preserves_valid_sort(self):
        # Valid sorts should be preserved
        params = self.api._build_params(
            group_by="type",
            sort="count:asc"
        )
        assert params["sort"] == "count:asc"


# =============================================================================
# BibTeX Formatting Tests
# =============================================================================

class TestBibTexFormatting:
    """Test BibTeX output generation."""

    def test_citation_key_generation(self):
        # Citation key format: lastname_year_firstword
        work = {
            "authorships": [{"author": {"display_name": "John Smith"}}],
            "publication_year": 2023,
            "title": "Attention Is All You Need"
        }
        key = _generate_citation_key(work)
        assert key == "smith2023attention"

    def test_citation_key_no_author(self):
        # Handle missing author gracefully
        work = {"authorships": [], "publication_year": 2023, "title": "Test"}
        key = _generate_citation_key(work)
        assert key == "unknown2023test"

    def test_latex_escaping(self):
        # Special LaTeX characters must be escaped
        assert _escape_latex("10% & $5") == r"10\% \& \$5"
        assert _escape_latex("test_name") == r"test\_name"

    def test_abstract_reconstruction(self):
        # OpenAlex stores abstracts as inverted index: {word: [positions]}
        inverted_index = {
            "Hello": [0],
            "world": [1],
            "test": [2]
        }
        abstract = _reconstruct_abstract(inverted_index)
        assert abstract == "Hello world test"

    def test_abstract_reconstruction_empty(self):
        assert _reconstruct_abstract(None) == ""
        assert _reconstruct_abstract({}) == ""

    def test_full_bibtex_output(self):
        # Test complete BibTeX entry generation
        work = {
            "title": "Test Paper",
            "authorships": [
                {"author": {"display_name": "Alice Smith"}},
                {"author": {"display_name": "Bob Jones"}}
            ],
            "publication_year": 2023,
            "type": "journal-article",
            "doi": "https://doi.org/10.1234/test",
            "id": "https://openalex.org/W123",
            "primary_location": {
                "source": {"display_name": "Nature"}
            },
            "biblio": {"volume": "42", "first_page": "1", "last_page": "10"}
        }
        bibtex = format_bibtex(work)

        # Verify key components
        assert "@article{" in bibtex
        assert "title = {Test Paper}" in bibtex
        assert "Alice Smith and Bob Jones" in bibtex
        assert "year = 2023" in bibtex
        assert "journal = {Nature}" in bibtex
        assert "doi = 10.1234/test" in bibtex
        assert "pages = 1--10" in bibtex


# =============================================================================
# JSON Formatting Tests
# =============================================================================

class TestJsonFormatting:
    """Test JSON output wrapper."""

    def test_single_result_wrapped(self):
        # Single item should be under 'result' key
        import json
        output = format_json({"id": "W123"}, pretty=False)
        parsed = json.loads(output)
        assert "result" in parsed
        assert parsed["result"]["id"] == "W123"

    def test_list_results_wrapped(self):
        # List should be under 'results' key with count
        import json
        output = format_json([{"id": "W1"}, {"id": "W2"}], pretty=False)
        parsed = json.loads(output)
        assert "results" in parsed
        assert parsed["count"] == 2

    def test_meta_included(self):
        # Meta should be passed through
        import json
        output = format_json([], meta={"page": 1, "per_page": 25}, pretty=False)
        parsed = json.loads(output)
        assert parsed["meta"]["page"] == 1


# =============================================================================
# Integration Tests (with mocked HTTP)
# =============================================================================

class TestAPIIntegration:
    """Integration tests with mocked HTTP responses."""

    def test_search_works_builds_correct_url(self):
        """Verify search_works constructs proper API call."""
        api = OpenAlexAPI(email="test@example.com")

        # Mock the HTTP client
        with patch.object(api, '_request') as mock_request:
            mock_request.return_value = {"results": [], "meta": {"count": 0}}

            api.search_works(
                query="machine learning",
                from_date="2023-01-01",
                min_citations=100,
                open_access=True
            )

            # Verify _request was called with correct params
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            params = call_args[1]["params"] if call_args[1] else call_args[0][2]

            assert params["search"] == "machine learning"
            assert "from_publication_date:2023-01-01" in params["filter"]
            assert "cited_by_count:>100" in params["filter"]
            assert "is_oa:true" in params["filter"]

    def test_group_by_search(self):
        """Verify group_by properly excludes select param."""
        api = OpenAlexAPI()

        with patch.object(api, '_request') as mock_request:
            mock_request.return_value = {"group_by": [], "meta": {"count": 0}}

            api.search_works(query="test", group_by="publication_year")

            call_args = mock_request.call_args
            params = call_args[1]["params"] if call_args[1] else call_args[0][2]

            # select should NOT be present with group_by
            assert "select" not in params
            assert params["group_by"] == "publication_year"
            assert params["sort"] == "count:desc"  # Default for group_by
