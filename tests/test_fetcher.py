"""
Unit tests for the Fetcher module.

Tests URL validation, XML endpoint derivation, and HTTP error handling.
"""

import pytest
from unittest.mock import patch, MagicMock

from legislation_pipeline.fetcher import (
    fetch_xml,
    _derive_xml_endpoint,
    _validate_url,
    FetchError,
)


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

class TestValidateUrl:
    def test_valid_www_host(self):
        _validate_url("https://www.legislation.gov.uk/ukpga/2024/15")  # no exception

    def test_valid_bare_host(self):
        _validate_url("https://legislation.gov.uk/ukpga/2024/15")  # no exception

    def test_invalid_host_raises(self):
        with pytest.raises(FetchError, match="not.*legislation.gov.uk"):
            _validate_url("https://example.com/ukpga/2024/15")

    def test_missing_scheme_raises(self):
        with pytest.raises(FetchError, match="missing scheme or host"):
            _validate_url("www.legislation.gov.uk/ukpga/2024/15")

    def test_missing_host_raises(self):
        with pytest.raises(FetchError, match="missing scheme or host"):
            _validate_url("https://")


# ---------------------------------------------------------------------------
# XML endpoint derivation
# ---------------------------------------------------------------------------

class TestDeriveXmlEndpoint:
    def test_plain_url(self):
        result = _derive_xml_endpoint("https://www.legislation.gov.uk/ukpga/2024/15")
        assert result == "https://www.legislation.gov.uk/ukpga/2024/15/data.xml"

    def test_trailing_slash_stripped(self):
        result = _derive_xml_endpoint("https://www.legislation.gov.uk/ukpga/2024/15/")
        assert result == "https://www.legislation.gov.uk/ukpga/2024/15/data.xml"

    def test_query_string_stripped(self):
        result = _derive_xml_endpoint(
            "https://www.legislation.gov.uk/ukpga/2024/15?view=plain"
        )
        assert result == "https://www.legislation.gov.uk/ukpga/2024/15/data.xml"

    def test_fragment_stripped(self):
        result = _derive_xml_endpoint(
            "https://www.legislation.gov.uk/ukpga/2024/15#section-1"
        )
        assert result == "https://www.legislation.gov.uk/ukpga/2024/15/data.xml"

    def test_query_and_fragment_stripped(self):
        result = _derive_xml_endpoint(
            "https://www.legislation.gov.uk/ukpga/2024/15?view=plain#s1"
        )
        assert result == "https://www.legislation.gov.uk/ukpga/2024/15/data.xml"


# ---------------------------------------------------------------------------
# HTTP fetching
# ---------------------------------------------------------------------------

class TestFetchXml:
    def _mock_response(self, status_code=200, content=b"<xml/>", content_type="application/xml"):
        mock_resp = MagicMock()
        mock_resp.status_code = status_code
        mock_resp.content = content
        mock_resp.headers = {"Content-Type": content_type}
        return mock_resp

    def test_successful_fetch(self):
        with patch("legislation_pipeline.fetcher.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(content=b"<xml/>")
            result = fetch_xml("https://www.legislation.gov.uk/ukpga/2024/15")
        assert result == b"<xml/>"

    def test_non_200_raises(self):
        with patch("legislation_pipeline.fetcher.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(status_code=404)
            with pytest.raises(FetchError, match="HTTP 404"):
                fetch_xml("https://www.legislation.gov.uk/ukpga/2024/15")

    def test_non_xml_content_type_raises(self):
        with patch("legislation_pipeline.fetcher.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(content_type="text/html")
            with pytest.raises(FetchError, match="Unexpected Content-Type"):
                fetch_xml("https://www.legislation.gov.uk/ukpga/2024/15")

    def test_timeout_raises(self):
        from requests.exceptions import Timeout
        with patch("legislation_pipeline.fetcher.requests.get", side_effect=Timeout()):
            with pytest.raises(FetchError, match="timed out"):
                fetch_xml("https://www.legislation.gov.uk/ukpga/2024/15")

    def test_connection_error_raises(self):
        from requests.exceptions import ConnectionError
        with patch("legislation_pipeline.fetcher.requests.get", side_effect=ConnectionError()):
            with pytest.raises(FetchError, match="Connection error"):
                fetch_xml("https://www.legislation.gov.uk/ukpga/2024/15")

    def test_invalid_host_raises_before_request(self):
        with patch("legislation_pipeline.fetcher.requests.get") as mock_get:
            with pytest.raises(FetchError, match="not.*legislation.gov.uk"):
                fetch_xml("https://example.com/ukpga/2024/15")
            mock_get.assert_not_called()
