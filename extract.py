#!/usr/bin/env python3
"""
CLI entry point for the UK Legislation Data Pipeline.

Usage:
    python extract.py <url> [--output <path>] [--format {json,csv}]
    python extract.py --help

Examples:
    python extract.py https://www.legislation.gov.uk/ukpga/2024/15
    python extract.py https://www.legislation.gov.uk/ukpga/2024/15 --output output.json
    python extract.py https://www.legislation.gov.uk/ukpga/2024/15 --format csv --output output.csv
"""

from __future__ import annotations

import argparse
import logging
import sys
from urllib.parse import urlparse

from legislation_pipeline.pipeline import run
from legislation_pipeline.fetcher import FetchError
from legislation_pipeline.extractor import ParseError, ExtractionError


def _configure_logging() -> None:
    """Configure basic logging to stderr."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def _is_syntactically_valid_url(url: str) -> bool:
    """Return True if the URL has both a scheme and a netloc (host)."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def main(argv: list[str] | None = None) -> int:
    """
    Main CLI entry point.

    Returns:
        0 on success, 1 on any error.
    """
    _configure_logging()

    parser = argparse.ArgumentParser(
        prog="extract.py",
        description=(
            "UK Legislation Data Pipeline — extract structured data from "
            "legislation.gov.uk XML."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python extract.py https://www.legislation.gov.uk/ukpga/2024/15\n"
            "  python extract.py https://www.legislation.gov.uk/ukpga/2024/15 "
            "--output output.json\n"
        ),
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="A legislation.gov.uk URL (e.g. https://www.legislation.gov.uk/ukpga/2024/15)",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        help="Write output to this file instead of stdout.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format: json (default) or csv.",
    )

    args = parser.parse_args(argv)

    # No URL provided
    if not args.url:
        parser.print_usage(sys.stderr)
        print(
            "error: a legislation URL is required.\n"
            "Example: python extract.py https://www.legislation.gov.uk/ukpga/2024/15",
            file=sys.stderr,
        )
        return 1

    # Syntactically malformed URL
    if not _is_syntactically_valid_url(args.url):
        print(
            f"error: '{args.url}' is not a valid URL. "
            "Provide a full URL including scheme and host, e.g. "
            "https://www.legislation.gov.uk/ukpga/2024/15",
            file=sys.stderr,
        )
        return 1

    # Fetch and extract
    try:
        record = run(args.url)
    except FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (ParseError, ExtractionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error: unexpected failure — {exc}", file=sys.stderr)
        return 1

    json_output = record.to_json() if args.format == "json" else record.to_csv()

    # Write to file or stdout
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(json_output)
                fh.write("\n")
        except OSError as exc:
            print(
                f"error: could not write to '{args.output}': {exc}",
                file=sys.stderr,
            )
            return 1
    else:
        print(json_output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
