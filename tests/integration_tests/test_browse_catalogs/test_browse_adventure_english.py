import pytest
from opds.catalog.types import CatalogRequest, CatalogType

from tests.integration_tests.test_browse_catalogs.base_browse import FIXTURES_DIR, BaseBrowseTest


CATEGORY_ADVENTURE_ENGLISH_FIXTURE = FIXTURES_DIR / "test_browse_categories_adventure_english.json"
CATEGORY_ADVENTURE_ENGLISH_ITEMS = FIXTURES_DIR / "test_items_metadata_browse_categories_adventure_english.json"


@pytest.fixture
def mock_browse_categories_adventure(make_mock_ia_admin_user):
    """Mock IA provider for browsing adventure category."""
    yield from make_mock_ia_admin_user(CATEGORY_ADVENTURE_ENGLISH_ITEMS, 11862)


class TestBrowseCategoriesAdventureEnglish(BaseBrowseTest):
    """Test browsing the Adventure category."""

    EXPECTED_FIXTURE = CATEGORY_ADVENTURE_ENGLISH_FIXTURE
    EXPECTED_SECTION = "categories"
    EXPECTED_ITEM = "adventure"

    @pytest.fixture
    def catalog(self, catalog_factory, mock_browse_categories_adventure):
        """Build adventure category browse catalog."""
        request = CatalogRequest(
            catalog_type=CatalogType.BROWSE.value,
            section=self.EXPECTED_SECTION,
            item=self.EXPECTED_ITEM,
            page=1,
            applied_facets={"languages": "english"}
        )
        return catalog_factory.build_catalog(request).model_dump(mode="json")

    def test_metadata_title(self, catalog):
        """Test catalog title matches category item title."""
        assert catalog["metadata"]["title"] == "Action / Adventure"

    def test_self_link_includes_facets(self, catalog):
        """Test self link includes facet parameters."""
        self_link = next(l for l in catalog["links"] if l["rel"] == "self")
        assert "facet_section=languages" in self_link["href"]
        assert "facet_item=english" in self_link["href"]

    def test_pagination_links_include_facets(self, catalog):
        """Test pagination links preserve facet parameters."""
        pagination_rels = ["first", "previous", "next", "last"]
        for rel in pagination_rels:
            link = next((l for l in catalog["links"] if l["rel"] == rel), None)
            if link:
                assert "facet_section=languages" in link["href"]
                assert "facet_item=english" in link["href"]

    def test_applied_facet_not_shown(self, catalog):
        """Test that applied facet (languages) is not shown in facets list."""
        if "facets" in catalog:
            facet_titles = [f["metadata"]["title"] for f in catalog["facets"]]
            assert "Browse by Language" not in facet_titles
            # Only availability facet should remain
            assert "Browse by Availability" in facet_titles

