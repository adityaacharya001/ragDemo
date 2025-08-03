# RAG (Retrieval-Augmented Generation) Demo

This is a demonstration project for implementing a RAG (Retrieval-Augmented Generation) system using OpenAI for embeddings and completions, and Pinecone as a vector database.

## Overview

RAG enhances language model outputs by retrieving relevant context from a knowledge base before generating responses. This approach combines the benefits of retrieval-based and generative AI systems.

## Key Components

1. **OpenAI API** - For generating embeddings and completions
2. **Pinecone** - Vector database for storing and retrieving embeddings
3. **Confluence API** - Optional data source for knowledge base content

## Setup Instructions

### 1. Environment Setup

First, create a `.env` file in the root directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Prepare Your Data

Place your knowledge base data in the `data` directory. The system expects a CSV file with at least these columns:
- `id` - Unique identifier for each document
- `tiny_link` - Source link or reference for the document
- `content` - The actual text content

The default data file is `data/confluence_pages.csv`.

### 4. Run the Application

```bash
python app_pinecone_openai.py
```

For a web interface, uncomment the Gradio code at the bottom of `app_pinecone_openai.py`.

## Handling Rate Limits

This implementation includes robust handling for OpenAI API rate limits:

### Strategies Implemented

1. **Batch Processing** - Data is processed in small batches to avoid hitting rate limits
2. **Exponential Backoff** - Automatic retries with increasing wait times
3. **Error Logging** - Detailed logs in the `logs` directory for troubleshooting
4. **Adaptive Pausing** - Dynamic adjustment of processing speed based on API response

### If You Encounter Rate Limit Issues

1. **Reduce Batch Size** - Lower the `batch_size` value in `app_pinecone_openai.py`
2. **Use a Different Model** - The smaller embedding models have higher rate limits
3. **Process in Multiple Sessions** - Split your data processing across different time periods
4. **Check Logs** - Review the logs directory for detailed error information

## Managing Pinecone Indexes

Use the `manage_pinecone_index.py` utility to create, delete, or reset your Pinecone indexes:

```bash
# Create a new index
python manage_pinecone_index.py --action create --name your-index-name

# Get statistics about an index
python manage_pinecone_index.py --action stats --name your-index-name

# Reset an index (delete and recreate)
python manage_pinecone_index.py --action reset --name your-index-name
```

## Additional Notes

- The default embedding model is `text-embedding-3-small`
- The default chat completion model is `gpt-3.5-turbo-0125`
- Error logs are stored in the `logs` directory
- For large datasets, consider splitting processing across multiple runs

## Troubleshooting

### OpenAI API Issues

If you encounter persistent rate limit errors:
1. Check your OpenAI API tier and usage limits
2. Consider upgrading your API tier for higher limits
3. Implement rate limiting in your application (already done in this codebase)

### Pinecone Issues

If you have issues with Pinecone:
1. Verify your API key is correct
2. Check that your index exists and has the correct dimensions
3. Use the `manage_pinecone_index.py` tool to reset or check your index

## License

This project is for educational purposes only.
