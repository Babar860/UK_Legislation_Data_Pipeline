"""
Data models for the UK Legislation Pipeline.

All extracted fields are represented as a typed Python dataclass.
None is used for any field that is absent in the source document.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class FormatLink:
    """An alternative format available for a piece of legislation."""
    type: str
    url: str


@dataclass
class VersionEntry:
    """A dated snapshot of a piece of legislation."""
    date: str   # ISO 8601 date string, or "enacted"
    url: str    # Absolute URL to that version


@dataclass
class UnappliedEffect:
    """A legislative change recorded but not yet applied to the text."""
    affecting_legislation: Optional[str]
    effect_type: Optional[str]
    affected_provision: Optional[str]
    affecting_provision: Optional[str]
    condition: Optional[str]
    last_modified: Optional[str]  # ISO 8601 date string


@dataclass
class DocumentStructure:
    """Navigation links to the major structural sections of the document."""
    introduction: Optional[str] = None
    body: Optional[str] = None
    schedules: Optional[str] = None
    contents: Optional[str] = None


@dataclass
class LegislationRecord:
    """
    Complete structured record for a single piece of UK legislation.

    All fields map directly to data present in the CLML XML document.
    No inference or enrichment is performed.
    """

    # Core metadata
    title: Optional[str] = None
    type: Optional[str] = None
    year: Optional[int] = None
    number: Optional[int] = None
    status: Optional[str] = None
    isbn: Optional[str] = None
    provisions: Optional[int] = None
    extent: Optional[str] = None

    # Dates
    enactment_date: Optional[str] = None
    last_modified: Optional[str] = None
    valid_from: Optional[str] = None

    # Identifiers and URIs
    uri: Optional[str] = None
    id_uri: Optional[str] = None
    xml_url: Optional[str] = None
    pdf_url: Optional[str] = None

    # Available formats
    formats: List[FormatLink] = field(default_factory=list)

    # Document structure
    structure: DocumentStructure = field(default_factory=DocumentStructure)

    # Version history
    versions: List[VersionEntry] = field(default_factory=list)
    version_count: int = 0

    # Unapplied effects
    unapplied_effects: List[UnappliedEffect] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Serialisation                                                        #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Return a plain dict representation suitable for JSON serialisation."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """
        Serialise the record to a JSON string.

        - None fields are serialised as JSON null.
        - Date fields are already stored as ISO 8601 strings.
        - List fields are sorted in ascending lexicographic order by their
          primary string identifier before serialisation (determinism).
        """
        d = self.to_dict()

        # Sort list fields by primary string identifier
        d["formats"] = sorted(d["formats"], key=lambda x: (x.get("type") or "", x.get("url") or ""))
        d["versions"] = sorted(d["versions"], key=lambda x: (x.get("date") or "", x.get("url") or ""))
        d["unapplied_effects"] = sorted(
            d["unapplied_effects"],
            key=lambda x: (x.get("affecting_legislation") or "", x.get("effect_type") or ""),
        )

        return json.dumps(d, indent=indent, ensure_ascii=False)

    def to_csv(self) -> str:
        """
        Serialise the record to a CSV string.

        Scalar fields occupy one row each (field, value).
        List fields (formats, versions, unapplied_effects) are serialised
        as separate sections with their own headers.
        """
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        # --- Scalar fields ---
        writer.writerow(["field", "value"])
        scalar_fields = [
            "title", "type", "year", "number", "status", "isbn",
            "provisions", "extent", "enactment_date", "last_modified",
            "valid_from", "uri", "id_uri", "xml_url", "pdf_url",
            "version_count",
        ]
        for f in scalar_fields:
            writer.writerow([f, getattr(self, f)])

        # Structure sub-fields
        for sub in ("introduction", "body", "schedules", "contents"):
            writer.writerow([f"structure.{sub}", getattr(self.structure, sub)])

        # --- Formats ---
        writer.writerow([])
        writer.writerow(["formats.type", "formats.url"])
        for fmt in sorted(self.formats, key=lambda x: (x.type, x.url)):
            writer.writerow([fmt.type, fmt.url])

        # --- Versions ---
        writer.writerow([])
        writer.writerow(["versions.date", "versions.url"])
        for v in sorted(self.versions, key=lambda x: (x.date, x.url)):
            writer.writerow([v.date, v.url])

        # --- Unapplied effects ---
        writer.writerow([])
        writer.writerow([
            "effects.affecting_legislation", "effects.effect_type",
            "effects.affected_provision", "effects.affecting_provision",
            "effects.condition", "effects.last_modified",
        ])
        for e in sorted(
            self.unapplied_effects,
            key=lambda x: (x.affecting_legislation or "", x.effect_type or ""),
        ):
            writer.writerow([
                e.affecting_legislation, e.effect_type,
                e.affected_provision, e.affecting_provision,
                e.condition, e.last_modified,
            ])

        return output.getvalue()

    @classmethod
    def from_dict(cls, data: dict) -> "LegislationRecord":
        """Deserialise a record from a plain dict (e.g. parsed from JSON)."""
        formats = [FormatLink(**f) for f in data.get("formats", [])]
        versions = [VersionEntry(**v) for v in data.get("versions", [])]
        effects = [UnappliedEffect(**e) for e in data.get("unapplied_effects", [])]
        structure_data = data.get("structure", {})
        structure = DocumentStructure(**structure_data) if structure_data else DocumentStructure()

        return cls(
            title=data.get("title"),
            type=data.get("type"),
            year=data.get("year"),
            number=data.get("number"),
            status=data.get("status"),
            isbn=data.get("isbn"),
            provisions=data.get("provisions"),
            extent=data.get("extent"),
            enactment_date=data.get("enactment_date"),
            last_modified=data.get("last_modified"),
            valid_from=data.get("valid_from"),
            uri=data.get("uri"),
            id_uri=data.get("id_uri"),
            xml_url=data.get("xml_url"),
            pdf_url=data.get("pdf_url"),
            formats=formats,
            structure=structure,
            versions=versions,
            version_count=data.get("version_count", 0),
            unapplied_effects=effects,
        )
