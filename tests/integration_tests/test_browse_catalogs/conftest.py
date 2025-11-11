import json
import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from opds.catalog.factory import CatalogBuilderFactory
from opds.config import DB_PATH, ITEMS_PER_PAGE


@pytest.fixture
def make_mock_ia_admin_user():
    """
    Factory fixture that produces a mocked IA_ADMIN_USER provider
    with configurable keywords + totals for group1 and group2.
    """

    def _make_mock(item_metadata_test_path, total):

        with open(item_metadata_test_path) as f:
            item_metadata_test = json.load(f)

        def mock_get(query, preferred_client_ip, sorts="", page=1, rows=ITEMS_PER_PAGE):
            return item_metadata_test[:rows], total

        with patch("opds.archiveorg.IA_ADMIN_USER") as m:
            m.get_search_info = Mock(side_effect=mock_get)
            yield m

    return _make_mock


@pytest.fixture
def catalog_factory():
    from opds.archiveorg import ArchiveOrgDataProvider
    return CatalogBuilderFactory(DB_PATH, ArchiveOrgDataProvider)
