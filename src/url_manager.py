#!/usr/bin/env python3
"""
LinkVault - A tool to categorize, store, and search web URLs for research and learning.
"""

import json
import os
import sys
import argparse
from datetime import datetime
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

# File to store the URL database
DB_FILE = os.path.expanduser("~/Documents/github/linkvault-mcp-server/data/url_database.json")

def load_database():
    """Load the URL database from file or create a new one if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Error: Database file is corrupted. Creating a new one.")
                return {"categories": {}, "tags": {}}
    else:
        return {"categories": {}, "tags": {}}

def save_database(db):
    """Save the URL database to file."""
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def extract_title(url):
    """Extract the title of a webpage."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            if soup.title and soup.title.string:
                return soup.title.string.strip()
    except Exception as e:
        print(f"Warning: Could not fetch title for {url}: {e}")
    
    # If we can't get the title, use the domain name
    parsed_url = urlparse(url)
    return parsed_url.netloc
def add_url(db, url, category, tags=None, title=None, notes=None):
    """Add a URL to the database."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Extract title if not provided
    if not title:
        title = extract_title(url)
    
    # Create category if it doesn't exist
    if category not in db["categories"]:
        db["categories"][category] = []
    
    # Check if URL already exists in this category
    for entry in db["categories"][category]:
        if entry["url"] == url:
            print(f"URL already exists in category '{category}'. Updating metadata.")
            entry["title"] = title
            if notes:
                entry["notes"] = notes
            if tags:
                entry["tags"] = list(set(entry.get("tags", []) + tags))
            save_database(db)
            return
    
    # Create new entry
    entry = {
        "url": url,
        "title": title,
        "added_date": datetime.now().isoformat(),
        "last_accessed": None
    }
    
    if notes:
        entry["notes"] = notes
    
    if tags:
        entry["tags"] = tags
        # Update tag index
        for tag in tags:
            if tag not in db["tags"]:
                db["tags"][tag] = []
            if url not in db["tags"][tag]:
                db["tags"][tag].append(url)
    
    db["categories"][category].append(entry)
    save_database(db)
    print(f"Added: {title} [{url}] to category '{category}'")

def list_categories(db):
    """List all categories and the number of URLs in each."""
    if not db["categories"]:
        print("No categories found.")
        return
    
    print("\nCategories:")
    print("-" * 50)
    for category, urls in db["categories"].items():
        print(f"{category}: {len(urls)} URLs")

def list_urls_in_category(db, category):
    """List all URLs in a specific category."""
    if category not in db["categories"]:
        print(f"Category '{category}' not found.")
        return
    
    urls = db["categories"][category]
    if not urls:
        print(f"No URLs in category '{category}'.")
        return
    
    print(f"\nURLs in category '{category}':")
    print("-" * 50)
    for i, entry in enumerate(urls, 1):
        print(f"{i}. {entry['title']}")
        print(f"   {entry['url']}")
        if "tags" in entry and entry["tags"]:
            print(f"   Tags: {', '.join(entry['tags'])}")
        print()
def search_urls(db, query):
    """Search for URLs by title, URL, tags, or notes."""
    results = []
    query_lower = query.lower()
    
    # Search in categories
    for category, urls in db["categories"].items():
        for entry in urls:
            if (query_lower in entry["url"].lower() or 
                query_lower in entry["title"].lower() or
                (entry.get("notes") and query_lower in entry["notes"].lower()) or
                (entry.get("tags") and any(query_lower in tag.lower() for tag in entry["tags"]))):
                results.append((category, entry))
    
    if not results:
        print(f"No results found for '{query}'.")
        return
    
    print(f"\nSearch results for '{query}':")
    print("-" * 50)
    for i, (category, entry) in enumerate(results, 1):
        print(f"{i}. [{category}] {entry['title']}")
        print(f"   {entry['url']}")
        if "tags" in entry and entry["tags"]:
            print(f"   Tags: {', '.join(entry['tags'])}")
        print()

def list_tags(db):
    """List all tags and the number of URLs with each tag."""
    if not db["tags"]:
        print("No tags found.")
        return
    
    print("\nTags:")
    print("-" * 50)
    for tag, urls in db["tags"].items():
        print(f"{tag}: {len(urls)} URLs")

def list_urls_with_tag(db, tag):
    """List all URLs with a specific tag."""
    if tag not in db["tags"]:
        print(f"Tag '{tag}' not found.")
        return
    
    urls = db["tags"][tag]
    if not urls:
        print(f"No URLs with tag '{tag}'.")
        return
    
    print(f"\nURLs with tag '{tag}':")
    print("-" * 50)
    
    for url in urls:
        # Find the entry with this URL
        for category, entries in db["categories"].items():
            for entry in entries:
                if entry["url"] == url:
                    print(f"[{category}] {entry['title']}")
                    print(f"   {entry['url']}")
                    print()
                    break
def delete_url(db, url, category=None):
    """Delete a URL from the database."""
    found = False
    
    # If category is specified, only look in that category
    if category:
        if category not in db["categories"]:
            print(f"Category '{category}' not found.")
            return
        
        categories_to_check = {category: db["categories"][category]}
    else:
        categories_to_check = db["categories"]
    
    # Look for the URL in the specified categories
    for cat, urls in categories_to_check.items():
        for i, entry in enumerate(urls):
            if entry["url"] == url:
                # Remove from tags index
                if "tags" in entry:
                    for tag in entry["tags"]:
                        if tag in db["tags"] and url in db["tags"][tag]:
                            db["tags"][tag].remove(url)
                            # Clean up empty tag lists
                            if not db["tags"][tag]:
                                del db["tags"][tag]
                
                # Remove the entry
                del db["categories"][cat][i]
                found = True
                print(f"Deleted: {entry['title']} [{url}] from category '{cat}'")
                break
        
        if found:
            break
    
    if not found:
        print(f"URL '{url}' not found in the database.")
        return
    
    save_database(db)

def rename_category(db, old_name, new_name):
    """Rename a category."""
    if old_name not in db["categories"]:
        print(f"Category '{old_name}' not found.")
        return
    
    if new_name in db["categories"]:
        print(f"Category '{new_name}' already exists.")
        return
    
    db["categories"][new_name] = db["categories"].pop(old_name)
    save_database(db)
    print(f"Renamed category '{old_name}' to '{new_name}'.")

def delete_category(db, category):
    """Delete a category and all its URLs."""
    if category not in db["categories"]:
        print(f"Category '{category}' not found.")
        return
    
    # Remove all URLs in this category from the tags index
    for entry in db["categories"][category]:
        url = entry["url"]
        if "tags" in entry:
            for tag in entry["tags"]:
                if tag in db["tags"] and url in db["tags"][tag]:
                    db["tags"][tag].remove(url)
                    # Clean up empty tag lists
                    if not db["tags"][tag]:
                        del db["tags"][tag]
    
    # Delete the category
    del db["categories"][category]
    save_database(db)
    print(f"Deleted category '{category}' and all its URLs.")
def main():
    parser = argparse.ArgumentParser(description="LinkVault - Store and categorize URLs for research")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add URL command
    add_parser = subparsers.add_parser("add", help="Add a new URL")
    add_parser.add_argument("url", help="The URL to add")
    add_parser.add_argument("category", help="Category to add the URL to")
    add_parser.add_argument("-t", "--tags", help="Comma-separated list of tags")
    add_parser.add_argument("-n", "--notes", help="Notes about the URL")
    add_parser.add_argument("--title", help="Custom title for the URL")
    
    # List categories command
    subparsers.add_parser("categories", help="List all categories")
    
    # List URLs in category command
    list_parser = subparsers.add_parser("list", help="List URLs in a category")
    list_parser.add_argument("category", help="Category to list URLs from")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for URLs")
    search_parser.add_argument("query", help="Search query")
    
    # Tags command
    subparsers.add_parser("tags", help="List all tags")
    
    # List URLs with tag command
    tag_parser = subparsers.add_parser("tag", help="List URLs with a specific tag")
    tag_parser.add_argument("tag", help="Tag to list URLs for")
    
    # Delete URL command
    delete_parser = subparsers.add_parser("delete", help="Delete a URL")
    delete_parser.add_argument("url", help="URL to delete")
    delete_parser.add_argument("-c", "--category", help="Category the URL is in (optional)")
    
    # Rename category command
    rename_parser = subparsers.add_parser("rename", help="Rename a category")
    rename_parser.add_argument("old_name", help="Current category name")
    rename_parser.add_argument("new_name", help="New category name")
    
    # Delete category command
    del_cat_parser = subparsers.add_parser("delcat", help="Delete a category and all its URLs")
    del_cat_parser.add_argument("category", help="Category to delete")
    
    args = parser.parse_args()
    
    # Load the database
    db = load_database()
    
    # Execute the appropriate command
    if args.command == "add":
        tags = [tag.strip() for tag in args.tags.split(",")] if args.tags else None
        add_url(db, args.url, args.category, tags, args.title, args.notes)
    
    elif args.command == "categories":
        list_categories(db)
    
    elif args.command == "list":
        list_urls_in_category(db, args.category)
    
    elif args.command == "search":
        search_urls(db, args.query)
    
    elif args.command == "tags":
        list_tags(db)
    
    elif args.command == "tag":
        list_urls_with_tag(db, args.tag)
    
    elif args.command == "delete":
        delete_url(db, args.url, args.category)
    
    elif args.command == "rename":
        rename_category(db, args.old_name, args.new_name)
    
    elif args.command == "delcat":
        delete_category(db, args.category)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
