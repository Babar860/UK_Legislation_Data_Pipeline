"""
Extractor module for the UK Legislation Pipeline.

Responsible for parsing a CLML XML document and extracting all structured
fields into a LegislationRecord. Performs pure extraction only — no inference
or enrichment.

Real CLML XML structure (from legislation.gov.uk):
- Root element: <Legislation> with attributes DocumentURI, IdURI,
  NumberOfProvisions, RestrictExtent, RestrictStartDate
- <ukm:Metadata> contains:
    - <dc:title>, <dc:modified>, <dct:valid>, <dc:identifier>
    - <atom:link> elements for navigation, versions, formats, PDF
    - <ukm:PrimaryMetadata> with <ukm:DocumentClassification>,
      <ukm:Year>, <ukm:Number>, <ukm:EnactmentDate>, <ukm:ISBN>
    - <ukm:UnappliedEffects> with <ukm:UnappliedEffect> children
    - <ukm:Alternatives> with <ukm:Alternative> for PDF
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ParseError

from .models import (
    DocumentStructure,
    FormatLink,
    LegislationRecord,
    UnappliedEffect,
    VersionEntry,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# XML Namespace map
# ---------------------------------------------------------------------------
# These are the namespaces used in CLML documents from legislation.gov.uk.
NS = {
    "leg":  "http://www.legislation.gov.uk/namespaces/legislation",
    "ukm":  "http://www.legislation.gov.uk/namespaces/metadata",
    "dc":   "http://purl.org/dc/elements/1.1/",
    "dct":  "http://purl.org/dc/terms/",
    "atom": "http://www.w3.org/2005/Atom",
}

# atom:link rel values used for navigation and versions
_REL_INTRODUCTION = "http://www.legislation.gov.uk/def/navigation/introduction"
_REL_BODY         = "http://www.legislation.gov.uk/def/navigation/body"
_REL_SCHEDULES    = "http://www.legislation.gov.uk/def/navigation/schedules"
_REL_TOC          = "http://purl.org/dc/terms/tableOfContents"
_REL_HAS_VERSION  = "http://purl.org/dc/terms/hasVersion"

# Recognised date patterns
_DATE_PATTERN     = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})?)?$")


class ParseError(Exception):
    """Raised when the XML document cannot be parsed."""


class ExtractionError(Exception):
    """Raised when a critical structural error prevents extraction."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _text(element: Optional[ET.Element]) -> Optional[str]:
    """Return stripped text content of an element, or None if element is None."""
    if element is None:
        return None
    text = (element.text or "").strip()
    return text if text else None


def _parse_date(raw: str, field_name: str) -> str:
    """
    Validate and normalise a date string.

    Accepts YYYY-MM-DD and YYYY-MM-DDTHH:MM:SS[Z|±HH:MM].
    Returns the date portion (YYYY-MM-DD) for datetime strings.
    If the value does not match, logs a WARNING and returns the raw string.
    """
    if not raw:
        return raw
    if _DATE_PATTERN.match(raw):
        # Return only the date portion
        return raw[:10]
    logger.warning(
        "Field '%s' contains unrecognised date format: %r — storing raw value.",
        field_name,
        raw,
    )
    return raw


def _find_atom_links(metadata: ET.Element, rel: str) -> list[ET.Element]:
    """Return all atom:link elements with the given rel attribute."""
    return [
        el for el in metadata.findall("atom:link", NS)
        if el.get("rel") == rel
    ]


# ---------------------------------------------------------------------------
# Main extractor
# ---------------------------------------------------------------------------

