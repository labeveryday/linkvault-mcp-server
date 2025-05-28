#!/usr/bin/env python3
"""
LinkVault MCP Server

This is an MCP server for bookmark management.
It provides tools for URL content extraction and bookmark storage.
"""

import os
import json
import sqlite3
import requests
from datetime import datetime
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from fastmcp import FastMCP

# Import browser integration utilities
try:
    from utils.browser_integration import get_chrome_bookmarks, list_chrome_bookmarks
except ImportError:
    # Create placeholder functions if the module is not available
    def get_chrome_bookmarks(flat=True):
        return {"success": False, "error": "Browser integration module not available", "bookmarks": []}
    
    def list_chrome_bookmarks(folder_path=None):
        return {"success": False, "error": "Browser integration module not available", "bookmarks": []}

# Database setup
DB_PATH = os.path.expanduser("~/Documents/github/linkvault-mcp-server/data/bookmarks.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create bookmarks table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        title TEXT,
        category TEXT,
        tags TEXT,  -- JSON array as string
        description TEXT,
        importance INTEGER,
        created_at TEXT,
        last_accessed TEXT
    )
    ''')
    
    # Check if notes column exists, add it if not
    cursor.execute("PRAGMA table_info(bookmarks)")
    columns = [col[1] for col in cursor.fetchall()]
    if "notes" not in columns:
        print("Adding 'notes' column to bookmarks table...")
        cursor.execute("ALTER TABLE bookmarks ADD COLUMN notes TEXT")
    
    # Create categories table for quick lookup
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        name TEXT PRIMARY KEY,
        count INTEGER DEFAULT 0
    )
    ''')
    
    # Create tags table for quick lookup
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tags (
        name TEXT PRIMARY KEY,
        count INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Create MCP server
app = FastMCP(name="bookmark_manager", description="LinkVault - A tool for managing bookmarks")

@app.tool("get_url_data")
def get_url_data(url: str) -> Dict[str, Any]:
    """
    Fetch and extract data from a URL.
    
    Args:
        url: The URL to fetch and analyze
        
    Returns:
        A dictionary containing extracted data from the URL
    """
    try:
        # Add http:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title - improved with multiple fallbacks
        title = ""
        # Try standard title tag first
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        
        # If title is too generic or empty, try Open Graph title
        if not title or title == "Workshop Studio" or len(title) < 5:
            og_title = soup.find('meta', attrs={'property': 'og:title'})
            if og_title and og_title.get('content'):
                title = og_title.get('content').strip()
                
        # Try h1 if still no good title
        if not title or title == "Workshop Studio" or len(title) < 5:
            h1 = soup.find('h1')
            if h1 and h1.get_text():
                title = h1.get_text().strip()
                
        # Extract meta description with improved fallbacks
        meta_description = ""
        for meta_attr in ['name', 'property']:
            for meta_val in ['description', 'og:description', 'twitter:description']:
                meta_tag = soup.find('meta', attrs={meta_attr: meta_val})
                if meta_tag and meta_tag.get('content'):
                    meta_description = meta_tag.get('content').strip()
                    if meta_description and len(meta_description) > 10:
                        break
            if meta_description and len(meta_description) > 10:
                break
                
        # If still no description, try to extract from first paragraph
        if not meta_description or len(meta_description) < 10:
            first_p = soup.find('p')
            if first_p and first_p.get_text():
                meta_description = first_p.get_text().strip()[:200]
        
        # Extract main content with improved extraction
        main_content = ""
        
        # Try to find main content container with more potential selectors
        main_element = (
            soup.find('main') or 
            soup.find('article') or 
            soup.find('div', class_=['content', 'main', 'post', 'entry', 'body', 'workshop-content']) or
            soup.find('div', id=['content', 'main', 'post', 'entry', 'workshop-content'])
        )
        
        if main_element:
            # Extract from main content area
            for p in main_element.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                text = p.get_text().strip()
                if text:
                    main_content += text + "\n\n"
        else:
            # Fallback: extract all paragraphs and headings
            for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = p.get_text().strip()
                if len(text) > 20:  # Skip very short paragraphs
                    main_content += text + "\n\n"
        
        # Limit content length but keep more content
        main_content = main_content[:12000]
        
        # Extract keywords/tags with improved extraction
        keywords = []
        
        # Try meta keywords
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag and keywords_tag.get('content'):
            keywords = [k.strip() for k in keywords_tag.get('content').split(',')]
            
        # If no keywords, try to extract from tags or categories
        if not keywords:
            # Look for common tag/category elements
            tag_elements = soup.find_all(['a', 'span', 'div'], class_=['tag', 'category', 'topic', 'label'])
            for tag_el in tag_elements:
                if tag_el.get_text().strip():
                    keywords.append(tag_el.get_text().strip())
                    
        # Extract URL path components as potential keywords
        path_parts = url.split('/')
        for part in path_parts:
            if part and part not in ['http:', 'https:', '', 'www', 'en', 'en-US', 'index.html']:
                # Convert dashes to spaces and clean up
                cleaned = part.replace('-', ' ').replace('_', ' ')
                if len(cleaned) > 2 and cleaned not in ['com', 'org', 'net', 'html']:
                    keywords.append(cleaned)
        
        # Deduplicate keywords
        keywords = list(set(keywords))[:10]
        
        # Special handling for AWS Workshop Studio URLs
        if 'workshops.aws' in url:
            # Extract workshop name from URL
            workshop_name = None
            for part in url.split('/'):
                if part not in ['http:', 'https:', '', 'catalog.workshops.aws', 'en-US', 'en', 'index.html']:
                    workshop_name = part.replace('-', ' ').title()
                    break
                    
            if workshop_name:
                if not title or title == "Workshop Studio":
                    title = f"AWS Workshop: {workshop_name}"
                if 'aws' not in keywords:
                    keywords.append('aws')
                if 'workshop' not in keywords:
                    keywords.append('workshop')
                if workshop_name.lower() not in [k.lower() for k in keywords]:
                    keywords.append(workshop_name)
        
        return {
            "url": url,
            "title": title,
            "meta_description": meta_description,
            "main_content": main_content,
            "keywords": keywords,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "url": url
        }

@app.tool("store_url")
def store_url(url: str, title: str, category: str, 
              tags: List[str], description: str, 
              importance: int, notes: str = None) -> Dict[str, Any]:
    """
    Store a URL with AI-generated metadata.
    
    Args:
        url: The URL to store
        title: The title of the webpage
        category: The category to assign
        tags: List of tags to associate with the URL
        description: A brief description of the content
        importance: Importance rating (1-5)
        notes: Optional additional notes or comments about the URL
        
    Returns:
        A dictionary indicating success or failure
    """
    try:
        # Add http:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if notes column exists, add it if not
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = [col[1] for col in cursor.fetchall()]
        if "notes" not in columns:
            print("Adding 'notes' column to bookmarks table...")
            cursor.execute("ALTER TABLE bookmarks ADD COLUMN notes TEXT")
            conn.commit()
            
        # Check if URL already exists
        cursor.execute("SELECT id FROM bookmarks WHERE url = ?", (url,))
        existing = cursor.fetchone()
        
        current_time = datetime.now().isoformat()
        date_added = current_time.split('T')[0]  # Extract just the date part
        
        if existing:
            # Update existing bookmark
            cursor.execute(
                """
                UPDATE bookmarks 
                SET title = ?, category = ?, tags = ?, description = ?, 
                    importance = ?, last_accessed = ?, notes = ?
                WHERE url = ?
                """,
                (title, category, json.dumps(tags), description, importance, current_time, notes, url)
            )
            message = f"Updated bookmark: {title}"
        else:
            # Insert new bookmark
            cursor.execute(
                """
                INSERT INTO bookmarks 
                (url, title, category, tags, description, importance, created_at, last_accessed, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (url, title, category, json.dumps(tags), description, importance, current_time, current_time, notes)
            )
            message = f"Added new bookmark: {title}"
        
        # Update category count
        cursor.execute(
            """
            INSERT INTO categories (name, count) VALUES (?, 1)
            ON CONFLICT(name) DO UPDATE SET count = count + 1
            """,
            (category,)
        )
        
        # Update tag counts
        for tag in tags:
            cursor.execute(
                """
                INSERT INTO tags (name, count) VALUES (?, 1)
                ON CONFLICT(name) DO UPDATE SET count = count + 1
                """,
                (tag,)
            )
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": message,
            "category": category,
            "tags": tags,
            "date_added": date_added
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url": url
        }

@app.tool("search_bookmarks")
def search_bookmarks(query: str) -> Dict[str, Any]:
    """
    Search for bookmarks by query.
    
    Args:
        query: The search query
        
    Returns:
        A dictionary containing search results
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        # Check if notes column exists
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = [col[1] for col in cursor.fetchall()]
        has_notes = "notes" in columns
        
        # Search in title, description, category, and tags
        if has_notes:
            cursor.execute(
                """
                SELECT * FROM bookmarks 
                WHERE title LIKE ? 
                   OR description LIKE ? 
                   OR category LIKE ?
                   OR tags LIKE ?
                   OR notes LIKE ?
                ORDER BY importance DESC, last_accessed DESC
                LIMIT 20
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
            )
        else:
            cursor.execute(
                """
                SELECT * FROM bookmarks 
                WHERE title LIKE ? 
                   OR description LIKE ? 
                   OR category LIKE ?
                   OR tags LIKE ?
                ORDER BY importance DESC, last_accessed DESC
                LIMIT 20
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%")
            )
        
        results = []
        for row in cursor.fetchall():
            bookmark = {
                "id": row["id"],
                "url": row["url"],
                "title": row["title"],
                "category": row["category"],
                "tags": json.loads(row["tags"]),
                "description": row["description"],
                "importance": row["importance"],
                "created_at": row["created_at"]
            }
            
            # Add notes if available
            if has_notes and "notes" in row.keys() and row["notes"]:
                bookmark["notes"] = row["notes"]
                
            results.append(bookmark)
        
        conn.close()
        
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

@app.tool("list_categories")
def list_categories() -> Dict[str, Any]:
    """
    List all bookmark categories.
    
    Returns:
        A dictionary containing all categories and their counts
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT name, count FROM categories ORDER BY count DESC")
        
        categories = []
        for row in cursor.fetchall():
            categories.append({
                "name": row["name"],
                "count": row["count"]
            })
        
        conn.close()
        
        return {
            "success": True,
            "count": len(categories),
            "categories": categories
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.tool("list_bookmarks_by_category")
def list_bookmarks_by_category(category: str) -> Dict[str, Any]:
    """
    List all bookmarks in a specific category.
    
    Args:
        category: The category name
        
    Returns:
        A dictionary containing bookmarks in the specified category
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if notes column exists
        cursor.execute("PRAGMA table_info(bookmarks)")
        columns = [col[1] for col in cursor.fetchall()]
        has_notes = "notes" in columns
        
        cursor.execute(
            """
            SELECT * FROM bookmarks 
            WHERE category = ? 
            ORDER BY importance DESC, last_accessed DESC
            """,
            (category,)
        )
        
        bookmarks = []
        for row in cursor.fetchall():
            bookmark = {
                "id": row["id"],
                "url": row["url"],
                "title": row["title"],
                "tags": json.loads(row["tags"]),
                "description": row["description"],
                "importance": row["importance"],
                "created_at": row["created_at"]
            }
            
            # Add notes if available
            if has_notes and "notes" in row.keys() and row["notes"]:
                bookmark["notes"] = row["notes"]
                
            bookmarks.append(bookmark)
        
        conn.close()
        
        return {
            "success": True,
            "category": category,
            "count": len(bookmarks),
            "bookmarks": bookmarks
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "category": category
        }

@app.tool("delete_bookmark")
def delete_bookmark(url: str, category: str = None) -> Dict[str, Any]:
    """
    Delete a bookmark from the database.
    
    Args:
        url: The URL of the bookmark to delete
        category: Optional category to specify which bookmark to delete if the same URL exists in multiple categories
        
    Returns:
        A dictionary indicating success or failure and details about the deleted bookmark
    """
    try:
        # Add http:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get bookmark details before deletion for confirmation
        if category:
            cursor.execute(
                """
                SELECT id, title, category, tags FROM bookmarks 
                WHERE url = ? AND category = ?
                """,
                (url, category)
            )
        else:
            cursor.execute(
                """
                SELECT id, title, category, tags FROM bookmarks 
                WHERE url = ?
                """,
                (url,)
            )
        
        bookmarks = cursor.fetchall()
        
        if not bookmarks:
            conn.close()
            return {
                "success": False,
                "message": f"No bookmark found with URL: {url}" + (f" in category: {category}" if category else "")
            }
        
        deleted_bookmarks = []
        
        # Process each matching bookmark
        for bookmark in bookmarks:
            bookmark_id = bookmark["id"]
            bookmark_title = bookmark["title"]
            bookmark_category = bookmark["category"]
            bookmark_tags = json.loads(bookmark["tags"])
            
            # Delete the bookmark
            cursor.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            
            # Update category count
            cursor.execute(
                """
                UPDATE categories
                SET count = count - 1
                WHERE name = ?
                """,
                (bookmark_category,)
            )
            
            # Clean up empty categories
            cursor.execute("DELETE FROM categories WHERE count <= 0")
            
            # Update tag counts
            for tag in bookmark_tags:
                cursor.execute(
                    """
                    UPDATE tags
                    SET count = count - 1
                    WHERE name = ?
                    """,
                    (tag,)
                )
            
            # Clean up empty tags
            cursor.execute("DELETE FROM tags WHERE count <= 0")
            
            deleted_bookmarks.append({
                "title": bookmark_title,
                "category": bookmark_category,
                "tags": bookmark_tags
            })
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"Deleted {len(deleted_bookmarks)} bookmark(s)",
            "deleted_bookmarks": deleted_bookmarks
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "url": url
        }

@app.tool("list_chrome_bookmarks")
def list_chrome_bookmarks_tool(folder: str = None) -> Dict[str, Any]:
    """
    List Chrome bookmarks, optionally filtered by folder.
    
    Args:
        folder: Optional folder path to filter bookmarks
        
    Returns:
        A dictionary containing Chrome bookmarks
    """
    return list_chrome_bookmarks(folder)

@app.tool("import_chrome_bookmark")
def import_chrome_bookmark(url: str, title: str, category: str, 
                          tags: List[str], description: str = "", 
                          importance: int = 3, notes: str = None) -> Dict[str, Any]:
    """
    Import a Chrome bookmark into the database.
    
    Args:
        url: The URL of the Chrome bookmark to import
        title: The title of the bookmark
        category: The category to assign
        tags: List of tags to associate with the URL
        description: A brief description of the content
        importance: Importance rating (1-5)
        notes: Optional additional notes or comments about the URL
        
    Returns:
        A dictionary indicating success or failure
    """
    return store_url(url, title, category, tags, description, importance, notes)

if __name__ == "__main__":
    # Start the MCP server
    print("Starting LinkVault MCP Server...")
    print(f"Database path: {DB_PATH}")
    app.run()
