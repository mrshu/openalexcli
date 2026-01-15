"""Table output formatting using Rich."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


def _truncate(text: str, max_length: int = 60) -> str:
    """Truncate text to max length with ellipsis."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def _format_authors(authorships: list[dict[str, Any]], max_authors: int = 3) -> str:
    """Format author list for display."""
    if not authorships:
        return ""

    authors = []
    for authorship in authorships[:max_authors]:
        author = authorship.get("author", {})
        name = author.get("display_name", "")
        if name:
            authors.append(name)

    result = ", ".join(authors)
    remaining = len(authorships) - max_authors
    if remaining > 0:
        result += f" +{remaining}"

    return result


def _format_number(n: int | None) -> str:
    """Format number with thousands separator."""
    if n is None:
        return "-"
    return f"{n:,}"


def _get_openalex_short_id(full_id: str) -> str:
    """Extract short ID from full OpenAlex URL."""
    if not full_id:
        return ""
    return full_id.replace("https://openalex.org/", "")


# -----------------------------------------------------------------------------
# Table formatters for lists
# -----------------------------------------------------------------------------


def format_works_table(
    works: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> None:
    """Print works as a Rich table."""
    console = Console()

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Year", justify="right")
    table.add_column("Cited", justify="right")
    table.add_column("Title", max_width=50)
    table.add_column("Authors", max_width=30)

    for work in works:
        work_id = _get_openalex_short_id(work.get("id", ""))
        year = str(work.get("publication_year", "")) or "-"
        citations = _format_number(work.get("cited_by_count"))
        title = _truncate(work.get("title", "") or "", 50)
        authors = _truncate(_format_authors(work.get("authorships", [])), 30)

        table.add_row(work_id, year, citations, title, authors)

    console.print(table)

    if meta:
        total = meta.get("count", 0)
        page = meta.get("page", 1)
        per_page = meta.get("per_page", 25)
        shown = len(works)
        console.print(
            f"\n[dim]Showing {shown} of {total:,} results (page {page})[/dim]"
        )


def format_authors_table(
    authors: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> None:
    """Print authors as a Rich table."""
    console = Console()

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", max_width=30)
    table.add_column("Works", justify="right")
    table.add_column("Cited", justify="right")
    table.add_column("h-index", justify="right")
    table.add_column("Affiliations", max_width=35)

    for author in authors:
        author_id = _get_openalex_short_id(author.get("id", ""))
        name = _truncate(author.get("display_name", "") or "", 30)
        works_count = _format_number(author.get("works_count"))
        citations = _format_number(author.get("cited_by_count"))

        # h-index from summary_stats
        summary = author.get("summary_stats", {}) or {}
        h_index = str(summary.get("h_index", "-")) if summary else "-"

        # Affiliations
        affiliations = author.get("last_known_institutions", []) or []
        if affiliations:
            aff_names = [
                a.get("display_name", "") for a in affiliations[:2] if a
            ]
            aff_str = ", ".join(filter(None, aff_names))
            if len(affiliations) > 2:
                aff_str += f" +{len(affiliations) - 2}"
        else:
            aff_str = "-"
        aff_str = _truncate(aff_str, 35)

        table.add_row(author_id, name, works_count, citations, h_index, aff_str)

    console.print(table)

    if meta:
        total = meta.get("count", 0)
        page = meta.get("page", 1)
        console.print(
            f"\n[dim]Showing {len(authors)} of {total:,} results (page {page})[/dim]"
        )


def format_institutions_table(
    institutions: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> None:
    """Print institutions as a Rich table."""
    console = Console()

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", max_width=40)
    table.add_column("Country", justify="center")
    table.add_column("Type", max_width=15)
    table.add_column("Works", justify="right")
    table.add_column("Cited", justify="right")

    for inst in institutions:
        inst_id = _get_openalex_short_id(inst.get("id", ""))
        name = _truncate(inst.get("display_name", "") or "", 40)
        country = inst.get("country_code", "") or "-"
        inst_type = inst.get("type", "") or "-"
        works_count = _format_number(inst.get("works_count"))
        citations = _format_number(inst.get("cited_by_count"))

        table.add_row(inst_id, name, country, inst_type, works_count, citations)

    console.print(table)

    if meta:
        total = meta.get("count", 0)
        page = meta.get("page", 1)
        console.print(
            f"\n[dim]Showing {len(institutions)} of {total:,} results (page {page})[/dim]"
        )


def format_sources_table(
    sources: list[dict[str, Any]],
    meta: dict[str, Any] | None = None,
) -> None:
    """Print sources as a Rich table."""
    console = Console()

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Name", max_width=45)
    table.add_column("Type", max_width=12)
    table.add_column("OA", justify="center")
    table.add_column("Works", justify="right")
    table.add_column("Cited", justify="right")

    for source in sources:
        source_id = _get_openalex_short_id(source.get("id", ""))
        name = _truncate(source.get("display_name", "") or "", 45)
        source_type = source.get("type", "") or "-"
        is_oa = "Yes" if source.get("is_oa") else "No"
        works_count = _format_number(source.get("works_count"))
        citations = _format_number(source.get("cited_by_count"))

        table.add_row(source_id, name, source_type, is_oa, works_count, citations)

    console.print(table)

    if meta:
        total = meta.get("count", 0)
        page = meta.get("page", 1)
        console.print(
            f"\n[dim]Showing {len(sources)} of {total:,} results (page {page})[/dim]"
        )


def format_groups_table(
    groups: list[dict[str, Any]],
    group_by: str,
    meta: dict[str, Any] | None = None,
) -> None:
    """Print group_by results as a Rich table."""
    console = Console()

    table = Table(
        show_header=True,
        header_style="bold",
        title=f"Grouped by: {group_by}",
    )
    table.add_column("Key", style="dim", no_wrap=True)
    table.add_column("Name", max_width=50)
    table.add_column("Count", justify="right")

    for group in groups:
        key = str(group.get("key", ""))
        display_name = group.get("key_display_name", "") or key
        display_name = _truncate(display_name, 50)
        count = _format_number(group.get("count"))

        table.add_row(key, display_name, count)

    console.print(table)

    if meta:
        total = meta.get("count", 0)
        groups_count = meta.get("groups_count", len(groups))
        console.print(f"\n[dim]Showing {groups_count} groups ({total:,} total entities)[/dim]")


# -----------------------------------------------------------------------------
# Detail formatters for single entities
# -----------------------------------------------------------------------------


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return ""

    max_pos = 0
    for positions in inverted_index.values():
        if positions:
            max_pos = max(max_pos, max(positions))

    words = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word

    return " ".join(words)


def format_work_detail(work: dict[str, Any]) -> None:
    """Print detailed work information."""
    console = Console()

    work_id = _get_openalex_short_id(work.get("id", ""))
    title = work.get("title", "") or "Untitled"

    # Build content
    lines = []

    lines.append(f"[bold]ID:[/bold] {work_id}")

    if work.get("doi"):
        lines.append(f"[bold]DOI:[/bold] {work['doi']}")

    lines.append(f"[bold]Year:[/bold] {work.get('publication_year', '-')}")
    lines.append(f"[bold]Type:[/bold] {work.get('type', '-')}")
    lines.append(f"[bold]Citations:[/bold] {_format_number(work.get('cited_by_count'))}")

    # Open access
    oa = work.get("open_access", {}) or {}
    oa_status = "Yes" if oa.get("is_oa") else "No"
    lines.append(f"[bold]Open Access:[/bold] {oa_status}")
    if oa.get("oa_url"):
        lines.append(f"[bold]OA URL:[/bold] {oa['oa_url']}")

    # Source
    primary_location = work.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    if source.get("display_name"):
        lines.append(f"[bold]Source:[/bold] {source['display_name']}")

    # Authors
    authorships = work.get("authorships", [])
    if authorships:
        author_names = []
        for authorship in authorships[:10]:
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                author_names.append(name)
        if author_names:
            authors_str = ", ".join(author_names)
            if len(authorships) > 10:
                authors_str += f" (+{len(authorships) - 10} more)"
            lines.append(f"[bold]Authors:[/bold] {authors_str}")

    # Abstract
    abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
    if abstract:
        lines.append("")
        lines.append("[bold]Abstract:[/bold]")
        # Wrap abstract
        lines.append(abstract[:500] + ("..." if len(abstract) > 500 else ""))

    # Topics
    topics = work.get("topics", [])
    if topics:
        topic_names = [t.get("display_name", "") for t in topics[:5] if t]
        if topic_names:
            lines.append("")
            lines.append(f"[bold]Topics:[/bold] {', '.join(filter(None, topic_names))}")

    panel = Panel(
        "\n".join(lines),
        title=_truncate(title, 70),
        title_align="left",
        border_style="blue",
    )
    console.print(panel)


def format_author_detail(author: dict[str, Any]) -> None:
    """Print detailed author information."""
    console = Console()

    author_id = _get_openalex_short_id(author.get("id", ""))
    name = author.get("display_name", "") or "Unknown"

    lines = []

    lines.append(f"[bold]ID:[/bold] {author_id}")

    if author.get("orcid"):
        lines.append(f"[bold]ORCID:[/bold] {author['orcid']}")

    lines.append(f"[bold]Works:[/bold] {_format_number(author.get('works_count'))}")
    lines.append(f"[bold]Citations:[/bold] {_format_number(author.get('cited_by_count'))}")

    # Summary stats
    summary = author.get("summary_stats", {}) or {}
    if summary:
        if summary.get("h_index") is not None:
            lines.append(f"[bold]h-index:[/bold] {summary['h_index']}")
        if summary.get("i10_index") is not None:
            lines.append(f"[bold]i10-index:[/bold] {summary['i10_index']}")

    # Affiliations
    affiliations = author.get("last_known_institutions", []) or []
    if affiliations:
        lines.append("")
        lines.append("[bold]Affiliations:[/bold]")
        for aff in affiliations[:5]:
            if aff:
                aff_name = aff.get("display_name", "")
                country = aff.get("country_code", "")
                if aff_name:
                    lines.append(f"  - {aff_name}" + (f" ({country})" if country else ""))

    # Topics
    topics = author.get("topics", [])
    if topics:
        topic_names = [t.get("display_name", "") for t in topics[:5] if t]
        if topic_names:
            lines.append("")
            lines.append(f"[bold]Topics:[/bold] {', '.join(filter(None, topic_names))}")

    panel = Panel(
        "\n".join(lines),
        title=name,
        title_align="left",
        border_style="green",
    )
    console.print(panel)


def format_institution_detail(inst: dict[str, Any]) -> None:
    """Print detailed institution information."""
    console = Console()

    inst_id = _get_openalex_short_id(inst.get("id", ""))
    name = inst.get("display_name", "") or "Unknown"

    lines = []

    lines.append(f"[bold]ID:[/bold] {inst_id}")

    if inst.get("ror"):
        lines.append(f"[bold]ROR:[/bold] {inst['ror']}")

    lines.append(f"[bold]Country:[/bold] {inst.get('country_code', '-')}")
    lines.append(f"[bold]Type:[/bold] {inst.get('type', '-')}")
    lines.append(f"[bold]Works:[/bold] {_format_number(inst.get('works_count'))}")
    lines.append(f"[bold]Citations:[/bold] {_format_number(inst.get('cited_by_count'))}")

    # Summary stats
    summary = inst.get("summary_stats", {}) or {}
    if summary:
        if summary.get("h_index") is not None:
            lines.append(f"[bold]h-index:[/bold] {summary['h_index']}")

    panel = Panel(
        "\n".join(lines),
        title=name,
        title_align="left",
        border_style="yellow",
    )
    console.print(panel)


def format_source_detail(source: dict[str, Any]) -> None:
    """Print detailed source information."""
    console = Console()

    source_id = _get_openalex_short_id(source.get("id", ""))
    name = source.get("display_name", "") or "Unknown"

    lines = []

    lines.append(f"[bold]ID:[/bold] {source_id}")

    if source.get("issn_l"):
        lines.append(f"[bold]ISSN-L:[/bold] {source['issn_l']}")

    lines.append(f"[bold]Type:[/bold] {source.get('type', '-')}")
    lines.append(f"[bold]Open Access:[/bold] {'Yes' if source.get('is_oa') else 'No'}")
    lines.append(f"[bold]Works:[/bold] {_format_number(source.get('works_count'))}")
    lines.append(f"[bold]Citations:[/bold] {_format_number(source.get('cited_by_count'))}")

    # Summary stats
    summary = source.get("summary_stats", {}) or {}
    if summary:
        if summary.get("h_index") is not None:
            lines.append(f"[bold]h-index:[/bold] {summary['h_index']}")

    panel = Panel(
        "\n".join(lines),
        title=name,
        title_align="left",
        border_style="magenta",
    )
    console.print(panel)
