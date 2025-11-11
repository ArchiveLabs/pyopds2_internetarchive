"""
Unit tests for acquisition_links module.

Tests cover link generation for free books, borrowable books,
external identifier parsing, and edge cases.
"""
import pytest
from unittest.mock import Mock, patch

from opds.acquisition_links import AcquisitionLinks, Formats
from opds.availability import AvailableInfo


class TestFormats:
    """Test Formats dataclass."""

    def test_formats_defaults(self):
        """Test default format values."""
        formats = Formats()
        assert formats.license_lcp == "lcp"
        assert formats.indirect_acquisition_lcp_type == "application/vnd.readium.lcp.license.v1.0+json"
        assert formats.book_type_pdf == "application/pdf"
        assert formats.book_type_epub == "application/epub+zip"

    def test_check_format_mapping(self):
        """Test format checking dictionary."""
        assert Formats.check_format["pdf"] == ("application/pdf", "lcp_pdf")
        assert Formats.check_format["epub"] == ("application/epub+zip", "lcp_epub")
        assert Formats.check_format["lcpau"] == ("application/audiobook+lcp", "lcp_audiobook")
        assert Formats.check_format["lcpdf"] == ("application/pdf+lcp", "lcp_pdf")


class TestAcquisitionLinks:
    """Test AcquisitionLinks class."""

    @pytest.fixture
    def available_info(self):
        """Create mock AvailableInfo."""
        return AvailableInfo(
            available_to_browse=True,
            available_to_borrow=True,
            available_to_waitlist=False,
            is_lendable=True,
            is_previewable=True,
            num_waitlist=0
        )

    @pytest.fixture
    def free_book_links(self, available_info):
        """Create AcquisitionLinks instance for free book."""
        return AcquisitionLinks(
            access_restricted_item=None,
            identifier="test_book_123",
            mediatype="texts",
            book_format=["Remediated EPUB", "PDF"],
            external_identifier=None,
            available_info=available_info
        )

    @pytest.fixture
    def borrowable_book_links(self, available_info):
        """Create AcquisitionLinks instance for borrowable book."""
        return AcquisitionLinks(
            access_restricted_item="1",
            identifier="borrow_book_456",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:lcp:borrow_book_456:pdf:a4a1de5e-3c50-4b97-b3c9-4defe677b5b6",
            available_info=available_info
        )

    def test_init(self, available_info):
        """Test AcquisitionLinks initialization."""
        links = AcquisitionLinks(
            access_restricted_item="1",
            identifier="test_id",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:lcp:test:pdf:uuid",
            available_info=available_info
        )

        assert links.access_restricted_item == "1"
        assert links.identifier == "test_id"
        assert links.mediatype == "texts"
        assert links.format == ["PDF"]
        assert links.external_identifier == "urn:lcp:test:pdf:uuid"
        assert links.available_info == available_info


