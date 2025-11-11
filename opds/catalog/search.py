"""Search catalog builder for user search queries.

This module implements the SearchCatalogBuilder which creates OPDS catalogs
for displaying search results. It extends BrowseCatalogBuilder to reuse
pagination and faceting functionality while customizing query building
for user search terms.
"""
from pyopds2 import Metadata

from opds.config import ITEMS_PER_PAGE, IA_SEARCH_ENGINE_LIMIT_PAGE
from opds.catalog.browse import BrowseCatalogBuilder
from opds.catalog.types import InternetArchiveSearchQueryBuilder


class SearchCatalogBuilder(BrowseCatalogBuilder):
    """Builder for search result catalogs with faceted filtering.

    This builder extends BrowseCatalogBuilder to create catalogs that display
    search results based on user queries. It inherits pagination and faceting
    capabilities while customizing the query building to use user search terms
    instead of predefined category queries.

    Search catalogs support:
    - Full-text search across Internet Archive items
    - Field-specific queries (e.g., "title:python", "creator:shakespeare")
    - Faceted filtering of search results (language, availability, etc.)
    - Pagination through large result sets
    - Quote normalization for better search accuracy

    The builder normalizes various quote characters to standard ASCII quotes
    to improve search results, as some clients may send Unicode quotes.

    Attributes:
        SEARCH_SECTION: Constant section key for search catalogs ("search").
        SEARCH_ITEM_KEY: Constant item key for search catalogs ("user-search").
        QUOTES_REPLACEMENTS: Tuple of Unicode quote characters to normalize.
    """
    SEARCH_SECTION = "search"
    SEARCH_ITEM_KEY = "user-search"
    QUOTES_REPLACEMENTS = ("“", "‘", "`", "'", "’")

    def _load_data(self):
        """Load search-specific section and item data from database.

        Overrides parent method to load the special "search" section
        configuration instead of requiring section/item in the request.

        Note:
            Unlike browse catalogs, search catalogs always use the predefined
            "search" section and "user-search" item from the database.
        """
        self.section_data = self.db.get_section(self.SEARCH_SECTION)
        self.item_data = self.db.get_item(
            self.SEARCH_SECTION, self.SEARCH_ITEM_KEY)

    def _build_metadata(self) -> Metadata:
        return Metadata(
            title=f"{self.item_data.title} '{self.total}'",
            numberOfItems=min(self.total, IA_SEARCH_ENGINE_LIMIT_PAGE),
            itemsPerPage=ITEMS_PER_PAGE,
            currentPage=self.request.page
        )

    def _build_internet_archive_search_query(
            self) -> InternetArchiveSearchQueryBuilder:
        """Build Internet Archive search query from user input and facets.

        Constructs the search query by combining:
        1. Base query (always applied for search to filter item types)
        2. Normalized user search query
        3. Applied facet filters

        The method normalizes various Unicode quote characters to standard
        ASCII quotes for better search compatibility.

        Returns:
            InternetArchiveSearchQueryBuilder with complete search query.

        Note:
            Unlike browse catalogs, search always includes the base query
            unless explicitly removed by a facet with needs_base_query=False.
        """
        query_parts = InternetArchiveSearchQueryBuilder()

        # Normalize quotes in user query
        user_query = self.request.query
        for quote in self.QUOTES_REPLACEMENTS:
            user_query = user_query.replace(quote, '"')

        # Base query (always for search)
        query_parts.base = self.db.base_query
        query_parts.item = user_query

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
