"""
Internet Archive API integration module.

This module provides a wrapper class for interacting with the Internet Archive
Python library, including search functionality and file URL retrieval for books
and media items.
"""
import os
from internetarchive import get_session, get_files


class ArchiveOrg:
    """Client for communicating with Internet Archive services.

    This class provides methods to search the Internet Archive catalog and
    retrieve download URLs for various media formats. It uses the internetarchive
    Python library with configured S3 credentials for authenticated access.

    Attributes:
        user: An authenticated Internet Archive session object used for all
            API interactions.
    """

    def __init__(self, s3_access: str, s3_secret: str):
        """Initialize the Archive.org client with S3 credentials."""

        config = dict(s3=dict(access=s3_access, secret=s3_secret))
        self.user = get_session(config)

    def get_search_info(self,
                        query: str,
                        preferred_client_ip: str,
                        sorts="",
                        page=1,
                        rows=25) -> (list,
                                     int):
        """Search the Internet Archive and retrieve item metadata.

        This method uses the Archive.org search engine to find items matching
        the given query and returns detailed metadata including lending status,
        format information, and bibliographic data.

        Args:
            query: Search query string in Archive.org search syntax.
                Examples: "title:(pride and prejudice)", "creator:shakespeare"
            preferred_client_ip: IP address of the end user making the request,
                used for access control and regional restrictions.
            sorts: Sort order for results. Examples: "downloads desc",
                "publicdate desc", "title asc". Defaults to "" (relevance).
            page: Page number for pagination, starting at 1. Defaults to 1.
            rows: Number of items to return per page, typically 1-100.
                Defaults to 25.

        Returns:
            A tuple containing:
            - List of dictionaries, where each dict contains metadata for one
              item including fields like title, creator, identifier, format,
              and lending status.
            - Total number of items found matching the query (integer).
        """
        params, items_metadata = dict(page=page, rows=rows), []
        params.update({"application_id": "opds",
                       "preferred_client_id": preferred_client_ip})
        query_metadata = self.user.search_items(query, fields=[
            "format",
            "identifier-access",
            "title",
            "language",
            "publicdate",
            "imagecount",
            "creator",
            "identifier",
            "description",
            "runtime",
            "mediatype",
            "access-restricted-item",
            "external-identifier",
            "lending___available_to_borrow",
            "lending___available_to_browse",
            "lending___max_lendable_copies",
            "lending___users_on_waitlist",
            "lending___active_borrows",
            "lending___active_browses",
            "lending___borrow_expiration",
            "lending___browse_expiration"
        ],
            params=params, sorts=sorts)
        for query_item_metadata in query_metadata:
            items_metadata.append(query_item_metadata)

        return items_metadata, query_metadata.num_found

    @staticmethod
    def get_urls(identifier, glob_pattern):
        """Retrieve download URLs for files in an Archive.org item.

        This method returns download links for files matching the specified
        pattern within an Archive.org item. It handles both single files and
        collections of files (e.g., MP3 audio files).

        Args:
            identifier: The globally unique Archive.org identifier for an item.
                Example: "pride-prejudice_1912_librivox"
            glob_pattern: File pattern to match using glob syntax.
                Examples: "*.pdf", "*.epub", "*mp3", "*.jpg"
                Special case: "*mp3" returns an iterator of all MP3 files.

        Returns:
            - For "*mp3" pattern: An iterator of File objects for all MP3 files
            - For other patterns: A string containing the URL of the first
              matching file
            - Empty list if no files match the pattern
        """
        try:
            if glob_pattern == "*mp3":
                return get_files(identifier, glob_pattern=glob_pattern)
            href = next(
                get_files(
                    identifier,
                    glob_pattern=glob_pattern)).url
            return href
        except StopIteration:
            return []


IA_ADMIN_USER = ArchiveOrg(
    os.environ.get("S3_ACCESS"),
    os.environ.get("S3_SECRET"))