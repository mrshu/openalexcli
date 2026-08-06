"""Tests for the OpenAlex API client."""

import httpx
import pytest

from openalexcli.api.client import APIError, OpenAlexAPI, RateLimitError

WORKS_PAGE = {
    "meta": {"count": 1, "db_response_time_ms": 12, "page": 1, "per_page": 25},
    "results": [
        {
            "id": "https://openalex.org/W2741809807",
            "doi": "https://doi.org/10.7717/peerj.4375",
            "title": "The state of OA",
            "publication_year": 2018,
            "cited_by_count": 1241,
        }
    ],
}


class TestAPIErrorToDict:
    def test_basic_error(self):
        error = APIError(message="Test error")
        d = error.to_dict()
        assert d["error"] == "Test error"
        assert d["documentation"] == "https://docs.openalex.org/"
        assert "status_code" not in d
        assert "suggestion" not in d

    def test_with_status_code(self):
        error = APIError(message="Not found", status_code=404)
        assert error.to_dict()["status_code"] == 404

    def test_with_suggestion(self):
        error = APIError(message="Error", suggestion="Try this")
        assert error.to_dict()["suggestion"] == "Try this"

    def test_rate_limit_error(self):
        error = RateLimitError(retry_after=30)
        assert error.status_code == 429
        assert error.retry_after == 30
        assert "Rate limit" in error.message


class TestWorkIdNormalization:
    """Test work ID normalization for various formats."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_openalex_id_unchanged(self):
        assert self.api._normalize_work_id("W2741809807") == "W2741809807"

    def test_openalex_url_stripped(self):
        assert self.api._normalize_work_id("https://openalex.org/W123") == "W123"

    def test_doi_with_prefix(self):
        assert self.api._normalize_work_id("doi:10.1234/test") == "doi:10.1234/test"

    def test_doi_bare(self):
        assert self.api._normalize_work_id("10.1234/test") == "doi:10.1234/test"

    def test_pmid_normalized(self):
        assert self.api._normalize_work_id("PMID:12345") == "pmid:12345"

    def test_mag_normalized(self):
        assert self.api._normalize_work_id("MAG:2741809807") == "mag:2741809807"


class TestAuthorIdNormalization:
    """Test author ID normalization."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_openalex_id_unchanged(self):
        assert self.api._normalize_author_id("A5048491430") == "A5048491430"

    def test_orcid_from_url(self):
        result = self.api._normalize_author_id("https://orcid.org/0000-0002-1825-0097")
        assert result == "orcid:0000-0002-1825-0097"

    def test_orcid_bare(self):
        result = self.api._normalize_author_id("0000-0002-1825-0097")
        assert result == "orcid:0000-0002-1825-0097"


