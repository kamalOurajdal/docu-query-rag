# DocuQuery

DocuQuery is a Flask-based document indexing and question-answering API. It accepts uploaded files, stores them on disk, extracts their content, chunks and embeds that content with OpenAI, indexes the vectors in Weaviate, and generates grounded answers from selected documents.

The current implementation is centered on a simple flow:

1. Upload a document through the API.
2. Save it under `UPLOAD_FOLDER`.
3. Create an `app_documents` record in MongoDB.
4. Extract and embed the document in a background thread.
5. Query one or more indexed document IDs through the chat endpoint.

## What It Does

- Uploads and stores supported files locally.
- Creates a MongoDB document record for each uploaded file.
- Extracts text from PDFs, Office files, text files, and images.
- Embeds extracted chunks with OpenAI.
- Stores vectors and chunk text in Weaviate.
- Generates grounded plain-text answers from retrieved chunks.
- Exposes health, document, and chat endpoints through Flask-RESTX.

## Architecture

The service uses four main pieces:

- `Flask`: HTTP API, app bootstrapping, and background task kickoff.
- `MongoDB`: stores document metadata and embedding status in `app_documents`.
- `Weaviate`: stores embedded chunks for retrieval.
- `OpenAI`: handles embeddings, scanned/image extraction, and answer generation.

High-level request flow:

1. `POST /documents/embed` receives a multipart upload.
2. The file is saved to `UPLOAD_FOLDER` with a generated ID prefix.
3. A MongoDB document is inserted with fields like `_id`, `name`, `path`, `size`, and `embedding`.
4. A background thread extracts text, chunks it, embeds it, and writes batches to Weaviate.
5. `POST /chat` embeds the query, retrieves the top matching chunks for the requested document IDs, and asks OpenAI to answer strictly from that context.

## Project Layout

```text
.
├── application.py
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── run.sh
├── setup-local-dev.sh
├── uploads/
└── app
    ├── db
    │   ├── connection.py
    │   ├── document.py
    │   └── models/app_document.py
    └── main
        ├── __init__.py
        ├── config.py
        ├── components
        │   ├── openai_client.py
        │   └── weaviate_client.py
        ├── controller
        ├── service
        └── util
```

Key files:

- [application.py](/home/kamal/Workspace/personal/projects/docu-query/application.py): app entrypoint plus `run`, `create_schema`, and `delete_schema` commands.
- [app/main/controller/document_controller.py](/home/kamal/Workspace/personal/projects/docu-query/app/main/controller/document_controller.py): upload, reindex, and unindex routes.
- [app/main/service/document_service.py](/home/kamal/Workspace/personal/projects/docu-query/app/main/service/document_service.py): upload persistence and embedding orchestration.
- [app/main/util/indexing.py](/home/kamal/Workspace/personal/projects/docu-query/app/main/util/indexing.py): background extraction, chunking, embedding, and indexing.
- [app/db/document.py](/home/kamal/Workspace/personal/projects/docu-query/app/db/document.py): lightweight base model for Mongo-backed documents.

## API

### `GET /health`

Checks connectivity to MongoDB and Weaviate.

Example response:

```json
{
  "status": "healthy",
  "message": "Docu-query service is UP"
}
```

### `POST /documents/embed`

Uploads a file, creates a document record, and starts background embedding.

Request type:

- `multipart/form-data`

Fields:

- `file` required: uploaded document
- `name` optional: display name stored in MongoDB, defaults to the filename

Example response when processing starts:

```json
{
  "status": "RUNNING",
  "message": "Embedding process started successfully.",
  "document_id": "66C3AF974BA54025856AD8D3EDE886CC"
}
```

### `POST /documents/<document_id>/reindex`

Retries indexing for an existing document if it is not already indexed and not already running.

### `DELETE /documents/<document_id>/unindex`

Deletes indexed chunks for a document from Weaviate.

### `POST /chat`

Generates an answer based on one or more indexed documents.

Request body:

```json
{
  "title": "What does the document say about planning and scheduling?",
  "document_ids": ["66C3AF974BA54025856AD8D3EDE886CC"]
}
```

Success response:

```json
{
  "content": "..."
}
```

No-context response:

