import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv
import pandas as pd
import sys
from bs4 import BeautifulSoup

# Load environment variables from .env file
load_dotenv()
confluence_domain = os.getenv("CONFLUENCE_DOMAIN")
confluence_token = os.getenv("CONFLUENCE_TOKEN")
# username = os.getenv("username")
# password = os.getenv("password")

# Set your Confluence details here
space_key = os.getenv("SPACE_KEY")  # replace with your info

# Function to fetch pages from Confluence
def fetch_pages(start, limit):
    url = f'{confluence_domain}/wiki/api/v2/spaces/{space_key}/pages?limit={limit}&start={start}'
    json_data = api_call(url)
    if json_data is not None:
        return json_data
    else:
        print("Failed to fetch pages.")
        return None
    
# Function to make an API call


def api_call(url):
    try:
        # Use Basic Authentication with email and API token
        email = "aditya2012ece@gmail.com"  # Use your Atlassian account email
        token = os.getenv('CONFLUENCE_TOKEN')

        response = requests.get(url, auth=(email, token))

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print(
                "Error: Permission denied (403 Forbidden). Your account doesn't have access to this resource.")
        elif response.status_code == 404:
            print("Error: Page not found.")
        elif response.status_code == 401:
            print("Error: Authentication failed. Check your email and token.")
        elif response.status_code == 500:
            print("Error: Internal server error.")
        else:
            print(
                f"Failed to get pages: HTTP status code {response.status_code}")
            print(f"Response content: {response.text[:200]}...")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    return None


# Function to fetch labels from Confluence
def fetch_labels(page_id):
    url = f'{confluence_domain}/wiki/api/v2/pages/{page_id}/labels'
    json_data = api_call(url)

    if json_data:
        try:
            internal_only = False
            for item in json_data.get("results", []):
                if item.get("name") == 'internal_only':
                    internal_only = True

            return internal_only
        except KeyError:
            print("Error processing JSON data.")
            return None
    else:
        print("Failed to fetch labels.")
        return None


# Function to fetch page content from Confluence
def fetch_page_content(page_id):
    url = f'{confluence_domain}/wiki/api/v2/pages/{page_id}?body-format=storage'
    json_data = api_call(url)

    if json_data:
        try:
            return json_data['body']['storage']['value']
        except KeyError:
            print("Error: Unable to access page content in the returned JSON.")
            return None
    else:
        print("Failed to fetch page content.")
        return None
    

# Function to create an empty DataFrame    
def create_dataframe():
    try:
        columns = ['id', 'type', 'status', 'tiny_link', 'title', 'content', 'is_internal']
        df = pd.DataFrame(columns=columns)
        return df
    except Exception as e:
        print(f"An error occurred while creating the DataFrame: {e}")
        return None


# Function to add all pages to the DataFrame
def add_all_pages_to_dataframe(df, all_pages):
    if not isinstance(df, pd.DataFrame):
        print("Error: The first argument must be a pandas DataFrame.")
        return None

    if not isinstance(all_pages, list):
        print("Error: The second argument must be a list.")
        return None

    for page in all_pages:
        try:
            new_record = [{
                'id': page.get('id', ''),
                'type': page.get('type', ''),
                'status': page.get('status', ''),
                'tiny_link': page.get('_links', {}).get('webui', ''),  # V2 API uses 'webui' instead of 'tinyui'
                'title': page.get('title', '')
            }]

            # Add new records to the DataFrame
            df = pd.concat([df, pd.DataFrame(new_record)], ignore_index=True)
        except Exception as e:
            print(f"An error occurred while adding a page to the DataFrame: {e}")

    return df


# Function index of the DataFrame
def set_index_of_dataframe(df):
    if not isinstance(df, pd.DataFrame):
        print("Error: The argument must be a pandas DataFrame.")
        return None

    if 'id' not in df.columns:
        print("Error: 'id' column not found in the DataFrame.")
        return None

    try:
        df.set_index('id', inplace=True)
        return df
    except Exception as e:
        print(f"An error occurred while setting the index: {e}")
        return None

# Function to fetch by limit


def fetch_pages_by_limit(all_pages, start, limit):
    if not isinstance(all_pages, list):
        print("Error: 'all_pages' must be a list.")
        return None

    while True:
        response_data = fetch_pages(start, limit)
        if response_data:
            results = response_data.get('results')
            if results:
                all_pages.extend(results)
                # Check if there are more pages using the 'next' link
                if response_data.get('_links', {}).get('next'):
                    start += limit
                else:
                    break
            else:
                print("Warning: No results found in the response.")
                break
        else:
            print("Error: Failed to fetch pages.")
            return None

    return all_pages

from tqdm import tqdm  # Make sure to import tqdm at the top of your script