class TestInstitutionIdNormalization:
    """Test institution ID normalization."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_openalex_id_unchanged(self):
        assert self.api._normalize_institution_id("I27837315") == "I27837315"

    def test_ror_from_url(self):
        result = self.api._normalize_institution_id("https://ror.org/03vek6s52")
        assert result == "ror:03vek6s52"

    def test_ror_with_prefix(self):
        assert self.api._normalize_institution_id("ror:03vek6s52") == "ror:03vek6s52"


class TestSourceIdNormalization:
    """Test source ID normalization."""

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_openalex_id_unchanged(self):
        assert self.api._normalize_source_id("S137773608") == "S137773608"

    def test_bare_issn(self):
        assert self.api._normalize_source_id("2167-8359") == "issn:2167-8359"

    def test_issn_with_prefix(self):
        assert self.api._normalize_source_id("ISSN:2167-8359") == "issn:2167-8359"


class TestBuildParams:
    """Test _build_params handles group_by constraints correctly.

    OpenAlex API constraints:
    - group_by cannot be used with select
    - group_by only allows sort by 'key' or 'count'
    """

    def setup_method(self):
        self.api = OpenAlexAPI()

    def test_normal_search_includes_select(self):
        params = self.api._build_params(
            search="test", select=["id", "title"], sort="cited_by_count:desc"
        )
        assert params["select"] == "id,title"
        assert params["sort"] == "cited_by_count:desc"

    def test_group_by_excludes_select(self):
        params = self.api._build_params(
            search="test", select=["id", "title"], group_by="publication_year"
        )
        assert "select" not in params
        assert params["group_by"] == "publication_year"

    def test_group_by_overrides_invalid_sort(self):
        params = self.api._build_params(group_by="type", sort="cited_by_count:desc")
        assert params["sort"] == "count:desc"

    def test_group_by_preserves_valid_sort(self):
        params = self.api._build_params(group_by="type", sort="count:asc")
        assert params["sort"] == "count:asc"

    def test_filters_combined(self):
        params = self.api._build_params(
            filter_str="is_oa:true",
            extra_filters={"from_publication_date": "2020-01-01", "type": None},
        )
        assert params["filter"] == "is_oa:true,from_publication_date:2020-01-01"

    def test_email_added_as_mailto(self):
        api = OpenAlexAPI(email="polite@example.com")
        params = api._build_params(search="test")
        assert params["mailto"] == "polite@example.com"


class TestSearchWorks:
    def test_basic_search(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        with OpenAlexAPI() as api:
            result = api.search_works(query="open access")

        assert result["meta"]["count"] == 1
        assert result["results"][0]["id"] == "https://openalex.org/W2741809807"

        request = httpx_mock.get_request()
        assert request.url.path == "/works"
        assert request.url.params["search"] == "open access"
        assert request.url.params["sort"] == "cited_by_count:desc"
        assert request.url.params["page"] == "1"
        assert request.url.params["per_page"] == "25"
        assert "id" in request.url.params["select"]

    def test_search_with_filters(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.search_works(
                query="machine learning",
                from_date="2023-01-01",
                to_date="2023-12-31",
                min_citations=100,
                open_access=True,
                work_type="article",
            )

        filter_param = httpx_mock.get_request().url.params["filter"]
        assert "from_publication_date:2023-01-01" in filter_param
        assert "to_publication_date:2023-12-31" in filter_param
        assert "cited_by_count:>100" in filter_param
        assert "is_oa:true" in filter_param
        assert "type:article" in filter_param

    def test_group_by_excludes_select(self, httpx_mock):
        httpx_mock.add_response(
            json={"meta": {"count": 10, "groups_count": 2}, "group_by": []}
        )

        with OpenAlexAPI() as api:
            api.search_works(query="test", group_by="publication_year")

        params = httpx_mock.get_request().url.params
        assert params["group_by"] == "publication_year"
        assert params["sort"] == "count:desc"
        assert "select" not in params

    def test_email_in_params_and_headers(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI(email="polite@example.com") as api:
            api.search_works(query="test")

        request = httpx_mock.get_request()
        assert request.url.params["mailto"] == "polite@example.com"
        assert request.headers["mailto"] == "polite@example.com"

    def test_pagination_params(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.search_works(query="test", page=3, per_page=50)

        params = httpx_mock.get_request().url.params
        assert params["page"] == "3"
        assert params["per_page"] == "50"


class TestGetWork:
    def test_get_by_openalex_id(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE["results"][0])

        with OpenAlexAPI() as api:
            result = api.get_work("W2741809807")

        assert result["id"] == "https://openalex.org/W2741809807"
        request = httpx_mock.get_request()
        assert request.url.path == "/works/W2741809807"
        assert "title" in request.url.params["select"]

    def test_get_by_doi(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE["results"][0])

        with OpenAlexAPI() as api:
            api.get_work("10.7717/peerj.4375")

        assert httpx_mock.get_request().url.path == "/works/doi:10.7717/peerj.4375"


class TestCitationsAndReferences:
    def test_citations_filter(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.get_citations("W123")

        params = httpx_mock.get_request().url.params
        assert params["filter"] == "cites:W123"

    def test_citations_resolves_doi_first(self, httpx_mock):
        httpx_mock.add_response(json={"id": "https://openalex.org/W123"})
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.get_citations("10.7717/peerj.4375")

        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert requests[0].url.path == "/works/doi:10.7717/peerj.4375"
        assert requests[1].url.params["filter"] == "cites:W123"

    def test_references_filter(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.get_references("W123")

        params = httpx_mock.get_request().url.params
        assert params["filter"] == "cited_by:W123"


class TestAuthorEndpoints:
    def test_get_author(self, httpx_mock):
        httpx_mock.add_response(
            json={"id": "https://openalex.org/A5048491430", "display_name": "Heather Piwowar"}
        )

        with OpenAlexAPI() as api:
            result = api.get_author("A5048491430")

        assert result["display_name"] == "Heather Piwowar"
        assert httpx_mock.get_request().url.path == "/authors/A5048491430"

    def test_get_author_by_orcid(self, httpx_mock):
        httpx_mock.add_response(json={"id": "https://openalex.org/A1"})

        with OpenAlexAPI() as api:
            api.get_author("0000-0002-1825-0097")

        assert httpx_mock.get_request().url.path == "/authors/orcid:0000-0002-1825-0097"

    def test_search_authors(self, httpx_mock):
        httpx_mock.add_response(
            json={"meta": {"count": 1}, "results": [{"display_name": "Heather Piwowar"}]}
        )

        with OpenAlexAPI() as api:
            result = api.search_authors("Piwowar")

        assert result["results"][0]["display_name"] == "Heather Piwowar"
        request = httpx_mock.get_request()
        assert request.url.path == "/authors"
        assert request.url.params["search"] == "Piwowar"

    def test_get_author_works(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.get_author_works("A5048491430")

        params = httpx_mock.get_request().url.params
        assert "authorships.author.id:A5048491430" in params["filter"]
        assert params["sort"] == "publication_date:desc"

    def test_get_author_works_resolves_orcid_first(self, httpx_mock):
        httpx_mock.add_response(json={"id": "https://openalex.org/A5048491430"})
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.get_author_works("0000-0003-1613-5981")

        requests = httpx_mock.get_requests()
        assert len(requests) == 2
        assert requests[0].url.path == "/authors/orcid:0000-0003-1613-5981"
        assert "authorships.author.id:A5048491430" in requests[1].url.params["filter"]


class TestInstitutionEndpoints:
    def test_get_institution(self, httpx_mock):
        httpx_mock.add_response(
            json={"id": "https://openalex.org/I27837315", "display_name": "University of Michigan"}
        )

        with OpenAlexAPI() as api:
            result = api.get_institution("I27837315")

        assert result["display_name"] == "University of Michigan"
        assert httpx_mock.get_request().url.path == "/institutions/I27837315"

    def test_search_institutions(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.search_institutions("Michigan")

        request = httpx_mock.get_request()
        assert request.url.path == "/institutions"
        assert request.url.params["search"] == "Michigan"

    def test_get_institution_works(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.get_institution_works("I27837315")

        params = httpx_mock.get_request().url.params
        assert "authorships.institutions.id:I27837315" in params["filter"]


class TestSourceEndpoints:
    def test_get_source(self, httpx_mock):
        httpx_mock.add_response(
            json={"id": "https://openalex.org/S137773608", "display_name": "PeerJ"}
        )

        with OpenAlexAPI() as api:
            result = api.get_source("S137773608")

        assert result["display_name"] == "PeerJ"
        assert httpx_mock.get_request().url.path == "/sources/S137773608"

    def test_search_sources(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.search_sources("PeerJ")

        request = httpx_mock.get_request()
        assert request.url.path == "/sources"
        assert request.url.params["search"] == "PeerJ"

    def test_get_source_works(self, httpx_mock):
        httpx_mock.add_response(json={"meta": {"count": 0}, "results": []})

        with OpenAlexAPI() as api:
            api.get_source_works("S137773608")

        params = httpx_mock.get_request().url.params
        assert "primary_location.source.id:S137773608" in params["filter"]


class TestErrorHandling:
    def test_404_raises_not_found(self, httpx_mock):
        httpx_mock.add_response(status_code=404)

        with OpenAlexAPI() as api, pytest.raises(APIError) as exc:
            api.get_work("W999")

        assert exc.value.status_code == 404
        assert exc.value.suggestion is not None

    def test_400_uses_api_message(self, httpx_mock):
        httpx_mock.add_response(status_code=400, json={"message": "Invalid filter"})

        with OpenAlexAPI() as api, pytest.raises(APIError) as exc:
            api.search_works(query="test")

        assert exc.value.status_code == 400
        assert "Invalid filter" in exc.value.message

    def test_400_with_non_json_body(self, httpx_mock):
        httpx_mock.add_response(status_code=400, text="not json")

        with OpenAlexAPI() as api, pytest.raises(APIError) as exc:
            api.search_works(query="test")

        assert exc.value.message == "Bad request"

    def test_unknown_error(self, httpx_mock):
        httpx_mock.add_response(status_code=500)

        with OpenAlexAPI() as api, pytest.raises(APIError) as exc:
            api.search_works(query="test")

        assert exc.value.status_code == 500

    def test_429_raises_rate_limit(self, httpx_mock):
        httpx_mock.add_response(status_code=429, headers={"Retry-After": "60"})

        with OpenAlexAPI(max_retries=0) as api, pytest.raises(RateLimitError) as exc:
            api.search_works(query="test")

        assert exc.value.retry_after == 60

    def test_429_with_http_date_retry_after(self, httpx_mock):
        # Retry-After may be an HTTP date (RFC 9110), not just seconds
        httpx_mock.add_response(
            status_code=429,
            headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
        )

        with OpenAlexAPI(max_retries=0) as api, pytest.raises(RateLimitError) as exc:
            api.search_works(query="test")

        assert exc.value.retry_after is None

    def test_retry_with_http_date_retry_after_uses_backoff(self, httpx_mock):
        httpx_mock.add_response(
            status_code=429,
            headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
        )
        httpx_mock.add_response(json={"id": "https://openalex.org/W123"})

        import openalexcli.api.client as client_module

        sleeps: list[float] = []
        original_sleep = client_module.time.sleep
        client_module.time.sleep = sleeps.append
        try:
            with OpenAlexAPI(max_retries=1, status_callback=lambda m: None) as api:
                result = api.search_works(query="test")
        finally:
            client_module.time.sleep = original_sleep

        assert result["id"] == "https://openalex.org/W123"
        assert len(sleeps) == 1

    def test_connection_error(self, httpx_mock):
        httpx_mock.add_exception(httpx.ConnectError("boom"))

        with OpenAlexAPI(max_retries=0) as api, pytest.raises(APIError) as exc:
            api.search_works(query="test")

        assert "Connection error" in exc.value.message
        assert exc.value.suggestion == "Check your network connection"


class TestRetryBehavior:
    def test_retries_on_rate_limit(self, httpx_mock):
        httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})
        httpx_mock.add_response(json={"id": "https://openalex.org/W123"})

        with OpenAlexAPI(max_retries=1, status_callback=lambda m: None) as api:
            result = api.get_work("W123")

        assert result["id"] == "https://openalex.org/W123"
        assert len(httpx_mock.get_requests()) == 2

    def test_gives_up_after_max_retries(self, httpx_mock):
        for _ in range(3):
            httpx_mock.add_response(status_code=429, headers={"Retry-After": "0"})

        with (
            OpenAlexAPI(max_retries=2, status_callback=lambda m: None) as api,
            pytest.raises(RateLimitError),
        ):
            api.get_work("W123")

        assert len(httpx_mock.get_requests()) == 3

    def test_retries_on_connection_error(self, httpx_mock, monkeypatch):
        import openalexcli.api.client as client_module

        monkeypatch.setattr(client_module.time, "sleep", lambda s: None)
        httpx_mock.add_exception(httpx.ConnectError("boom"))
        httpx_mock.add_response(json={"id": "https://openalex.org/W123"})

        with OpenAlexAPI(max_retries=1, status_callback=lambda m: None) as api:
            result = api.get_work("W123")

        assert result["id"] == "https://openalex.org/W123"
        assert len(httpx_mock.get_requests()) == 2


class TestContextManager:
    def test_context_manager_closes_client(self, httpx_mock):
        httpx_mock.add_response(json={"id": "https://openalex.org/W123"})

        with OpenAlexAPI() as api:
            api.get_work("W123")
            assert api._client is not None

        assert api._client is None
