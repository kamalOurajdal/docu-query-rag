# DocuQuery

DocuQuery is a Flask-based Retrieval-Augmented Generation (RAG) API for indexing business documents and generating grounded report content from them. It stores document metadata in MongoDB, pushes embedded chunks into Weaviate, and uses OpenAI for embeddings, OCR-style extraction, and answer generation.

The current codebase is optimized for a workflow where documents already exist in MongoDB with file metadata pointing to files on disk. Once a document is embedded, the API can retrieve relevant chunks across one or more document IDs and generate a section draft from that evidence.

## What It Does

- Checks service health for MongoDB and Weaviate.
- Embeds supported documents into Weaviate in the background.
- Reindexes documents that previously failed.
- Removes indexed chunks for a document from Weaviate.
- Generates report sections using vector search plus LLM completion.
- Uses OpenAI for embeddings, extraction, and generation.

## Architecture

The service is structured around three layers:

- `MongoDB`: stores the `app_documents` records and embedding status.
- `Weaviate`: stores chunk vectors and searchable chunk text.
- `OpenAI`: creates embeddings, extracts content from scanned PDFs and images, and generates final responses.

High-level flow:

1. A document record is loaded from MongoDB.
2. The service reads the file from `file_metadata.full_path`.
3. Text is extracted based on file type.
4. The text is split into overlapping chunks.
5. Chunks are embedded and indexed into Weaviate.
6. A chat request embeds the query, retrieves top matches from Weaviate, and asks the LLM to generate a grounded answer.

## Project Layout

```text
.
├── application.py               # App entrypoint, Flask-Script commands, schema helpers
├── Dockerfile                   # Container image for production-style serving with Gunicorn
├── requirements.txt
└── app
    ├── db
    │   ├── connection.py        # Mongo client
    │   └── models/app_document.py
    └── main
        ├── __init__.py          # Flask app factory
        ├── config.py            # Env-based configuration
        ├── components
        │   ├── openai_client.py
        │   └── weaviate_client.py
        ├── controller           # REST endpoints
        ├── service              # Business logic
        └── util                 # Chunking, RAG, extractors, DTOs, enums
```

## API Surface

### `GET /health`

Checks connectivity to MongoDB and Weaviate.

Example success response:

```json
{
  "status": "healthy",
  "message": "Docu-query service is UP"
}
```

### `POST /documents/<document_id>/embed`

Starts asynchronous extraction, chunking, embedding, and indexing for a document.

Returns `202` when processing starts.

### `POST /documents/<document_id>/reindex`

Retries indexing for a document that is not already indexed and is not currently running.

### `DELETE /documents/<document_id>/unindex`

Deletes all indexed Weaviate chunks for the given document ID.

### `POST /chat`

Generates a grounded section from one or more indexed documents.

Request body:

```json
{
  "title": "Politique environnementale",
  "document_ids": ["DOC123", "DOC456"]
}
```

Example success response:

```json
{
  "content": "..."
}
```

If no relevant context is found, the service returns:

```json
{
  "status": "not_found",
  "content": null
}
```

## Supported File Types

The indexing pipeline is reliably implemented for these formats:

- `pdf`
- `docx`
- `txt`
- `xlsx`
- `pptx`
- `png`
- `jpg`
- `jpeg`
- `webp`

Notes:

- PDFs use native extraction first, then fall back to OpenAI for scanned or image-heavy pages.
- Images are sent to the model for structured visual/text extraction.
- The codebase contains some legacy extension references such as `doc`, `ppt`, and `csv`, but they are not fully wired end-to-end in the current indexing path.

## Document Model Expectations

Embedding assumes a MongoDB document exists in `app_documents` with at least:

- `_id`
- `file_metadata.filename`
- `file_metadata.full_path`
- `file_metadata.file_type`
- `embedding.status`

The service updates `embedding.status` through these states:

- `NOT_STARTED`
- `RUNNING`
- `DONE`
- `ERROR`

On application startup, any documents left in `RUNNING` are reset to `ERROR` so they can be retried.

## Configuration

Environment variables are loaded from the environment or a local `.env` file.

### Core

- `APP_ENV` - `dev` or `prod`
- `MONGO_URI` - MongoDB connection string
- `WEAVIATE_URL` - Weaviate base URL

### OpenAI

- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL` default: `text-embedding-3-small`
- `OPENAI_CHAT_MODEL` default: `gpt-4o`
- `OPENAI_TIMEOUT` default: `60.0`
- `OPENAI_MAX_RETRIES` default: `2`

### Authentication

Requests may be protected by an auth decorator depending on your deployment setup. Refer to the wider platform this service belongs to for token format and auth behavior.

## Local Development

### 1. Create a virtual environment

```bash
python3.8 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Set environment variables

Example:

```bash
export APP_ENV=dev
export MONGO_URI="mongodb://localhost:27017/docuquery"
export WEAVIATE_URL="http://localhost:8080"
export OPENAI_API_KEY="your-key"
export OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
export OPENAI_CHAT_MODEL="gpt-4o"
```

### 4. Start the API locally

```bash
python application.py run
```

This starts the Flask development server on port `5008`.

### 5. Initialize Weaviate schema

```bash
python application.py create_schema
```

To remove it:

```bash
python application.py delete_schema
```

## Running with Docker

Build:

```bash
docker build -t docu-query .
```

Run:

```bash
docker run --rm -p 5000:5000 \
  -e APP_ENV=prod \
  -e MONGO_URI="mongodb://host.docker.internal:27017/docuquery" \
  -e WEAVIATE_URL="http://host.docker.internal:8080" \
  -e OPENAI_API_KEY="your-key" \
  docu-query
```

The container serves the app with Gunicorn on port `5000`.

## Weaviate Schema

`create_schema` creates an `AppDocuments` class with these properties:

- `document_id`
- `chunk_index`
- `text`
- `filename`

Vectors are generated externally and stored with `vectorizer: none`.

## Extraction and RAG Notes

- Chunking uses fixed-size overlapping windows, with a small attempt to break on sentence boundaries.
- Retrieval currently uses the top `6` matching chunks filtered by document IDs.
- Generated report text is instructed to stay grounded in retrieved context only.
- Report output is intentionally plain text and defaults to French unless the retrieved context is clearly in another language.

## Known Limitations

- There is no upload endpoint in this repository; files must already exist on disk and be referenced from MongoDB.
- The project uses a shared `Document` base model defined in `app/db/document.py`.
- The repository currently contains a checked-in `venv/`, which is usually better excluded from source control.
- There are no automated tests in this repository yet.
- Some extension allow-lists and extractor mappings are slightly inconsistent, so unsupported edge cases may surface for `doc`, `ppt`, or `csv`.

## Suggested Next Improvements

- Add a `.env.example` file.
- Add upload and document creation endpoints.
- Add automated tests for extraction, indexing, and chat flows.
- Normalize file type support so allowed extensions and extractors match exactly.
- Add request/response examples for every endpoint in Swagger or the README.
