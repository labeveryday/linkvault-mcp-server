"""
Browser integration utilities for LinkVault.

This module provides functions to interact with browser bookmarks,
currently supporting Chrome on Windows, macOS, and Linux.
"""

import json
import os
import platform
import glob
from pathlib import Path
from typing import Dict, List, Any, Optional, Union


def get_chrome_bookmarks_paths() -> List[Path]:
    """
    Get paths to all Chrome bookmarks files based on the operating system.
    
    Returns:
        List of Path objects to Chrome bookmarks files
    """
    system = platform.system()
    paths = []
    
    if system == "Darwin":  # macOS
        # Check all profiles
        profile_pattern = str(Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "*" / "Bookmarks")
        paths = [Path(p) for p in glob.glob(profile_pattern) if os.path.isfile(p)]
    elif system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            # Check all profiles
            profile_pattern = str(Path(local_app_data) / "Google" / "Chrome" / "User Data" / "*" / "Bookmarks")
            paths = [Path(p) for p in glob.glob(profile_pattern) if os.path.isfile(p)]
    elif system == "Linux":
        # Check all profiles
        profile_pattern = str(Path.home() / ".config" / "google-chrome" / "*" / "Bookmarks")
        paths = [Path(p) for p in glob.glob(profile_pattern) if os.path.isfile(p)]
    
    return [p for p in paths if p.exists()]


def parse_chrome_bookmarks(bookmarks_path: Path) -> Dict[str, Any]:
    """
    Parse Chrome bookmarks from a bookmarks file.
    
    Args:
        bookmarks_path: Path to the Chrome bookmarks file
    
    Returns:
        Dictionary containing parsed bookmarks structure or empty dict if not found
    
    Raises:
        FileNotFoundError: If bookmarks file doesn't exist
        json.JSONDecodeError: If bookmarks file is not valid JSON
    """
    if not bookmarks_path.exists():
        return {"roots": {}, "error": f"Bookmarks file not found: {bookmarks_path}"}
    
    try:
        with open(bookmarks_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"roots": {}, "error": f"Invalid bookmarks file format: {bookmarks_path}"}
    except Exception as e:
        return {"roots": {}, "error": f"Error reading bookmarks: {str(e)}"}


def extract_bookmarks_from_node(node: Dict[str, Any], path: str = "") -> List[Dict[str, Any]]:
    """
    Extract bookmarks from a Chrome bookmarks node recursively.
    
    Args:
        node: Chrome bookmarks node
        path: Current path in the bookmarks hierarchy
    
    Returns:
        List of dictionaries containing bookmark information
    """
    results = []
    
    if node.get("type") == "url":
        results.append({
            "title": node.get("name", ""),
            "url": node.get("url", ""),
            "path": path,
            "date_added": node.get("date_added", ""),
            "id": node.get("id", "")
        })
    
    if "children" in node:
        current_path = f"{path}/{node.get('name', '')}" if path else node.get("name", "")
        for child in node["children"]:
            results.extend(extract_bookmarks_from_node(child, current_path))
    
    return results


def get_chrome_bookmarks(flat: bool = True) -> Dict[str, Any]:
    """
    Get Chrome bookmarks as a structured dictionary from all profiles.
    
    Args:
        flat: If True, returns a flat list of all bookmarks
              If False, returns the original nested structure
    
    Returns:
        Dictionary containing bookmarks or error information
    """
    bookmark_paths = get_chrome_bookmarks_paths()
    
    if not bookmark_paths:
        return {"success": False, "error": "No Chrome bookmark files found", "bookmarks": []}
    
    all_bookmarks = []
    errors = []
    
    for path in bookmark_paths:
        bookmarks_data = parse_chrome_bookmarks(path)
        
        if "error" in bookmarks_data and "roots" not in bookmarks_data:
            errors.append(bookmarks_data["error"])
            continue
        
        if flat:
            profile_name = path.parent.name
            roots = bookmarks_data.get("roots", {})
            
            for root_name, root_data in roots.items():
                if root_name in ("sync_transaction_version", "version"):
                    continue
                
                # Add profile information to the path
                bookmarks = extract_bookmarks_from_node(root_data, f"{profile_name}/{root_name}")
                all_bookmarks.extend(bookmarks)
    
    if not all_bookmarks and errors:
        return {"success": False, "error": "; ".join(errors), "bookmarks": []}
    
    return {
        "success": True,
        "count": len(all_bookmarks),
        "bookmarks": all_bookmarks
    }


def list_chrome_bookmarks(folder_path: Optional[str] = None) -> Dict[str, Any]:
    """
    List Chrome bookmarks, optionally filtered by folder path.
    
    Args:
        folder_path: Optional path to filter bookmarks by folder
                    Format: "Profile 1/Bookmarks Bar/Work" or "Default/Other Bookmarks/Personal"
    
    Returns:
        Dictionary containing filtered bookmarks
    """
    result = get_chrome_bookmarks(flat=True)
    
    if not result["success"]:
        return result
    
    if folder_path:
        filtered_bookmarks = [
            b for b in result["bookmarks"] 
            if b["path"] and folder_path in b["path"]
        ]
        
        return {
            "success": True,
            "count": len(filtered_bookmarks),
            "folder": folder_path,
            "bookmarks": filtered_bookmarks
        }
    
    return result
