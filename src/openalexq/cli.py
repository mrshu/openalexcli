"""OpenAlex CLI - Command-line interface for the OpenAlex API."""

from __future__ import annotations

import os
import sys
from typing import Annotated, Optional

import typer
from rich.console import Console

from openalexq.api import OpenAlexAPI, APIError
from openalexq.formatters import (
    format_bibtex,
    format_works_bibtex,
    format_json,
    format_error_json,
    format_works_table,
    format_authors_table,
    format_institutions_table,
    format_sources_table,
    format_groups_table,
    format_work_detail,
    format_author_detail,
    format_institution_detail,
    format_source_detail,
)

# CLI app
app = typer.Typer(
    name="openalexq",
    help="Command-line interface for the OpenAlex API",
    no_args_is_help=True,
)

# Subcommand groups
author_app = typer.Typer(help="Author-related commands", no_args_is_help=True)
institution_app = typer.Typer(help="Institution-related commands", no_args_is_help=True)
source_app = typer.Typer(help="Source/journal-related commands", no_args_is_help=True)

app.add_typer(author_app, name="author")
app.add_typer(institution_app, name="institution")
app.add_typer(source_app, name="source")

# Console for error output
console = Console(stderr=True)


def get_email() -> str | None:
    """Get email from environment variable."""
    return os.environ.get("OPENALEX_EMAIL")


def handle_error(e: APIError, use_json: bool = False) -> None:
    """Handle API errors with appropriate output format."""
    if use_json or not sys.stdout.isatty():
        print(format_error_json(e.to_dict()))
    else:
        console.print(f"[red]Error:[/red] {e.message}")
        if e.suggestion:
            console.print(f"[dim]{e.suggestion}[/dim]")
    raise typer.Exit(1)


def output_works(
    response: dict,
    use_json: bool,
    use_bibtex: bool,
    group_by: str | None = None,
) -> None:
    """Output works in the appropriate format."""
    meta = response.get("meta", {})

    if group_by:
        groups = response.get("group_by", [])
        if use_json or not sys.stdout.isatty():
            print(format_json(groups, meta))
        else:
            format_groups_table(groups, group_by, meta)
        return

    results = response.get("results", [])

    if use_bibtex:
        print(format_works_bibtex(results))
    elif use_json or not sys.stdout.isatty():
        print(format_json(results, meta))
    else:
        format_works_table(results, meta)


# -----------------------------------------------------------------------------
# Work commands
# -----------------------------------------------------------------------------


