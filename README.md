# Archive.org OPDS 2.0 Catalog

A production-ready OPDS 2.0 catalog server for Internet Archive's library, providing seamless access to books and audiobooks through standardized OPDS feeds.


## Architecture

### Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **pyopds2**: OPDS 2.0 library ([pyopds2](https://github.com/ArchiveLabs/pyopds2))
- **Internet Archive API**: Direct integration with archive.org search
- **Pydantic**: Data validation and serialization
- **Uvicorn**: ASGI server

### Project Structure

```
.
├── main.py                    # FastAPI application and endpoints
├── opds/
│   ├── catalog/              # Catalog building system
│   │   ├── base.py          # Abstract base catalog builder
│   │   ├── browse.py        # Browse catalog with facets
│   │   ├── navigation.py    # Navigation catalog with menus
│   │   ├── search.py        # Search catalog with results
│   │   ├── types.py         # Type definitions and models
│   │   └── factory.py       # Catalog builder factory
│   ├── archiveorg.py         # Archive.org data provider and records
│   ├── acquisition_links.py  # OPDS acquisition link generation
│   ├── availability.py       # Book availability info
│   ├── internet_archive.py   # IA API client
│   └── config.py            # Configuration constants
├── database/
│   ├── interfaces.py         # DB interface for navigation structure
│   └── db.json              # Navigation and query definitions
└── README.md
```

## Core Components

### 1. Catalog Builder System (`opds/catalog/`)

The catalog building system uses the **Factory Pattern** and **Template Method Pattern** for flexible, maintainable OPDS feed generation.

**Architecture:**
- `factory.py`: CatalogBuilderFactory selects appropriate builder based on request type
- `base.py`: BaseCatalogBuilder defines common structure using template method pattern
- `navigation.py`: NavigationCatalogBuilder for menus and featured groups
- `browse.py`: BrowseCatalogBuilder for category browsing with facets
- `search.py`: SearchCatalogBuilder for search results (extends BrowseCatalogBuilder)
- `types.py`: Data models (CatalogType, CatalogRequest, CatalogContext, QueryBuilder)

### 2. DBInterface (`database/interfaces.py`)

Manages the navigation structure and query definitions from `db.json`.

**Data Classes:**
- `QueryItem`: Individual browseable items (e.g., "Romance", "English")
- `Section`: Groups of items (e.g., "Categories", "Languages")
- `Navigation`: Page definitions with sections and featured groups
- `FeaturedGroups`: Curated collections for navigation pages

### 3. ArchiveOrgDataProvider (`opds/archiveorg.py`)

Interfaces with Internet Archive's search API:

- Concurrent metadata fetching
- Record validation and transformation
- Language code normalization
- Availability information processing

## Database Structure (`db.json`)

The `db.json` file defines the entire navigation structure and query logic.

### Structure Overview

```json
{
  "base_query": "...",      // Base filter for all searches
  "sections": {...},        // Browseable sections
  "navigation": {...}       // Navigation page definitions
}
```

### Sections

Each section defines a group of browseable items:

```json
"sections": {
  "categories": {
    "title": "Browse by Category",
    "needs_base_query": true,           // Whether to include base_query
    "facets": ["languages", "availability"],  // Available facets
    "items": {
      "romance": {
        "title": "Romance",
        "query": "subject:(romance)",   // Archive.org query
        "sort": ["-week"]              // Optional: sort order
      },
      "scifi": {
        "title": "Science Fiction / Fantasy",
        "query": "subject:('science fiction' OR 'fantasy fiction')"
      }
    }
  },
  "languages": {
    "title": "Browse by Language",
    "needs_base_query": true,
    "facets": ["categories", "availability"],
    "items": {
      "english": {
        "title": "English",
        "query": "languageSorter:English"
      },
      "french": {
        "title": "French",
        "query": "languageSorter:French"
      }
    }
  }
}
```

**Section Properties:**
- `title`: Display name for the section
- `needs_base_query`: If `true`, prepends `base_query` to all item queries
- `facets`: List of other sections available as filters
- `items`: Dictionary of browseable items

**Item Properties:**
- `key`: Unique identifier (dictionary key)
- `title`: Display name
- `query`: Internet Archive search query
- `sort`: Optional sort parameter(s)

### Navigation

Defines the structure of navigation pages:

```json
"navigation": {
  "main": {
    "title": "Archive.org",
    "show_sections": ["collections", "availability"],
    "show_navigation_pages": ["page_titles", "page_languages", "page_categories"],
    "featured_groups": {
      "section": "collections",
      "groups": ["available-now", "print-disability"]
    }
  },
  "page_categories": {
    "title": "Browse by Category",
    "show_sections": ["categories"],
    "featured_groups": {
      "section": "categories",
      "groups": ["adventure", "romance"]
    }
  }
}
```

**Navigation Properties:**
- `title`: Page title
- `show_sections`: Sections to display as navigation links
- `show_navigation_pages`: Sub-navigation pages to link
- `featured_groups`: Curated collections with preview publications
  - `section`: Which section to pull groups from
  - `groups`: List of item keys to feature

