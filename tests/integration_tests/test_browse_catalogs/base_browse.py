"""
Base class for browse catalog tests.

Provides common assertions and test structure for all browse catalog tests,
similar to BaseNavigationTest but adapted for browse catalogs with pagination
and facets.
"""
import json
from pathlib import Path
from opds.config import ITEMS_PER_PAGE

FIXTURES_DIR = Path("/app/tests/integration_tests/test_browse_catalogs/files")


class BaseBrowseTest:
    """
    Base class with common BROWSE catalog assertions that are same for all BROWSE endpoints.

    Child classes must override:
    - EXPECTED_FIXTURE: Path to the golden catalog JSON file
    - EXPECTED_SECTION: Section key (e.g., "categories", "languages")
    - EXPECTED_ITEM: Item key within section (e.g., "adventure", "english")
    """

    EXPECTED_FIXTURE = None
    EXPECTED_SECTION = None
    EXPECTED_ITEM = None

    def test_structure(self, catalog):
        """Test that catalog has required OPDS browse structure."""
        assert "@context" in catalog
        assert "metadata" in catalog
        assert "links" in catalog
        assert "publications" in catalog

    def test_metadata_structure(self, catalog):
        """Test metadata contains required pagination fields."""
        metadata = catalog["metadata"]
        assert "title" in metadata
        assert "numberOfItems" in metadata
        assert "itemsPerPage" in metadata
        assert "currentPage" in metadata
        assert metadata["itemsPerPage"] == ITEMS_PER_PAGE
        assert metadata["currentPage"] >= 1

    def test_links_structure(self, catalog):
        """Test links array contains required link relations."""
        link_rels = [link["rel"] for link in catalog["links"]]

        # Common links
        assert "search" in link_rels
        assert "http://opds-spec.org/shelf" in link_rels
        assert "profile" in link_rels
        assert "self" in link_rels

        # Pagination links (if there are results)
        if catalog["metadata"]["numberOfItems"] > 0:
            assert "first" in link_rels
            assert "previous" in link_rels
            assert "next" in link_rels
            assert "last" in link_rels

    def test_publications_structure(self, catalog):
        """Test publications have correct structure."""
        assert len(catalog["publications"]) <= ITEMS_PER_PAGE

        if catalog["publications"]:
            pub = catalog["publications"][0]
            assert "metadata" in pub
            assert "links" in pub
            assert "images" in pub

            # Check metadata fields
            assert "title" in pub["metadata"]
            assert "identifier" in pub["metadata"]
            assert "type" in pub["metadata"]

    def test_self_link_format(self, catalog):
        """Test self link contains correct parameters."""
        self_link = next(l for l in catalog["links"] if l["rel"] == "self")
        assert "type=browse" in self_link["href"]
        if self.EXPECTED_SECTION:
            assert f"section={self.EXPECTED_SECTION}" in self_link["href"]
        if self.EXPECTED_ITEM:
            assert f"item={self.EXPECTED_ITEM}" in self_link["href"]

    def test_matches_expected_fixture(self, catalog):
        """Test catalog matches golden file output."""
        assert self.EXPECTED_FIXTURE is not None, \
            "child test class must define EXPECTED_FIXTURE"

        with open(self.EXPECTED_FIXTURE) as f:
            expected = json.load(f)

        # Compare structure
        assert catalog["metadata"] == expected["metadata"]
        assert catalog["links"] == expected["links"]

        # Compare publications (may need to be flexible about order)
        assert len(catalog["publications"]) == len(expected["publications"])

        # Compare facets if present
        if "facets" in expected:
            assert "facets" in catalog
            assert catalog["facets"] == expected["facets"]
