"""
Archive.org DataProvider / OPDS metadata adapter.

This module defines data model conversions between archive.org search metadata
and OPDS2 DataProvider record output format. It converts raw IA metadata into
OPDS record, metadata, cover links and acquisition links. Supports both free
and borrowable / LCP protected items.
"""
import datetime
import typing
import concurrent.futures
from typing import List, Optional, Union
from pydantic import Field, field_validator

import langcodes
from pyopds2 import DataProvider, DataProviderRecord, Metadata, Link, Contributor

from opds.availability import AvailableInfo
from opds.acquisition_links import AcquisitionLinks
from opds.internet_archive import IA_ADMIN_USER
from opds.config import ITEMS_PER_PAGE, MAX_WORKERS


class ArchiveOrgDataRecord(DataProviderRecord):
    """
    DataProviderRecord implementation for archive.org items.

    Converts archive.org raw metadata fields to OPDS2 compatible record fields.
    """
    ARCHIVE_DETAILS_URL: str = "https://archive.org/details"
    ARCHIVE_DOWNLOAD_URL: str = "https://archive.org/download"
    ARCHIVE_IMAGE_NAME: str = "__ia_thumb.jpg"

    raw_identifier: str = Field(..., description="Archive.org identifier")
    mediatype: Optional[str] = Field(
        None, description="Media type from archive.org")
    title: Optional[str] = Field(None, description="Title of the resource")
    published: Optional[Union[str, datetime.datetime]] = Field(
        None, description="Publication date")
    numberOfPages: Optional[int] = Field(
        None, description="Number of pages in book")
    duration: Optional[float] = Field(
        None, description="Duration in seconds")
    access_restricted_item: Optional[str] = Field(
        None, description="Internet Archive field for borrowed books.")
    book_format: Optional[List[str]] = Field(
        None, description="All possible books format")

    author: Optional[Union[str, List[str]]] = Field(None, description="Author")
    description: Optional[Union[str, List[str]]] = Field(
        None, description="Description of the resource")
    language: Optional[Union[str, List[str]]] = Field(
        None, description="Language")
    external_identifier: Optional[Union[str, List[str]]] = Field(
        None, description="Internet Archive field")

    available_info: Optional[AvailableInfo] = Field(
        None, description="IA fields for availability")

    @property
    def type(self) -> str:
        """Dynamically return type based on mediatype."""
        if self.mediatype == "audio":
            return "http://schema.org/Audiobook"

        return "http://schema.org/Book"


    @property
    def identifier(self) -> str:
        """Return full archive.org detail URL."""
        return f"{self.ARCHIVE_DETAILS_URL}/{self.raw_identifier}"

    @field_validator('language', mode='before')
    @classmethod
    def convert_language(cls,
                         lang_input: Union[str,
                                           List[str]]) -> Optional[Union[str,
                                                                         List[Optional[str]]]]:
        """
        Normalize language input to ISO-639-1 2-letter codes.

        Args:
            lang_input: A single language string or list of language strings.

        Returns:
            A single ISO 639-1 code or list of codes. Returns None if no valid
            language information can be determined.
        """
        if isinstance(lang_input, list):
            # Convert each item and filter out None values
            converted = [
                cls.convert_language(item)
                for item in lang_input
            ]
            # Filter out None values
            filtered = [lang for lang in converted if lang is not None]
            # Return None if empty, otherwise return the filtered list
            return filtered if filtered else None

        if not isinstance(lang_input, str) or not lang_input.strip():
            return None

        try:
            # Language names or codes longer than 3 characters
            if len(lang_input) > 3:
                lang = langcodes.find(lang_input)
                return lang.language

            # Already a short code (ISO 639-1 or 639-2)
            return langcodes.standardize_tag(lang_input)

        except (LookupError, AttributeError, ValueError):
            return None

    @field_validator('duration', mode='before')
    @classmethod
    def convert_duration(cls, runtime):
        """
        Convert runtime HH:MM:SS string format into total seconds.

        Example: "1:48:13" → 6493 seconds

        Args:
            runtime: Duration string in time format

        Returns:
            Integer duration in seconds or None if value is empty.
        """
        if runtime:
            return sum(
                float(x) * 60 ** i for i,
                x in enumerate(
                    reversed(
                        runtime.split(':'))))
        return None

    @field_validator('description', mode='before')
    @classmethod
    def get_description(cls, description) -> Union[str, None]:
        """
        Normalize description metadata.

        The IA metadata can contain description either as a string or as a
        list of strings. OPDS encryption tooling expects a single string.
        Newlines and array values are merged into HTML <br> formatted output.

        Args:
            description: Raw description metadata

        Returns:
            Normalized single description string or None.
        """
        if isinstance(description, str):
            return description
        if isinstance(description, list):
            return '<br><br>'.join(
                [str(elem).replace('\n', '<br />') for elem in description])
        return None

    def metadata(self):
        """
        Build OPDS2 Metadata record from archive.org fields.

        Returns:
            opds2.models.Metadata instance.
        """
        # Helper function to ensure value is a list
        # opds2.models.Metadata expects language and author to be lists
        def ensure_list(value):
            if value is None:
                return None
            if isinstance(value, list):
                return value
            return [value]  # Convert string to list

        # Convert author string to Contributor list
        def get_authors() -> Optional[List[Contributor]]:
            if self.author:
                author_list = ensure_list(self.author)
                return [Contributor(name=name) for name in author_list]
            return None

        return Metadata(type=self.type,
                        title=self.title,
                        language=ensure_list(self.language),
                        published=self.published,
                        numberOfPages=self.numberOfPages,
                        author=get_authors(),
                        identifier=self.identifier,
                        description=self.description,
                        duration=self.duration
                        )

    def links(self):
        """
        Generate acquisition + sample links for OPDS2 record.

        Returns:
            List of Link objects for reading / borrowing.
        """
        links = [
            Link(
                rel="http://opds-spec.org/acquisition/sample",
                type="text/html",
                href=f"{self.ARCHIVE_DETAILS_URL}/{self.raw_identifier}&view=theater")]
        acquisition_links = AcquisitionLinks(
            access_restricted_item=self.access_restricted_item,
            identifier=self.raw_identifier,
            book_format=self.book_format,
            external_identifier=self.external_identifier,
            mediatype=self.mediatype,
            available_info=self.available_info
        )
        return links + acquisition_links.create_acquisition_links()

    def images(self):
        """
        Generate cover image links for OPDS2 record.

        Returns:
            List of Link objects representing record cover images.
        """
        image_link = f"{self.ARCHIVE_DOWNLOAD_URL}/" \
                     f"{self.raw_identifier}/{self.ARCHIVE_IMAGE_NAME}"
        return [
            Link(
                href=image_link,
                type="image/jpeg",
                rel="cover",
                height=1400,
                width=800),
            Link(
                href=image_link,
                type="image/jpeg",
                height=700,
                width=400),
        ]


