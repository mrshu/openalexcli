"""BibTeX output formatting for OpenAlex works."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _normalize_to_ascii(text: str) -> str:
    """Normalize unicode characters to ASCII equivalents."""
    # Normalize to decomposed form, then encode to ASCII ignoring errors
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    replacements = [
        ("\\", "\\textbackslash{}"),
        ("&", "\\&"),
        ("%", "\\%"),
        ("$", "\\$"),
        ("#", "\\#"),
        ("_", "\\_"),
        ("{", "\\{"),
        ("}", "\\}"),
        ("~", "\\textasciitilde{}"),
        ("^", "\\textasciicircum{}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _generate_citation_key(work: dict[str, Any]) -> str:
    """Generate a citation key from work metadata."""
    # Get first author's last name
    authorships = work.get("authorships", [])
    if authorships:
        author_name = authorships[0].get("author", {}).get("display_name", "")
        # Extract last name (last word of name)
        last_name = author_name.split()[-1] if author_name else "unknown"
        last_name = _normalize_to_ascii(last_name).lower()
        last_name = re.sub(r"[^a-z]", "", last_name)
    else:
        last_name = "unknown"

    # Get year
    year = work.get("publication_year", "")
    if not year:
        year = "nd"  # no date

    # Get first meaningful word from title
    title = work.get("title", "")
    if title:
        # Remove common words and get first significant word
        stopwords = {"a", "an", "the", "on", "in", "of", "for", "to", "and", "with"}
        words = re.findall(r"[a-zA-Z]+", title.lower())
        title_word = next((w for w in words if w not in stopwords), "untitled")
        title_word = _normalize_to_ascii(title_word)
    else:
        title_word = "untitled"

    return f"{last_name}{year}{title_word}"


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return ""

    # Find max position
    max_pos = 0
    for positions in inverted_index.values():
        if positions:
            max_pos = max(max_pos, max(positions))

    # Reconstruct
    words = [""] * (max_pos + 1)
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word

    abstract = " ".join(words)
    # Truncate if too long
    if len(abstract) > 1000:
        abstract = abstract[:997] + "..."
    return abstract


def _get_entry_type(work: dict[str, Any]) -> str:
    """Determine BibTeX entry type from work type."""
    work_type = work.get("type", "")
    type_mapping = {
        "journal-article": "article",
        "article": "article",
        "proceedings-article": "inproceedings",
        "book": "book",
        "book-chapter": "incollection",
        "dissertation": "phdthesis",
        "dataset": "misc",
        "preprint": "unpublished",
        "report": "techreport",
    }
    return type_mapping.get(work_type, "misc")


def format_bibtex(work: dict[str, Any]) -> str:
    """Format a single work as BibTeX."""
    entry_type = _get_entry_type(work)
    citation_key = _generate_citation_key(work)

    fields: list[tuple[str, str]] = []

    # Title
    title = work.get("title", "")
    if title:
        fields.append(("title", f"{{{_escape_latex(title)}}}"))

    # Authors
    authorships = work.get("authorships", [])
    if authorships:
        authors = []
        for authorship in authorships:
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(_escape_latex(name))
        if authors:
            fields.append(("author", "{" + " and ".join(authors) + "}"))

    # Year
    year = work.get("publication_year")
    if year:
        fields.append(("year", str(year)))

    # Journal/Booktitle/Publisher
    primary_location = work.get("primary_location", {}) or {}
    source = primary_location.get("source", {}) or {}
    source_name = source.get("display_name", "")

    if source_name:
        if entry_type == "article":
            fields.append(("journal", f"{{{_escape_latex(source_name)}}}"))
        elif entry_type in ("inproceedings", "incollection"):
            fields.append(("booktitle", f"{{{_escape_latex(source_name)}}}"))
        else:
            fields.append(("publisher", f"{{{_escape_latex(source_name)}}}"))

    # Volume, Issue, Pages from biblio
    biblio = work.get("biblio", {}) or {}
    if biblio.get("volume"):
        fields.append(("volume", str(biblio["volume"])))
    if biblio.get("issue"):
        fields.append(("number", str(biblio["issue"])))
    if biblio.get("first_page"):
        pages = biblio["first_page"]
        if biblio.get("last_page"):
            pages += f"--{biblio['last_page']}"
        fields.append(("pages", pages))

    # DOI
    doi = work.get("doi")
    if doi:
        # Clean up DOI URL
        doi_clean = doi.replace("https://doi.org/", "")
        fields.append(("doi", doi_clean))

    # URL (OpenAlex URL as fallback)
    work_id = work.get("id", "")
    if work_id:
        fields.append(("url", work_id))

    # Abstract
    abstract_index = work.get("abstract_inverted_index")
    abstract = _reconstruct_abstract(abstract_index)
    if abstract:
        fields.append(("abstract", f"{{{_escape_latex(abstract)}}}"))

    # Build BibTeX entry
    lines = [f"@{entry_type}{{{citation_key},"]
    for i, (key, value) in enumerate(fields):
        comma = "," if i < len(fields) - 1 else ""
        lines.append(f"  {key} = {value}{comma}")
    lines.append("}")

    return "\n".join(lines)


def format_works_bibtex(works: list[dict[str, Any]]) -> str:
    """Format multiple works as BibTeX entries."""
    entries = [format_bibtex(work) for work in works]
    return "\n\n".join(entries)
