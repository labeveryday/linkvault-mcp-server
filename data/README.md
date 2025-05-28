# LinkVault Data Directory

This directory stores the database and configuration files for LinkVault.

## Expected Files

When running LinkVault, the following files will be created in this directory:

- `bookmarks.db`: SQLite database for MCP server mode
- `url_database.json`: JSON file for CLI mode

## Important Notes

- These files are automatically created when you run LinkVault
- They are excluded from Git via .gitignore to protect your private bookmark data
- Do not manually edit these files unless you know what you're doing

## First-Time Setup

No manual setup is required. The application will create these files with the correct structure when you first run it.

## Backup

If you want to back up your bookmarks, you can copy these files to a secure location. To restore, simply place them back in this directory.
