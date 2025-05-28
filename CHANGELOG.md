# Changelog

## [1.0.0] - 2025-05-28

### Added
- Initial release of LinkVault MCP Server
- CLI interface with JSON storage
- MCP server with SQLite storage
- Content extraction from web pages
- Intelligent categorization and tagging
- Main entry point supporting both CLI and MCP modes

### Features
- CLI Commands:
  - Add URLs with categories and tags
  - List categories and URLs
  - Search URLs by query
  - List and filter by tags
  - Delete URLs and categories
  - Rename categories

- MCP Tools:
  - get_url_data: Extract data from URLs
  - store_url: Store URLs with metadata
  - search_bookmarks: Search for bookmarks
  - list_categories: List all categories
  - list_bookmarks_by_category: List bookmarks in a category
  - delete_bookmark: Delete bookmarks by URL

### Improvements
- Enhanced URL content extraction with multiple fallbacks
- Support for notes in bookmarks
- Robust error handling for database operations
- Automatic schema migration for adding new fields

### Technical
- Python 3.10+ compatibility
- SQLite database for MCP server
- JSON file storage for CLI
- BeautifulSoup for web scraping
- FastMCP for MCP server implementation
