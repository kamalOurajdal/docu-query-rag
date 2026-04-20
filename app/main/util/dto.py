
from flask_restx import Namespace, fields
from werkzeug.datastructures import FileStorage


class ChatDTO:
    api = Namespace("Chat", description="Document query and answer generation operations")
    chat_request = api.model("ChatRequest", {
        "title": fields.String(required=True, description="Query or topic to generate content for"),
        "document_ids": fields.List(fields.String, required=True, description="Document IDs to retrieve context from")
    })


class HealthCheckDTO:
    api = Namespace("Health Check", description="Health Check operations")
    healthcheck = api.model("Health Check", {
        "status": fields.String,
        "message": fields.String
    })


class DocumentDto:
    api = Namespace("Documents", description="Document ingestion and indexing operations")

    upload_parser = api.parser()
    upload_parser.add_argument(
        "file", location="files", type=FileStorage, required=True, help="File to upload and embed"
    )
    upload_parser.add_argument(
        "name", location="form", type=str, required=False, help="Document name (defaults to filename)"
    )