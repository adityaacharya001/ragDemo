import os
from dotenv import load_dotenv
import gradio as gr
import sys
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
from utils.confluence_api import (
    get_all_spaces,
    get_all_spaces_list,
    get_space_id_by_key, 
    get_pages_by_space_id,
    get_pages_by_space_key,
    fetch_page_content,
    fetch_labels
)

# Load environment variables
load_dotenv()
space_key = os.getenv("SPACE_KEY")

def list_all_spaces():
    """List all available spaces in Confluence"""
    spaces = get_all_spaces_list()
    
    if spaces:
        print(f"Found {len(spaces)} spaces:")
        for space in spaces:
            print(f"Key: {space.get('key')}, Name: {space.get('name')}, ID: {space.get('id')}")
        return spaces
    else:
        print("No spaces found or error fetching spaces.")
        return None

def get_pages_for_space_key(space_key, limit=25):
    """Get pages for a space using space key"""
    print(f"Fetching pages for space with key: {space_key}")
    
    # First get the space ID
    space_id = get_space_id_by_key(space_key)
    
    if space_id:
        print(f"Space ID for key '{space_key}': {space_id}")
        
        # Use the space ID to fetch pages
        all_pages = []
        start = 0
        
        # Fetch pages until there are no more
        while True:
            pages_data = get_pages_by_space_id(space_id, start, limit)
            
            if pages_data and "results" in pages_data:
                results = pages_data["results"]
                if not results:
                    break
                    
                all_pages.extend(results)
                print(f"Fetched {len(results)} pages, total: {len(all_pages)}")
                
                # Check if there are more pages
                if not pages_data.get("_links", {}).get("next"):
                    break
                    
                start += limit
            else:
                print("Error fetching pages or no pages found.")
                break
        
        return all_pages
    else:
        print(f"Could not find space ID for key: {space_key}")
        
        # Try direct API call using space key instead
        print("Trying to fetch pages directly using space key...")
        all_pages = []
        start = 0
        
        while True:
            pages_data = get_pages_by_space_key(space_key, start, limit)
            
            if pages_data and "results" in pages_data:
                results = pages_data["results"]
                if not results:
                    break
                    
                all_pages.extend(results)
                print(f"Fetched {len(results)} pages, total: {len(all_pages)}")
                
                # Check if there are more pages
                if not pages_data.get("_links", {}).get("next"):
                    break
                    
                start += limit
            else:
                print("Error fetching pages or no pages found.")
                break
        
        return all_pages

def create_pages_dataframe(pages):
    """Create a DataFrame from pages data"""
    if not pages:
        return None
        
    # Create DataFrame with page information
    df = pd.DataFrame([{
        'id': page.get('id', ''),
        'type': page.get('type', ''),
        'status': page.get('status', ''),
        'tiny_link': page.get('_links', {}).get('webui', ''),
        'title': page.get('title', ''),
        'space_id': page.get('spaceId', '')
    } for page in pages])
    
    # Set ID as index
    if 'id' in df.columns:
        df.set_index('id', inplace=True)
    
    return df

def add_content_and_labels_to_dataframe(df):
    """Add content and labels info to DataFrame"""
    # Add is_internal column if it doesn't exist
    if 'is_internal' not in df.columns:
        df['is_internal'] = False
    
    # Add content column if it doesn't exist
    if 'content' not in df.columns:
        df['content'] = ''
    
    # Process each page
    for page_id, row in tqdm(df.iterrows(), total=df.shape[0], desc="Processing pages"):
        # Get labels
        is_internal = fetch_labels(page_id)
        if is_internal is not None:
            df.loc[page_id, 'is_internal'] = is_internal
        
        # Get content
        html_content = fetch_page_content(page_id)
        if html_content is not None:
            try:
                # Parse HTML
                soup = BeautifulSoup(html_content, "lxml")
                
                # Extract text
                text_parts = []
                for element in soup.stripped_strings:
                    text_parts.append(element)
                
                page_content = ' '.join(text_parts)
                df.loc[page_id, 'content'] = page_content
            except Exception as e:
                print(f"Error processing HTML content for page ID {page_id}: {e}")
    
    return df

def save_to_csv(df, filename):
    """Save DataFrame to CSV file"""
    if df is not None and not df.empty:
        try:
            df.to_csv(filename, index=True)
            print(f"Data successfully saved ({len(df)} records) to {filename}")
        except Exception as e:
            print(f"Error saving DataFrame to CSV: {e}")
    else:
        print("No data to save.")

def main():
    # If no space key is provided, list all available spaces
    if not space_key:
        print("No SPACE_KEY found in .env file")
        spaces = list_all_spaces()
        if spaces:
            print("\nTo fetch pages for a specific space, add its key to your .env file as SPACE_KEY")
        return
    
    # Get pages for the specified space key
    pages = get_pages_for_space_key(space_key)
    
    if pages:
        print(f"\nFound {len(pages)} pages for space key: {space_key}")
        
        # Create DataFrame
        df = create_pages_dataframe(pages)
        
        # Automatically fetch content and labels (always assume 'yes')
        print("Fetching content and labels for all pages...")
        df = add_content_and_labels_to_dataframe(df)
        
        # Automatically remove internal pages (always assume 'yes')
        original_count = len(df)
        df = df[df['is_internal'] != True]
        print(f"Removed {original_count - len(df)} internal-only pages")
        
        # Save to CSV
        save_to_csv(df, './data/confluence_pages.csv')
    else:
        print(f"No pages found for space key: {space_key}")

# if __name__ == "__main__":
#     main()

#create Gradio interface for the chatbot
gr.close_all()
demo = gr.Interface(fn=main,
                    inputs=[gr.Textbox(label="Hello, my name is ASA, your customer service assistant, how can i help?", lines=1,placeholder=""),],
                    outputs=[gr.Textbox(label="response", lines=30)],
                    title="Customer Service Assistant",
                    description="A question and answering chatbot that answers questions based on your confluence knowledge base.  Note: anything that was tagged internal_only has been removed",
                    allow_flagging="never")
demo.launch(server_name="localhost", server_port=8888)
