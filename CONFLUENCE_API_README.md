# Space and Page Examples for Confluence API v2

This document explains how to use the new Confluence API v2 functionality to:
1. Get information about spaces
2. Get space ID by space key
3. Fetch pages related to a space

## Quick Start

To quickly get a space ID by key and fetch all its pages:

```bash
# Basic usage (automatically saves results to ./data/space_pages.csv)
python get_space_id_and_pages.py YOURSPACEKEY

# Limit the number of pages
python get_space_id_and_pages.py YOURSPACEKEY --limit 10

# Specify custom output file
python get_space_id_and_pages.py YOURSPACEKEY --output ./data/my_pages.csv
```

For automatic exploration of spaces and pages:
```bash
python get_space_and_pages.py
```

Note: All scripts now automatically perform actions without prompting for confirmation.

## Prerequisites

1. Set up your `.env` file with the following variables:
   ```
   CONFLUENCE_DOMAIN=https://your-domain.atlassian.net
   CONFLUENCE_TOKEN=your_api_token
   CONFLUENCE_EMAIL=your_email@example.com
   SPACE_KEY=optional_default_space_key
   ```

2. Make sure all dependencies are installed:
   ```
   pip install -r requirements.txt
   ```

## Using the Utility Functions

The `utils/confluence_api.py` module contains standalone functions that you can import and use in your own scripts:

```python
from utils.confluence_api import (
    get_all_spaces,
    get_space_id_by_key,
    get_pages_by_space_id,
    get_pages_by_space_key
)

# List all available spaces
spaces_data = get_all_spaces()
if spaces_data:
    print([space.get('key') for space in spaces_data.get('results', [])])

# Get space ID by key
space_id = get_space_id_by_key("YOURSPACEKEY")
print(f"Space ID: {space_id}")

# Get pages by space ID
pages = get_pages_by_space_id(space_id, start=0, limit=25)

# Get pages directly by space key (fallback method)
pages = get_pages_by_space_key("YOURSPACEKEY", start=0, limit=25)
```

## Using the Command-Line Script

You can run the `app_confluence_v2.py` script to:

1. List all available spaces:
   ```
   python app_confluence_v2.py
   ```

2. Fetch pages for a specific space (defined in .env):
   ```
   # After setting SPACE_KEY in .env
   python app_confluence_v2.py
   ```

The script will:
1. Get the space ID using the space key
2. Fetch all pages for that space
3. Automatically fetch content and labels for each page
4. Automatically remove internal-only pages
5. Save the results to a CSV file

## Difference from Original Implementation

The new implementation provides these improvements:
1. First gets the space ID by key and then finds pages related to it
2. Separates API calls into a reusable module
3. Has better error handling and fallbacks
4. Provides more detailed feedback during the process

For more information, see the Confluence API v2 documentation.