class TestFreeBookLinks:
    """Test free book link generation."""

    @pytest.fixture
    def available_info(self):
        return AvailableInfo(
            available_to_browse=True,
            available_to_borrow=True,
            available_to_waitlist=False,
            is_lendable=True,
            is_previewable=True,
            num_waitlist=0
        )

    def test_free_texts_with_epub(self, available_info):
        """Test free text book with EPUB format."""
        links_gen = AcquisitionLinks(
            access_restricted_item=None,
            identifier="free_book_001",
            mediatype="texts",
            book_format=["Remediated EPUB", "PDF"],
            external_identifier=None,
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        # Should have self link + PDF + EPUB = 3 links
        assert len(links) == 3

        # Check self link
        assert links[0].rel == "self"
        assert links[0].type == "application/opds-publication+json"
        assert "free_book_001" in links[0].href
        assert "opds=1" not in links[0].href  # Free books don't have opds=1

        # Check PDF link
        pdf_link = next(l for l in links if l.type == "application/pdf")
        assert pdf_link.rel == "http://opds-spec.org/acquisition/open-access"
        assert "/book/free_book_001?glob_pattern=*pdf" in pdf_link.href
        assert pdf_link.properties["availability"]["state"] == "available"

        # Check EPUB link
        epub_link = next(l for l in links if l.type == "application/epub+zip")
        assert epub_link.rel == "http://opds-spec.org/acquisition/open-access"
        assert "/book/free_book_001?glob_pattern=*epub" in epub_link.href
        assert epub_link.properties["availability"]["state"] == "available"

    def test_free_texts_without_epub(self, available_info):
        """Test free text book without EPUB format."""
        links_gen = AcquisitionLinks(
            access_restricted_item=None,
            identifier="free_book_002",
            mediatype="texts",
            book_format=["PDF"],  # No Remediated EPUB
            external_identifier=None,
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        # Should have self link + PDF only = 2 links
        assert len(links) == 2

        # Should not have EPUB link
        epub_links = [l for l in links if l.type == "application/epub+zip"]
        assert len(epub_links) == 0

    def test_free_audio(self, available_info):
        """Test free audiobook."""
        links_gen = AcquisitionLinks(
            access_restricted_item=None,
            identifier="audio_book_001",
            mediatype="audio",
            book_format=[],
            external_identifier=None,
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        # Should have self link + audiobook = 2 links
        assert len(links) == 2

        # Check audiobook link
        audio_link = next(l for l in links if l.type == "application/audiobook+json")
        assert audio_link.rel == "http://opds-spec.org/acquisition/open-access"
        assert "/audiobooks/audio_book_001" in audio_link.href
        assert audio_link.properties["availability"]["state"] == "available"


class TestBorrowableBookLinks:
    """Test borrowable book link generation."""

    @pytest.fixture
    def available_info(self):
        return AvailableInfo(
            available_to_browse=True,
            available_to_borrow=True,
            available_to_waitlist=False,
            is_lendable=True,
            is_previewable=True,
            num_waitlist=0
        )

    @pytest.fixture
    def unavailable_info(self):
        return AvailableInfo(
            available_to_browse=False,
            available_to_borrow=False,
            available_to_waitlist=True,
            is_lendable=True,
            is_previewable=False,
            num_waitlist=5
        )

    @patch('opds.acquisition_links.check_availability')
    def test_borrowable_book_available(self, mock_check, available_info):
        """Test borrowable book when available."""
        mock_check.return_value = {"state": "available"}

        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="borrow_001",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:lcp:borrow_001:pdf:uuid-123",
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        # Should have self link + borrow link = 2 links
        assert len(links) == 2

        # Check self link has opds=1
        assert "opds=1" in links[0].href

        # Check borrow link
        borrow_link = links[1]
        assert borrow_link.rel == "http://opds-spec.org/acquisition/borrow"
        assert "opds=1" in borrow_link.href
        assert "identifier=borrow_001" in borrow_link.href
        assert "action=webpub" in borrow_link.href

        # Check indirect acquisition
        assert "indirectAcquisition" in borrow_link.properties
        indirect = borrow_link.properties["indirectAcquisition"]
        assert len(indirect) == 1
        assert indirect[0]["type"] == "application/vnd.readium.lcp.license.v1.0+json"
        assert indirect[0]["child"][0]["type"] == "application/pdf"

    @patch('opds.acquisition_links.check_availability')
    def test_borrowable_book_unavailable(self, mock_check, unavailable_info):
        """Test borrowable book when unavailable."""
        mock_check.return_value = {"state": "unavailable"}

        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="borrow_002",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:lcp:borrow_002:pdf:uuid-456",
            available_info=unavailable_info
        )

        links = links_gen.create_acquisition_links()

        # Borrow link should have empty href
        borrow_link = next(l for l in links if l.rel == "http://opds-spec.org/acquisition/borrow")
        assert borrow_link.href == ""
        assert borrow_link.properties["availability"]["state"] == "unavailable"

    @patch('opds.acquisition_links.check_availability')
    def test_borrowable_book_no_external_identifier(self, mock_check, available_info):
        """Test borrowable book without external identifier."""
        mock_check.return_value = {"state": "available"}

        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="borrow_003",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier=None,  # No external ID
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        # Should still create link but with empty href
        borrow_link = next(l for l in links if l.rel == "http://opds-spec.org/acquisition/borrow")
        assert borrow_link.href == ""

    @patch('opds.acquisition_links.check_availability')
    def test_borrowable_book_different_filename_base(self, mock_check, available_info):
        """Test borrowable book with different filename base."""
        mock_check.return_value = {"state": "available"}

        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="borrow_004",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:lcp:different_name:pdf:uuid-789",
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        borrow_link = next(l for l in links if l.rel == "http://opds-spec.org/acquisition/borrow")
        assert "filename_base=different_name" in borrow_link.href

    @patch('opds.acquisition_links.check_availability')
    def test_borrowable_book_same_filename_base(self, mock_check, available_info):
        """Test borrowable book where filename_base matches identifier."""
        mock_check.return_value = {"state": "available"}

        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="borrow_005",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:lcp:borrow_005:pdf:uuid-abc",
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        borrow_link = next(l for l in links if l.rel == "http://opds-spec.org/acquisition/borrow")
        assert "filename_base=" not in borrow_link.href

    @patch('opds.acquisition_links.check_availability')
    def test_borrowable_book_multiple_formats(self, mock_check, available_info):
        """Test borrowable book with multiple formats."""
        mock_check.return_value = {"state": "available"}

        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="borrow_006",
            mediatype="texts",
            book_format=["PDF", "EPUB"],
            external_identifier=[
                "urn:lcp:borrow_006:pdf:uuid-1",
                "urn:lcp:borrow_006:epub:uuid-2"
            ],
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        borrow_link = next(l for l in links if l.rel == "http://opds-spec.org/acquisition/borrow")

        # Should have two indirect acquisitions
        indirect = borrow_link.properties["indirectAcquisition"]
        assert len(indirect) == 2

        # Check both formats present
        types = [ia["child"][0]["type"] for ia in indirect]
        assert "application/pdf" in types
        assert "application/epub+zip" in types


class TestExternalIdentifierParsing:
    """Test external identifier parsing."""

    @pytest.fixture
    def available_info(self):
        return AvailableInfo(
            available_to_browse=True,
            available_to_borrow=True,
            available_to_waitlist=False,
            is_lendable=True,
            is_previewable=True,
            num_waitlist=0
        )

    def test_parse_single_pdf_identifier(self, available_info):
        """Test parsing single PDF external identifier."""
        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="test",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:lcp:filename:pdf:uuid-123",
            available_info=available_info
        )

        result = links_gen._parse_external_identifier()

        assert len(result) == 1
        info = result[0]
        assert info.book_format == "lcp_pdf"
        assert info.book_type == "application/pdf"
        assert info.indirect_acquisition_type == "application/vnd.readium.lcp.license.v1.0+json"
        assert info.filename_base == "filename"

    def test_parse_single_epub_identifier(self, available_info):
        """Test parsing single EPUB external identifier."""
        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="test",
            mediatype="texts",
            book_format=["EPUB"],
            external_identifier="urn:lcp:mybook:epub:uuid-456",
            available_info=available_info
        )

        result = links_gen._parse_external_identifier()

        info = result[0]
        assert info.book_format == "lcp_epub"
        assert info.book_type == "application/epub+zip"
        assert info.filename_base == "mybook"

    def test_parse_audiobook_identifier(self, available_info):
        """Test parsing audiobook external identifier."""
        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="test",
            mediatype="audio",
            book_format=[],
            external_identifier="urn:lcp:audiobook:lcpau:uuid-789",
            available_info=available_info
        )

        result = links_gen._parse_external_identifier()

        info = result[0]
        assert info.book_format == "lcp_audiobook"
        assert info.book_type == "application/audiobook+lcp"
        assert info.filename_base == "audiobook"

    def test_parse_lcpdf_identifier(self, available_info):
        """Test parsing lcpdf external identifier."""
        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="test",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:lcp:pdfbook:lcpdf:uuid-abc",
            available_info=available_info
        )

        result = links_gen._parse_external_identifier()

        info = result[0]
        assert info.book_format == "lcp_pdf"
        assert info.book_type == "application/pdf+lcp"
        assert info.filename_base == "pdfbook"

    def test_parse_multiple_identifiers(self, available_info):
        """Test parsing list of external identifiers."""
        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="test",
            mediatype="texts",
            book_format=["PDF", "EPUB"],
            external_identifier=[
                "urn:lcp:book1:pdf:uuid-1",
                "urn:lcp:book1:epub:uuid-2"
            ],
            available_info=available_info
        )

        result = links_gen._parse_external_identifier()

        assert len(result) == 2
        assert result[0].book_type == "application/pdf"
        assert result[1].book_type == "application/epub+zip"

    def test_parse_non_lcp_identifier(self, available_info):
        """Test parsing non-LCP external identifier returns None."""
        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="test",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier="urn:isbn:1234567890",
            available_info=available_info
        )

        result = links_gen._parse_external_identifier()

        assert len(result) == 1
        assert result[0] is None

    def test_parse_mixed_identifiers(self, available_info):
        """Test parsing mix of LCP and non-LCP identifiers."""
        links_gen = AcquisitionLinks(
            access_restricted_item="1",
            identifier="test",
            mediatype="texts",
            book_format=["PDF"],
            external_identifier=[
                "urn:lcp:book:pdf:uuid-1",
                "urn:isbn:1234567890",
                "urn:lcp:book:epub:uuid-2"
            ],
            available_info=available_info
        )

        result = links_gen._parse_external_identifier()

        assert len(result) == 3
        assert result[0] is not None
        assert result[1] is None  # non-LCP
        assert result[2] is not None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def available_info(self):
        return AvailableInfo(
            available_to_browse=True,
            available_to_borrow=True,
            available_to_waitlist=False,
            is_lendable=True,
            is_previewable=True,
            num_waitlist=0
        )

    def test_empty_book_format(self, available_info):
        """Test with empty book format list."""
        links_gen = AcquisitionLinks(
            access_restricted_item=None,
            identifier="test",
            mediatype="texts",
            book_format=[],
            external_identifier=None,
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        # Should still have self link and PDF (always added for texts)
        assert len(links) == 2
        assert any(l.type == "application/pdf" for l in links)

    def test_unknown_mediatype(self, available_info):
        """Test with unknown mediatype."""
        links_gen = AcquisitionLinks(
            access_restricted_item=None,
            identifier="test",
            mediatype="video",  # Unknown type
            book_format=[],
            external_identifier=None,
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        # Should only have self link
        assert len(links) == 1
        assert links[0].rel == "self"

    def test_static_title_present(self, available_info):
        """Test that all links have static title."""
        links_gen = AcquisitionLinks(
            access_restricted_item=None,
            identifier="test",
            mediatype="texts",
            book_format=["Remediated EPUB"],
            external_identifier=None,
            available_info=available_info
        )

        links = links_gen.create_acquisition_links()

        for link in links:
            assert link.title == "Internet Archive"
