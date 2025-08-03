#!/usr/bin/env python
"""
Pinecone Index Management Utility

This script provides functions for managing Pinecone indexes, including:
- Creating a new index
- Deleting an existing index
- Resetting an index (delete and recreate)
- Checking index statistics

Usage:
  python manage_pinecone_index.py --action create --name your-index-name
  python manage_pinecone_index.py --action delete --name your-index-name
  python manage_pinecone_index.py --action reset --name your-index-name
  python manage_pinecone_index.py --action stats --name your-index-name
"""

import os
import time
import argparse
from dotenv import load_dotenv, find_dotenv
from pinecone import Pinecone

# Load environment variables
load_dotenv(find_dotenv())

def create_pinecone_index(index_name, dimension=1536):
    """Create a new Pinecone index."""
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        print("Error: PINECONE_API_KEY not found in environment variables")
        return False

    try:
        pc = Pinecone(api_key=pinecone_api_key)
        
        # Check if index already exists
        if index_name in [idx.name for idx in pc.list_indexes()]:
            print(f"Index '{index_name}' already exists")
            return True
            
        # Create the index
        print(f"Creating index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=dimension,
            metric="cosine",
            spec={
                "serverless": {
                    "cloud": "aws", 
                    "region": "us-west-2"
                }
            }
        )
        
        # Wait for the index to be ready
        print("Waiting for index to initialize...")
        while not index_name in [idx.name for idx in pc.list_indexes()]:
            time.sleep(5)
            
        print(f"Index '{index_name}' created successfully")
        return True
    
    except Exception as e:
        print(f"Error creating index: {e}")
        return False


def delete_pinecone_index(index_name):
    """Delete an existing Pinecone index."""
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        print("Error: PINECONE_API_KEY not found in environment variables")
        return False

    try:
        pc = Pinecone(api_key=pinecone_api_key)
        
        # Check if index exists
        if not index_name in [idx.name for idx in pc.list_indexes()]:
            print(f"Index '{index_name}' does not exist")
            return True
            
        # Delete the index
        print(f"Deleting index '{index_name}'...")
        pc.delete_index(index_name)
        
        # Wait for the index to be deleted
        print("Waiting for index to be deleted...")
        while index_name in [idx.name for idx in pc.list_indexes()]:
            time.sleep(5)
            
        print(f"Index '{index_name}' deleted successfully")
        return True
    
    except Exception as e:
        print(f"Error deleting index: {e}")
        return False


def reset_pinecone_index(index_name, dimension=1536):
    """Reset a Pinecone index by deleting and recreating it."""
    print(f"Resetting index '{index_name}'...")
    
    # Delete the index if it exists
    delete_success = delete_pinecone_index(index_name)
    if not delete_success:
        print("Error resetting index: Failed to delete existing index")
        return False
        
    # Wait a bit before creating the new index
    time.sleep(5)
        
    # Create a new index
    create_success = create_pinecone_index(index_name, dimension)
    if not create_success:
        print("Error resetting index: Failed to create new index")
        return False
        
    print(f"Index '{index_name}' has been reset successfully")
    return True


def get_index_stats(index_name):
    """Get statistics for a Pinecone index."""
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        print("Error: PINECONE_API_KEY not found in environment variables")
        return False

    try:
        pc = Pinecone(api_key=pinecone_api_key)
        
        # Check if index exists
        if not index_name in [idx.name for idx in pc.list_indexes()]:
            print(f"Index '{index_name}' does not exist")
            return False
            
        # Get the index
        index = pc.Index(index_name)
        
        # Get index statistics
        stats = index.describe_index_stats()
        
        print(f"\nIndex: {index_name}")
        print(f"Total vector count: {stats.get('total_vector_count', 'Unknown')}")
        print(f"Dimension: {stats.get('dimension', 'Unknown')}")
        
        namespaces = stats.get('namespaces', {})
        if namespaces:
            print("\nNamespaces:")
            for ns, ns_stats in namespaces.items():
                print(f"  {ns}: {ns_stats.get('vector_count', 'Unknown')} vectors")
        else:
            print("\nNamespaces: None")
            
        return True
    
    except Exception as e:
        print(f"Error getting index stats: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Manage Pinecone indexes')
    parser.add_argument('--action', choices=['create', 'delete', 'reset', 'stats'], required=True,
                        help='Action to perform on the index')
    parser.add_argument('--name', required=True, help='Name of the Pinecone index')
    parser.add_argument('--dimension', type=int, default=1536, 
                        help='Dimension of vectors for the index (default: 1536)')
    
    args = parser.parse_args()
    
    if args.action == 'create':
        create_pinecone_index(args.name, args.dimension)
    elif args.action == 'delete':
        delete_pinecone_index(args.name)
    elif args.action == 'reset':
        reset_pinecone_index(args.name, args.dimension)
    elif args.action == 'stats':
        get_index_stats(args.name)
    else:
        print(f"Unknown action: {args.action}")


if __name__ == "__main__":
    main()
