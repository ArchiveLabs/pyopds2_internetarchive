from collections import namedtuple
from opds.internet_archive import IA_ADMIN_USER


ReturnLink = namedtuple("TestReturnLink", ["url"])


def simple_generator():
    yield ReturnLink("http://test.pdf")


def test_get_urls_mp3(mocker):
    mock_get_files = mocker.patch(
        "opds.internet_archive.get_files")
    mock_get_files.return_value = None

    result = IA_ADMIN_USER.get_urls("test", "*mp3")
    assert result is None


def test_get_urls_pdf(mocker):
    mock_get_files = mocker.patch(
        "opds.internet_archive.get_files")

    generator = simple_generator()
    mock_get_files.return_value = generator
    result = IA_ADMIN_USER.get_urls("test", "*pdf")

    assert result == "http://test.pdf"
