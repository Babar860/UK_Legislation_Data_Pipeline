"""
Pipeline module — top-level orchestration.

Combines the Fetcher and Extractor into a single callable that accepts
a legislation URL and returns a populated LegislationRecord.
"""

from __future__ import annotations

from .fetcher import fetch_xml, DEFAULT_TIMEOUT
from .extractor import extract
from .models import LegislationRecord


def run(url: str, timeout: int = DEFAULT_TIMEOUT) -> LegislationRecord:
    """
    Fetch and extract a piece of UK legislation.

    Args:
        url:     A legislation.gov.uk URL.
        timeout: HTTP request timeout in seconds (default: 30).

    Returns:
        A populated LegislationRecord.

    Raises:
        FetchError:      If the URL is invalid or the HTTP request fails.
        ParseError:      If the XML is not well-formed.
        ExtractionError: If the document structure is unrecognisable.
    """
    xml_bytes = fetch_xml(url, timeout=timeout)
    return extract(xml_bytes, source=url)
