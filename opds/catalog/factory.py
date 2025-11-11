"""Factory for creating catalog builders and audiobook manifests.

Implements the factory pattern for selecting appropriate OPDS catalog builders
based on request type, and provides helpers for generating W3C audiobook manifests.
"""
from typing import List

from pyopds2 import Catalog, Link

from opds.internet_archive import IA_ADMIN_USER
from database.interfaces import DBinterface
from opds.catalog.types import CatalogContext, CatalogRequest, CatalogType
from opds.catalog.browse import BrowseCatalogBuilder
from opds.catalog.navigation import NavigationCatalogBuilder
from opds.catalog.search import SearchCatalogBuilder


class CatalogBuilderFactory:
    """Factory for creating OPDS catalog builders.

    Encapsulates creation/selection logic for the different catalog builders and
    manages shared dependencies (DB interface + IA data provider).
    """

    def __init__(self, db_path: str, provider):
        """Initialize the factory with database and data provider.

        Args:
            db_path: Path to the JSON database file containing catalog
                structure definitions.
            provider: Data provider class for Internet Archive integration.
        """
        self.db = DBinterface(db_path)
        self.provider = provider

    def build_catalog(self, request: CatalogRequest) -> Catalog:
        """Build an OPDS catalog based on request type using factory pattern.

        Selects and instantiates the appropriate builder class based on the
        catalog_type in the request, then delegates to the builder's build()
        method.

        Args:
            request: CatalogRequest object containing type and parameters
                for the desired catalog.

        Returns:
            Complete OPDS Catalog object ready for JSON serialization.

        Raises:
            ValueError: If the catalog_type is not recognized or if the
                builder encounters validation errors.
        """
        context = CatalogContext(
            db=self.db,
            provider=self.provider,
            request=request
        )

        # Select appropriate builder
        if request.catalog_type == CatalogType.NAVIGATION.value:
            builder = NavigationCatalogBuilder(context)
        elif request.catalog_type == CatalogType.BROWSE.value:
            builder = BrowseCatalogBuilder(context)
        elif request.catalog_type == CatalogType.SEARCH.value:
            builder = SearchCatalogBuilder(context)
        else:
            raise ValueError(f"Unknown catalog type: {request.catalog_type}")

        return builder.build()


class AudiobookManifest:
    """
    Class for creating W3C audiobook manifests
    """
    AUDIO_FORMAT = "64Kbps MP3"

    def __init__(self, provider):
        self.provider = provider

    def create_manifest(
            self,
            identifier: str,
            preferred_client_ip: str) -> Catalog:
        """Create a W3C audiobook manifest for a specific audiobook item.

        This method generates a W3C-compliant audiobook manifest by fetching
        the item metadata from Internet Archive and constructing a reading
        order from the available MP3 files. The manifest includes metadata,
        cover images, and ordered audio file links.

        Args:
            identifier: Internet Archive identifier for the audiobook item
                (e.g., "alice-wonderland_1234_librivox").
            preferred_client_ip: IP address of the end user for access control.

        Returns:
            Catalog object structured as a W3C audiobook manifest with:
            - metadata: Title, author, duration, etc.
            - links: Cover images and other resources
            - readingOrder: Ordered list of audio file links

        Raises:
            ValueError: If the audiobook identifier is not found in Internet
                Archive.
        """
        results, total = self.provider.search(
            query=f"(identifier:{identifier})",
            preferred_client_ip=preferred_client_ip
        )

        if total < 1:
            raise ValueError(f"Audiobook {identifier} not found")

        publication = [record.to_publication() for record in results][0]
        reading_order = self._create_reading_order(identifier)

        return Catalog(
            metadata=publication.metadata,
            links=publication.images,
            readingOrder=reading_order,
        )

    def _create_reading_order(self, identifier: str) -> List[Link]:
        """Extract and order MP3 audio files for audiobook reading order.

        Retrieves all MP3 files from the Internet Archive item and filters
        for the 64Kbps format to create a consistent reading order. The files
        are returned with their download URLs, titles, and durations.

        Args:
            identifier: Internet Archive identifier for the audiobook item.

        Returns:
            List of Link objects representing audio files in reading order.
            Each link contains:
            - href: Direct download URL for the MP3 file
            - type: "audio/mpeg"
            - title: Chapter or file title
            - duration: Audio duration in seconds (if available)
        """
        download_links = IA_ADMIN_USER.get_urls(
            identifier, glob_pattern="*mp3")

        return [
            Link(href=link.url, type="audio/mpeg", title=link.title, duration=link.length or None)
            for link in download_links if link.format == self.AUDIO_FORMAT
        ]
