import pandas as pd
import json
import time
import datetime
from tqdm.auto import tqdm
from utils.openai_logic import create_embeddings
import os, sys
from collections import defaultdict

# Function to get dataset
def import_csv(df, csv_file, max_rows):
    print("Start: Getting dataset")

    # Check if file exists
    if not os.path.exists(csv_file):
        print("Error: CSV file does not exist.")
        return df
    
    try:
        # Attempt to read the CSV file
        df = pd.read_csv(csv_file, usecols=['id', 'tiny_link', 'content'], nrows=max_rows)
    except FileNotFoundError:
        print("Error: CSV file not found.")
        return df
    except PermissionError:
        print("Error: Permission denied when accessing the CSV file.")
        return df
    except Exception as e:
        print(
            f"Error: An unexpected error occurred while reading the CSV file. ({e})")
        return df
    
    # Check if DataFrame is empty
    if df.empty:
        print("Error: No data found in the CSV file.")
    
    return df
    

def clean_data_pinecone_schema(df):
    # Ensure df is a DataFrame
    if not isinstance(df, pd.DataFrame):
        print(f"Error: Expected DataFrame but got {type(df)}")
        return pd.DataFrame(columns=['id', 'metadata'])

    # Ensure necessary columns are present
    required_columns = {'id', 'tiny_link', 'content'}
    if not required_columns.issubset(df.columns):
        missing_columns = required_columns - set(df.columns)
        print(
            f"Error: CSV file is missing required columns: {missing_columns}")
        return pd.DataFrame(columns=['id', 'metadata'])
    
    # Filter out rows where 'content' is empty
    df = df[df['content'].notna() & (df['content'] != '')]
    
    if df.empty:
        print("Error: No valid data found in the CSV file after filtering empty content.")
        return pd.DataFrame(columns=['id', 'metadata'])
    
    # Proceed with the function's main logic
    df['id'] = df['id'].astype(str)
    df.rename(columns={'tiny_link': 'source'}, inplace=True)
    df['metadata'] = df.apply(lambda row: json.dumps({'source': row['source'], 'text': row['content']}), axis=1)
    df = df[['id', 'metadata']]
    # print(df.head())
    print("Done: Dataset retrieved")
    return df
    return df


