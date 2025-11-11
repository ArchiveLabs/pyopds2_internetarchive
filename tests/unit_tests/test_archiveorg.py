import pytest

from opds.archiveorg import (
    ArchiveOrgDataRecord,
    ArchiveOrgDataProvider,
    _create_record
)


@pytest.fixture()
def sample_item_metadata():
    """Sample metadata dict from archive.org search result."""
    return {
        "identifier": "test_book_123",
        "mediatype": "texts",
        "title": "Test Book Title",
        "publicdate": "2023-01-15",
        "imagecount": 250,
        "creator": "Test Author",
        "description": "A test book description",
        "runtime": "1:30:45",
        "language": "eng",
        "access-restricted-item": "true",
        "format": ["PDF", "EPUB"],
        "external-identifier": "urn:lcp:test:pdf:abc123",
        "lending___available_to_borrow": True,
        "lending___available_to_browse": False,
        "lending___max_lendable_copies": 5,
        "lending___users_on_waitlist": 2,
        "lending___active_borrows": 3,
        "lending___active_browses": 0,
        "lending___borrow_expiration": None,
        "lending___browse_expiration": None
    }


@pytest.fixture()
def sample_audiobook_metadata():
    """Sample audiobook metadata from archive.org."""
    return {
        "identifier": "audio_book_456",
        "mediatype": "audio",
        "title": "Test Audiobook",
        "publicdate": "2024-03-20",
        "creator": ["Author One", "Author Two"],
        "description": ["Line 1 description", "Line 2 description"],
        "runtime": "2:15:30",
        "language": ["eng", "fre"],
        "format": ["VBR MP3"],
    }


class TestArchiveOrgDataRecord:
    """Test cases for ArchiveOrgDataRecord model."""

    def test_record_creation(self, sample_item_metadata):
        """Test basic record creation from metadata."""
        record = _create_record(sample_item_metadata)

        assert isinstance(record, ArchiveOrgDataRecord)
        assert record.raw_identifier == "test_book_123"
        assert record.title == "Test Book Title"
        assert record.mediatype == "texts"
        assert record.numberOfPages == 250

    def test_type_property_book(self, sample_item_metadata):
        """Test type property returns Book schema for texts."""
        record = _create_record(sample_item_metadata)
        assert record.type == "http://schema.org/Book"

    def test_type_property_audiobook(self, sample_audiobook_metadata):
        """Test type property returns Audiobook schema for audio."""
        record = _create_record(sample_audiobook_metadata)
        assert record.type == "http://schema.org/Audiobook"

    def test_identifier_property(self, sample_item_metadata):
        """Test identifier property generates correct archive.org URL."""
        record = _create_record(sample_item_metadata)
        expected = "https://archive.org/details/test_book_123"
        assert record.identifier == expected

    @pytest.mark.parametrize("runtime, expected", [
        ("1:33:33", 5613.0),
        ("33:33", 2013.0),
        ("33", 33.0),
        ("2:15:30", 8130.0),
        ("", None),
        (None, None),
    ])
    def test_duration_conversion(self, runtime, expected):
        """Test runtime string conversion to seconds."""
        record = ArchiveOrgDataRecord(
            raw_identifier="test",
            duration=runtime
        )
        assert record.duration == expected

    @pytest.mark.parametrize("input_lang, expected", [
        ('eng', 'en'),
        ('fre', 'fr'),
        ('ger', 'de'),
        ('chi', 'zh'),
        ('dut', 'nl'),
        ('jpn', 'ja'),
        ('kor', 'ko'),
        ('pol', 'pl'),
        ('gre', 'el'),
        ('ukr', 'uk'),
        ('por', 'pt'),
        ('rus', 'ru'),
        ('Italian', 'it'),
        ('Spanish', 'es'),
        ('Latin', 'la'),
        ('Dutch', 'nl'),
        ('Chinese', 'zh'),
        ('Polish', 'pl'),
        ('Ukrainian', 'uk'),
        ('Portuguese', 'pt'),
        ('', None),
        ('invalid_lang', None),
    ])
    def test_language_conversion_single(self, input_lang, expected):
        """Test language code normalization to ISO 639-1."""
        record = ArchiveOrgDataRecord(
            raw_identifier="test",
            language=input_lang
        )
        assert record.language == expected

    def test_language_conversion_list(self):
        """Test language conversion with list input."""
        record = ArchiveOrgDataRecord(
            raw_identifier="test",
            language=['eng', 'fre', 'invalid']
        )
        assert record.language == ['en', 'fr']

    def test_language_conversion_empty_list(self):
        """Test language conversion returns None for empty list."""
        record = ArchiveOrgDataRecord(
            raw_identifier="test",
            language=['', '   ', 'invalid']
        )
        assert record.language is None

    @pytest.mark.parametrize("description, expected", [
        ("Simple description", "Simple description"),
        (["Line 1", "Line 2"], "Line 1<br><br>Line 2"),
        (["Line with\nnewline"], "Line with<br />newline"),
        ("", ""),
        (None, None),
    ])
    def test_description_normalization(self, description, expected):
        """Test description field normalization."""
        record = ArchiveOrgDataRecord(
            raw_identifier="test",
            description=description
        )
        assert record.description == expected

    def test_metadata_generation(self, sample_item_metadata):
        """Test metadata() method generates valid OPDS2 Metadata."""
        record = _create_record(sample_item_metadata)
        metadata = record.metadata()

        assert metadata.type == "http://schema.org/Book"
        assert metadata.title == "Test Book Title"
        assert metadata.language == ['en']  # Converted from 'eng'
        assert metadata.numberOfPages == 250
        assert len(metadata.author) == 1
        assert metadata.author[0].name == "Test Author"
        assert metadata.identifier == "https://archive.org/details/test_book_123"

    def test_metadata_with_multiple_authors(self, sample_audiobook_metadata):
        """Test metadata with multiple authors."""
        record = _create_record(sample_audiobook_metadata)
        metadata = record.metadata()

        assert len(metadata.author) == 2
        assert metadata.author[0].name == "Author One"
        assert metadata.author[1].name == "Author Two"

    def test_links_generation(self, sample_item_metadata):
        """Test links() method generates acquisition and sample links."""
        record = _create_record(sample_item_metadata)
        links = record.links()

        assert len(links) > 0
        # Check sample link is present
        sample_link = next((link for link in links if "sample" in link.rel), None)
        assert sample_link is not None
        assert "theater" in sample_link.href

    def test_images_generation(self, sample_item_metadata):
        """Test images() method generates cover image links."""
        record = _create_record(sample_item_metadata)
        images = record.images()

        assert len(images) == 2
        assert all(link.type == "image/jpeg" for link in images)
        assert all("__ia_thumb.jpg" in link.href for link in images)
        assert images[0].height == 1400
        assert images[0].width == 800
        assert images[1].height == 700
        assert images[1].width == 400

    def test_available_info_integration(self, sample_item_metadata):
        """Test AvailableInfo is correctly populated."""
        record = _create_record(sample_item_metadata)

        assert record.available_info is not None
        assert record.available_info.lending_available_to_borrow is True
        assert record.available_info.lending_max_lendable_copies == 5
        assert record.available_info.lending_users_on_waitlist == 2


