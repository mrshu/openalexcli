# openalexcli

A CLI for [OpenAlex API](https://openalex.org/) - designed for humans and AI agents.

## Installation

```bash
pip install openalexcli
```

Or with uv:

```bash
uv pip install openalexcli
```

Or run directly without installing:

```bash
uvx openalexcli search "machine learning"
```

For development:

```bash
pip install -e .
```

## Usage

### Search for works

```bash
# Basic search
openalexcli search "machine learning"

# With filters
openalexcli search "transformers" --from-date 2020-01-01 --min-citations 100

# Open access only
openalexcli search "climate change" --open-access

# Output as JSON (auto-detected when piped)
openalexcli search "neural networks" --json

# Output as BibTeX
openalexcli search "attention mechanism" --bibtex

# Group by field (aggregated statistics)
openalexcli search "CRISPR" --group-by publication_year

# Use raw OpenAlex filter syntax
openalexcli search "deep learning" --filter "type:article,is_oa:true"
```

### Get work details

```bash
# By OpenAlex ID
openalexcli work W2741809807

# By DOI
openalexcli work "10.1038/nature12373"

# Multiple works
openalexcli work W2741809807 W2100837269

# Export as BibTeX
openalexcli bibtex W2741809807 W2100837269
```

### Citations and references

```bash
# Get works that cite a paper
openalexcli citations W2741809807

# Get works cited by a paper
openalexcli references W2741809807
```

### Author commands

```bash
# Get author by ID or ORCID
openalexcli author get A5023888391
openalexcli author get "0000-0002-1825-0097"

# Search authors
openalexcli author search "Yann LeCun"

# Get author's works
openalexcli author works A5023888391 --from-date 2020-01-01

# Group author's works by year
openalexcli author works A5023888391 --group-by publication_year
```

### Institution commands

```bash
# Get institution by ID or ROR
openalexcli institution get I136199984
openalexcli institution get "ror:03vek6s52"

# Search institutions
openalexcli institution search "MIT"

# Get works from an institution
openalexcli institution works I136199984 --from-date 2023-01-01
```

### Source (journal) commands

```bash
# Get source by ID or ISSN
openalexcli source get S137773608
openalexcli source get "0028-0836"

# Search sources
openalexcli source search "Nature"

# Get works from a source
openalexcli source works S137773608 --from-date 2024-01-01
```

## Output Formats

The CLI automatically selects the best output format:

- **Terminal**: Human-readable tables (using Rich)
- **Piped output**: Compact JSON for machine consumption
- **--json**: Force JSON output
- **--bibtex**: BibTeX format (for works/publications only)

## Polite Pool

OpenAlex provides higher rate limits when you identify yourself with an email:

```bash
# Per command
openalexcli search "query" --email your@email.com

# Or set environment variable
export OPENALEX_EMAIL="your@email.com"
openalexcli search "query"
```

## Filter Syntax

Use `--filter` to pass raw OpenAlex filter expressions:

```bash
# Multiple filters (AND)
openalexcli search "AI" --filter "type:article,cited_by_count:>100"

# OR within a filter
openalexcli search "AI" --filter "publication_year:2023|2024"

# Negation
openalexcli search "AI" --filter "type:!book"
```

See [OpenAlex filter documentation](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/filter-entity-lists) for all options.

## Group By

Get aggregated statistics instead of individual results:

```bash
# Works by type
openalexcli search "machine learning" --group-by type

# Works by year
openalexcli search "quantum computing" --group-by publication_year

# Works by institution
openalexcli search "CRISPR" --group-by authorships.institutions.id

# Author's works by open access status
openalexcli author works A5023888391 --group-by open_access.is_oa
```

## Releasing

Releases are published automatically to PyPI when a version tag is pushed:

```bash
git tag v0.x.x
git push origin v0.x.x
```

## License

MIT
