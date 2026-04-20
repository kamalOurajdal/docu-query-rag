from flask_restx import Resource

from app.main.service.document_service import upload_and_embed_document, reindex_document, unindex_document
from app.main.util.dto import DocumentDto

api = DocumentDto.api


@api.route("/embed")
class DocumentEmbedResource(Resource):
    @api.doc("Upload a file, create a document record, and start embedding")
    @api.expect(DocumentDto.upload_parser)
    def post(self):
        args = DocumentDto.upload_parser.parse_args()
        return upload_and_embed_document(file=args["file"])


@api.route("/<document_id>/reindex")
class DocumentReindexResource(Resource):
    @api.doc("Re-attempt indexing for a document that previously failed")
    def post(self, document_id):
        return reindex_document(document_id)


@api.route("/<document_id>/unindex")
class DocumentUnindexResource(Resource):
    @api.doc(
        "Unindex a document",
        responses={
            200: "Document successfully unindexed",
            404: "Document not found",
        },
    )
    def delete(self, document_id):
        return unindex_document(document_id)