class TestArchiveOrgDataProvider:
    """Test cases for ArchiveOrgDataProvider."""

    def test_search_basic(self, mocker, sample_item_metadata):
        """Test basic search functionality."""
        mock_get_search_info = mocker.patch(
            "opds.archiveorg.IA_ADMIN_USER.get_search_info"
        )
        mock_get_search_info.return_value = ([sample_item_metadata], 1)

        records, total = ArchiveOrgDataProvider.search(
            query="test query",
            limit=10,
            page=1
        )

        assert len(records) == 1
        assert total == 1
        assert isinstance(records[0], ArchiveOrgDataRecord)
        assert records[0].raw_identifier == "test_book_123"

    def test_search_with_pagination(self, mocker, sample_item_metadata):
        """Test search with pagination parameters."""
        mock_get_search_info = mocker.patch(
            "opds.archiveorg.IA_ADMIN_USER.get_search_info"
        )
        mock_get_search_info.return_value = ([sample_item_metadata] * 5, 50)

        records, total = ArchiveOrgDataProvider.search(
            query="test",
            limit=5,
            page=2,
            sort="title asc"
        )

        assert len(records) == 5
        assert total == 50
        mock_get_search_info.assert_called_once()
        call_kwargs = mock_get_search_info.call_args[1]
        assert call_kwargs['page'] == 2
        assert call_kwargs['rows'] == 5
        assert call_kwargs['sorts'] == "title asc"

    def test_search_with_client_ip(self, mocker, sample_item_metadata):
        """Test search passes preferred_client_ip to IA."""
        mock_get_search_info = mocker.patch(
            "opds.archiveorg.IA_ADMIN_USER.get_search_info"
        )
        mock_get_search_info.return_value = ([sample_item_metadata], 1)

        ArchiveOrgDataProvider.search(
            query="test",
            preferred_client_ip="192.168.1.1"
        )

        call_kwargs = mock_get_search_info.call_args[1]
        assert call_kwargs['preferred_client_ip'] == "192.168.1.1"

    def test_search_parallel_processing(self, mocker):
        """Test search processes multiple records in parallel."""
        # Create multiple test items
        items = [
            {"identifier": f"book_{i}", "title": f"Book {i}"}
            for i in range(10)
        ]

        mock_get_search_info = mocker.patch(
            "opds.archiveorg.IA_ADMIN_USER.get_search_info"
        )
        mock_get_search_info.return_value = (items, 10)

        records, total = ArchiveOrgDataProvider.search(query="test")

        assert len(records) == 10
        assert all(isinstance(r, ArchiveOrgDataRecord) for r in records)
        assert total == 10


class TestCreateRecord:
    """Test cases for _create_record helper function."""

    def test_create_record_minimal(self):
        """Test record creation with minimal metadata."""
        metadata = {"identifier": "minimal_book"}
        record = _create_record(metadata)

        assert record.raw_identifier == "minimal_book"
        assert record.title is None
        assert record.author is None

    def test_create_record_full(self, sample_item_metadata):
        """Test record creation with complete metadata."""
        record = _create_record(sample_item_metadata)

        assert record.raw_identifier == "test_book_123"
        assert record.title == "Test Book Title"
        assert record.author == "Test Author"
        assert record.mediatype == "texts"
        assert record.access_restricted_item == "true"
        assert record.book_format == ["PDF", "EPUB"]

    def test_create_record_with_availability(self, sample_item_metadata):
        """Test availability info is correctly extracted."""
        record = _create_record(sample_item_metadata)

        assert record.available_info.lending_available_to_borrow is True
        assert record.available_info.lending_max_lendable_copies == 5
        assert record.available_info.lending_active_borrows == 3