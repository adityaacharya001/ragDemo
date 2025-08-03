import requests
from requests.auth import HTTPBasicAuth
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
confluence_domain = os.getenv("CONFLUENCE_DOMAIN")
email = os.getenv("CONFLUENCE_EMAIL", "aditya2012ece@gmail.com")
token = os.getenv("CONFLUENCE_TOKEN")

def api_call(url):
    """
    Make a GET API call to Confluence with authentication
    """
    try:
        response = requests.get(url, auth=(email, token))

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            print("Error: Permission denied (403 Forbidden). Your account doesn't have access to this resource.")
        elif response.status_code == 404:
            print("Error: Resource not found.")
        elif response.status_code == 401:
            print("Error: Authentication failed. Check your email and token.")
        elif response.status_code == 500:
            print("Error: Internal server error.")
        else:
            print(f"Failed to make API call: HTTP status code {response.status_code}")
            print(f"Response content: {response.text[:200]}...")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

    return None

def get_all_spaces(start=0, limit=100):
    """
    Get all available Confluence spaces with pagination
    """
    url = f'{confluence_domain}/wiki/api/v2/spaces?limit={limit}&start={start}'
    return api_call(url)

def get_all_spaces_list():
    """
    Get complete list of all available Confluence spaces
    """
    all_spaces = []
    start = 0
    limit = 100  # API max is 100
    
    while True:
        spaces_data = get_all_spaces(start, limit)
        if not spaces_data or "results" not in spaces_data:
            break
            
        results = spaces_data["results"]
        if not results:
            break
            
        all_spaces.extend(results)
        
        if not spaces_data.get("_links", {}).get("next"):
            break
            
        start += limit
    
    return all_spaces

def get_space_by_key(space_key):
    """
    Get space information by space key
    """
    url = f'{confluence_domain}/wiki/api/v2/spaces'
    spaces_data = api_call(url)
    
    if spaces_data and "results" in spaces_data:
        for space in spaces_data["results"]:
            if space.get("key") == space_key:
                return space
    
    return None

def get_space_id_by_key(space_key):
    """
    Get space ID using space key
    """
    space_data = get_space_by_key(space_key)
    if space_data and 'id' in space_data:
        return space_data['id']
    return None

def get_pages_by_space_id(space_id, start=0, limit=25):
    """
    Get pages by space ID with pagination
    """
    url = f'{confluence_domain}/wiki/api/v2/spaces/{space_id}/pages?limit={limit}&start={start}'
    return api_call(url)

def get_pages_by_space_key(space_key, start=0, limit=25):
    """
    Get pages by space key with pagination
    """
    # First get the space ID by key
    space_id = get_space_id_by_key(space_key)
    if space_id:
        return get_pages_by_space_id(space_id, start, limit)
    return None

def fetch_page_content(page_id):
    """
    Fetch page content by page ID
    """
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

def fetch_labels(page_id):
    """
    Fetch labels for a page by page ID
    """
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
