# openalexq

Command-line interface for the [OpenAlex API](https://openalex.org/).

## Installation

```bash
pip install -e .
```

## Usage

### Search for works

```bash
# Basic search
openalexq search "machine learning"

# With filters
openalexq search "transformers" --from-date 2020-01-01 --min-citations 100

# Open access only
openalexq search "climate change" --open-access

# Output as JSON (auto-detected when piped)
openalexq search "neural networks" --json

# Output as BibTeX
openalexq search "attention mechanism" --bibtex

# Group by field (aggregated statistics)
openalexq search "CRISPR" --group-by publication_year

# Use raw OpenAlex filter syntax
openalexq search "deep learning" --filter "type:article,is_oa:true"
```

### Get work details

```bash
# By OpenAlex ID
openalexq work W2741809807

# By DOI
openalexq work "10.1038/nature12373"

# Multiple works
openalexq work W2741809807 W2100837269

# Export as BibTeX
openalexq bibtex W2741809807 W2100837269
```

### Citations and references

```bash
# Get works that cite a paper
openalexq citations W2741809807

# Get works cited by a paper
openalexq references W2741809807
```

### Author commands

```bash
# Get author by ID or ORCID
openalexq author get A5023888391
openalexq author get "0000-0002-1825-0097"

# Search authors
openalexq author search "Yann LeCun"

# Get author's works
openalexq author works A5023888391 --from-date 2020-01-01

# Group author's works by year
openalexq author works A5023888391 --group-by publication_year
```

### Institution commands

```bash
# Get institution by ID or ROR
openalexq institution get I136199984
openalexq institution get "ror:03vek6s52"

# Search institutions
openalexq institution search "MIT"

# Get works from an institution
openalexq institution works I136199984 --from-date 2023-01-01
```

### Source (journal) commands

```bash
# Get source by ID or ISSN
openalexq source get S137773608
openalexq source get "0028-0836"

# Search sources
openalexq source search "Nature"

# Get works from a source
openalexq source works S137773608 --from-date 2024-01-01
```

## Output Formats

The CLI automatically selects the best output format:

- **Terminal**: Human-readable tables (using Rich)
- **Piped output**: Compact JSON for machine consumption
- **--json**: Force JSON output
- **--bibtex**: BibTeX citations (works only)

## Polite Pool

OpenAlex provides higher rate limits when you identify yourself with an email:

```bash
# Per command
openalexq search "query" --email your@email.com

# Or set environment variable
export OPENALEX_EMAIL="your@email.com"
openalexq search "query"
```

## Filter Syntax

Use `--filter` to pass raw OpenAlex filter expressions:

```bash
# Multiple filters (AND)
openalexq search "AI" --filter "type:article,cited_by_count:>100"

# OR within a filter
openalexq search "AI" --filter "publication_year:2023|2024"

# Negation
openalexq search "AI" --filter "type:!book"
```

See [OpenAlex filter documentation](https://docs.openalex.org/how-to-use-the-api/get-lists-of-entities/filter-entity-lists) for all options.

## Group By

Get aggregated statistics instead of individual results:

```bash
# Works by type
openalexq search "machine learning" --group-by type

# Works by year
openalexq search "quantum computing" --group-by publication_year

# Works by institution
openalexq search "CRISPR" --group-by authorships.institutions.id

# Author's works by open access status
openalexq author works A5023888391 --group-by open_access.is_oa
```

## License

MIT
