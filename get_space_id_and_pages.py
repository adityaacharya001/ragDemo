#!/usr/bin/env python
"""
Simple utility script to get space ID by key and find all pages for that space
"""
import os
import sys
import argparse
import pandas as pd
from dotenv import load_dotenv
from utils.confluence_api import get_space_id_by_key, get_pages_by_space_id

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Get space ID by key and find all pages')
    parser.add_argument('space_key', type=str, help='Space key to look up')
    parser.add_argument('--limit', type=int, default=25, help='Limit for number of pages (default: 25)')
    parser.add_argument('--output', type=str, default='./data/space_pages.csv', help='Output CSV file path')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    # Get space ID by key
    print(f"Getting space ID for key: {args.space_key}")
    space_id = get_space_id_by_key(args.space_key)
    
    if not space_id:
        print(f"Could not find space ID for key: {args.space_key}")
        sys.exit(1)
    
    print(f"Space ID for key '{args.space_key}': {space_id}")
    
    # Get pages for space ID
    print(f"Fetching pages for space ID: {space_id} (limit: {args.limit})")
    all_pages = []
    start = 0
    limit = args.limit
    
    while True:
        pages_data = get_pages_by_space_id(space_id, start, min(limit, 100))  # API max is 100 per request
        
        if not pages_data or "results" not in pages_data:
            print("Error fetching pages.")
            break
            
        results = pages_data["results"]
        if not results:
            break
            
        all_pages.extend(results)
        print(f"Fetched {len(results)} pages, total: {len(all_pages)}")
        
        # Check if we've reached the user's limit or if there are no more pages
        if len(all_pages) >= limit or not pages_data.get("_links", {}).get("next"):
            break
            
        start += len(results)
    
    # Display results
    if all_pages:
        print(f"\nFound {len(all_pages)} pages for space key: {args.space_key} (ID: {space_id})")
        
        # Create DataFrame for better display
        df = pd.DataFrame([{
            'id': page.get('id', ''),
            'title': page.get('title', ''),
            'type': page.get('type', ''),
            'status': page.get('status', ''),
            'webui_link': page.get('_links', {}).get('webui', '')
        } for page in all_pages])
        
        # Display in table format
        pd.set_option('display.max_rows', 20)
        pd.set_option('display.width', 120)
        pd.set_option('display.max_colwidth', 30)
        print("\nPage list:")
        print(df)
        
        # Always save to CSV (assume yes)
        output_path = args.output
        df.to_csv(output_path, index=False)
        print(f"\nSaved {len(df)} pages to {output_path}")
    else:
        print("No pages found.")

if __name__ == "__main__":
    main()
