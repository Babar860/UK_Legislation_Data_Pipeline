"""
Fetcher module for the UK Legislation Pipeline.

Responsible for:
- Validating that a URL belongs to legislation.gov.uk
- Deriving the XML endpoint from a legislation URL
- Performing the HTTP GET request and returning raw XML bytes
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

import requests
from requests.exceptions import ConnectionError, Timeout, RequestException


# Allowed hostnames for legislation.gov.uk
_ALLOWED_HOSTS = {"legislation.gov.uk", "www.legislation.gov.uk"}

# Default request timeout in seconds
DEFAULT_TIMEOUT = 30


class FetchError(Exception):
    """Raised when the Fetcher cannot retrieve the XML document."""


def _validate_url(url: str) -> None:
    """
    Raise FetchError if the URL is not a valid legislation.gov.uk address.

    Checks:
    - URL has a scheme (http or https)
    - Hostname is legislation.gov.uk or www.legislation.gov.uk
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise FetchError(
            f"Invalid URL '{url}': missing scheme or host. "
            "Expected a full URL such as https://www.legislation.gov.uk/ukpga/2024/15"
        )
    if parsed.hostname not in _ALLOWED_HOSTS:
        raise FetchError(
            f"Invalid URL '{url}': hostname '{parsed.hostname}' is not "
            "legislation.gov.uk or www.legislation.gov.uk"
        )


def _derive_xml_endpoint(url: str) -> str:
    """
    Derive the XML endpoint from a legislation URL.

    Strips query string, fragment, and trailing slash from the path,
    then appends /data.xml.

    Examples:
        https://www.legislation.gov.uk/ukpga/2024/15
            -> https://www.legislation.gov.uk/ukpga/2024/15/data.xml
        https://www.legislation.gov.uk/ukpga/2024/15/
            -> https://www.legislation.gov.uk/ukpga/2024/15/data.xml
        https://www.legislation.gov.uk/ukpga/2024/15?view=plain#section-1
            -> https://www.legislation.gov.uk/ukpga/2024/15/data.xml
    """
    parsed = urlparse(url)
    # Strip trailing slash from path
    clean_path = parsed.path.rstrip("/")
    # Reconstruct without query string or fragment
    clean_url = urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))
    return clean_url + "/data.xml"


def fetch_xml(url: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    """
    Fetch the CLML XML document for the given legislation URL.

    Args:
        url:     A legislation.gov.uk URL (e.g. https://www.legislation.gov.uk/ukpga/2024/15).
        timeout: HTTP request timeout in seconds (default: 30).

    Returns:
        Raw XML response body as bytes.

    Raises:
        FetchError: If the URL is invalid, the request fails, or the response
                    is not a 200 OK with an XML content type.
    """
    _validate_url(url)
    xml_endpoint = _derive_xml_endpoint(url)

    try:
        response = requests.get(xml_endpoint, timeout=timeout)
    except Timeout:
        raise FetchError(
            f"Request to '{xml_endpoint}' timed out after {timeout} seconds."
        )
    except ConnectionError as exc:
        raise FetchError(
            f"Connection error while fetching '{xml_endpoint}': {exc}"
        )
    except RequestException as exc:
        raise FetchError(
            f"Network error while fetching '{xml_endpoint}': {exc}"
        )

    if response.status_code != 200:
        raise FetchError(
            f"HTTP {response.status_code} received for '{xml_endpoint}'. "
            "Expected 200 OK."
        )

    content_type = response.headers.get("Content-Type", "")
    if "xml" not in content_type.lower():
        raise FetchError(
            f"Unexpected Content-Type '{content_type}' for '{xml_endpoint}'. "
            "Expected an XML response."
        )

    return response.content
