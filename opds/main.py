"""OPDS catalog service API using FastAPI.

This module implements a FastAPI-based web service that provides OPDS
(Open Publication Distribution System) catalogs for Internet Archive content.
It supports navigation, browsing, searching, and faceted filtering of books
and audiobooks.

The service provides endpoints for:
- Main catalog navigation
- Dynamic catalog generation with facets
- Authentication document retrieval
- Audiobook manifest generation
- Direct book download redirects
- Health check monitoring
"""
import logging
import sys
from typing import Optional, List

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from opds.config import AUTHENTICATION_DOCUMENT, DB_PATH
from opds.archiveorg import ArchiveOrgDataProvider
from opds.internet_archive import IA_ADMIN_USER

from opds.catalog.factory import CatalogBuilderFactory, AudiobookManifest
from opds.catalog.types import CatalogRequest, CatalogType

app = FastAPI()

# Initialize builder
builder = CatalogBuilderFactory(
    db_path=DB_PATH,
    provider=ArchiveOrgDataProvider
)

# Configure CORS with permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin"],
    expose_headers=[
        "Content-Type",
        "Authorization"],
)


@app.get("/")
async def main_page(request: Request):
    """Serve the main OPDS catalog navigation page.

    This endpoint returns the root navigation catalog without authentication.

    Args:
        request: FastAPI Request object containing HTTP request metadata,
            including headers for client IP extraction.

    Returns:
        JSONResponse containing the main navigation catalog in OPDS JSON format
        with status 200 and media type "application/opds+json".
    """
    preferred_client_ip = request.headers.get("X-Real-Ip")
    catalog_request = CatalogRequest(
        catalog_type=CatalogType.NAVIGATION.value,
        nav_key="main",
        preferred_client_ip=preferred_client_ip
    )
    catalog = builder.build_catalog(catalog_request)

    return JSONResponse(
        content=catalog.model_dump(mode='json'),
        status_code=200,
        media_type="application/opds+json"
    )


@app.get("/catalog")
async def get_catalog(
        request: Request,
        # Catalog type
        type: str = Query(
            "navigation",
            description="Catalog type: navigation, browse, search"),

        # Navigation parameters
        nav_key: Optional[str] = Query(
            None, description="Navigation key (for type=navigation)"),

        # Browse parameters
        section: Optional[str] = Query(
            None, description="Section key (for type=browse)"),
        item: Optional[str] = Query(
            None, description="Item key (for type=browse)"),

        # Search parameters
        query: Optional[str] = Query(
            None, description="Search query (for type=search)"),

        # Facet parameters as LISTS
        facet_section: Optional[List[str]] = Query(
            default=[], description="Facet section keys (e.g., languages, categories)"),
        facet_item: Optional[List[str]] = Query(
            default=[], description="Facet item keys (e.g., english, romance)"),

        # Common parameters
        page: int = Query(1, description="Page"),
):
    """
    Universal OPDS catalog endpoint with facets using lists.

    This endpoint generates dynamic OPDS catalogs based on the requested type
    (navigation, browse, or search) and applies optional facet filters. Facets
    allow users to refine results by multiple dimensions such as language,
    category, and availability.

    Args:
        request: FastAPI Request object for extracting client IP from headers.
        type: Catalog type - "navigation", "browse", or "search".
            Defaults to "navigation".
        nav_key: Navigation key for type=navigation (e.g., "main", "genres").
        section: Section key for type=browse (e.g., "categories", "subjects").
        item: Item key within section for type=browse (e.g., "romance", "fiction").
        query: Search query string for type=search.
        facet_section: List of facet section identifiers to apply as filters.
            Must correspond by index with facet_item.
        facet_item: List of facet item identifiers to apply as filters.
            Must correspond by index with facet_section.
        page: Page number for paginated results, starting at 1. Defaults to 1.

    Returns:
        JSONResponse containing the requested catalog in OPDS JSON format
        with status 200 and media type "application/opds+json".


    Examples:
        - Navigation:
          /catalog?type=navigation&nav_key=main

        - Browse:
          /catalog?type=browse&section=categories&item=romance

        - Browse + Language facet:
          /catalog?type=browse&section=categories&item=romance&facet_section=languages&facet_item=english

        - Browse + Multiple facets (Language + Availability):
          /catalog?type=browse&section=categories&item=romance&facet_section=languages&facet_item=english&facet_section=availability&facet_item=available-now

        - Search:
          /catalog?type=search&query=python

        - Search + Multiple facets:
          /catalog?type=search&query=python&facet_section=languages&facet_item=english&facet_section=categories&facet_item=textbooks

    Note: facet_section and facet_item must have same length and correspond by index:
        facet_section[0] + facet_item[0] = first facet
        facet_section[1] + facet_item[1] = second facet
    """
    preferred_client_ip = request.headers.get("X-Real-Ip")

    applied_facets = {}
    if facet_section:
        # Build applied_facets dict from lists
        for i in range(len(facet_section)):
            applied_facets[facet_section[i]] = facet_item[i]

    # Browse with facets
    catalog_request = CatalogRequest(
        catalog_type=type,
        nav_key=nav_key,
        section=section,
        item=item,
        query=query,
        page=page,
        preferred_client_ip=preferred_client_ip,
        applied_facets=applied_facets,
    )
    catalog = builder.build_catalog(catalog_request)

    return JSONResponse(
        content=catalog.model_dump(mode='json'),
        status_code=200,
        media_type="application/opds+json"
    )


