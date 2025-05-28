#!/usr/bin/env python3
"""
LinkVault MCP Server - Main entry point
"""

import os
import sys
import argparse
from server import app as mcp_app

def start_mcp_server():
    """Start the MCP server for bookmark management."""
    print("Starting MCP Bookmark Manager Server...")
    mcp_app.run()

def start_cli():
    """Start the command-line interface."""
    # Import here to avoid circular imports
    from url_manager import main as url_manager_main
    url_manager_main()

def main():
    """Main entry point for the LinkVault MCP Server."""
    parser = argparse.ArgumentParser(description="LinkVault MCP Server")
    parser.add_argument("--mode", choices=["cli", "mcp"], default="cli",
                        help="Mode to run (cli or mcp)")
    
    args = parser.parse_args()
    
    if args.mode == "mcp":
        start_mcp_server()
    else:
        start_cli()

if __name__ == "__main__":
    main()
