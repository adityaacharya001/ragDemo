import os
import pandas as pd
import time
from dotenv import load_dotenv, find_dotenv
import gradio as gr
import openai
from utils.pinecone_logic import delete_pinecone_index, get_pinecone_index, upsert_data
from utils.data_prep import import_csv, clean_data_pinecone_schema, generate_embeddings_and_add_to_df
from utils.openai_logic import get_embeddings, create_prompt, add_prompt_messages, get_chat_completion_messages, create_system_prompt
import sys

# load environment variables
load_dotenv(find_dotenv())

# Function to extract information
def extract_info(data):
    extracted_info = []
    for match in data['matches']:
        source = match['metadata']['source']
        score = match['score']
        extracted_info.append((source, score))
    return extracted_info


# main function
def main(query):
    # https://platform.openai.com/docs/models  ## validate the model you want to use
    # https://platform.openai.com/api-keys ## sign up for an API key
    # https://www.pinecone.io ## sign up access and for an API key (serverless vector database)

    print("Start: Main function")
    
    model_for_openai_embedding="text-embedding-3-small"
    model_for_openai_chat="gpt-3.5-turbo-0125"
    index_name = "aditya-acharya-ai"
    csv_file = './data/confluence_pages.csv'
    # query = "This is where I put a question if I'm Testing?"

    try:
        # Check if Pinecone API key is valid
        if not os.getenv("PINECONE_API_KEY"):
            print("Error: PINECONE_API_KEY environment variable is not set.")
            return "Error: PINECONE_API_KEY environment variable is not set."

        # Check if OpenAI API key is valid
        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY environment variable is not set.")
            return "Error: OPENAI_API_KEY environment variable is not set."

        # Get or create Pinecone index
        try:
            # delete_pinecone_index(index_name)  # uncomment to delete index
            index, index_created = get_pinecone_index(index_name)
        except Exception as e:
            print(f"Error with Pinecone: {e}")
            return f"Error with Pinecone: {e}"

        try:
            # Import error tracker
            from utils.error_logger import get_error_tracker
            error_tracker = get_error_tracker()

            # Always refresh data in the index
            df = pd.DataFrame(columns=['id', 'tiny_link', 'content'])
            df = import_csv(df, csv_file, max_rows=2000)
            if df.empty:
                error_msg = f"Warning: No data found in {csv_file}"
                print(error_msg)
                error_tracker.log_error("empty_data", error_msg)

            # Clean the data
            df = clean_data_pinecone_schema(df)

            # Process data in smaller batches to reduce rate limit issues
            batch_size = 25  # Smaller batch size to be more conservative with API limits
            total_rows = len(df)
            processed_df = pd.DataFrame(columns=['id', 'metadata', 'values'])

            # Track batch statistics
            batch_stats = {
                "total_batches": (total_rows + batch_size - 1) // batch_size,
                "successful_batches": 0,
                "failed_batches": 0,
                "total_rows_processed": 0
            }

            # Adaptively adjust batch timing based on errors
            batch_pause_time = 2  # start with 2 seconds between batches

            for i in range(0, total_rows, batch_size):
                current_batch = i // batch_size + 1
                batch_range = f"{i}-{min(i+batch_size, total_rows)}"
                print(
                    f"Processing batch {current_batch}/{batch_stats['total_batches']} ({batch_range})")
                batch_df = df.iloc[i:i+batch_size].copy()

                # Check if we should continue based on recent error patterns
                if not error_tracker.should_continue("rate_limit", threshold=10, window_seconds=60):
                    print(
                        f"Too many rate limit errors detected. Pausing batch processing and using data collected so far.")
                    break

                # Generate embeddings for this batch
                try:
                    start_time = time.time()
                    batch_df = generate_embeddings_and_add_to_df(
                        batch_df, model_for_openai_embedding)

                    # Filter out rows without embeddings
                    success_rows = batch_df[batch_df['embedding_status'] == "success"].copy(
                    )
                    if not success_rows.empty:
                        processed_df = pd.concat([processed_df, success_rows])
                        batch_stats["successful_batches"] += 1
                        batch_stats["total_rows_processed"] += len(
                            success_rows)

                    # Adaptively adjust the pause time between batches
                    batch_duration = time.time() - start_time
                    if batch_duration < 1:  # If batch processed very quickly
                        # Reduce pause but not below 1 second
                        batch_pause_time = max(1, batch_pause_time - 0.5)

                    # Introduce a pause between batches to reduce rate limit issues
                    if i + batch_size < total_rows:
                        print(
                            f"Batch {current_batch} completed. Pausing for {batch_pause_time} seconds before next batch...")
                        time.sleep(batch_pause_time)

                except Exception as batch_error:
                    error_msg = f"Error processing batch {current_batch}: {batch_error}"
                    print(error_msg)
                    error_tracker.log_error("batch_processing", error_msg)
                    batch_stats["failed_batches"] += 1

                    # Increase pause time after an error
                    # Exponential backoff up to 30 seconds
                    batch_pause_time = min(30, batch_pause_time * 2)

                    # Pause longer after error
                    time.sleep(batch_pause_time)

            # Print batch statistics
            print(
                f"Batch processing complete: {batch_stats['successful_batches']}/{batch_stats['total_batches']} batches successful")
            print(
                f"Total rows with embeddings: {batch_stats['total_rows_processed']}/{total_rows}")

            # Use the processed dataframe for upsert if we have data
            if not processed_df.empty:
                # Drop any extra columns we added for tracking
                if 'embedding_status' in processed_df.columns:
                    processed_df = processed_df.drop(
                        'embedding_status', axis=1)

                try:
                    print(
                        f"Upserting {len(processed_df)} records to Pinecone index...")
                    upsert_data(index, processed_df)
                    print("Upsert to Pinecone completed successfully.")
                except Exception as upsert_error:
                    error_msg = f"Error during Pinecone upsert: {upsert_error}"
                    print(error_msg)
                    error_tracker.log_error("pinecone_upsert", error_msg)
            else:
                error_msg = "Warning: No data was successfully processed for embedding. Using existing index data if available."
                print(error_msg)
                error_tracker.log_error("no_embeddings", error_msg)

        except Exception as e:
            error_msg = f"Error preparing data: {e}"
            print(error_msg)
            # Log the error
            from utils.error_logger import get_error_tracker
            error_tracker = get_error_tracker()
            error_tracker.log_error("data_preparation", error_msg)
            # Continue anyway, we might have existing data in the index

        try:
            # Generate query embedding and search
            embed = get_embeddings(query, model_for_openai_embedding)
            res = index.query(
                vector=embed.data[0].embedding, top_k=3, include_metadata=True)

            # create system prompt and user prompt for openai chat completion
            messages = []
            system_prompt = create_system_prompt()
            prompt = create_prompt(query, res)
            messages = add_prompt_messages("system", system_prompt, messages)
            messages = add_prompt_messages("user", prompt, messages)
            response = get_chat_completion_messages(
                messages, model_for_openai_chat)

            print('-' * 80)
            extracted_info = extract_info(res)
            validated_info = []
            for info in extracted_info:
                source, score = info
                validated_info.append(f"Source: {source}    Score: {score}")

            validated_info_str = "\n".join(validated_info)
            final_output = response + "\n\n" + validated_info_str
            print(final_output)
            print('-' * 80)
            return final_output
        except openai.RateLimitError as e:
            error_msg = "OpenAI API Error: You've exceeded your quota. Please check your OpenAI API key and billing details."
            print(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(error_msg)
            return error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        return error_msg


# if __name__ == "__main__":
#     main("What is your contact information?")


# create Gradio interface for the chatbot
gr.close_all()
demo = gr.Interface(fn=main,
                    inputs=[gr.Textbox(
                        label="Hello, my name is Aiden, your customer service assistant, how can i help?", lines=1, placeholder=""),],
                    outputs=[gr.Textbox(label="response", lines=30)],
                    title="Ask SourceWise Anything (ASA)",
                    description="A question and answering chatbot that answers questions based on your confluence knowledge base.  Note: anything that was tagged internal_only has been removed",
                    allow_flagging="never")
demo.launch(server_name="localhost", server_port=8888)
