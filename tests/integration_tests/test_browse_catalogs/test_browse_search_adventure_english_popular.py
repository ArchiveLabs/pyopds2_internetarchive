import pytest
from opds.catalog.types import CatalogRequest, CatalogType

from tests.integration_tests.test_browse_catalogs.base_browse import FIXTURES_DIR, BaseBrowseTest


SEARCH_ADVENTURE_ENGLISH_POPULAR_FIXTURE = FIXTURES_DIR / "test_browse_search_adventure_english_popular.json"
SEARCH_ADVENTURE_ENGLISH_POPULAR_ITEMS = FIXTURES_DIR / "test_items_metadata_browse_search_adventure_english_popular.json"


@pytest.fixture
def mock_browse_categories_adventure(make_mock_ia_admin_user):
    """Mock IA provider for browsing adventure category."""
    yield from make_mock_ia_admin_user(SEARCH_ADVENTURE_ENGLISH_POPULAR_ITEMS, 37)


class TestBrowseSearchAdventureEnglishPopular(BaseBrowseTest):
    """Test browsing the Adventure category."""

    EXPECTED_FIXTURE = SEARCH_ADVENTURE_ENGLISH_POPULAR_FIXTURE
    EXPECTED_SECTION = None
    EXPECTED_ITEM = None

    @pytest.fixture
    def catalog(self, catalog_factory, mock_browse_categories_adventure):
        """Build adventure category browse catalog."""
        request = CatalogRequest(
            catalog_type=CatalogType.SEARCH.value,
            section=self.EXPECTED_SECTION,
            item=self.EXPECTED_ITEM,
            page=1,
            query="bear",
            applied_facets={"languages": "english",
                            "availability": "popular",
                            "categories": "adventure"}
        )
        return catalog_factory.build_catalog(request).model_dump(mode="json")

    def test_metadata_title(self, catalog):
        """Test catalog title matches category item title."""
        assert catalog["metadata"]["title"] == "Results for query '37'"

    def test_self_link_format(self, catalog):
        """Test self link contains correct parameters."""
        self_link = next(l for l in catalog["links"] if l["rel"] == "self")
        assert "type=search" in self_link["href"]
        if self.EXPECTED_SECTION:
            assert f"section={self.EXPECTED_SECTION}" in self_link["href"]
        if self.EXPECTED_ITEM:
            assert f"item={self.EXPECTED_ITEM}" in self_link["href"]

    def test_self_link_includes_facets(self, catalog):
        """Test self link includes facet parameters."""
        self_link = next(l for l in catalog["links"] if l["rel"] == "self")
        assert "facet_section=languages" in self_link["href"]
        assert "facet_item=english" in self_link["href"]

        assert "facet_section=availability" in self_link["href"]
        assert "facet_item=popular" in self_link["href"]

        assert "facet_section=categories" in self_link["href"]
        assert "facet_item=adventure" in self_link["href"]

    def test_pagination_links_include_facets(self, catalog):
        """Test pagination links preserve facet parameters."""
        pagination_rels = ["first", "previous", "next", "last"]
        for rel in pagination_rels:
            link = next((l for l in catalog["links"] if l["rel"] == rel), None)
            if link:
                assert "facet_section=languages" in link["href"]
                assert "facet_item=english" in link["href"]

                assert "facet_section=availability" in link["href"]
                assert "facet_item=popular" in link["href"]

                assert "facet_section=categories" in link["href"]
                assert "facet_item=adventure" in link["href"]

    def test_applied_facet_not_shown(self, catalog):
        """Test that applied facet (languages) is not shown in facets list."""
        assert "facets" not in catalog

