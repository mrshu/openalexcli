"""Output formatters for OpenAlex CLI."""

from openalexcli.formatters.bibtex import format_bibtex, format_works_bibtex
from openalexcli.formatters.json_fmt import format_error_json, format_json
from openalexcli.formatters.table import (
    format_author_detail,
    format_authors_table,
    format_groups_table,
    format_institution_detail,
    format_institutions_table,
    format_source_detail,
    format_sources_table,
    format_work_detail,
    format_works_table,
)

__all__ = [
    "format_bibtex",
    "format_works_bibtex",
    "format_json",
    "format_error_json",
    "format_works_table",
    "format_authors_table",
    "format_institutions_table",
    "format_sources_table",
    "format_groups_table",
    "format_work_detail",
    "format_author_detail",
    "format_institution_detail",
    "format_source_detail",
]
