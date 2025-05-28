#!/usr/bin/env python3
"""
LinkVault - A tool to categorize, store, and search web URLs for research and learning.
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import browser integration utilities
try:
    from utils.browser_integration import get_chrome_bookmarks, list_chrome_bookmarks
except ImportError:
    # Create placeholder functions if the module is not available
    def get_chrome_bookmarks(flat=True):
        return {"success": False, "error": "Browser integration module not available", "bookmarks": []}
    
    def list_chrome_bookmarks(folder_path=None):
        return {"success": False, "error": "Browser integration module not available", "bookmarks": []}

# Define the path to the JSON database file
DATA_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "data"
DB_FILE = DATA_DIR / "url_database.json"

# Ensure the data directory exists
DATA_DIR.mkdir(exist_ok=True)

def load_database() -> Dict[str, Any]:
    """Load the URL database from the JSON file."""
    if not DB_FILE.exists():
        return {"categories": {}}
    
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_database(data: Dict[str, Any]) -> None:
    """Save the URL database to the JSON file."""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def add_url(url: str, category: str, tags: List[str] = None, notes: str = None, title: str = None) -> Dict[str, Any]:
    """Add a URL to the database."""
    data = load_database()
    
    if category not in data["categories"]:
        data["categories"][category] = []
    
    # Check if URL already exists in this category
    for entry in data["categories"][category]:
        if entry["url"] == url:
            return {"success": False, "message": f"URL already exists in category '{category}'"}
    
    # Add the URL to the specified category
    entry = {
        "url": url,
        "title": title or url,
        "tags": tags or [],
        "notes": notes or "",
        "date_added": datetime.now().isoformat()
    }
    
    data["categories"][category].append(entry)
    save_database(data)
    
    return {"success": True, "message": f"Added URL to category '{category}'"}

def list_categories() -> Dict[str, Any]:
    """List all categories and their URL counts."""
    data = load_database()
    result = {}
    
    for category, urls in data["categories"].items():
        result[category] = len(urls)
    
    return {"success": True, "categories": result}

def list_urls_in_category(category: str) -> Dict[str, Any]:
    """List all URLs in a specific category."""
    data = load_database()
    
    if category not in data["categories"]:
        return {"success": False, "message": f"Category '{category}' not found"}
    
    return {"success": True, "category": category, "urls": data["categories"][category]}

def search_urls(query: str) -> Dict[str, Any]:
    """Search for URLs containing the query string."""
    data = load_database()
    results = []
    
    for category, urls in data["categories"].items():
        for url in urls:
            if (query.lower() in url["url"].lower() or 
                query.lower() in url["title"].lower() or 
                query.lower() in url.get("notes", "").lower() or
                any(query.lower() in tag.lower() for tag in url.get("tags", []))):
                result = url.copy()
                result["category"] = category
                results.append(result)
    
    return {"success": True, "query": query, "results": results}

def list_tags() -> Dict[str, Any]:
    """List all tags and their counts."""
    data = load_database()
    tag_counts = {}
    
    for category, urls in data["categories"].items():
        for url in urls:
            for tag in url.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    return {"success": True, "tags": tag_counts}

def list_urls_with_tag(tag: str) -> Dict[str, Any]:
    """List all URLs with a specific tag."""
    data = load_database()
    results = []
    
    for category, urls in data["categories"].items():
        for url in urls:
            if tag in url.get("tags", []):
                result = url.copy()
                result["category"] = category
                results.append(result)
    
    return {"success": True, "tag": tag, "results": results}

def delete_url(url: str, category: Optional[str] = None) -> Dict[str, Any]:
    """Delete a URL from the database."""
    data = load_database()
    
    if category:
        if category not in data["categories"]:
            return {"success": False, "message": f"Category '{category}' not found"}
        
        for i, entry in enumerate(data["categories"][category]):
            if entry["url"] == url:
                del data["categories"][category][i]
                save_database(data)
                return {"success": True, "message": f"Deleted URL from category '{category}'"}
        
        return {"success": False, "message": f"URL not found in category '{category}'"}
    
    # If no category specified, search all categories
    found = False
    for cat, urls in data["categories"].items():
        for i, entry in enumerate(urls):
            if entry["url"] == url:
                del data["categories"][cat][i]
                found = True
                break
    
    if found:
        save_database(data)
        return {"success": True, "message": "Deleted URL"}
    
    return {"success": False, "message": "URL not found"}

def rename_category(old_name: str, new_name: str) -> Dict[str, Any]:
    """Rename a category."""
    data = load_database()
    
    if old_name not in data["categories"]:
        return {"success": False, "message": f"Category '{old_name}' not found"}
    
    if new_name in data["categories"]:
        return {"success": False, "message": f"Category '{new_name}' already exists"}
    
    data["categories"][new_name] = data["categories"][old_name]
    del data["categories"][old_name]
    save_database(data)
    
    return {"success": True, "message": f"Renamed category '{old_name}' to '{new_name}'"}

def delete_category(category: str) -> Dict[str, Any]:
    """Delete a category and all its URLs."""
    data = load_database()
    
    if category not in data["categories"]:
        return {"success": False, "message": f"Category '{category}' not found"}
    
    del data["categories"][category]
    save_database(data)
    
    return {"success": True, "message": f"Deleted category '{category}'"}

def list_chrome_bookmarks_cli(folder: Optional[str] = None) -> Dict[str, Any]:
    """List Chrome bookmarks from CLI."""
    return list_chrome_bookmarks(folder)

def import_chrome_bookmark(url: str, title: str, category: str, tags: List[str] = None) -> Dict[str, Any]:
    """Import a Chrome bookmark into the database."""
    return add_url(url, category, tags, None, title)

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="LinkVault CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add URL command
    add_parser = subparsers.add_parser("add", help="Add a URL")
    add_parser.add_argument("url", help="URL to add")
    add_parser.add_argument("category", help="Category to add the URL to")
    add_parser.add_argument("-t", "--tags", nargs="+", help="Tags for the URL")
    add_parser.add_argument("-n", "--notes", help="Notes for the URL")
    add_parser.add_argument("--title", help="Custom title for the URL")
    
    # List categories command
    subparsers.add_parser("categories", help="List all categories")
    
    # List URLs in category command
    list_parser = subparsers.add_parser("list", help="List URLs in a category")
    list_parser.add_argument("category", help="Category to list URLs from")
    
    # Search URLs command
    search_parser = subparsers.add_parser("search", help="Search for URLs")
    search_parser.add_argument("query", help="Search query")
    
    # List tags command
    subparsers.add_parser("tags", help="List all tags")
    
    # List URLs with tag command
    tag_parser = subparsers.add_parser("tag", help="List URLs with a specific tag")
    tag_parser.add_argument("tag", help="Tag to filter by")
    
    # Delete URL command
    delete_parser = subparsers.add_parser("delete", help="Delete a URL")
    delete_parser.add_argument("url", help="URL to delete")
    delete_parser.add_argument("-c", "--category", help="Category containing the URL")
    
    # Rename category command
    rename_parser = subparsers.add_parser("rename", help="Rename a category")
    rename_parser.add_argument("old_name", help="Current category name")
    rename_parser.add_argument("new_name", help="New category name")
    
    # Delete category command
    delcat_parser = subparsers.add_parser("delcat", help="Delete a category")
    delcat_parser.add_argument("category", help="Category to delete")
    
    # List Chrome bookmarks command
    chrome_parser = subparsers.add_parser("chrome", help="List Chrome bookmarks")
    chrome_parser.add_argument("-f", "--folder", help="Filter by folder path (e.g., 'Bookmarks Bar/Work')")
    
    # Import Chrome bookmark command
    import_parser = subparsers.add_parser("import", help="Import a Chrome bookmark")
    import_parser.add_argument("url", help="URL of the Chrome bookmark to import")
    import_parser.add_argument("category", help="Category to import the bookmark to")
    import_parser.add_argument("-t", "--tags", nargs="+", help="Tags for the bookmark")
    import_parser.add_argument("--title", help="Title for the bookmark (defaults to URL if not provided)")
    
    args = parser.parse_args()
    
    if args.command == "add":
        result = add_url(args.url, args.category, args.tags, args.notes, args.title)
        print(result["message"])
    
    elif args.command == "categories":
        result = list_categories()
        if result["categories"]:
            for category, count in result["categories"].items():
                print(f"{category}: {count} URLs")
        else:
            print("No categories found")
    
    elif args.command == "list":
        result = list_urls_in_category(args.category)
        if result["success"]:
            print(f"URLs in category '{args.category}':")
            for url in result["urls"]:
                print(f"- {url['title']}: {url['url']}")
                if url.get("tags"):
                    print(f"  Tags: {', '.join(url['tags'])}")
                if url.get("notes"):
                    print(f"  Notes: {url['notes']}")
        else:
            print(result["message"])
    
    elif args.command == "search":
        result = search_urls(args.query)
        if result["results"]:
            print(f"Search results for '{args.query}':")
            for url in result["results"]:
                print(f"- [{url['category']}] {url['title']}: {url['url']}")
                if url.get("tags"):
                    print(f"  Tags: {', '.join(url['tags'])}")
                if url.get("notes"):
                    print(f"  Notes: {url['notes']}")
        else:
            print(f"No results found for '{args.query}'")
    
    elif args.command == "tags":
        result = list_tags()
        if result["tags"]:
            for tag, count in result["tags"].items():
                print(f"{tag}: {count} URLs")
        else:
            print("No tags found")
    
    elif args.command == "tag":
        result = list_urls_with_tag(args.tag)
        if result["results"]:
            print(f"URLs with tag '{args.tag}':")
            for url in result["results"]:
                print(f"- [{url['category']}] {url['title']}: {url['url']}")
                if url.get("notes"):
                    print(f"  Notes: {url['notes']}")
        else:
            print(f"No URLs found with tag '{args.tag}'")
    
    elif args.command == "delete":
        result = delete_url(args.url, args.category)
        print(result["message"])
    
    elif args.command == "rename":
        result = rename_category(args.old_name, args.new_name)
        print(result["message"])
    
    elif args.command == "delcat":
        result = delete_category(args.category)
        print(result["message"])
    
    elif args.command == "chrome":
        result = list_chrome_bookmarks_cli(args.folder)
        if result["success"]:
            print(f"Found {result['count']} Chrome bookmarks:")
            for i, bookmark in enumerate(result["bookmarks"]):
                print(f"{i+1}. [{bookmark['path']}] {bookmark['title']}")
                print(f"   URL: {bookmark['url']}")
                print()
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
    
    elif args.command == "import":
        result = import_chrome_bookmark(args.url, args.title or args.url, args.category, args.tags)
        print(result["message"])
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
