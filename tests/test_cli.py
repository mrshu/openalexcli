"""Tests for CLI commands."""

import json
import types

import pytest
from typer.testing import CliRunner

from openalexcli.cli import app

runner = CliRunner()

# Fixtures modeled on real OpenAlex API responses
# (e.g. https://api.openalex.org/works/W2741809807).
WORK = {
    "id": "https://openalex.org/W2741809807",
    "doi": "https://doi.org/10.7717/peerj.4375",
    "title": "The state of OA: a large-scale analysis of Open Access articles",
    "publication_year": 2018,
    "publication_date": "2018-02-13",
    "type": "article",
    "cited_by_count": 1241,
    "open_access": {
        "is_oa": True,
        "oa_status": "gold",
        "oa_url": "https://doi.org/10.7717/peerj.4375",
    },
    "authorships": [
        {
            "author_position": "first",
            "author": {
                "id": "https://openalex.org/A5048491430",
                "display_name": "Heather Piwowar",
                "orcid": "https://orcid.org/0000-0003-1613-5981",
            },
            "institutions": [
                {
                    "id": "https://openalex.org/I4200000001",
                    "display_name": "OpenAlex",
                    "country_code": "CA",
                    "type": "nonprofit",
                }
            ],
        },
        {
            "author_position": "middle",
            "author": {
                "id": "https://openalex.org/A5023888391",
                "display_name": "Jason R Priem",
                "orcid": "https://orcid.org/0000-0001-6187-6610",
            },
            "institutions": [],
        },
    ],
    "primary_location": {
        "source": {
            "id": "https://openalex.org/S1983995261",
            "display_name": "PeerJ",
            "type": "journal",
        }
    },
    "abstract_inverted_index": {"Despite": [0], "growing": [1], "interest": [2]},
    "topics": [{"display_name": "Open Access Publishing"}],
    "biblio": {"volume": "6", "issue": None, "first_page": "e4375", "last_page": None},
}

META = {"count": 1, "db_response_time_ms": 12, "page": 1, "per_page": 25}

WORKS_PAGE = {"meta": META, "results": [WORK]}

AUTHOR = {
    "id": "https://openalex.org/A5048491430",
    "orcid": "https://orcid.org/0000-0003-1613-5981",
    "display_name": "Heather Piwowar",
    "works_count": 50,
    "cited_by_count": 5000,
    "summary_stats": {"h_index": 25, "i10_index": 40},
    "last_known_institutions": [{"display_name": "OpenAlex", "country_code": "CA"}],
    "topics": [{"display_name": "Scholarly Communication"}],
}

INSTITUTION = {
    "id": "https://openalex.org/I27837315",
    "ror": "https://ror.org/00jmfr291",
    "display_name": "University of Michigan",
    "country_code": "US",
    "type": "funder",
    "works_count": 100000,
    "cited_by_count": 5000000,
    "summary_stats": {"h_index": 1000},
}

SOURCE = {
    "id": "https://openalex.org/S1983995261",
    "issn_l": "2167-8359",
    "display_name": "PeerJ",
    "type": "journal",
    "works_count": 20000,
    "cited_by_count": 300000,
    "is_oa": True,
    "summary_stats": {"h_index": 120},
}

GROUPS_PAGE = {
    "meta": {"count": 100, "groups_count": 2},
    "group_by": [
        {"key": "2018", "key_display_name": "2018", "count": 60},
        {"key": "2019", "key_display_name": "2019", "count": 40},
    ],
}


@pytest.fixture
def fake_tty(monkeypatch):
    """Make the CLI believe stdout is a terminal."""
    fake_sys = types.SimpleNamespace(
        stdout=types.SimpleNamespace(isatty=lambda: True),
        stderr=types.SimpleNamespace(isatty=lambda: True),
    )
    monkeypatch.setattr("openalexcli.cli.sys", fake_sys)


