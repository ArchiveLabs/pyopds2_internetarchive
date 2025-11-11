"""
Acquisition link builder module.

This module provides classes used to generate acquisition links for OPDS
publications coming from Internet Archive metadata. It supports both free
public domain publications and borrowable LCP protected books.
"""
from dataclasses import dataclass
from collections import namedtuple
from typing import Union

from pyopds2 import Link

from opds.availability import check_availability, AvailableInfo


@dataclass
class Formats:
    """
    The class contains information about different types of licenses and book formats
    """
    license_lcp: str = "lcp"
    indirect_acquisition_lcp_type: str = "application/vnd.readium.lcp.license.v1.0+json"
    book_type_pdf: str = "application/pdf"
    book_type_epub: str = "application/epub+zip"
    book_type_audiobook: str = "application/audiobook+lcp"
    book_type_rpf: str = "application/pdf+lcp"
    check_format = {
        "pdf": (book_type_pdf, "lcp_pdf"),
        "epub": (book_type_epub, "lcp_epub"),
        "lcpau": (book_type_audiobook, "lcp_audiobook"),
        "lcpdf": (book_type_rpf, "lcp_pdf")
    }


class AcquisitionLinks:
    """
    Generate OPDS acquisition links for either free or borrowable publications.

    All link outputs conform to OPDS2 link object specification.
    """
    STATIC_TITLE = "Internet Archive"
    ARCHIVE_SELF_URL = "https://archive.org/services/loans/loan/?action=webpub"
    ARCHIVE_BORROWABLE_URL = "https://archive.org/services/loans/loan/?opds=1"

    FREE_EPUB_FORMAT = "Remediated EPUB"
    AcquisitionInfo = namedtuple(
        "AcquisitionInfo", [
            "book_format", "book_type", "indirect_acquisition_type", "filename_base"])

    def __init__(self, access_restricted_item: str,
                 identifier: str, mediatype: str,
                 book_format: list[str],
                 external_identifier: str,
                 available_info: AvailableInfo):
        """
        Initialize acquisition link generator.

        Args:
            access_restricted_item: Indicates if item is borrow-only.
            identifier: Archive.org item identifier.
            mediatype: Item media type (texts / audio).
            book_format: List of existing formats found in metadata.
            external_identifier: Raw external acquisition mapping string(s).
            available_info: Archive.org item field data is used to calculate availability.
        """
        self.access_restricted_item = access_restricted_item
        self.identifier = identifier
        self.mediatype = mediatype
        self.format = book_format
        self.available_info = available_info
        self.external_identifier = external_identifier

    def create_acquisition_links(self) -> list[Link]:
        """
        Build acquisition link set based on item availability type.

        Returns:
            List of OPDS2 Link objects describing acquisition.
        """
        links: list[Link] = []

        # For free books
        if self.access_restricted_item is None:
            self_link = f"{self.ARCHIVE_SELF_URL}&identifier={self.identifier}"
            links += [
                Link(
                    rel="self",
                    type="application/opds-publication+json",
                    href=self_link,
                    title=self.STATIC_TITLE
                )
            ]
            return links + self._acquisition_links_for_free_books(self.mediatype,
                                                                  self.identifier,
                                                                  self.format)

        # For borrowable book
        self_link = f"{self.ARCHIVE_SELF_URL}&identifier={self.identifier}&opds=1"
        links += [
            Link(
                rel="self",
                type="application/opds-publication+json",
                href=self_link,
                title=self.STATIC_TITLE
            )
        ]
        return links + \
            self._acquisition_links_for_borrow_books(self.available_info)

    def _acquisition_links_for_free_books(
            self,
            mediatype: str,
            identifier: str,
            book_format: list[str]) -> list[Link]:
        """
        Build free + public domain OPDS acquisition links.

        Args:
            mediatype: Item media type.
            identifier: Item identifier.
            book_format: Available book formats.

        Returns:
            List of Link objects for open-access.
        """
        links: list[Link] = []
        if mediatype == "texts":
            # Always add PDF link for texts
            links += [
                Link(
                    rel="http://opds-spec.org/acquisition/open-access",
                    type="application/pdf",
                    href=f"/book/{identifier}?glob_pattern=*pdf",
                    title=self.STATIC_TITLE,
                    properties={"availability": {"state": "available"}}
                )
            ]
            # Add EPUB link if 'Remediated EPUB' is available
            if self.FREE_EPUB_FORMAT in book_format:
                links += [
                    Link(
                        rel="http://opds-spec.org/acquisition/open-access",
                        type="application/epub+zip",
                        title=self.STATIC_TITLE,
                        href=f"/book/{identifier}?glob_pattern=*epub",
                        properties={"availability": {"state": "available"}}
                    )
                ]
        elif mediatype == "audio":
            links += [
                Link(
                    rel="http://opds-spec.org/acquisition/open-access",
                    type="application/audiobook+json",
                    title=self.STATIC_TITLE,
                    href=f"/audiobooks/{identifier}",
                    properties={"availability": {"state": "available"}}
                )
            ]

        return links

    def _acquisition_links_for_borrow_books(
            self, available_info: AvailableInfo) -> list[Link]:
        """
        Build acquisition links for borrowable / LCP protected items.

        Args:
            available_info: Archive.org item field data is used to calculate availability.

        Returns:
            List of OPDS2 Link objects for borrow flow.
        """
        availability = check_availability(available_info)

        if any(
            (availability.get("state") == "unavailable",
             not self.external_identifier)):
            return [
                Link(
                    rel="http://opds-spec.org/acquisition/borrow",
                    type="application/opds-publication+json",
                    href="",
                    title=self.STATIC_TITLE,
                    properties={
                        "availability": availability
                    }
                )
            ]
        acquisition_links_info = self._parse_external_identifier()
        borrowable_url = f"{self.ARCHIVE_BORROWABLE_URL}&" \
                         f"identifier={self.identifier}&" \
                         f"action=webpub"
        # filename_base is the same it all objects in the tuple
        acquisition_info_element = next((acquisition_info_element for acquisition_info_element
                                         in acquisition_links_info if acquisition_info_element is not None), None)

        if acquisition_info_element and acquisition_info_element.filename_base != self.identifier:
            borrowable_url += f"&filename_base={acquisition_info_element.filename_base}"

        return [
            Link(
                rel="http://opds-spec.org/acquisition/borrow",
                type="application/opds-publication+json",
                href=borrowable_url,
                title=self.STATIC_TITLE,
                availability=availability,
                properties={
                    "indirectAcquisition": [{
                        "type": acquisition_link.indirect_acquisition_type,
                        "child": [
                            {"type": acquisition_link.book_type}
                        ]
                    } for acquisition_link in acquisition_links_info if acquisition_link],
                })
        ]

    def _parse_external_identifier(self):
        """
        Parse external identifier field into AcquisitionInfo objects.

        Returns:
            Tuple or list of AcquisitionInfo objects or None entries.
            Returned structure matches external_identifier type (str or list).
        """
        if isinstance(self.external_identifier, str):
            return self._get_acquisition_info(self.external_identifier),
        return [self._get_acquisition_info(ext_id)
                for ext_id in self.external_identifier]

    def _get_acquisition_info(
            self, external_identifier: str) -> Union[AcquisitionInfo, None]:
        """
        Parse external_identifier entry and convert into AcquisitionInfo.

        Example external_identifier format:
            urn:lcp:identifier:pdf:a4a1de5e-3c50-4b97-b3c9-4defe677b5b6

        Args:
            external_identifier: External acquisition mapping value.

        Returns:
            AcquisitionInfo or None if value invalid or non LCP type.
        """
        if Formats.license_lcp not in external_identifier:
            return None
        # Ex: ['urn', 'lcp', 'identifier', 'pdf',
        # 'a4a1de5e-3c50-4b97-b3c9-4defe677b5b6']
        part_of_external_identifier = external_identifier.split(":")
        _, filename_base, book_extension = part_of_external_identifier[1:4]
        book_type, lcp_naming = Formats.check_format.get(book_extension)
        return self.AcquisitionInfo(lcp_naming,
                                    book_type,
                                    Formats.indirect_acquisition_lcp_type,
                                    filename_base)