##  Getting Started


### Installation

1. Clone the repository
2. Install dependencies
3. Configure `db.json` with your navigation structure
4. Build the image `docker build -t opds .`
5. Run the docker ` docker run -p 5000:5000 -e S3_ACCESS=<your_ia_s3_key> -e S3_SECRET=<your_ia_s3_key> opds`


The server starts on `http://localhost:5000`

### Configuration

Edit `opds/config.py`:

```python
ITEMS_PER_PAGE = 25          # Publications per page
ITEMS_PER_GROUP = 10         # Publications in featured groups
MAX_WORKERS = 10             # Concurrent metadata fetching threads
```

## API Endpoints

### Root Catalog
```
GET /
```
Returns the main navigation catalog.

### Universal Catalog Endpoint
```
GET /catalog
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | Catalog type: `navigation`, `browse`, `search` |
| `nav_key` | string | Navigation key (for type=navigation) |
| `section` | string | Section key (for type=browse) |
| `item` | string | Item key (for type=browse) |
| `query` | string | Search query (for type=search) |
| `page` | integer | Page number (default: 1) |
| `facet_section` | list[string] | Facet section keys |
| `facet_item` | list[string] | Facet item keys |
| `preferred_client_ip` | string | Client IP for availability |

**Examples:**

```bash
# Navigation catalog
GET /catalog?type=navigation&nav_key=main

# Browse romance books
GET /catalog?type=browse&section=categories&item=romance

# Browse romance + filter by English
GET /catalog?type=browse&section=categories&item=romance&facet_section=languages&facet_item=english

# Browse romance + English + Available Now
GET /catalog?type=browse&section=categories&item=romance&facet_section=languages&facet_item=english&facet_section=availability&facet_item=available-now

# Search for "python programming"
GET /catalog?type=search&query=python+programming

# Search with language filter
GET /catalog?type=search&query=python&facet_section=languages&facet_item=english
```

### Other Endpoints

```bash
GET /authentication_document  # OPDS authentication document
GET /book/{identifier}        # Redirect to book download
GET /healthcheck             # Health check endpoint
```

## Cumulative Facets

Facets work cumulatively - each selected facet **adds** to the query:

1. **Start**: Browse Romance
   - Query: `base_query AND subject:(romance)`
   - Available facets: Languages, Availability

2. **Add Language = English**
   - Query: `base_query AND subject:(romance) AND languageSorter:English`
   - Available facets: Availability (Languages now hidden)

3. **Add Availability = Available Now**
   - Query: `base_query AND subject:(romance) AND languageSorter:English AND (lending___available_to_borrow:true...)`
   - Available facets: None (all applied)

**Key Behaviors:**
- Applied facets disappear from the facet list
- All links (pagination, self) preserve applied facets
- Facets are passed as repeated query parameters


##  Data Models

### Publication Record

```python
class ArchiveOrgDataRecord:
    raw_identifier: str      # Archive.org item ID
    mediatype: str          # "texts" or "audio"
    title: str
    published: str
    numberOfPages: int
    author: str | List[str]
    description: str
    language: str | List[str]
    available_info: AvailableInfo  # Lending status
```

### Catalog Structure

```python
{
  "metadata": {
    "title": "...",
    "numberOfItems": 1000,
    "itemsPerPage": 50,
    "currentPage": 1
  },
  "links": [...],           # Self, pagination, search, shelf, profile
  "publications": [...],    # Publication entries (browse/search only)
  "navigation": [...],      # Navigation links (navigation only)
  "groups": [...],         # Featured groups (navigation only)
  "facets": [...]          # Filter options (browse/search only)
}
```

## Extending the System

### Adding a New Section

1. Add to `db.json` under `sections`:
```json
"awards": {
  "title": "Browse by Award",
  "needs_base_query": true,
  "facets": ["languages", "categories"],
  "items": {
    "pulitzer": {
      "title": "Pulitzer Prize Winners",
      "query": "subject:(pulitzer prize)"
    }
  }
}
```

2. Reference in navigation:
```json
"navigation": {
  "main": {
    "show_sections": ["collections", "awards"]
  }
}
```

### Adding New Facets

Simply add the section key to the `facets` array of other sections:

```json
"categories": {
  "facets": ["languages", "availability", "awards"]
}
```

### Custom Sort Orders

Add `sort` parameter to items:

```json
"recently-added": {
  "title": "Recently Added",
  "query": "collection:inlibrary",
  "sort": ["-publicdate"]
}
```

## Authentication

The system supports OPDS authentication documents for user-specific features:

```bash
GET /authentication_document
```

Returns an OPDS Authentication Document for client authentication flows.

## Health Monitoring

```bash
GET /healthcheck
```

Returns:
```json
{
  "status": "healthy",
  "message": "Service is running"
}
```

## Acknowledgments

- [Internet Archive](https://archive.org) for providing access to millions of books
- [pyopds2](https://github.com/ArchiveLabs/pyopds2) for OPDS 2.0 implementation
- OPDS community for the specification