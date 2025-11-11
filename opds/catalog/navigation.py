"""Navigation catalog builder for hierarchical menu structures.

This module implements the NavigationCatalogBuilder which creates OPDS
navigation catalogs with hierarchical menus and featured content groups.
Navigation catalogs are used for the main menu and other browsing pages
that don't display individual publications.
"""
from typing import Optional, List

from pyopds2 import Catalog, Metadata, Link, Navigation

from opds.catalog.base import BaseCatalogBuilder
from opds.config import ITEMS_PER_GROUP


class NavigationCatalogBuilder(BaseCatalogBuilder):
    """Builder for OPDS navigation catalogs with menus and featured groups.

    This builder creates catalogs that display hierarchical navigation menus
    with links to browse pages and sub-navigation pages. It can also include
    featured content groups that preview items from popular categories.

    Navigation catalogs are typically used for:
    - Main landing page with featured collections
    - Genre/category selection menus
    - Subject browsing hierarchies
    """

    def _build_metadata(self) -> Metadata:
        """Build metadata for the navigation catalog.

        Retrieves the navigation definition from the database and creates
        metadata with the navigation page title.

        Returns:
            Metadata object containing the navigation page title.

        Raises:
            ValueError: If the requested navigation page is not found in
                the database.
        """

        nav_def = self.db.get_navigation(self.request.nav_key)
        if not nav_def:
            raise ValueError(f"Navigation '{self.request.nav_key}' not found")

        return Metadata(title=nav_def.title)

    def _build_navigation(self) -> List[Navigation]:
        """Build navigation items from sections and nested pages.

        Creates Navigation objects for all items specified in the navigation
        definition, including both browse sections and sub-navigation pages.

        Returns:
            List of Navigation objects representing menu items. Each Navigation
            contains a title, href, and OPDS type.
        """
        nav_def = self.db.get_navigation(self.request.nav_key)
        if not nav_def:
            raise ValueError(f"Navigation {self.request.nav_key} not found")
        navigation = []

        # Add sections
        if nav_def.show_sections:
            for section_key in nav_def.show_sections:
                section_data = self.db.get_section(section_key)
                if not section_data:
                    continue

                for item_key, item_data in section_data.items.items():
                    navigation.append(
                        Navigation(
                            title=item_data.title,
                            href=f"/catalog?type=browse&section={section_key}&item={item_key}",
                            rel="collection",
                            type="application/opds+json"))

        # Add navigation pages
        if nav_def.show_navigation_pages:
            for page_key in nav_def.show_navigation_pages:
                page_nav = self.db.get_navigation(page_key)
                if page_nav:
                    navigation.append(Navigation(
                        title=page_nav.title,
                        href=f"/catalog?type=navigation&nav_key={page_key}",
                        rel="collection",
                        type="application/opds+json"
                    ))

        return navigation

    def _build_groups(self) -> Optional[List[Catalog]]:
        """Build featured content groups for the navigation page.

        Featured groups are sub-catalogs that preview items from popular
        categories, typically displayed on the main landing page. Each group
        shows a limited number of items with a link to view more.

        Returns:
            List of Catalog objects representing featured groups, or None
            if no featured groups are configured for this navigation page.
        """
        nav_def = self.db.get_navigation(self.request.nav_key)

        if not nav_def.featured_groups:
            return None

        groups = []
        section_key = nav_def.featured_groups.section

        for group_key in nav_def.featured_groups.groups:
            group = self._build_featured_group(section_key, group_key)
            if group:
                groups.append(group)

        return groups if groups else None

    def _build_featured_group(
            self,
            section_key: str,
            group_key: str) -> Optional[Catalog]:
        """Build a single featured content group.

        Fetches a preview of items from the specified category and creates
        a sub-catalog with metadata, publications, and a link to browse more.

        Args:
            section_key: Section identifier (e.g., "categories", "subjects").
            group_key: Item identifier within the section (e.g., "fiction",
                "romance").

        Returns:
            Catalog object containing the featured group with preview items,
            or None if the section/item is not found or has no results.
        """
        section_data = self.db.get_section(section_key)
        if not section_data or group_key not in section_data.items:
            return None

        item_data = section_data.items[group_key]

        # Build query
        query = item_data.query
        if section_data.needs_base_query and self.db.base_query:
            query = f"({self.db.base_query}) AND ({query})"

        # Fetch preview
        results, total = self.provider.search(
            query=query,
            limit=ITEMS_PER_GROUP,
            page=1,
            sort=item_data.sort if item_data.sort else "",
            preferred_client_ip=self.request.preferred_client_ip
        )

        publications = [record.to_publication() for record in results]
        browse_url = f"/catalog?type=browse&section={section_key}&item={group_key}"

        return Catalog(
            metadata=Metadata(
                title=item_data.title,
                numberOfItems=total),
            links=[
                Link(
                    rel="self",
                    href=browse_url,
                    type="application/opds+json")],
            publications=publications)