# Function to generate embeddings and add to DataFrame
def generate_embeddings_and_add_to_df(df, model_emb):
    print("Start: Generating embeddings and adding to DataFrame")
    # Check if the DataFrame and the 'metadata' column exist
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        print("Error: DataFrame is None, not a DataFrame, or empty.")
        return pd.DataFrame(columns=['id', 'metadata', 'values'])
    
    if 'metadata' not in df.columns:
        print("Error: DataFrame is missing 'metadata' column.")
        return pd.DataFrame(columns=['id', 'metadata', 'values'])

    # Import OpenAI specific exceptions for better error handling
    from openai import RateLimitError, APIError, APIConnectionError
    # Import the error tracker
    from utils.error_logger import get_error_tracker
    error_tracker = get_error_tracker()
    
    df['values'] = None

    # Keep track of stats
    total_rows = len(df)
    successful_embeddings = 0
    failed_embeddings = 0
    max_retries = 3

    # Set the time to wait between each embedding request
    # This helps avoid hitting rate limits
    time_between_requests = 0.1  # seconds

    for index, row in tqdm(df.iterrows(), total=df.shape[0]):
        try:
            content = row['metadata']
            meta = json.loads(content)
        except json.JSONDecodeError as e:
            error_msg = f"Error decoding JSON for row {index}: {e}"
            print(error_msg)
            error_tracker.log_error("json_decode", error_msg)
            failed_embeddings += 1
            continue  # Skip to the next iteration

        text = meta.get('text', '')
        if not text:
            error_msg = f"Warning: Missing 'text' in metadata for row {index}. Skipping."
            print(error_msg)
            error_tracker.log_error("missing_text", error_msg)
            failed_embeddings += 1
            continue

        # Implement retry logic with exponential backoff
        retries = 0
        while retries <= max_retries:
            # Check if we should continue based on recent error patterns
            if not error_tracker.should_continue("rate_limit", threshold=5, window_seconds=60):
                print(
                    f"Too many rate limit errors in short period. Pausing operations and returning partial results.")
                # Add processing status to the DataFrame
                df['embedding_status'] = df.apply(
                    lambda x: "success" if isinstance(
                        x.get('values', None), list) else "not_processed",
                    axis=1
                )
                print(
                    f"Embedding Generation Summary: {successful_embeddings}/{total_rows} successful, {failed_embeddings}/{total_rows} failed")
                return df

            try:
                # Add a small delay to avoid hitting rate limits
                time.sleep(time_between_requests)

                # Generate embedding
                response = create_embeddings(text, model_emb)

                # Store the embedding
                df.at[index, 'values'] = response

                # Log success
                error_tracker.log_success("embedding_generation")
                successful_embeddings += 1
                break

            except RateLimitError as e:
                error_details = {
                    "row_index": index,
                    "retry": retries,
                    "message": str(e)
                }
                error_tracker.log_error("rate_limit", error_details)

                # Exponential backoff: 5, 10, 20 seconds
                wait_time = (2 ** retries) * 5
                retries += 1

                if retries > max_retries:
                    print(
                        f"Error: OpenAI rate limit exceeded. Reached maximum retries for row {index}.")
                    print(
                        f"Consider: 1) Increasing your OpenAI quota, 2) Using a different embedding model, or 3) Processing data in smaller batches.")
                    failed_embeddings += 1
                    break

                print(
                    f"Rate limit error for row {index}. Waiting for {wait_time} seconds before retry {retries}/{max_retries}...")
                time.sleep(wait_time)

            except APIConnectionError as e:
                error_details = {
                    "row_index": index,
                    "retry": retries,
                    "message": str(e)
                }
                error_tracker.log_error("api_connection", error_details)

                if retries < max_retries:
                    wait_time = 5 * retries
                    print(
                        f"Retrying in {wait_time} seconds... ({retries+1}/{max_retries})")
                    time.sleep(wait_time)
                    retries += 1
                else:
                    print(f"Failed after {max_retries} retries.")
                    failed_embeddings += 1
                    break

            except APIError as e:
                error_type = "api_error"
                status_code = getattr(e, "status_code", None)

                if status_code == 429:  # Rate limit error
                    error_type = "rate_limit"
                    wait_time = (2 ** retries) * 5
                    retries += 1

                    if retries > max_retries:
                        print(
                            f"Error: OpenAI API rate limit (429) exceeded. Reached maximum retries.")
                        failed_embeddings += 1
                        break

                    print(
                        f"Rate limit error for row {index}. Waiting for {wait_time} seconds before retry {retries}/{max_retries}...")
                    time.sleep(wait_time)
                else:
                    error_details = {
                        "row_index": index,
                        "status_code": status_code,
                        "message": str(e)
                    }
                    error_tracker.log_error(error_type, error_details)
                    print(f"OpenAI API error for row {index}: {e}")
                    failed_embeddings += 1
                    break

            except Exception as e:
                error_details = {
                    "row_index": index,
                    "exception_type": type(e).__name__,
                    "message": str(e)
                }
                error_tracker.log_error("unknown", error_details)
                print(f"Error generating embedding for row {index}: {e}")
                failed_embeddings += 1
                break

    # Print summary
    print(
        f"Embedding Generation Summary: {successful_embeddings}/{total_rows} successful, {failed_embeddings}/{total_rows} failed")

    # Add processing status to the DataFrame
    df['embedding_status'] = df.apply(
        lambda x: "success" if isinstance(
            x.get('values', None), list) else "not_processed",
        axis=1
    )

    # Get error summary
    error_summary = error_tracker.get_error_summary()
    print(f"Error summary: {error_summary}")

    print("Done: Generating embeddings and adding to DataFrame")
    return df

