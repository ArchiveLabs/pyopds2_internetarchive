import requests
from typing import List, Optional
from pydantic import Field

from opds2 import (
    DataProvider,
    DataProviderRecord,
    SearchRequest,
    SearchResponse,
    Contributor,
    Metadata,
    Link
)

class InternetArchiveDataRecord(DataProviderRecord):
    """
    Pydantic model for a single Internet Archive search result.
    Fields mirror the archive.org advancedsearch response.
    """
    identifier: str = Field(..., description="Internet Archive item identifier (e.g. 'example_item')")
    title: str = Field(..., min_length=1, description="Title of the item")
    creator: Optional[List[str]] = Field(None, description="List of creators/authors of the item")
    description: Optional[str] = Field(None, description="Description of the item")
    language: Optional[List[str]] = Field(None, description="Languages of the item")
    mediatype: Optional[str] = Field(None, description="Media type of the item (e.g. 'texts', 'movies')")
    year: Optional[int] = Field(None, description="Year of publication or release")
    coverurl: Optional[str] = Field(None, description="URL to the cover image of the item")
    
    @property
    def type(self) -> str:
        return "http://schema.org/Book"
    
    def links(self) -> List[Link]:
        href = f"https://archive.org/details/{self.identifier}"
        return [
            Link(
                href=href,
                rel="http://opds-spec.org/acquisition",
                type="text/html",
                title="Internet Archive Item Page"
            )
        ]
        
    def images(self) -> Optional[List[Link]]:
        if self.coverurl:
            return [Link(href=self.coverurl, type="image/jpeg", rel="cover")]
        if self.identifier:
            from pyopds2_internetarchive import InternetArchiveDataProvider
            fallback = InternetArchiveDataProvider._get_cover_url(self.identifier)
            return [Link(href=fallback, type="image/jpeg", rel="cover")]
        return None
    
    def metadata(self) -> Metadata:
        authors = None
        if self.creator:
            authors = [Contributor(name=creator) for creator in self.creator]
        return Metadata(
            title=self.title or self.identifier,
            type=self.type,
            author=authors,
            language=self.language,
            description=self.description,
            published=self.year if self.year else None
        )

class InternetArchiveDataProvider(DataProvider):
    """
    Data provider for Internet Archive (archive.org) using their advanced search API. 
    """
    URL = "https://archive.org"
    TITLE = "Internet Archive OPDS Service"
    CATALOG_URL = "/opds/catalog"
    SEARCH_URL = "/opds/search{?query}"
    SEARCH_TIMEOUT = 10  # seconds
    
    @staticmethod
    def _get_cover_url(identifier: str) -> str:
        """Generate the cover URL for an Internet Archive item."""
        return f"https://archive.org/download/{identifier}/{identifier}_thumb.jpg"
    
    @staticmethod
    def search(
        query: str,
        limit: int = 50,
        offset: int = 0,
        sort: Optional[str] = None
        ) -> SearchResponse:
        """Use the archive.org advancedsearch endpoint to find items.
        Returns a SearchResponse containing records and metadata.
        
        Args:
            query (str): Search query string.
            limit (int, optional): Maximum number of results to return. Defaults to 50.
            offset (int, optional): Number of results to skip. Defaults to 0.
            sort (Optional[str], optional): Sort field. Defaults to None.

        Returns:
            SearchResponse: SearchResponse object containing records and total count.
        """
        q = query if query else "mediatype:texts"
        page = (offset // limit) + 1 if limit else 1
        fields=[
            "identifier",
            "title",
            "creator",
            "language",
            "mediatype",
            "year",
            "description",
        ]
        params = {
            "q": q,
            "fl[]": fields,
            "rows": limit,
            "page": page,
            "output": "json"
        }
        if sort:
            params["sort[]"] = sort
            
        r = requests.get(
            f"{InternetArchiveDataProvider.URL}/advancedsearch.php",
            params=params,
            timeout=InternetArchiveDataProvider.SEARCH_TIMEOUT
        )
        r.raise_for_status()
        data = r.json()
        resp = data.get("response", {})
        docs = resp.get("docs", [])
        total = resp.get("numFound", 0)
        
        records: List[InternetArchiveDataRecord] = []
        for doc in docs:
            doc = dict(doc)
            # coerce fields that may be returned as a single string into lists
            if "creator" in doc and isinstance(doc["creator"], str):
                doc["creator"] = [doc["creator"]]
            if "language" in doc and isinstance(doc["language"], str):
                doc["language"] = [doc["language"]]
            # set fallback cover only when identifier exists
            if "identifier" in doc:
                doc.setdefault("coverurl", InternetArchiveDataProvider._get_cover_url(doc["identifier"]))
            records.append(InternetArchiveDataRecord.model_validate(doc))
        return SearchResponse(records, int(total or 0), SearchRequest(query, limit, offset, sort))
