import pytest
from opds.catalog.types import CatalogRequest, CatalogType
from opds.config import ITEMS_PER_GROUP

from tests.integration_tests.test_navigation_catalogs.base_navigation import BaseNavigationTest, FIXTURES_DIR

NAV_EXPECTED = FIXTURES_DIR / "test_nav_language.json"

GROUP_1 = {
    "path": FIXTURES_DIR / "test_items_metadata_nav_language_g1.json",
    "title": "English",
    "keyword": "english",
    "total": 5250562
}

GROUP_2 = {
    "path": FIXTURES_DIR / "test_items_metadata_nav_language_g2.json",
    "title": "French",
    "keyword": "french",
    "total": 507555
}

@pytest.fixture(autouse=True)
def _apply_mock(make_mock_ia_admin_user):
    """
    automatically patch IA provider for this NAV main suite
    """
    yield from make_mock_ia_admin_user(GROUP_1, GROUP_2)


class TestNavigationLanguage(BaseNavigationTest):
    EXPECTED_FIXTURE = NAV_EXPECTED

    @pytest.fixture
    def catalog(self, catalog_factory):
        req = CatalogRequest(CatalogType.NAVIGATION.value, nav_key="page_languages")
        return catalog_factory.build_catalog(req).model_dump(mode="json")

    def test_metadata_title(self, catalog):
        assert catalog["metadata"]["title"] == "Browse by Language"

    def test_links(self, catalog):
        link_rels = [l["rel"] for l in catalog["links"]]
        assert {"search", "http://opds-spec.org/shelf", "profile", "self"} <= set(link_rels)
        assert next(l for l in catalog["links"] if l["rel"] == "self")["href"] == "/catalog?type=navigation&nav_key=page_languages"

    def test_navigation_items(self, catalog):
        assert len(catalog["navigation"]) == 11

    def test_featured_groups(self, catalog):
        g1, g2 = catalog["groups"]
        assert g1["metadata"]["title"] == GROUP_1["title"]
        assert g1["metadata"]["numberOfItems"] == GROUP_1["total"]
        assert len(g1["publications"]) == ITEMS_PER_GROUP
        assert g2["metadata"]["title"] == GROUP_2["title"]
        assert g2["metadata"]["numberOfItems"] == GROUP_2["total"]
        assert len(g2["publications"]) == ITEMS_PER_GROUP