def fetch_all_pages(all_pages, start, limit, max_chunk_size=200):
    print(f"Total pages fetched: {len(all_pages)}")
    return all_pages

    # Calculate the total number of chunks to fetch based on the limit and max_chunk_size
    total_chunks = (limit + max_chunk_size - 1) // max_chunk_size

    # Initialize the tqdm progress bar
    with tqdm(total=limit, desc="Fetching pages") as pbar:
        while True:
            chunk_size = min(limit, max_chunk_size)  # Determine the size of the next chunk
            response_data = fetch_pages(start, chunk_size)
            if response_data:
                results = response_data.get('results')
                if results is not None:
                    all_pages.extend(results)
                    fetched_count = len(results)
                    pbar.update(fetched_count)  # Update the progress bar with the number of fetched results
                    if fetched_count < chunk_size:
                        break  # Break the loop if the number of results is less than the chunk size
                    start += fetched_count
                    limit -= fetched_count  # Decrease the remaining limit by the number of fetched results
                    if limit <= 0:
                        break  # If the remaining limit is 0 or less, we've fetched everything needed
                else:
                    print("Warning: No results found in the response.")
                    break
            else:
                print("Error: Failed to fetch pages.")
                return None
            
    return all_pages


# Function to delete internal_only records
def delete_internal_only_records(df):
    # Ensure df is a pandas DataFrame
    if not isinstance(df, pd.DataFrame):
        print("Error: The variable 'df' must be a pandas DataFrame.")
        return df
    
    # Loop through the DataFrame with a tqdm progress bar
    if 'is_internal' in df.columns:
        for page_id, row in tqdm(df.iterrows(), total=df.shape[0], desc="Updating is_internal status"):
            is_internal_page = fetch_labels(page_id)
            
            if is_internal_page is not None:
                df.loc[page_id, 'is_internal'] = is_internal_page
            else:
                print(f"Warning: Could not fetch labels for page ID {page_id}.")
    else:
        print("Error: 'is_internal' column not found in the DataFrame.")
        return df
    
    # Delete internal_only records
    df = df[df['is_internal'] != True]

    return df


def add_content_to_dataframe(df):
    # Check if the input is a pandas DataFrame
    if not isinstance(df, pd.DataFrame):
        print("Error: The variable 'df' must be a pandas DataFrame.")
        return df

    # Wrap the loop in tqdm for progress tracking
    for page_id, row in tqdm(df.iterrows(), total=df.shape[0], desc="Updating DataFrame"):
        html_content = fetch_page_content(page_id)

        if html_content is not None:
            try:
                # Parse the HTML content
                soup = BeautifulSoup(html_content, "lxml")

                # Extract text with proper spacing
                text_parts = []
                for element in soup.stripped_strings:
                    text_parts.append(element)

                page_content = ' '.join(text_parts)

                # Update the DataFrame with the extracted content
                df.loc[page_id, 'content'] = page_content
            except Exception as e:
                print(f"Error processing HTML content for page ID {page_id}: {e}")
        else:
            print(f"Warning: Could not fetch content for page ID {page_id}.")

    return df



def save_dataframe_to_csv(df, filename):
    if not isinstance(df, pd.DataFrame):
        print("Error: The variable 'df' must be a pandas DataFrame.")
    else:
        try:
            df.to_csv(filename, index=True)
            print("Data successfully saved " + str(len(df)) + " records to " + filename)
        except Exception as e:
            print(f"An error occurred while saving the DataFrame to CSV: {e}")


def test_api_connection():
    """Test the connection to the Confluence API."""
    url = f'{confluence_domain}/wiki/api/v2/spaces'
    print(f"Testing connection to: {url}")

    try:
        email = "aditya2012ece@gmail.com"  # Use your Atlassian account email
        token = confluence_token

        response = requests.get(url, auth=(email, token))

        print(f"Response status code: {response.status_code}")
        if response.status_code == 200:
            print("Connection successful!")
            spaces = response.json().get('results', [])
            print(f"Available spaces: {[space.get('key') for space in spaces]}")
            return True
        else:
            print(f"Connection failed with status code: {response.status_code}")
            print(f"Response text: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"Error connecting to API: {e}")
        return False

def main():
    #Fetch pages on limit occurance
    all_pages = []
    start = 0
    limit = 25
    csv_file = './data/kb.csv'

    if not test_api_connection():
        print("Failed to connect to the Confluence API. Exiting.")
        return
    
    print("Fetching pages...")
    # all_pages = fetch_pages_by_limit(all_pages, start, limit)
    all_pages = fetch_all_pages(all_pages, start, limit)
    print(f"Fetched {len(all_pages)} pages in total.")
    print(f"all_pages", all_pages[:5])  # Print first 5 pages for debugging
    df = create_dataframe()
    df = add_all_pages_to_dataframe(df, all_pages)
    df = set_index_of_dataframe(df)
    df = delete_internal_only_records(df)
    print("Removed " + str(limit - len(df)) + " internal_only records")
    print("Adding content to DataFrame...")
    df = add_content_to_dataframe(df)
    save_dataframe_to_csv(df, csv_file)


if __name__ == "__main__":
    main()