import json
import pytest
from unittest.mock import Mock, patch
from dataclasses import dataclass
from pathlib import Path

from opds.catalog.factory import AudiobookManifest
from opds.config import ITEMS_PER_PAGE

FIXTURES_DIR = Path("/app/tests/integration_tests/test_audiobook_manifest/files")
AUDIOBOOK_FILES = FIXTURES_DIR / "test_get_files.json"

@dataclass
class File:
    url: str
    title: str
    length: str
    format: str


@pytest.fixture
def expected_files():
    data = json.load(open(AUDIOBOOK_FILES))
    return [File(**item) for item in data]


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

        def mock_get_filese(identifier, glob_pattern="*mp3"):
            return expected_files

        with patch("opds.internet_archive.IA_ADMIN_USER") as m:
            m.get_search_info = Mock(side_effect=mock_get)
            m.get_urls = Mock(side_effect=mock_get_filese)
            yield m

    return _make_mock


@pytest.fixture
def catalog_factory():
    from opds.archiveorg import ArchiveOrgDataProvider
    return AudiobookManifest(ArchiveOrgDataProvider)
