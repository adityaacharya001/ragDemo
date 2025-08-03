#!/usr/bin/env python
"""
Automated RAG Pipeline - Runs all scripts in sequence without user input
"""
import os
import sys
import subprocess
import time
from dotenv import load_dotenv

def run_command(command, description):
    """Run a shell command and print its output"""
    print(f"\n{'='*80}\n{description}\n{'='*80}")
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

def main():
    # Load environment variables
    load_dotenv()
    
    # Ensure data directory exists
    os.makedirs("./data", exist_ok=True)
    
    # Check if SPACE_KEY is set in .env
    space_key = os.getenv("SPACE_KEY")
    if not space_key:
        print("No SPACE_KEY found in .env file.")
        print("Please add SPACE_KEY=your_space_key to your .env file.")
        return
        
    # Step 1: Get space ID and basic page info
    print(f"Step 1: Getting space ID and basic page info for space key: {space_key}")
    if not run_command(f"python get_space_id_and_pages.py {space_key} --limit 50", "Running get_space_id_and_pages.py"):
        print("Failed to get space ID and pages. Exiting.")
        return
        
    # Step 2: Get detailed page content and labels
    print("\nStep 2: Getting detailed page content and labels")
    if not run_command("python app_confluence_v2.py", "Running app_confluence_v2.py"):
        print("Failed to get detailed page content. Exiting.")
        return
    
    # Step 3: Process data for RAG (if app_pinecone_openai.py exists)
    if os.path.exists("./app_pinecone_openai.py"):
        print("\nStep 3: Processing data for RAG")
        if not run_command("python app_pinecone_openai.py", "Running app_pinecone_openai.py"):
            print("Failed to process data for RAG.")
    
    print("\nAutomated pipeline completed successfully!")
    print(f"Data files available in the './data' directory:")
    for file in os.listdir("./data"):
        if file.endswith(".csv"):
            size = os.path.getsize(os.path.join("./data", file)) / 1024  # KB
            print(f"- {file} ({size:.2f} KB)")

if __name__ == "__main__":
    main()
