"""
Database interface for OPDS Query configuration loader.

This module loads OPDS query configuration from a JSON file and exposes helper
methods to read sections, items and navigation metadata. It provides dataclasses
describing sections, query items and navigation structures used across the OPDS
builder.
"""
import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryItem:
    """Single item inside a Section that can represent a filter, category or sorting option."""
    key: str
    title: str
    query: Optional[str] = None
    sort: Optional[str] = None


@dataclass
class Section:
    """Logical section grouping multiple QueryItem objects."""
    key: str
    title: str
    needs_base_query: bool
    facets: list[str]
    items: dict[str, QueryItem]


@dataclass
class FeaturedGroups:
    """Represents featured groups inside a navigation page."""
    section: str
    groups: list[str]


@dataclass
class Navigation:
    """Represents navigation page structure used by the OPDS."""
    key: str
    title: str
    show_sections: list[str] = None
    show_navigation_pages: Optional[str] = None
    featured_groups: Optional[FeaturedGroups] = None


class DBinterface:
    """Database loader that reads JSON OPDS config and provides lookup helpers."""

    def __init__(self, json_path: str):
        """
        Load JSON file and initialize Sections, Items and Navigation structure.

        Args:
            json_path: Path to configuration JSON file.
        """
        with open(json_path, encoding="utf-8") as f:
            self.data = json.load(f)
        self.base_query = self.data["base_query"].replace("'", '"')
        self.sections = self._load_sections()
        self.navigation = self._load_navigation()

    def _load_sections(self) -> dict[str, Section]:
        """
        Internal loader: parse sections from JSON configuration.

        Returns:
            Mapping of section name to Section object.
        """
        sections = {}
        for name, info in self.data["sections"].items():
            items = {
                key: QueryItem(
                    key=key,
                    title=value["title"],
                    query=value.get("query").replace("'", '"'),
                    sort=value.get("sort"),
                )
                for key, value in info["items"].items()
            }
            sections[name] = Section(
                key=name,
                title=info["title"],
                needs_base_query=info.get("needs_base_query", True),
                facets=info.get("facets", []),
                items=items
            )
        return sections

    def _load_navigation(self) -> dict[str, Navigation]:
        """
        Internal loader: parse navigation pages from JSON configuration.

        Returns:
            Mapping of navigation key to Navigation object.
        """
        nav = {}
        for key, info in self.data["navigation"].items():
            # Parse featured_groups
            featured_groups = None
            if "featured_groups" in info:
                fg = info["featured_groups"]
                featured_groups = FeaturedGroups(
                    section=fg["section"],
                    groups=fg["groups"]
                )

            nav[key] = Navigation(
                key=key,
                title=info["title"],
                show_sections=info.get("show_sections"),
                show_navigation_pages=info.get("show_navigation_pages"),
                featured_groups=featured_groups
            )
        return nav

    def get_section(self, name: str) -> Optional[Section]:
        """
        Get section by name.

        Args:
            name: Section key/name.

        Returns:
            Section object or None.
        """
        return self.sections.get(name)

    def get_item(self, section: str, key: str) -> Optional[QueryItem]:
        """
        Get item (facet) inside a section.

        Args:
            section: Section name.
            key: Item key.

        Returns:
            QueryItem object or None.
        """
        sec = self.sections.get(section)
        return sec.items.get(key) if sec else None

    def get_navigation(self, name: str) -> Optional[Navigation]:
        """
        Get navigation page by name.

        Args:
            name: Navigation key/name.

        Returns:
            Navigation object or None.
        """
        return self.navigation.get(name)
