import json
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from opds.catalog.factory import CatalogBuilderFactory
from opds.config import DB_PATH, ITEMS_PER_GROUP


@pytest.fixture
def make_mock_ia_admin_user():
    """
    Factory fixture that produces a mocked IA_ADMIN_USER provider
    with configurable keywords + totals for group1 and group2.
    """

    def _make_mock(g1_info, g2_info):

        with open(g1_info["path"]) as f:
            g1 = json.load(f)
        with open(g2_info["path"]) as f:
            g2 = json.load(f)

        def mock_get(query, preferred_client_ip, sorts="", page=1, rows=ITEMS_PER_GROUP):
            q = query.lower()
            if g1_info["keyword"] in q:
                return g1[:rows], g1_info["total"]
            if g2_info["keyword"] in q:
                return g2[:rows], g2_info["total"]
            return [], 0

        with patch("opds.archiveorg.IA_ADMIN_USER") as m:
            m.get_search_info = Mock(side_effect=mock_get)
            yield m

    return _make_mock


@pytest.fixture
def catalog_factory():
    from opds.archiveorg import ArchiveOrgDataProvider
    return CatalogBuilderFactory(DB_PATH, ArchiveOrgDataProvider)
