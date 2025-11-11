"""Browse catalog builder for category and faceted browsing.

This module implements the BrowseCatalogBuilder which creates OPDS catalogs
for browsing items by category, subject, or other dimensions. It supports
pagination and faceted filtering to refine results.
"""
from urllib.parse import urlencode
from typing import Optional, List, Dict, Any

from pyopds2 import Metadata, Link, Publication

from opds.catalog.base import BaseCatalogBuilder
from opds.catalog.types import CatalogContext, InternetArchiveSearchQueryBuilder

from opds.config import ITEMS_PER_PAGE, IA_SEARCH_ENGINE_LIMIT_PAGE


class BrowseCatalogBuilder(BaseCatalogBuilder):
    """Builder for browse catalogs with pagination and faceted filtering.

    This builder creates catalogs that display paginated lists of publications
    filtered by category, subject, or other criteria. It supports multi-faceted
    filtering to allow users to refine results by language, availability, etc.

    Browse catalogs are used for:
    - Category browsing (e.g., Fiction, Science, History)
    - Language-specific collections
    - Any other filtered collection of items

    Attributes:
        section_data: Database definition for the browse section (e.g., categories).
        item_data: Database definition for the specific item being browsed
            (e.g., "fiction" within categories).
        total: Total number of items matching the current query.
    """

    def __init__(self, context: CatalogContext):
        """Initialize the browse builder and load section/item data.

        Args:
            context: CatalogContext containing database, provider, and request.

        Raises:
            ValueError: If the section or item is not found in the database.
        """
        super().__init__(context)
        self.section_data = None
        self.item_data = None
        self.total = 0
        self._load_data()

    def _load_data(self):
        """Load section and item definitions from the database.

        Retrieves and validates the section and item data needed to build
        the browse query.

        Raises:
            ValueError: If the section or item is not found in the database.
        """
        self.section_data = self.db.get_section(self.request.section)
        if not self.section_data:
            raise ValueError(f"Section '{self.request.section}' not found")

        self.item_data = self.db.get_item(
            self.request.section, self.request.item)
        if not self.item_data:
            raise ValueError(f"Item '{self.request.item}' not found")

    def _build_publications(self) -> List[Publication]:
        """Fetch and build the list of publications for the current page.

        Constructs the search query from item and facets, executes the search,
        and converts results to Publication objects. Updates total count and
        max page number as side effects.

        Returns:
            List of Publication objects for the current page.

        Example:
            For browsing "Fiction" in English:
            - Query: "(mediatype:texts) AND (subject:fiction) AND (language:eng)"
            - Returns 25 publications (one page)
        """
        internet_archive_search_query = self._build_internet_archive_search_query()
        full_query = internet_archive_search_query.get_full_query()

        results, self.total = self.provider.search(
            query=full_query,
            page=self.request.page,
            sort=self.item_data.sort,
            preferred_client_ip=self.request.preferred_client_ip
        )

        return [record.to_publication() for record in results]

    def _build_metadata(self) -> Metadata:
        """Build metadata for the browse catalog.

        Creates metadata with the item title and pagination information.

        Returns:
            Metadata object with title, pagination info, and total items.
        """
        return Metadata(
            title=self.item_data.title,
            numberOfItems=min(self.total, IA_SEARCH_ENGINE_LIMIT_PAGE),
            itemsPerPage=ITEMS_PER_PAGE,
            currentPage=self.request.page
        )

    def _build_internet_archive_search_query(
            self) -> InternetArchiveSearchQueryBuilder:
        """Build the Internet Archive search query from item and facets.

        Combines the base query (if needed), item query, and all applied
        facet queries into a structured query builder.

        Returns:
            InternetArchiveSearchQueryBuilder with all query components.
        """
        query_parts = InternetArchiveSearchQueryBuilder()

        # Base query
        if self.section_data.needs_base_query and self.db.base_query:
            query_parts.base = self.db.base_query

        # Item query
        query_parts.item = self.item_data.query

        # Facet queries
        if self.request.applied_facets:
            for facet_section, facet_item in self.request.applied_facets.items():
                facet_section_data = self.db.get_section(facet_section)
                facet_item_data = self.db.get_item(facet_section, facet_item)

                if facet_item_data and facet_item_data.query:
                    if facet_section_data.needs_base_query is False:
                        query_parts.remove_base_query()
                    query_parts.facets.append(f"({facet_item_data.query})")

        return query_parts

    def _build_pagination_links(self) -> List[Link]:
        """Build pagination links for navigating through result pages.

        Creates first, previous, next, and last links for paginated results.
        Returns empty list if there are no results.

        Returns:
            List of Link objects for pagination (first, previous, next, last).
        """
        if self.total == 0:
            return []

        return self._create_pagination_links(self.total)

    def _create_pagination_links(self, total: int) -> List[Link]:
        """Create pagination link objects.

        Args:
            total: Total number of items in the result set.

        Returns:
            List of four Link objects (first, previous, next, last).

        Note:
            Previous link on page 1 points to page 1.
            Next link on last page points to last page.
        """
        links = []
        max_page = min(
            total //
            ITEMS_PER_PAGE,
            IA_SEARCH_ENGINE_LIMIT_PAGE //
            ITEMS_PER_PAGE)
        page = self.request.page

        params = self.request.to_url_params()
        facet_query = self._build_facet_param_query_string()

        # First
        params["page"] = 1
        links.append(Link(
            rel="first",
            href=f"/catalog?{urlencode(params)}{facet_query}",
            type="application/opds+json"
        ))

        # Previous
        params["page"] = max(1, page - 1)
        links.append(Link(
            rel="previous",
            href=f"/catalog?{urlencode(params)}{facet_query}",
            type="application/opds+json"
        ))

        # Next
        params["page"] = min(max_page, page + 1)
        links.append(Link(
            rel="next",
            href=f"/catalog?{urlencode(params)}{facet_query}",
            type="application/opds+json"
        ))

        # Last
        params["page"] = max_page
        links.append(Link(
            rel="last",
            href=f"/catalog?{urlencode(params)}{facet_query}",
            type="application/opds+json"
        ))

        return links

    def _build_facets(self) -> Optional[List[Dict[str, Any]]]:
        """Build facet groups for filtering results.

        Creates facet filter groups based on the section configuration.
        Excludes facets that are already applied.

        Returns:
            List of facet group dictionaries, each containing metadata
            and a list of filter links. Returns None if no facets are
            configured or all are already applied.
        """
        if not self.section_data.facets:
            return None

        return self._create_facet_links(self.section_data.facets)

    def _create_facet_links(
            self, facet_sections: List[str]) -> Optional[List[Dict[str, Any]]]:
        """Create facet filter group structures.

        Args:
            facet_sections: List of section keys to create facets for
                (e.g., ["languages", "availability"]).

        Returns:
            List of facet group dictionaries or None if no valid facets exist.
            Each dictionary contains:
            - metadata: Dict with title
            - links: List of filter option dicts with title, href, type
        """
        facets = []

        for facet_section_key in facet_sections:
            # Skip already applied facets
            if facet_section_key in self.request.applied_facets:
                continue

            facet_section = self.db.get_section(facet_section_key)
            if not facet_section:
                continue

            links = []
            for facet_item_key, facet_item_data in facet_section.items.items():
                # Build base params without pagination
                params = self.request.to_url_params()
                params.pop("page", None)
                base_query = urlencode(params)

                # Build facet query
                facet_parts = []
                for section, item in self.request.applied_facets.items():
                    facet_parts.append(
                        f"facet_section={section}&facet_item={item}")
                facet_parts.append(
                    f"facet_section={facet_section_key}&facet_item={facet_item_key}")

                facet_query = "&".join(facet_parts)
                href = f"/catalog?{base_query}&{facet_query}"

                links.append({
                    "title": facet_item_data.title,
                    "href": href,
                    "type": "application/opds+json"
                })

            facets.append({
                "metadata": {"title": facet_section.title},
                "links": links
            })

        return facets if facets else None
