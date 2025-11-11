"""Abstract base class for OPDS catalog builders.

This module implements the template method pattern for building OPDS catalogs.
It provides a common structure and shared functionality that all catalog types
(navigation, browse, search) inherit and customize.
"""
from urllib.parse import urlencode
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from pyopds2 import Catalog, Metadata, Link, Navigation, Publication

from opds.config import SHELF_LINK, USER_PROFILE_LINK
from opds.catalog.types import CatalogContext


class BaseCatalogBuilder(ABC):
    """Abstract base class for all catalog builders using template pattern.

    This class defines the common structure for building OPDS catalogs and
    provides shared functionality for links, pagination, and URL generation.
    Subclasses override specific methods to implement navigation, browse,
    or search catalog types.

    Attributes:
        db: Database interface for accessing catalog structure.
        provider: Data provider for fetching items from Internet Archive.
        request: Validated catalog request with all parameters.
    """

    def __init__(self, context: CatalogContext):
        """Initialize the catalog builder with context dependencies.

        Args:
            context: CatalogContext object containing database, provider,
                and request parameters.
        """
        self.db = context.db
        self.provider = context.provider
        self.request = context.request

    def build(self) -> Catalog:
        """Build a complete OPDS catalog using the template method pattern.

        This method orchestrates the catalog building process by calling
        specific builder methods in the correct order. It validates the
        request, builds all catalog components, and assembles them into
        a complete Catalog object.

        The build order ensures publications are built first to retrieve
        total item counts from the search engine, which are needed for
        pagination and metadata.

        Returns:
            Complete OPDS Catalog object ready for serialization to JSON.

        Raises:
            ValueError: If request validation fails or required data is missing.
        """
        # Validate request
        self.request.validate()

        # Build type-specific components
        catalog_dict = {}

        # Add optional components
        # Publications must be first to get total counts from IA
        if publications := self._build_publications():
            catalog_dict["publications"] = publications

        if navigation := self._build_navigation():
            catalog_dict["navigation"] = navigation

        if groups := self._build_groups():
            catalog_dict["groups"] = groups

        if facets := self._build_facets():
            catalog_dict["facets"] = facets

        catalog_dict["metadata"] = self._build_metadata()
        catalog_dict["links"] = self._build_links()

        return Catalog(**catalog_dict)

    @abstractmethod
    def _build_metadata(self) -> Metadata:
        """Build catalog metadata (title, pagination info, etc.).

        This abstract method must be implemented by all subclasses to provide
        appropriate metadata for their catalog type.

        Returns:
            Metadata object with title and optional pagination information.
        """
        pass

    def _build_links(self) -> List[Link]:
        """Build all links including common links and pagination.

        Combines common links (search, shelf, profile, self) with type-specific
        pagination links.

        Returns:
            List of Link objects for the catalog.
        """
        links = []
        links.extend(self._build_common_links())
        links.extend(self._build_pagination_links())
        return links

    def _build_common_links(self) -> List[Link]:
        """Build links common to all catalog types.

        Creates standard OPDS links including search template, user shelf,
        user profile, and self reference.

        Returns:
            List of common Link objects present in all catalogs.
        """
        links = [
            Link(
                rel="search",
                href="/catalog{?query}&type=search",
                type="application/opds+json",
                templated=True
            ),  # Search link
            Link(
                rel="http://opds-spec.org/shelf",
                href=SHELF_LINK,
                type="application/opds+json"
            ),  # Shelf link
            Link(
                rel="profile",
                href=USER_PROFILE_LINK,
                type="application/opds-profile+json"
            )  # Profile link
        ]

        # Self link
        url = self._build_self_url()
        links += [
            Link(
                rel="self",
                href=url,
                type="application/opds+json"
            )]

        return links

    def _build_self_url(self) -> str:
        """Build the self URL from current request parameters.

        Constructs the complete URL for the current catalog including all
        request parameters and applied facets.

        Returns:
            Complete URL string for the self link.
        """
        params = self.request.to_url_params()
        base_query = urlencode(params)
        facet_query = self._build_facet_param_query_string()

        return f"/catalog?{base_query}{facet_query}"

    def _build_facet_param_query_string(self) -> str:
        """Build query string fragment for applied facets.

        Converts the applied_facets dictionary into URL query parameters
        using the facet_section and facet_item parameter format.

        Returns:
            Query string fragment starting with '&' if facets exist,
            empty string otherwise.
        """
        if not self.request.applied_facets:
            return ""

        facet_parts = [
            f"facet_section={section}&facet_item={item}"
            for section, item in self.request.applied_facets.items()
        ]
        return "&" + "&".join(facet_parts)

    def _build_pagination_links(self) -> List[Link]:
        """Build pagination links (first, previous, next, last).

        This method can be overridden by subclasses that support pagination.
        The base implementation returns an empty list.

        Returns:
            List of pagination Link objects, empty by default.
        """
        return []

    def _build_navigation(self) -> Optional[List[Navigation]]:
        """Build navigation items for hierarchical menus.

        This method can be overridden by NavigationCatalogBuilder.
        The base implementation returns None.

        Returns:
            List of Navigation objects or None if not applicable.
        """
        return None

    def _build_groups(self) -> Optional[List[Catalog]]:
        """Build featured content groups.

        This method can be overridden by NavigationCatalogBuilder to show
        featured collections on the home page.
        The base implementation returns None.

        Returns:
            List of sub-Catalog objects representing featured groups,
            or None if not applicable.
        """
        return None

    def _build_publications(self) -> Optional[List[Publication]]:
        """Build list of publications (books/media items).

        This method can be overridden by BrowseCatalogBuilder and
        SearchCatalogBuilder to fetch and display items.
        The base implementation returns None.

        Returns:
            List of Publication objects or None if not applicable.
        """
        return None

    def _build_facets(self) -> Optional[List[Dict[str, Any]]]:
        """Build facet groups for filtering results.

        This method can be overridden by BrowseCatalogBuilder and
        SearchCatalogBuilder to provide faceted navigation.
        The base implementation returns None.

        Returns:
            List of facet group dictionaries or None if not applicable.
            Each facet group contains metadata and a list of filter links.
        """
        return None