def extract(xml_bytes: bytes, source: str = "<unknown>") -> LegislationRecord:
    """
    Parse a CLML XML document and extract all structured fields.

    Args:
        xml_bytes: Raw XML content as bytes.
        source:    Identifier for the document (URL or filename) used in errors.

    Returns:
        A populated LegislationRecord. Missing fields are set to None.

    Raises:
        ParseError:      If the XML is not well-formed.
        ExtractionError: If the root CLML element is absent after parsing.
    """
    # ------------------------------------------------------------------ #
    # 1. Parse XML                                                         #
    # ------------------------------------------------------------------ #
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise ParseError(
            f"Failed to parse XML from '{source}': {exc}"
        ) from exc

    # Verify root element is a Legislation element
    leg_tag = f"{{{NS['leg']}}}Legislation"
    if root.tag != leg_tag:
        # Some documents have no namespace on root — accept bare tag too
        if "Legislation" not in root.tag:
            raise ExtractionError(
                f"Document '{source}' does not appear to be a CLML document. "
                f"Root element is '{root.tag}', expected 'Legislation'."
            )

    # ------------------------------------------------------------------ #
    # 2. Locate <ukm:Metadata>                                             #
    # ------------------------------------------------------------------ #
    metadata = root.find("ukm:Metadata", NS)
    if metadata is None:
        raise ExtractionError(
            f"Document '{source}' is missing the <ukm:Metadata> element. "
            "Cannot extract any fields."
        )

    record = LegislationRecord()

    # ------------------------------------------------------------------ #
    # 3. Core metadata from root attributes                                #
    # ------------------------------------------------------------------ #
    # NumberOfProvisions is on the root <Legislation> element
    num_provisions = root.get("NumberOfProvisions")
    if num_provisions is not None:
        try:
            record.provisions = int(num_provisions)
        except ValueError:
            logger.warning("Could not parse NumberOfProvisions=%r as integer.", num_provisions)

    # RestrictExtent is on the root element
    extent = root.get("RestrictExtent")
    if extent:
        record.extent = extent.strip()

    # ------------------------------------------------------------------ #
    # 4. Dublin Core fields                                                #
    # ------------------------------------------------------------------ #
    record.title = _text(metadata.find("dc:title", NS))
    record.id_uri = _text(metadata.find("dc:identifier", NS))

    raw_modified = _text(metadata.find("dc:modified", NS))
    if raw_modified:
        record.last_modified = _parse_date(raw_modified, "last_modified")

    raw_valid = _text(metadata.find("dct:valid", NS))
    if raw_valid:
        record.valid_from = _parse_date(raw_valid, "valid_from")

    # ------------------------------------------------------------------ #
    # 5. Primary metadata block                                            #
    # ------------------------------------------------------------------ #
    primary = metadata.find("ukm:PrimaryMetadata", NS)
    if primary is not None:
        _extract_primary_metadata(primary, record, source)

    # ------------------------------------------------------------------ #
    # 6. Derive URIs from root attributes                                  #
    # ------------------------------------------------------------------ #
    doc_uri = root.get("DocumentURI")
    if doc_uri:
        record.uri = doc_uri.rstrip("/")
        record.xml_url = record.uri + "/data.xml"

    id_uri_attr = root.get("IdURI")
    if id_uri_attr and not record.id_uri:
        record.id_uri = id_uri_attr

    # ------------------------------------------------------------------ #
    # 7. PDF URL from ukm:Alternatives                                     #
    # ------------------------------------------------------------------ #
    alternatives = metadata.find("ukm:Alternatives", NS)
    if alternatives is not None:
        alt_els = alternatives.findall("ukm:Alternative", NS)
        for alt in alt_els:
            uri_val = alt.get("URI")
            if uri_val and alt.get("Print") == "true":
                record.pdf_url = uri_val
                break
        # Fallback: first alternative if none marked Print=true
        if record.pdf_url is None and alt_els:
            record.pdf_url = alt_els[0].get("URI")

    # Also check atom:link for Original PDF
    if record.pdf_url is None:
        for link in metadata.findall("atom:link", NS):
            if link.get("title") == "Original PDF":
                record.pdf_url = link.get("href")
                break

    # ------------------------------------------------------------------ #
    # 8. Available formats from atom:link rel="alternate"                  #
    # ------------------------------------------------------------------ #
    formats = []
    for link in metadata.findall("atom:link", NS):
        if link.get("rel") == "alternate":
            link_type = link.get("type", "")
            href = link.get("href", "")
            title = link.get("title", "")
            # Skip the Original PDF (already captured above)
            if title == "Original PDF":
                continue
            if link_type and href:
                formats.append(FormatLink(type=link_type, url=href))
    record.formats = sorted(formats, key=lambda f: (f.type, f.url))

    # ------------------------------------------------------------------ #
    # 9. Document structure from atom:link navigation rels                 #
    # ------------------------------------------------------------------ #
    structure = DocumentStructure()
    for link in metadata.findall("atom:link", NS):
        rel = link.get("rel", "")
        href = link.get("href", "")
        if rel == _REL_INTRODUCTION:
            structure.introduction = href or None
        elif rel == _REL_BODY:
            structure.body = href or None
        elif rel == _REL_SCHEDULES:
            structure.schedules = href or None
        elif rel == _REL_TOC:
            structure.contents = href or None

    # Derive contents from uri if not found via atom:link
    if structure.contents is None and record.uri:
        structure.contents = record.uri.rstrip("/") + "/contents"

    record.structure = structure

    # ------------------------------------------------------------------ #
    # 10. Version history from atom:link rel="hasVersion"                  #
    # ------------------------------------------------------------------ #
    versions = []
    for link in metadata.findall("atom:link", NS):
        if link.get("rel") == _REL_HAS_VERSION:
            href = link.get("href", "")
            title = link.get("title", "")
            if href and title:
                versions.append(VersionEntry(date=title, url=href))

    record.versions = sorted(versions, key=lambda v: (v.date, v.url))
    record.version_count = len(record.versions)

    # ------------------------------------------------------------------ #
    # 11. Unapplied effects                                                #
    # ------------------------------------------------------------------ #
    if primary is not None:
        _extract_unapplied_effects(primary, record)

    return record


