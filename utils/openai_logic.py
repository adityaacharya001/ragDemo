# note which revision of python, for example 3.9.6
from datasets import load_dataset
from openai import OpenAI
import openai  # Import both the module and the class
from openai import RateLimitError, APIError, APIConnectionError
from pinecone import Pinecone
from tqdm.auto import tqdm
import ast
import os
import time
import pandas as pd
from dotenv import load_dotenv, find_dotenv
import sys
import json 
import numpy as np
import gradio as gr

#Global variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)


# get embeddings
def get_embeddings(query, model_emb):
   embedding = openai_client.embeddings.create(input = query, model=model_emb)
   print("Dimension of query embedding: ", len(embedding.data[0].embedding))
   return embedding


def create_embeddings(text, model_emb):
    try:
        # Truncate text if it exceeds token limits (OpenAI text-embedding models typically have ~8K token limit)
        max_length = 8000  # Conservative estimate
        if len(text) > max_length:
            print(
                f"Warning: Text exceeded maximum length. Truncating from {len(text)} to {max_length} characters.")
            text = text[:max_length]

        response = openai_client.embeddings.create(
            input=text,
            model=model_emb
        )
        embedding = response.data[0].embedding
        return embedding
    except Exception as e:
        # Re-raise the exception to be handled by the caller with more context
        print(f"Error in create_embeddings: {str(e)}")
        raise

# create prompt for openai
def create_prompt(query, res):
    contexts = [ x['metadata']['text'] for x in res['matches']]
    prompt_start = ("Answer the question based on the context and sentiment of the question.\n\n" + "Context:\n") # also, do not discuss any Personally Identifiable Information.
    prompt_end = (f"\n\nQuestion: {query}\nAnswer:")
    prompt = (prompt_start + "\n\n---\n\n".join(contexts) + prompt_end)
    return prompt


def add_prompt_messages(role, content, messages):
    json_message = {
        "role": role, 
        "content": content
    }
    messages.append(json_message)
    return messages

def get_chat_completion_messages(messages, model_chat, temperature=0.0): 
    from openai import RateLimitError, APIError, APIConnectionError
    import time

    max_retries = 3
    retry_count = 0

    while retry_count <= max_retries:
        try:
            response = openai_client.chat.completions.create(
                model=model_chat,
                messages=messages,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            retry_count += 1
            wait_time = (2 ** retry_count) * 5

            if retry_count > max_retries:
                print(
                    f"OpenAI rate limit exceeded after {max_retries} retries.")
                return "I'm sorry, but I'm currently experiencing high traffic. Please try again in a few minutes."

            print(
                f"Rate limit error. Waiting for {wait_time} seconds before retry {retry_count}/{max_retries}...")
            time.sleep(wait_time)

        except APIConnectionError as e:
            retry_count += 1
            wait_time = 5 * retry_count

            if retry_count > max_retries:
                print(f"OpenAI API connection error: {e}")
                return "I'm sorry, but I'm having trouble connecting to the AI service. Please try again later."

            print(
                f"API connection error. Retrying in {wait_time} seconds... ({retry_count}/{max_retries})")
            time.sleep(wait_time)

        except APIError as e:
            if e.status_code == 429:  # Rate limit error
                retry_count += 1
                wait_time = (2 ** retry_count) * 5

                if retry_count > max_retries:
                    print(
                        f"OpenAI API rate limit (429) exceeded after {max_retries} retries.")
                    return "I'm sorry, but the service is currently busy. Please try again in a few minutes."

                print(
                    f"Rate limit error. Waiting for {wait_time} seconds before retry {retry_count}/{max_retries}...")
                time.sleep(wait_time)
            else:
                print(f"OpenAI API error: {e}")
                return "I apologize, but I encountered an error processing your request."

        except Exception as e:
            print(f"Error in get_chat_completion_messages: {e}")
            return "I apologize, but something went wrong while processing your request."


def create_system_prompt(role="customer_service"):
    """
    Create a system prompt for the LLM based on the role.
    
    Args:
        role: The role the LLM should assume. Defaults to "customer_service".
        
    Returns:
        str: A formatted system prompt.
    """

    prompts = {
        "customer_service": """
        You are a helpful customer service specialist who provides accurate and helpful information based on the provided context.
        
        Guidelines:
        1. Answer questions based ONLY on the context provided.
        2. If you don't know the answer based on the context, acknowledge that and don't make up information.
        3. Be concise and clear in your responses.
        4. Maintain a professional, friendly tone.
        5. Do not reveal any personal or confidential information unless it's explicitly in the provided context.
        6. When relevant, cite the source of your information.
        """,

        "technical_support": """
        You are a technical support specialist who helps users solve technical problems based on the provided context.
        
        Guidelines:
        1. Answer questions based ONLY on the technical documentation provided in the context.
        2. Provide step-by-step troubleshooting instructions when appropriate.
        3. If you don't know the answer based on the context, acknowledge that and don't make up technical details.
        4. Be precise and accurate in your explanations.
        5. Use clear, jargon-free language whenever possible.
        """,

        "general_assistant": """
        You are a helpful assistant who provides information based strictly on the provided context.
        
        Guidelines:
        1. Answer questions based ONLY on the context provided.
        2. If the information is not in the context, acknowledge that and don't make up information.
        3. Be helpful, concise, and accurate.
        4. Maintain a conversational, friendly tone.
        """
    }

    # Get the appropriate prompt or default to general_assistant if role not found
    system_prompt = prompts.get(role, prompts["general_assistant"])

    # Track the prompt creation in logs (without storing the actual prompt content)
    try:
        from utils.error_logger import get_error_tracker
        error_tracker = get_error_tracker()
        error_tracker.log_success(f"system_prompt_{role}")
    except ImportError:
        # If error_logger is not available, continue without logging
        pass

    return system_prompt.strip()