@app.get("/authentication_document")
async def authentication_document():
    """Return the OPDS authentication document.

    This endpoint provides the authentication document that describes how
    OPDS clients should authenticate with the service, including OAuth
    endpoints, login field labels, and related links.

    Returns:
        JSONResponse containing the authentication document with status 200
        and media type "application/opds-authentication+json".
    """
    return JSONResponse(content=AUTHENTICATION_DOCUMENT,
                        media_type="application/opds-authentication+json",
                        status_code=200)


@app.get("/audiobooks/{identifier}")
async def audiobooks_manifest(request: Request, identifier: str, ):
    """Generate a W3C Audiobook manifest for a specific audiobook.

    This endpoint creates a W3C-compliant audiobook manifest that describes
    the structure, metadata, and reading order of an audiobook from Internet
    Archive.

    Args:
        request: FastAPI Request object for extracting client IP from
            X-Forwarded-For header.
        identifier: Internet Archive identifier for the audiobook item
            (e.g., "pride-prejudice_librivox").

    Returns:
        JSONResponse containing the W3C audiobook manifest with status 200.
    """
    audiobook_manifest = AudiobookManifest(ArchiveOrgDataProvider)
    preferred_client_ip = request.headers.get("X-Forwarded-For")

    catalog = audiobook_manifest.create_manifest(
        identifier, preferred_client_ip)

    return JSONResponse(
        content=catalog.model_dump(mode='json'),
        status_code=200,
    )


@app.get("/book/{identifier}")
async def get_free_book(
        identifier: str,
        glob_pattern: str = Query(default=None)
):
    """Redirect to the download URL for a free book or media file.

    This endpoint retrieves the direct download URL from Internet Archive
    for a specific file within an item and returns an HTTP 302 redirect
    to that URL.

    Args:
        identifier: Internet Archive identifier for the book item
            (e.g., "moby-dick-1851").
        glob_pattern: File pattern to match using glob syntax
            (e.g., "*.pdf", "*.epub", "*.mp3"). If None, returns the
            first available file.

    Returns:
        RedirectResponse with status 302 redirecting to the Internet Archive
        download URL.
    """
    url = IA_ADMIN_USER.get_urls(identifier, glob_pattern)
    return RedirectResponse(url=url, status_code=302)


@app.get('/healthcheck')
async def health_check():
    """Health check endpoint for service monitoring.

    This endpoint provides a simple health check that returns a 200 status
    code when the service is running. It's typically used by container
    orchestrators, load balancers, and monitoring systems.

    Returns:
        JSONResponse with status 200 containing a health status object.
    """
    health_status = {
        'status': 'healthy',
        'message': 'Service is running',
    }

    status_code = 200
    return JSONResponse(content=health_status, status_code=status_code)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s %(threadName)s :%(message)s',
        handlers=[
            logging.StreamHandler(
                sys.stdout)])

    # Run the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="debug"
    )
