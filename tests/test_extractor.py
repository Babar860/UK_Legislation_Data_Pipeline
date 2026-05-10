"""
Unit tests for the Extractor module.

Tests field extraction, None fallback, error handling, and determinism.
"""

import json
import pytest

from legislation_pipeline.extractor import extract, ParseError, ExtractionError
from legislation_pipeline.models import LegislationRecord
from tests.fixtures import MINIMAL_CLML, EMPTY_CLML, MALFORMED_XML


# ---------------------------------------------------------------------------
# Happy path — full extraction from MINIMAL_CLML
# ---------------------------------------------------------------------------

class TestExtractMinimal:
    def setup_method(self):
        self.record = extract(MINIMAL_CLML, source="test-fixture")

    def test_title(self):
        assert self.record.title == "Media Act 2024"

    def test_type(self):
        assert self.record.type == "ukpga"

    def test_year(self):
        assert self.record.year == 2024

    def test_number(self):
        assert self.record.number == 15

    def test_status(self):
        assert self.record.status == "revised"

    def test_isbn(self):
        assert self.record.isbn == "9780105702658"

    def test_provisions(self):
        assert self.record.provisions == 382

    def test_extent(self):
        assert self.record.extent == "E+W+S+N.I."

    def test_enactment_date(self):
        assert self.record.enactment_date == "2024-05-24"

    def test_last_modified(self):
        assert self.record.last_modified == "2026-01-16"

    def test_valid_from(self):
        assert self.record.valid_from == "2026-01-01"

    def test_uri(self):
        assert self.record.uri == "http://www.legislation.gov.uk/ukpga/2024/15"

    def test_id_uri(self):
        assert self.record.id_uri == "http://www.legislation.gov.uk/id/ukpga/2024/15"

    def test_xml_url(self):
        assert self.record.xml_url == "http://www.legislation.gov.uk/ukpga/2024/15/data.xml"

    def test_pdf_url(self):
        assert self.record.pdf_url == "http://www.legislation.gov.uk/ukpga/2024/15/pdfs/ukpga_20240015_en.pdf"

    def test_formats_not_empty(self):
        assert len(self.record.formats) >= 1

    def test_formats_have_type_and_url(self):
        for fmt in self.record.formats:
            assert fmt.type
            assert fmt.url

    def test_structure_introduction(self):
        assert self.record.structure.introduction == "http://www.legislation.gov.uk/ukpga/2024/15/introduction"

    def test_structure_body(self):
        assert self.record.structure.body == "http://www.legislation.gov.uk/ukpga/2024/15/body"

    def test_structure_schedules(self):
        assert self.record.structure.schedules == "http://www.legislation.gov.uk/ukpga/2024/15/schedules"

    def test_structure_contents(self):
        assert self.record.structure.contents == "http://www.legislation.gov.uk/ukpga/2024/15/contents"

    def test_versions_not_empty(self):
        assert len(self.record.versions) >= 1

    def test_versions_have_date_and_url(self):
        for v in self.record.versions:
            assert v.date
            assert v.url

    def test_version_count_matches_list(self):
        assert self.record.version_count == len(self.record.versions)

    def test_unapplied_effects_not_empty(self):
        assert len(self.record.unapplied_effects) >= 1

    def test_unapplied_effect_fields(self):
        effect = self.record.unapplied_effects[0]
        assert effect.affecting_legislation is not None
        assert effect.effect_type is not None


# ---------------------------------------------------------------------------
# Empty / minimal document — None fallback
# ---------------------------------------------------------------------------

class TestExtractEmpty:
    def setup_method(self):
        self.record = extract(EMPTY_CLML, source="empty-fixture")

    def test_title_is_none(self):
        assert self.record.title is None

    def test_year_is_none(self):
        assert self.record.year is None

    def test_number_is_none(self):
        assert self.record.number is None

    def test_isbn_is_none(self):
        assert self.record.isbn is None

    def test_formats_is_empty_list(self):
        assert self.record.formats == []

    def test_versions_is_empty_list(self):
        assert self.record.versions == []

    def test_version_count_is_zero(self):
        assert self.record.version_count == 0

    def test_unapplied_effects_is_empty_list(self):
        assert self.record.unapplied_effects == []

    def test_status_extracted(self):
        # EMPTY_CLML still has DocumentStatus
        assert self.record.status == "enacted"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestExtractErrors:
    def test_malformed_xml_raises_parse_error(self):
        with pytest.raises(ParseError):
            extract(MALFORMED_XML, source="malformed")

    def test_non_legislation_root_raises_extraction_error(self):
        # A completely unrelated root element (no "Legislation" in tag name)
        xml = b'<FooDocument xmlns="http://example.com"/>'
        with pytest.raises(ExtractionError, match="does not appear to be a CLML"):
            extract(xml, source="wrong-root")


# ---------------------------------------------------------------------------
# Serialisation and round-trip
# ---------------------------------------------------------------------------

class TestSerialisation:
    def test_to_json_is_valid_json(self):
        record = extract(MINIMAL_CLML)
        json_str = record.to_json()
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_none_fields_serialised_as_null(self):
        record = extract(EMPTY_CLML)
        json_str = record.to_json()
        parsed = json.loads(json_str)
        assert parsed["title"] is None
        assert parsed["year"] is None

    def test_round_trip(self):
        record = extract(MINIMAL_CLML)
        json_str = record.to_json()
        parsed = json.loads(json_str)
        restored = LegislationRecord.from_dict(parsed)
        assert restored.title == record.title
        assert restored.year == record.year
        assert restored.number == record.number
        assert restored.enactment_date == record.enactment_date
        assert restored.version_count == record.version_count
        assert len(restored.versions) == len(record.versions)
        assert len(restored.formats) == len(record.formats)
        assert len(restored.unapplied_effects) == len(record.unapplied_effects)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_produces_identical_output(self):
        json1 = extract(MINIMAL_CLML).to_json()
        json2 = extract(MINIMAL_CLML).to_json()
        assert json1 == json2

    def test_list_fields_are_sorted(self):
        record = extract(MINIMAL_CLML)
        json_str = record.to_json()
        parsed = json.loads(json_str)

        formats = parsed["formats"]
        if len(formats) > 1:
            keys = [(f["type"], f["url"]) for f in formats]
            assert keys == sorted(keys)

        versions = parsed["versions"]
        if len(versions) > 1:
            keys = [(v["date"], v["url"]) for v in versions]
            assert keys == sorted(keys)