@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Search query")],
    filter_str: Annotated[
        Optional[str],
        typer.Option("--filter", "-f", help="OpenAlex filter string"),
    ] = None,
    from_date: Annotated[
        Optional[str],
        typer.Option("--from-date", help="Start date (YYYY-MM-DD)"),
    ] = None,
    to_date: Annotated[
        Optional[str],
        typer.Option("--to-date", help="End date (YYYY-MM-DD)"),
    ] = None,
    min_citations: Annotated[
        Optional[int],
        typer.Option("--min-citations", help="Minimum citation count"),
    ] = None,
    open_access: Annotated[
        bool,
        typer.Option("--open-access", "--oa", help="Only open access works"),
    ] = False,
    work_type: Annotated[
        Optional[str],
        typer.Option("--type", help="Work type (article, book, etc.)"),
    ] = None,
    sort: Annotated[
        Optional[str],
        typer.Option("--sort", help="Sort field (e.g., cited_by_count:desc)"),
    ] = None,
    group_by: Annotated[
        Optional[str],
        typer.Option("--group-by", help="Group results by field"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results per page"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    use_bibtex: Annotated[
        bool,
        typer.Option("--bibtex", help="Output as BibTeX"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Search for works in OpenAlex."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.search_works(
                query=query,
                filter_str=filter_str,
                from_date=from_date,
                to_date=to_date,
                min_citations=min_citations,
                open_access=open_access if open_access else None,
                work_type=work_type,
                sort=sort,
                page=page,
                per_page=limit,
                group_by=group_by,
            )
            output_works(response, use_json, use_bibtex, group_by)
        except APIError as e:
            handle_error(e, use_json)


@app.command()
def work(
    work_ids: Annotated[
        list[str],
        typer.Argument(help="Work ID(s) - OpenAlex ID, DOI, PMID, etc."),
    ],
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    use_bibtex: Annotated[
        bool,
        typer.Option("--bibtex", help="Output as BibTeX"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get work(s) by ID."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        works = []
        for work_id in work_ids:
            try:
                result = api.get_work(work_id)
                works.append(result)
            except APIError as e:
                handle_error(e, use_json)

        if len(works) == 1 and not use_bibtex:
            if use_json or not sys.stdout.isatty():
                print(format_json(works[0]))
            else:
                format_work_detail(works[0])
        else:
            if use_bibtex:
                print(format_works_bibtex(works))
            elif use_json or not sys.stdout.isatty():
                print(format_json(works))
            else:
                format_works_table(works)


@app.command()
def citations(
    work_id: Annotated[str, typer.Argument(help="Work ID")],
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    use_bibtex: Annotated[
        bool,
        typer.Option("--bibtex", help="Output as BibTeX"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get works that cite a given work."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.get_citations(
                work_id=work_id,
                page=page,
                per_page=limit,
            )
            output_works(response, use_json, use_bibtex)
        except APIError as e:
            handle_error(e, use_json)


@app.command()
def references(
    work_id: Annotated[str, typer.Argument(help="Work ID")],
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    use_bibtex: Annotated[
        bool,
        typer.Option("--bibtex", help="Output as BibTeX"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get works cited by a given work (references)."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.get_references(
                work_id=work_id,
                page=page,
                per_page=limit,
            )
            output_works(response, use_json, use_bibtex)
        except APIError as e:
            handle_error(e, use_json)


@app.command()
def bibtex(
    work_ids: Annotated[
        list[str],
        typer.Argument(help="Work ID(s)"),
    ],
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Export BibTeX citations for work(s)."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        works = []
        for work_id in work_ids:
            try:
                result = api.get_work(work_id)
                works.append(result)
            except APIError as e:
                handle_error(e, use_json=False)

        print(format_works_bibtex(works))


# -----------------------------------------------------------------------------
# Author commands
# -----------------------------------------------------------------------------


@author_app.command("get")
def author_get(
    author_id: Annotated[str, typer.Argument(help="Author ID (OpenAlex ID or ORCID)")],
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get author details by ID."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            result = api.get_author(author_id)
            if use_json or not sys.stdout.isatty():
                print(format_json(result))
            else:
                format_author_detail(result)
        except APIError as e:
            handle_error(e, use_json)


@author_app.command("search")
def author_search(
    query: Annotated[str, typer.Argument(help="Search query (author name)")],
    filter_str: Annotated[
        Optional[str],
        typer.Option("--filter", "-f", help="OpenAlex filter string"),
    ] = None,
    sort: Annotated[
        Optional[str],
        typer.Option("--sort", help="Sort field"),
    ] = None,
    group_by: Annotated[
        Optional[str],
        typer.Option("--group-by", help="Group results by field"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Search for authors by name."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.search_authors(
                query=query,
                filter_str=filter_str,
                sort=sort,
                page=page,
                per_page=limit,
                group_by=group_by,
            )

            meta = response.get("meta", {})

            if group_by:
                groups = response.get("group_by", [])
                if use_json or not sys.stdout.isatty():
                    print(format_json(groups, meta))
                else:
                    format_groups_table(groups, group_by, meta)
            else:
                results = response.get("results", [])
                if use_json or not sys.stdout.isatty():
                    print(format_json(results, meta))
                else:
                    format_authors_table(results, meta)
        except APIError as e:
            handle_error(e, use_json)


@author_app.command("works")
def author_works(
    author_id: Annotated[str, typer.Argument(help="Author ID")],
    filter_str: Annotated[
        Optional[str],
        typer.Option("--filter", "-f", help="OpenAlex filter string"),
    ] = None,
    from_date: Annotated[
        Optional[str],
        typer.Option("--from-date", help="Start date (YYYY-MM-DD)"),
    ] = None,
    to_date: Annotated[
        Optional[str],
        typer.Option("--to-date", help="End date (YYYY-MM-DD)"),
    ] = None,
    sort: Annotated[
        Optional[str],
        typer.Option("--sort", help="Sort field"),
    ] = None,
    group_by: Annotated[
        Optional[str],
        typer.Option("--group-by", help="Group results by field"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    use_bibtex: Annotated[
        bool,
        typer.Option("--bibtex", help="Output as BibTeX"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get works by an author."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.get_author_works(
                author_id=author_id,
                filter_str=filter_str,
                from_date=from_date,
                to_date=to_date,
                sort=sort,
                page=page,
                per_page=limit,
                group_by=group_by,
            )
            output_works(response, use_json, use_bibtex, group_by)
        except APIError as e:
            handle_error(e, use_json)


# -----------------------------------------------------------------------------
# Institution commands
# -----------------------------------------------------------------------------


@institution_app.command("get")
def institution_get(
    institution_id: Annotated[
        str,
        typer.Argument(help="Institution ID (OpenAlex ID or ROR)"),
    ],
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get institution details by ID."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            result = api.get_institution(institution_id)
            if use_json or not sys.stdout.isatty():
                print(format_json(result))
            else:
                format_institution_detail(result)
        except APIError as e:
            handle_error(e, use_json)


@institution_app.command("search")
def institution_search(
    query: Annotated[str, typer.Argument(help="Search query (institution name)")],
    filter_str: Annotated[
        Optional[str],
        typer.Option("--filter", "-f", help="OpenAlex filter string"),
    ] = None,
    sort: Annotated[
        Optional[str],
        typer.Option("--sort", help="Sort field"),
    ] = None,
    group_by: Annotated[
        Optional[str],
        typer.Option("--group-by", help="Group results by field"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Search for institutions by name."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.search_institutions(
                query=query,
                filter_str=filter_str,
                sort=sort,
                page=page,
                per_page=limit,
                group_by=group_by,
            )

            meta = response.get("meta", {})

            if group_by:
                groups = response.get("group_by", [])
                if use_json or not sys.stdout.isatty():
                    print(format_json(groups, meta))
                else:
                    format_groups_table(groups, group_by, meta)
            else:
                results = response.get("results", [])
                if use_json or not sys.stdout.isatty():
                    print(format_json(results, meta))
                else:
                    format_institutions_table(results, meta)
        except APIError as e:
            handle_error(e, use_json)


@institution_app.command("works")
def institution_works(
    institution_id: Annotated[str, typer.Argument(help="Institution ID")],
    filter_str: Annotated[
        Optional[str],
        typer.Option("--filter", "-f", help="OpenAlex filter string"),
    ] = None,
    from_date: Annotated[
        Optional[str],
        typer.Option("--from-date", help="Start date (YYYY-MM-DD)"),
    ] = None,
    to_date: Annotated[
        Optional[str],
        typer.Option("--to-date", help="End date (YYYY-MM-DD)"),
    ] = None,
    sort: Annotated[
        Optional[str],
        typer.Option("--sort", help="Sort field"),
    ] = None,
    group_by: Annotated[
        Optional[str],
        typer.Option("--group-by", help="Group results by field"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    use_bibtex: Annotated[
        bool,
        typer.Option("--bibtex", help="Output as BibTeX"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get works from an institution."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.get_institution_works(
                institution_id=institution_id,
                filter_str=filter_str,
                from_date=from_date,
                to_date=to_date,
                sort=sort,
                page=page,
                per_page=limit,
                group_by=group_by,
            )
            output_works(response, use_json, use_bibtex, group_by)
        except APIError as e:
            handle_error(e, use_json)


# -----------------------------------------------------------------------------
# Source commands
# -----------------------------------------------------------------------------


@source_app.command("get")
def source_get(
    source_id: Annotated[
        str,
        typer.Argument(help="Source ID (OpenAlex ID or ISSN)"),
    ],
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get source (journal/venue) details by ID."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            result = api.get_source(source_id)
            if use_json or not sys.stdout.isatty():
                print(format_json(result))
            else:
                format_source_detail(result)
        except APIError as e:
            handle_error(e, use_json)


@source_app.command("search")
def source_search(
    query: Annotated[str, typer.Argument(help="Search query (source name)")],
    filter_str: Annotated[
        Optional[str],
        typer.Option("--filter", "-f", help="OpenAlex filter string"),
    ] = None,
    sort: Annotated[
        Optional[str],
        typer.Option("--sort", help="Sort field"),
    ] = None,
    group_by: Annotated[
        Optional[str],
        typer.Option("--group-by", help="Group results by field"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Search for sources (journals/venues) by name."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.search_sources(
                query=query,
                filter_str=filter_str,
                sort=sort,
                page=page,
                per_page=limit,
                group_by=group_by,
            )

            meta = response.get("meta", {})

            if group_by:
                groups = response.get("group_by", [])
                if use_json or not sys.stdout.isatty():
                    print(format_json(groups, meta))
                else:
                    format_groups_table(groups, group_by, meta)
            else:
                results = response.get("results", [])
                if use_json or not sys.stdout.isatty():
                    print(format_json(results, meta))
                else:
                    format_sources_table(results, meta)
        except APIError as e:
            handle_error(e, use_json)


@source_app.command("works")
def source_works(
    source_id: Annotated[str, typer.Argument(help="Source ID")],
    filter_str: Annotated[
        Optional[str],
        typer.Option("--filter", "-f", help="OpenAlex filter string"),
    ] = None,
    from_date: Annotated[
        Optional[str],
        typer.Option("--from-date", help="Start date (YYYY-MM-DD)"),
    ] = None,
    to_date: Annotated[
        Optional[str],
        typer.Option("--to-date", help="End date (YYYY-MM-DD)"),
    ] = None,
    sort: Annotated[
        Optional[str],
        typer.Option("--sort", help="Sort field"),
    ] = None,
    group_by: Annotated[
        Optional[str],
        typer.Option("--group-by", help="Group results by field"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of results"),
    ] = 25,
    page: Annotated[
        int,
        typer.Option("--page", "-p", help="Page number"),
    ] = 1,
    use_json: Annotated[
        bool,
        typer.Option("--json", help="Output as JSON"),
    ] = False,
    use_bibtex: Annotated[
        bool,
        typer.Option("--bibtex", help="Output as BibTeX"),
    ] = False,
    email: Annotated[
        Optional[str],
        typer.Option("--email", help="Email for polite pool"),
    ] = None,
) -> None:
    """Get works from a source (journal/venue)."""
    api_email = email or get_email()

    with OpenAlexAPI(email=api_email) as api:
        try:
            response = api.get_source_works(
                source_id=source_id,
                filter_str=filter_str,
                from_date=from_date,
                to_date=to_date,
                sort=sort,
                page=page,
                per_page=limit,
                group_by=group_by,
            )
            output_works(response, use_json, use_bibtex, group_by)
        except APIError as e:
            handle_error(e, use_json)


if __name__ == "__main__":
    app()
