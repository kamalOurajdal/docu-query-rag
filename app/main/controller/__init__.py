from flask import Blueprint
from flask_restx import Api

from app.main.controller.chat_controller import api as chat_ns
from app.main.controller.document_controller import api as document_ns
from app.main.controller.health_controller import api as health_ns

blueprint = Blueprint("docu_query", __name__)

api = Api(
    blueprint,
    title="Docu-query API",
    version="1.0",
    description="REST API for document management, chat interactions, and health monitoring.",
)

api.add_namespace(health_ns, path="/health")
api.add_namespace(chat_ns, path="/chat")
api.add_namespace(document_ns, path="/documents")