```json
{
  "status": "not_found",
  "content": null
}
```

## Supported File Types

The current indexing allow-list in code is:

- `pdf`
- `docx`
- `txt`
- `doc`
- `xlsx`
- `ppt`
- `pptx`
- `png`
- `jpg`
- `jpeg`
- `webp`

Extraction is fully wired for:

- `pdf`
- `docx`
- `txt`
- `csv`
- `xlsx`
- `pptx`
- `png`
- `jpg`
- `jpeg`
- `webp`

Notes:

- PDFs use native text extraction first and fall back to OpenAI for scanned or image-heavy pages.
- Images are processed with OpenAI Vision-style prompting.
- There is still a mismatch between the allow-list and extractor dispatcher, so legacy extensions like `doc` and `ppt` are allowed by validation but do not have matching extractor handlers yet.

## Data Model

The service stores document records in the `app_documents` collection. A document created by the upload flow currently includes fields such as:

- `_id`
- `name`
- `path`
- `size`
- `embedding.status`
- `created_on`

Embedding status values:

- `NOT_STARTED`
- `RUNNING`
- `DONE`
- `ERROR`

On startup, the app resets any documents left in `RUNNING` to `ERROR` so they can be retried.

## Configuration

Environment variables are loaded from the shell or `.env`.

Core variables:

- `APP_ENV` - `dev` or `prod`
- `MONGO_URI` - MongoDB connection string
- `WEAVIATE_URL` - Weaviate base URL
- `UPLOAD_FOLDER` - local storage directory for uploaded files, default `./uploads`

OpenAI variables:

- `OPENAI_API_KEY`
- `OPENAI_EMBEDDING_MODEL` default: `text-embedding-3-small`
- `OPENAI_CHAT_MODEL` default: `gpt-4o`
- `OPENAI_TIMEOUT` default: `60.0`
- `OPENAI_MAX_RETRIES` default: `2`

## Local Development

### Manual setup

```bash
python3.8 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python application.py run
```

The Flask development server runs on port `5008`.

### Helper script

You can also use the local setup helper:

```bash
./setup-local-dev.sh docu-query
```

And the shared runner script from the parent workspace convention:

```bash
./run.sh docu-query
```

## Docker

Build the image:

```bash
docker build -t dq-query:latest .
```

Run the container:

```bash
docker run --rm -p 5000:5000 \
  --env-file .env \
  -v "$(pwd)/uploads:/usr/src/app/uploads" \
  dq-query:latest
```

The container serves the app with Gunicorn on port `5000`.

## Docker Compose

The repository includes [docker-compose.yaml](/home/kamal/Workspace/personal/projects/docu-query/docker-compose.yaml) for MongoDB, Weaviate, and the API container.

Important notes about the current compose file:

- It expects an image named `dq-query:latest` to already exist.
- It uses `.env` for app configuration.
- It mounts a named volume for document data.
- The checked-in `.env` currently points to local host-style service URLs, so you may need to adjust it depending on whether you run the app directly or through Compose.

Typical flow:

```bash
docker build -t dq-query:latest .
docker compose up
```

## Schema Management

Create the Weaviate schema:

```bash
python application.py create_schema
```

Delete the Weaviate schema:

```bash
python application.py delete_schema
```

The `AppDocuments` class contains:

- `document_id`
- `chunk_index`
- `text`
- `filename`

Vectors are supplied externally and stored with `vectorizer: none`.

## Retrieval and Generation Behavior

- Text is chunked into overlapping windows before embedding.
- Chunk batches are embedded in groups of `20`.
- Retrieval uses the top `6` chunks filtered by the provided document IDs.
- Answers are instructed to be evidence-only, plain text, and language-matched to the retrieved context.
- If retrieval produces no usable context, the model is instructed to return exactly `NOT_FOUND`.

## Current Limitations

- `doc` and `ppt` are allowed by upload validation but are not actually handled by the extractor dispatcher.
- `csv` has an extractor but is not in the current upload allow-list.
- The checked-in `uploads/` directory currently contains sample uploaded files and is still untracked in Git status.
- `docker-compose.yaml` relies on a prebuilt app image instead of building it directly.
- There is no automated test suite in the repository yet.