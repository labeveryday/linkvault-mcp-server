#!/usr/bin/env python3
"""
LinkVault MCP Server - Main entry point
"""

import os
import sys
import argparse

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def start_mcp_server():
    """Start the MCP server for bookmark management."""
    from src.server import app
    print("Starting LinkVault MCP Server...")
    app.run()

def start_cli():
    """Start the command-line interface."""
    from src.url_manager import main as url_manager_main
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
