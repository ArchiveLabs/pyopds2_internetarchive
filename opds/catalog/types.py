"""Catalog type definitions and request models.

This module defines the core data structures used throughout the catalog
system, including catalog type enumerations, request parameters, query
builders, and context objects for catalog construction.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from database.interfaces import DBinterface


class CatalogType(Enum):
    """Enumeration of supported OPDS catalog types.

    Attributes:
        NAVIGATION: Catalog type for navigation menus and groups.
        BROWSE: Catalog type for browsing items(publications) and facet.
        SEARCH: Catalog type for displaying search results.
    """
    NAVIGATION = "navigation"
    BROWSE = "browse"
    SEARCH = "search"


@dataclass
class InternetArchiveSearchQueryBuilder:
    """Builder for constructing Internet Archive search queries.

    This class provides a structured way to build complex search queries
    by combining base queries, item queries, and facet filters with
    proper AND logic.

    Attributes:
        base: Base query that applies to all items (e.g., "mediatype:texts").
            Can be None if not needed or removed by facets.
        item: Primary item query (e.g., category or search term).
        facets: List of facet filter queries to apply (e.g., language,
            availability filters).
    """
    base: str | None = None
    item: str = ""
    facets: list[str] = field(default_factory=list)

    def get_full_query(self) -> str:
        """Combine all query parts into a single search query.

        Joins base, item, and facet queries with AND operators, excluding
        any empty or None values.

        Returns:
            Complete search query string suitable for Internet Archive API.
        """
        parts = [q for q in [self.base, self.item] + self.facets if q]
        return " AND ".join(parts)

    def remove_base_query(self) -> None:
        """Remove the base query from the builder.

        This is used when a facet needs to override or exclude the base
        query (e.g., when browsing items that don't fit the standard
        media type filter).
        """
        self.base = None


@dataclass
class CatalogRequest:
    """Universal request parameters for building any catalog type.

    This dataclass encapsulates all possible parameters needed to build
    navigation, browse, or search catalogs. Only fields relevant to the
    specified catalog_type are validated and used.

    Attributes:
        catalog_type: Type of catalog to build ("navigation", "browse",
            or "search").
        nav_key: Navigation page identifier (required for navigation type).
        section: Section identifier for browsing (required for browse type).
        item: Item identifier within section (required for browse type).
        query: User search query string (required for search type).
        page: Current page number for pagination, starting at 1. Defaults to 1.
        applied_facets: Dictionary mapping facet section keys to selected
            facet item keys (e.g., {"languages": "english"}).
        preferred_client_ip: IP address of the end user for access control
            and analytics.
    """
    # Catalog type
    catalog_type: str

    # Navigation parameters
    nav_key: Optional[str] = None

    # Browse/Search parameters
    section: Optional[str] = None
    item: Optional[str] = None

    # Search parameters
    query: Optional[str] = None

    # Pagination
    page: int = 1

    # Filtering
    applied_facets: Dict[str, str] = field(default_factory=dict)

    # Client info
    preferred_client_ip: Optional[str] = None

    def validate(self) -> None:
        """Validate that required fields are present for the catalog type.

        Raises:
            ValueError: If required fields are missing for the specified
                catalog_type.
        """
        if self.catalog_type == CatalogType.NAVIGATION:
            if not self.nav_key:
                raise ValueError("Navigation catalog requires 'nav_key'")

        elif self.catalog_type == CatalogType.BROWSE:
            if not self.section or not self.item:
                raise ValueError("Browse catalog requires 'section' and 'item'")

        elif self.catalog_type == CatalogType.SEARCH:
            if not self.query:
                raise ValueError("Search catalog requires 'query'")

    def to_url_params(self) -> Dict[str, Any]:
        """Convert request to URL query parameters dictionary.

        Creates a dictionary of URL parameters suitable for building self
        and pagination links. Only includes parameters that are set and
        excludes default values.

        Returns:
            Dictionary mapping parameter names to their values, excluding
            None values and page=1 (default).
        """
        params = {"type": self.catalog_type}

        if self.nav_key:
            params["nav_key"] = self.nav_key
        if self.section:
            params["section"] = self.section
        if self.item:
            params["item"] = self.item
        if self.query:
            params["query"] = self.query
        if self.page > 1:
            params["page"] = self.page

        return params


@dataclass
class CatalogContext:
    """Context object containing resources needed for catalog building.

    This context object is passed to catalog builders and provides access
    to all necessary dependencies including the database interface, data
    provider, and request parameters.

    Attributes:
        db: Database interface for accessing catalog structure and metadata.
        provider: Data provider for fetching items from Internet Archive.
        request: Validated catalog request containing all parameters.
    """
    db: DBinterface
    provider: Any
    request: CatalogRequest
