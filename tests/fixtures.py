"""
Shared test fixtures — minimal CLML XML documents for unit testing.
"""

MINIMAL_CLML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Legislation xmlns="http://www.legislation.gov.uk/namespaces/legislation"
             DocumentURI="http://www.legislation.gov.uk/ukpga/2024/15"
             IdURI="http://www.legislation.gov.uk/id/ukpga/2024/15"
             NumberOfProvisions="382"
             RestrictExtent="E+W+S+N.I."
             RestrictStartDate="2026-01-01">
  <ukm:Metadata xmlns:dc="http://purl.org/dc/elements/1.1/"
                xmlns:dct="http://purl.org/dc/terms/"
                xmlns:atom="http://www.w3.org/2005/Atom"
                xmlns:ukm="http://www.legislation.gov.uk/namespaces/metadata">
    <dc:identifier>http://www.legislation.gov.uk/id/ukpga/2024/15</dc:identifier>
    <dc:title>Media Act 2024</dc:title>
    <dc:modified>2026-01-16</dc:modified>
    <dct:valid>2026-01-01</dct:valid>

    <atom:link rel="http://www.legislation.gov.uk/def/navigation/introduction"
               href="http://www.legislation.gov.uk/ukpga/2024/15/introduction"/>
    <atom:link rel="http://www.legislation.gov.uk/def/navigation/body"
               href="http://www.legislation.gov.uk/ukpga/2024/15/body"/>
    <atom:link rel="http://www.legislation.gov.uk/def/navigation/schedules"
               href="http://www.legislation.gov.uk/ukpga/2024/15/schedules"/>
    <atom:link rel="http://purl.org/dc/terms/tableOfContents"
               href="http://www.legislation.gov.uk/ukpga/2024/15/contents"/>

    <atom:link rel="alternate" type="application/rdf+xml"
               href="http://www.legislation.gov.uk/ukpga/2024/15/data.rdf" title="RDF/XML"/>
    <atom:link rel="alternate" type="text/csv"
               href="http://www.legislation.gov.uk/ukpga/2024/15/data.csv" title="CSV"/>
    <atom:link rel="alternate" href="http://www.legislation.gov.uk/ukpga/2024/15/pdfs/ukpga_20240015_en.pdf"
               type="application/pdf" title="Original PDF"/>

    <atom:link rel="http://purl.org/dc/terms/hasVersion"
               href="http://www.legislation.gov.uk/ukpga/2024/15/enacted" title="enacted"/>
    <atom:link rel="http://purl.org/dc/terms/hasVersion"
               href="http://www.legislation.gov.uk/ukpga/2024/15/2024-05-24" title="2024-05-24"/>

    <ukm:PrimaryMetadata>
      <ukm:DocumentClassification>
        <ukm:DocumentCategory Value="primary"/>
        <ukm:DocumentMainType Value="UnitedKingdomPublicGeneralAct"/>
        <ukm:DocumentStatus Value="revised"/>
      </ukm:DocumentClassification>
      <ukm:Year Value="2024"/>
      <ukm:Number Value="15"/>
      <ukm:EnactmentDate Date="2024-05-24"/>
      <ukm:ISBN Value="9780105702658"/>
      <ukm:UnappliedEffects>
        <ukm:UnappliedEffect
          AffectingURI="http://www.legislation.gov.uk/id/uksi/2024/858"
          Type="coming into force"
          AffectedProvisions="Sch. 2 para. 12(2)"
          AffectingProvisions="reg. 4(a)"
          RequiresApplied="true"
          Modified="2024-08-22T12:07:58Z"
          Comments="comes into force on the date on which section 299(1) of the 2003 Act comes into force">
          <ukm:AffectedProvisions>
            <ukm:Section>Sch. 2 para. 12(2)</ukm:Section>
          </ukm:AffectedProvisions>
          <ukm:AffectingProvisions>
            <ukm:Section>reg. 4(a)</ukm:Section>
          </ukm:AffectingProvisions>
        </ukm:UnappliedEffect>
      </ukm:UnappliedEffects>
    </ukm:PrimaryMetadata>

    <ukm:Alternatives>
      <ukm:Alternative URI="http://www.legislation.gov.uk/ukpga/2024/15/pdfs/ukpga_20240015_en.pdf"
                        Date="2024-06-05" Size="2296694" Print="true"/>
    </ukm:Alternatives>
  </ukm:Metadata>
</Legislation>
"""

EMPTY_CLML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Legislation xmlns="http://www.legislation.gov.uk/namespaces/legislation"
             DocumentURI="http://www.legislation.gov.uk/ukpga/2020/1">
  <ukm:Metadata xmlns:ukm="http://www.legislation.gov.uk/namespaces/metadata">
    <ukm:PrimaryMetadata>
      <ukm:DocumentClassification>
        <ukm:DocumentStatus Value="enacted"/>
      </ukm:DocumentClassification>
    </ukm:PrimaryMetadata>
  </ukm:Metadata>
</Legislation>
"""

MALFORMED_XML = b"<Legislation><ukm:Metadata></Legislation>"
