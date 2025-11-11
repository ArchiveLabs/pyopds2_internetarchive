import pytest
from opds.catalog.types import CatalogRequest, CatalogType

from tests.integration_tests.test_browse_catalogs.base_browse import FIXTURES_DIR, BaseBrowseTest


CATEGORY_ADVENTURE_FIXTURE = FIXTURES_DIR / "test_browse_categories_adventure.json"
CATEGORY_ADVENTURE_ITEMS = FIXTURES_DIR / "test_items_metadata_browse_categories_adventure.json"


@pytest.fixture
def mock_browse_categories_adventure(make_mock_ia_admin_user):
    """Mock IA provider for browsing adventure category."""
    yield from make_mock_ia_admin_user(CATEGORY_ADVENTURE_ITEMS, 12894)


class TestBrowseCategoriesAdventure(BaseBrowseTest):
    """Test browsing the Adventure category."""

    EXPECTED_FIXTURE = CATEGORY_ADVENTURE_FIXTURE
    EXPECTED_SECTION = "categories"
    EXPECTED_ITEM = "adventure"

    @pytest.fixture
    def catalog(self, catalog_factory, mock_browse_categories_adventure):
        """Build adventure category browse catalog."""
        request = CatalogRequest(
            catalog_type=CatalogType.BROWSE.value,
            section="categories",
            item="adventure",
            page=1
        )
        return catalog_factory.build_catalog(request).model_dump(mode="json")

    def test_metadata_title(self, catalog):
        """Test catalog title matches category item title."""
        assert catalog["metadata"]["title"] == "Action / Adventure"

    def test_has_facets(self, catalog):
        """Test that facets are present for filtering."""
        assert "facets" in catalog
        # Categories section has "languages" and "availability" facets
        facet_titles = [f["metadata"]["title"] for f in catalog["facets"]]
        assert "Browse by Language" in facet_titles
        assert "Browse by Availability" in facet_titles