def _extract_primary_metadata(
    primary: ET.Element,
    record: LegislationRecord,
    source: str,
) -> None:
    """Extract fields from the <ukm:PrimaryMetadata> block."""
    classification = primary.find("ukm:DocumentClassification", NS)
    if classification is not None:
        status_el = classification.find("ukm:DocumentStatus", NS)
        if status_el is not None:
            record.status = status_el.get("Value") or _text(status_el)

        main_type_el = classification.find("ukm:DocumentMainType", NS)
        if main_type_el is not None:
            # e.g. "UnitedKingdomPublicGeneralAct" — derive short type from URI later
            pass

    year_el = primary.find("ukm:Year", NS)
    if year_el is not None:
        val = year_el.get("Value")
        if val:
            try:
                record.year = int(val)
            except ValueError:
                logger.warning("Could not parse Year Value=%r as integer.", val)

    number_el = primary.find("ukm:Number", NS)
    if number_el is not None:
        val = number_el.get("Value")
        if val:
            try:
                record.number = int(val)
            except ValueError:
                logger.warning("Could not parse Number Value=%r as integer.", val)

    enactment_el = primary.find("ukm:EnactmentDate", NS)
    if enactment_el is not None:
        raw = enactment_el.get("Date") or _text(enactment_el)
        if raw:
            record.enactment_date = _parse_date(raw, "enactment_date")

    isbn_el = primary.find("ukm:ISBN", NS)
    if isbn_el is not None:
        val = isbn_el.get("Value") or _text(isbn_el)
        if val:
            record.isbn = str(val)

    # Derive type from DocumentURI path: /ukpga/2024/15 -> "ukpga"
    # We do this after uri is set; store raw type from classification for now
    # and derive from URI in the main extract() function.