class TestSearchCommand:
    def test_piped_output_defaults_to_json(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["search", "open access"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["results"][0]["id"] == "https://openalex.org/W2741809807"
        assert output["meta"]["count"] == 1

    def test_json_flag(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["search", "open access", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["count"] == 1

    def test_bibtex_flag(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["search", "open access", "--bibtex"])

        assert result.exit_code == 0
        assert "@article{piwowar2018state," in result.stdout
        assert "Heather Piwowar and Jason R Priem" in result.stdout

    def test_tty_renders_table(self, httpx_mock, fake_tty):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["search", "open access"])

        assert result.exit_code == 0
        assert "W2741809807" in result.stdout
        assert "Cited" in result.stdout
        assert "Showing 1 of 1 results" in result.stdout

    def test_filters_forwarded_to_api(self, httpx_mock):
        httpx_mock.add_response(json={"meta": META, "results": []})

        result = runner.invoke(
            app,
            [
                "search",
                "ML",
                "--from-date",
                "2023-01-01",
                "--min-citations",
                "100",
                "--oa",
                "--type",
                "article",
            ],
        )

        assert result.exit_code == 0
        filter_param = httpx_mock.get_request().url.params["filter"]
        assert "from_publication_date:2023-01-01" in filter_param
        assert "cited_by_count:>100" in filter_param
        assert "is_oa:true" in filter_param
        assert "type:article" in filter_param

    def test_group_by_json(self, httpx_mock):
        httpx_mock.add_response(json=GROUPS_PAGE)

        result = runner.invoke(
            app, ["search", "test", "--group-by", "publication_year", "--json"]
        )

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["results"][0]["key"] == "2018"
        assert output["count"] == 2

    def test_group_by_tty_table(self, httpx_mock, fake_tty):
        httpx_mock.add_response(json=GROUPS_PAGE)

        result = runner.invoke(app, ["search", "test", "--group-by", "publication_year"])

        assert result.exit_code == 0
        assert "Grouped by:" in result.stdout
        assert "publication_year" in result.stdout
        assert "2018" in result.stdout

    def test_email_option_forwarded(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(
            app, ["search", "test", "--email", "polite@example.com"]
        )

        assert result.exit_code == 0
        assert httpx_mock.get_request().url.params["mailto"] == "polite@example.com"

    def test_email_env_var(self, httpx_mock, monkeypatch):
        monkeypatch.setenv("OPENALEX_EMAIL", "env@example.com")
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["search", "test"])

        assert result.exit_code == 0
        assert httpx_mock.get_request().url.params["mailto"] == "env@example.com"


class TestWorkCommand:
    def test_single_work_json(self, httpx_mock):
        httpx_mock.add_response(json=WORK)

        result = runner.invoke(app, ["work", "W2741809807", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"]["id"] == "https://openalex.org/W2741809807"

    def test_single_work_tty_detail(self, httpx_mock, fake_tty):
        httpx_mock.add_response(json=WORK)

        result = runner.invoke(app, ["work", "W2741809807"])

        assert result.exit_code == 0
        assert "W2741809807" in result.stdout
        assert "Heather Piwowar" in result.stdout

    def test_multiple_works_json(self, httpx_mock):
        httpx_mock.add_response(json=WORK)
        httpx_mock.add_response(json={**WORK, "id": "https://openalex.org/W999"})

        result = runner.invoke(app, ["work", "W2741809807", "W999", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["count"] == 2

    def test_work_bibtex(self, httpx_mock):
        httpx_mock.add_response(json=WORK)

        result = runner.invoke(app, ["work", "W2741809807", "--bibtex"])

        assert result.exit_code == 0
        assert "@article{piwowar2018state," in result.stdout

    def test_work_by_doi(self, httpx_mock):
        httpx_mock.add_response(json=WORK)

        result = runner.invoke(app, ["work", "10.7717/peerj.4375", "--json"])

        assert result.exit_code == 0
        assert httpx_mock.get_request().url.path == "/works/doi:10.7717/peerj.4375"


class TestCitationsCommand:
    def test_citations_json(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["citations", "W123", "--json"])

        assert result.exit_code == 0
        assert httpx_mock.get_request().url.params["filter"] == "cites:W123"
        output = json.loads(result.stdout)
        assert output["count"] == 1


class TestReferencesCommand:
    def test_references_json(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["references", "W123", "--json"])

        assert result.exit_code == 0
        assert httpx_mock.get_request().url.params["filter"] == "cited_by:W123"


class TestBibtexCommand:
    def test_bibtex_single(self, httpx_mock):
        httpx_mock.add_response(json=WORK)

        result = runner.invoke(app, ["bibtex", "W2741809807"])

        assert result.exit_code == 0
        assert "@article{piwowar2018state," in result.stdout
        assert "journal = {PeerJ}" in result.stdout

    def test_bibtex_multiple(self, httpx_mock):
        httpx_mock.add_response(json=WORK)
        httpx_mock.add_response(
            json={**WORK, "title": "Second Paper", "publication_year": 2019}
        )

        result = runner.invoke(app, ["bibtex", "W1", "W2"])

        assert result.exit_code == 0
        assert result.stdout.count("@article") == 2
        assert "Second Paper" in result.stdout


class TestAuthorCommands:
    def test_author_get_json(self, httpx_mock):
        httpx_mock.add_response(json=AUTHOR)

        result = runner.invoke(app, ["author", "get", "A5048491430", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"]["display_name"] == "Heather Piwowar"

    def test_author_get_tty_detail(self, httpx_mock, fake_tty):
        httpx_mock.add_response(json=AUTHOR)

        result = runner.invoke(app, ["author", "get", "A5048491430"])

        assert result.exit_code == 0
        assert "Heather Piwowar" in result.stdout
        assert "h-index" in result.stdout

    def test_author_search_json(self, httpx_mock):
        httpx_mock.add_response(json={"meta": META, "results": [AUTHOR]})

        result = runner.invoke(app, ["author", "search", "Piwowar", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["results"][0]["display_name"] == "Heather Piwowar"

    def test_author_search_tty_table(self, httpx_mock, fake_tty):
        httpx_mock.add_response(json={"meta": META, "results": [AUTHOR]})

        result = runner.invoke(app, ["author", "search", "Piwowar"])

        assert result.exit_code == 0
        assert "A5048491430" in result.stdout

    def test_author_works_json(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["author", "works", "A5048491430", "--json"])

        assert result.exit_code == 0
        filter_param = httpx_mock.get_request().url.params["filter"]
        assert "authorships.author.id:A5048491430" in filter_param


class TestInstitutionCommands:
    def test_institution_get_json(self, httpx_mock):
        httpx_mock.add_response(json=INSTITUTION)

        result = runner.invoke(app, ["institution", "get", "I27837315", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"]["display_name"] == "University of Michigan"

    def test_institution_search_json(self, httpx_mock):
        httpx_mock.add_response(json={"meta": META, "results": [INSTITUTION]})

        result = runner.invoke(app, ["institution", "search", "Michigan", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["results"][0]["id"] == "https://openalex.org/I27837315"

    def test_institution_works_json(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["institution", "works", "I27837315", "--json"])

        assert result.exit_code == 0
        filter_param = httpx_mock.get_request().url.params["filter"]
        assert "authorships.institutions.id:I27837315" in filter_param


class TestSourceCommands:
    def test_source_get_json(self, httpx_mock):
        httpx_mock.add_response(json=SOURCE)

        result = runner.invoke(app, ["source", "get", "S1983995261", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["result"]["display_name"] == "PeerJ"

    def test_source_search_json(self, httpx_mock):
        httpx_mock.add_response(json={"meta": META, "results": [SOURCE]})

        result = runner.invoke(app, ["source", "search", "PeerJ", "--json"])

        assert result.exit_code == 0
        output = json.loads(result.stdout)
        assert output["results"][0]["issn_l"] == "2167-8359"

    def test_source_works_json(self, httpx_mock):
        httpx_mock.add_response(json=WORKS_PAGE)

        result = runner.invoke(app, ["source", "works", "S1983995261", "--json"])

        assert result.exit_code == 0
        filter_param = httpx_mock.get_request().url.params["filter"]
        assert "primary_location.source.id:S1983995261" in filter_param


class TestErrorHandling:
    def test_not_found_json_error(self, httpx_mock):
        httpx_mock.add_response(status_code=404)

        result = runner.invoke(app, ["work", "W999", "--json"])

        assert result.exit_code == 1
        output = json.loads(result.stdout)
        assert output["error"] == "Entity not found"
        assert output["status_code"] == 404
        assert "suggestion" in output

    def test_not_found_piped_defaults_to_json_error(self, httpx_mock):
        httpx_mock.add_response(status_code=404)

        result = runner.invoke(app, ["author", "get", "A999"])

        assert result.exit_code == 1
        output = json.loads(result.stdout)
        assert output["error"] == "Entity not found"

    def test_bad_request_exits_nonzero(self, httpx_mock):
        httpx_mock.add_response(status_code=400, json={"message": "Invalid filter"})

        result = runner.invoke(app, ["search", "test", "--json"])

        assert result.exit_code == 1
        output = json.loads(result.stdout)
        assert output["error"] == "Invalid filter"


class TestNoArgsShowsHelp:
    def test_no_args(self):
        result = runner.invoke(app, [])

        assert result.exit_code == 0 or "Usage" in result.stdout
        assert "search" in result.stdout.lower() or "Usage" in result.stdout