class ArchiveOrgDataProvider(DataProvider):
    """
    Archive.org OPDS2 DataProvider implementation.

    Defines how records are searched, paginated and converted from IA metadata
    into ArchiveOrgDataRecord instances.
    """
    @typing.override
    @staticmethod
    def search(
            query: str,
            limit: int = ITEMS_PER_PAGE,
            page: int = 1,
            sort: Optional[str] = None,
            preferred_client_ip: Optional[str] = None,
            **kwargs) \
            -> tuple[List[ArchiveOrgDataRecord], int]:
        """
        Execute archive.org search and convert results into OPDS2 records.

        Args:
            query: Query string to search on archive.org.
            limit: Items per page.
            page: Pagination page number.
            sort: IA sort expression.
            preferred_client_ip: Optional end user IP for IA CDN geo selection.

        Returns:
            Tuple of (list[ArchiveOrgDataRecord], total_items_count)
        """
        items_metadata, number_of_items = IA_ADMIN_USER.get_search_info(
            query=query, sorts=sort, page=page, rows=limit, preferred_client_ip=preferred_client_ip)

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            records = list(executor.map(_create_record, items_metadata))

        return records, number_of_items


def _create_record(item_metadata: dict) -> ArchiveOrgDataRecord:
    """
    Convert raw archive.org metadata dict into ArchiveOrgDataRecord.

    Args:
        item_metadata: Raw IA metadata dictionary for a single record.

    Returns:
        ArchiveOrgDataRecord instance.
    """
    available_info = AvailableInfo(
        lending_available_to_borrow=item_metadata.get("lending___available_to_borrow"),
        lending_available_to_browse=item_metadata.get("lending___available_to_browse"),
        lending_max_lendable_copies=item_metadata.get("lending___max_lendable_copies"),
        lending_users_on_waitlist=item_metadata.get("lending___users_on_waitlist"),
        lending_active_borrows=item_metadata.get("lending___active_borrows"),
        lending_active_browses=item_metadata.get("lending___active_browses"),
        lending_borrow_expiration=item_metadata.get("lending___borrow_expiration"),
        lending_browse_expiration=item_metadata.get("lending___browse_expiration"))

    record = ArchiveOrgDataRecord(
        raw_identifier=item_metadata.get("identifier"),
        mediatype=item_metadata.get("mediatype"),
        title=item_metadata.get("title"),
        published=item_metadata.get("publicdate"),
        numberOfPages=item_metadata.get("imagecount"),
        author=item_metadata.get("creator"),
        description=item_metadata.get("description"),
        duration=item_metadata.get("runtime"),
        language=item_metadata.get("language"),
        access_restricted_item=item_metadata.get("access-restricted-item"),
        book_format=item_metadata.get("format"),
        external_identifier=item_metadata.get("external-identifier"),
        available_info=available_info
    )

    return record