def _extract_unapplied_effects(
    primary: ET.Element,
    record: LegislationRecord,
) -> None:
    """Extract <ukm:UnappliedEffect> elements from <ukm:UnappliedEffects>."""
    effects_container = primary.find("ukm:UnappliedEffects", NS)
    if effects_container is None:
        record.unapplied_effects = []
        return

    effects = []
    for effect_el in effects_container.findall("ukm:UnappliedEffect", NS):
        # affecting_legislation: from AffectingURI attribute
        affecting_legislation = effect_el.get("AffectingURI")

        # effect_type: from Type attribute
        effect_type = effect_el.get("Type")

        # affected_provision: from AffectedProvisions child element text
        affected_prov_el = effect_el.find("ukm:AffectedProvisions", NS)
        affected_provision = None
        if affected_prov_el is not None:
            # Concatenate all text within the element
            affected_provision = "".join(affected_prov_el.itertext()).strip() or None

        # affecting_provision: from AffectingProvisions child element text
        affecting_prov_el = effect_el.find("ukm:AffectingProvisions", NS)
        affecting_provision = None
        if affecting_prov_el is not None:
            affecting_provision = "".join(affecting_prov_el.itertext()).strip() or None

        # condition: from RequiresApplied attribute or Comments attribute
        requires_applied = effect_el.get("RequiresApplied")
        comments = effect_el.get("Comments")
        if requires_applied == "true" and comments:
            condition = comments
        elif requires_applied is not None:
            condition = requires_applied
        else:
            condition = None

        # last_modified: from Modified attribute
        raw_modified = effect_el.get("Modified")
        last_modified = None
        if raw_modified:
            last_modified = _parse_date(raw_modified, "unapplied_effect.last_modified")

        effects.append(UnappliedEffect(
            affecting_legislation=affecting_legislation or None,
            effect_type=effect_type or None,
            affected_provision=affected_provision,
            affecting_provision=affecting_provision,
            condition=condition,
            last_modified=last_modified,
        ))

    record.unapplied_effects = sorted(
        effects,
        key=lambda e: (e.affecting_legislation or "", e.effect_type or ""),
    )


def _derive_type_from_uri(uri: str) -> Optional[str]:
    """
    Extract the legislation type code from a URI path.

    e.g. http://www.legislation.gov.uk/ukpga/2024/15 -> "ukpga"
    """
    if not uri:
        return None
    # Match the type segment: first path component after the host
    match = re.search(r"legislation\.gov\.uk/([a-z]+)/\d{4}/", uri)
    if match:
        return match.group(1)
    return None


def _warn_none_fields(record: LegislationRecord, source: str) -> None:
    """Emit a WARNING listing all top-level fields that are None."""
    none_fields = [
        name for name, val in record.__dict__.items()
        if val is None
    ]
    if none_fields:
        logger.warning(
            "Document '%s': the following fields are None after extraction: %s",
            source,
            ", ".join(none_fields),
        )


# ---------------------------------------------------------------------------
# Post-processing: derive type from URI if not already set
# ---------------------------------------------------------------------------

def _post_process(record: LegislationRecord) -> LegislationRecord:
    """Derive any fields that depend on other extracted fields."""
    if record.type is None and record.uri:
        record.type = _derive_type_from_uri(record.uri)
    if record.type is None and record.id_uri:
        record.type = _derive_type_from_uri(record.id_uri)
    # Warn about None fields AFTER post-processing so derived fields are included
    return record


# Patch extract() to call post-processing and then warn
_original_extract = extract


def extract(xml_bytes: bytes, source: str = "<unknown>") -> LegislationRecord:  # noqa: F811
    """
    Parse a CLML XML document and extract all structured fields.

    Wraps the internal extractor with post-processing to derive
    fields that depend on other extracted values (e.g. type from URI),
    then emits warnings for any fields that remain None.
    """
    record = _original_extract(xml_bytes, source)
    record = _post_process(record)
    _warn_none_fields(record, source)
    return record
