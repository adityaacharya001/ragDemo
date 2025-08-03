#!/usr/bin/env python
"""
Simple example script showing how to get space ID and fetch related pages
"""
import os
from dotenv import load_dotenv
from utils.confluence_api import get_all_spaces_list, get_space_id_by_key, get_pages_by_space_id

# Load environment variables
load_dotenv()

def main():
    # 1. List all available spaces
    print("Fetching all Confluence spaces...")
    spaces = get_all_spaces_list()
    
    if not spaces:
        print("No spaces found or error fetching spaces.")
        return
    
    print(f"\nFound {len(spaces)} spaces:")
    
    # Print space details in a table format
    print("\n{:<15} {:<30} {:<15}".format("KEY", "NAME", "ID"))
    print("-" * 60)
    for space in spaces:
        print("{:<15} {:<30} {:<15}".format(
            space.get('key', 'N/A'),
            space.get('name', 'N/A')[:30],
            space.get('id', 'N/A')
        ))
    
    # 2. Use the first space key or environment variable
    space_key = os.getenv("SPACE_KEY")
    if not space_key and spaces:
        space_key = spaces[0].get('key')
        print(f"\nUsing first available space key: {space_key}")
    
    # 3. Get space ID by key
    space_id = get_space_id_by_key(space_key)
    
    if not space_id:
        print(f"Could not find space ID for key: {space_key}")
        return
    
    print(f"\nSpace ID for key '{space_key}': {space_id}")
    
    # 4. Set a default limit
    limit = 10
    
    print(f"\nFetching up to {limit} pages for space ID {space_id}...")
    pages_data = get_pages_by_space_id(space_id, start=0, limit=limit)
    
    if not pages_data or "results" not in pages_data:
        print("No pages found or error fetching pages.")
        return
    
    pages = pages_data.get("results", [])
    
    print(f"\nFound {len(pages)} pages:")
    print("\n{:<10} {:<40} {:<15}".format("ID", "TITLE", "STATUS"))
    print("-" * 65)
    
    for page in pages:
        print("{:<10} {:<40} {:<15}".format(
            page.get('id', 'N/A'),
            page.get('title', 'N/A')[:40],
            page.get('status', 'N/A')
        ))
    
    print("\nDemonstration complete!")

if __name__ == "__main__":
    main()
