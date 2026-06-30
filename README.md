# UK Legislation Data Pipeline

A Python data pipeline that fetches UK legislation from [legislation.gov.uk](https://www.legislation.gov.uk), parses the Crown Legislation Markup Language (CLML) XML format, and extracts all structured fields into a clean, deterministic JSON output.

---

## Research Motivation

Legal AI and retrieval-augmented generation systems need reliable, structured, and reproducible legal corpora. This project explores the data engineering foundation required before downstream NLP or RAG systems can reason over legislation with traceable source fields.

## Research Problem

How can large-scale legislative text be collected and transformed into deterministic structured records that preserve legal metadata, document structure, version links, and retrieval-ready fields?

## Objectives

- Fetch legislation from official `legislation.gov.uk` sources.
- Parse CLML XML into stable structured JSON records.
- Preserve legal metadata, document links, versions, formats, and pending effects.
- Keep extraction deterministic for reproducible NLP and RAG experiments.
- Provide tests that validate extraction, serialization, CLI behavior, and error handling.

## Project Contribution

This project contributes the data preparation layer required before legal NLP or RAG research can be reliable. It converts official legislation sources into structured records with metadata, links, versions, formats, and document structure preserved for downstream retrieval and analysis.

## Research Relevance

The pipeline is relevant to research on legal NLP, retrieval-augmented generation, corpus construction, and trustworthy information access. Its main research value is reproducibility: outputs are deterministic, schema-like, and suitable for evaluating retrieval strategies over legal documents.

## System Architecture

The pipeline separates URL validation and fetching, CLML XML extraction, typed record modeling, JSON serialization, and CLI orchestration. This layered structure makes it easier to replace or extend components for batch collection, retrieval indexing, or downstream legal NLP experiments.

## Experimental Setup

- Real legislation URLs are fetched through the CLI and converted into JSON.
- Fixture-based tests cover CLML parsing, field extraction, serialization, and round-trip behavior.
- Deterministic sorting and null handling are used to make outputs stable across runs.
- Example output supports manual inspection and downstream retrieval pipeline testing.

## Future Research

- Add batch processing for large-scale legal corpus collection.
- Build RAG-ready chunking and metadata indexing over extracted legislation.
- Compare retrieval performance across CLML structure-aware and plain-text chunking strategies.
- Add version-diff analysis for studying legal change over time.
- Evaluate question-answering quality over structured legislation records.

## Citation

```bibtex
@software{saeed2026uklegislationpipeline,
  author = {Saeed, Babar},
  title = {UK Legislation Data Pipeline},
  year = {2026},
  url = {https://github.com/Babar860/UK_Legislation_Data_Pipeline}
}
```

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run against any legislation URL
python extract.py https://www.legislation.gov.uk/ukpga/2024/15

# Save output to a file
python extract.py https://www.legislation.gov.uk/ukpga/2024/15 --output output.json
```

---

## Project Structure

```
UK_Legislation_Data_Pipeline/
├── extract.py                      # CLI entry point
├── requirements.txt
├── example_output.json             # Example output for Media Act 2024
├── legislation_pipeline/
│   ├── __init__.py
│   ├── models.py                   # LegislationRecord dataclass
│   ├── fetcher.py                  # URL validation + HTTP fetching
│   ├── extractor.py                # CLML XML parsing + field extraction
│   └── pipeline.py                 # Top-level orchestration
└── tests/
    ├── fixtures.py                 # Minimal CLML XML test documents
    ├── test_fetcher.py
    ├── test_extractor.py
    └── test_cli.py
```

---

## CLI Usage

```
python extract.py <url> [--output PATH]

positional arguments:
  url            A legislation.gov.uk URL

optional arguments:
  --output PATH  Write JSON output to this file instead of stdout
  --help         Show this help message and exit
```

**Exit codes:** `0` on success, `1` on any error (invalid URL, HTTP error, parse error, unwritable output path).

---

## Output Fields

| Field | Type | Description |
|---|---|---|
| `title` | string | Legislation title |
| `type` | string | Type code (e.g. `ukpga`, `uksi`) |
| `year` | integer | Year of enactment |
| `number` | integer | Chapter or instrument number |
| `status` | string | Document status (e.g. `revised`, `enacted`) |
| `isbn` | string | ISBN |
| `provisions` | integer | Number of provisions |
| `extent` | string | Geographic extent (e.g. `E+W+S+N.I.`) |
| `enactment_date` | string | ISO 8601 date |
| `last_modified` | string | ISO 8601 date |
| `valid_from` | string | ISO 8601 date |
| `uri` | string | Document URI |
| `id_uri` | string | Identifier URI |
| `xml_url` | string | XML data endpoint |
| `pdf_url` | string | Original PDF URL |
| `formats` | list | Available formats `[{type, url}]` |
| `structure` | object | Navigation links `{introduction, body, schedules, contents}` |
| `versions` | list | Version history `[{date, url}]` |
| `version_count` | integer | Total number of versions |
| `unapplied_effects` | list | Pending legislative changes |

All absent fields are serialised as JSON `null`.

---

## Running Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

68 tests covering fetcher, extractor, serialisation, round-trip, determinism, and CLI.

---

## Approach

The pipeline has three layers:

1. **Fetcher** (`fetcher.py`) — validates the URL is a `legislation.gov.uk` address, derives the `/data.xml` endpoint, performs the HTTP GET, and validates the response.

2. **Extractor** (`extractor.py`) — parses the CLML XML using Python's `xml.etree.ElementTree`. The real CLML format uses `atom:link` elements for navigation, versions, and formats (not `ukm:` elements as the schema documentation might suggest). All fields are extracted directly from the XML with no inference.

3. **Models** (`models.py`) — a `LegislationRecord` dataclass with typed fields, a `to_json()` method that sorts list fields for determinism, and a `from_dict()` method for round-trip deserialisation.

## Trade-offs

- **stdlib XML parser** — `xml.etree.ElementTree` is used rather than `lxml` to keep dependencies minimal. It handles all real CLML documents correctly.
- **Pure extraction** — no field is inferred or enriched. If a value is absent in the XML, it is `None` in the output.
- **`id_uri` vs `uri`** — the live API returns the same value for both `DocumentURI` (on the root element) and `dc:identifier` (in metadata). The `id_uri` field is populated from `dc:identifier` / `IdURI` attribute.

## What I Would Improve With More Time

- Add a `--format csv` flag to export as CSV
- Add version comparison (diff two dated versions)
- Add an async batch mode to process multiple URLs concurrently
- Publish as a proper package with `pyproject.toml`
- Add property-based tests with Hypothesis for the serialisation round-trip
