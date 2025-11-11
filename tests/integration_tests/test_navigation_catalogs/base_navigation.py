import json
from pathlib import Path

FIXTURES_DIR = Path("/app/tests/integration_tests/test_navigation_catalogs/files")


class BaseNavigationTest:
    """
    Base class with common NAV catalog assertions that are same for all NAV endpoints.
    """

    EXPECTED_FIXTURE = None  # child class must override

    def test_structure(self, catalog):
        assert "@context" in catalog
        assert "metadata" in catalog
        assert "links" in catalog
        assert "navigation" in catalog
        assert "groups" in catalog

    def test_matches_expected_fixture(self, catalog):
        assert self.EXPECTED_FIXTURE is not None, "child test class must define EXPECTED_FIXTURE"
        with open(self.EXPECTED_FIXTURE) as f:
            exp = json.load(f)

        assert catalog["metadata"] == exp["metadata"]
        assert catalog["links"] == exp["links"]
        assert catalog["navigation"] == exp["navigation"]
        assert catalog["groups"] == exp["groups"]
