"""
Tests for AudiobookManifest W3C audiobook manifest generation.
"""
import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path("/app/tests/integration_tests/test_audiobook_manifest/files")

AUDIOBOOK_FIXTURE = FIXTURES_DIR / "test_audiobook_manifest.json"
AUDIOBOOK_ITEMS = FIXTURES_DIR / "test_items_metadata_audiobook.json"


@pytest.fixture
def mock_item_metadata(make_mock_ia_admin_user):
    """Mock IA provider for browsing adventure category."""
    yield from make_mock_ia_admin_user(AUDIOBOOK_ITEMS, 1)


class TestAudioBookManifest:
    """
    Tests for AudiobookManifest W3C audiobook manifest generation.

    Validates that manifests conform to W3C audiobook specification with:
    - Proper metadata structure
    - Cover image links
    - Ordered reading list of audio files
    """
    IDENTIFIER = "picture_dorian_gray_1204_librivox"
    PREFERRED_CLIENT_IP = "127.0.0.1"

    @pytest.fixture
    def manifest(self, catalog_factory, mock_item_metadata):
        """Build adventure category browse catalog."""
        return catalog_factory.create_manifest(
            self.IDENTIFIER,
            self.PREFERRED_CLIENT_IP
        ).model_dump(mode='json')

    def test_structure(self, manifest):
        """Test that manifest has required W3C audiobook structure."""
        assert "@context" in manifest
        assert "metadata" in manifest
        assert "links" in manifest
        assert "readingOrder" in manifest

    def test_context(self, manifest):
        """Test that @context points to W3C readium manifest."""
        assert manifest["@context"] == "https://readium.org/webpub-manifest/context.jsonld"

    def test_metadata_structure(self, manifest):
        """Test metadata contains required audiobook fields."""
        metadata = manifest["metadata"]

        # Required fields
        assert "title" in metadata
        assert "identifier" in metadata
        assert "type" in metadata
        assert "language" in metadata
        assert "author" in metadata

        # Optional but expected
        assert "description" in metadata
        assert "published" in metadata
        assert "duration" in metadata

    def test_links_cover_images(self, manifest):
        """Test that cover images have different sizes."""
        links = manifest["links"]

        # Should have at least 2 cover images (thumbnail and full size)
        assert len(links) >= 2

    def test_reading_order_structure(self, manifest):
        """Test readingOrder has correct structure."""
        reading_order = manifest["readingOrder"]

        assert len(reading_order) > 0

        # Check first item structure
        first_item = reading_order[0]
        assert "href" in first_item
        assert "type" in first_item
        assert "title" in first_item
        assert "duration" in first_item

        assert first_item["type"] == "audio/mpeg"

    def test_reading_order_urls(self, manifest):
        """Test readingOrder URLs are valid archive.org links."""
        reading_order = manifest["readingOrder"]

        for item in reading_order:
            assert item["href"].startswith("https://archive.org/download/")
            assert self.IDENTIFIER in item["href"]
            assert item["href"].endswith("_64kb.mp3")

    def test_matches_expected_fixture(self, manifest):
        """Test manifest matches golden file output."""
        with open(AUDIOBOOK_FIXTURE) as f:
            expected = json.load(f)

        # Compare metadata
        assert manifest["metadata"] == expected["metadata"]

        # Compare links (cover images)
        assert len(manifest["links"]) == len(expected["links"])
        assert manifest["links"] == expected["links"]

        # Compare readingOrder
        assert len(manifest["readingOrder"]) == len(expected["readingOrder"])

        for actual, expected_item in zip(manifest["readingOrder"], expected["readingOrder"]):
            assert actual["href"] == expected_item["href"]
            assert actual["type"] == expected_item["type"]
            assert actual["title"] == expected_item["title"]
            assert actual["duration"] == expected_item["duration"]

