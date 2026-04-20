import os

from flask_script import Manager
from loguru import logger

from app.main import create_app
from app.main.components.weaviate_client import WeaviateClient
from app.main.controller import blueprint
from app.main.util.enums.weaviate_enums import WeaviateClassEnum


app = create_app(os.getenv("APP_ENV") or "prod")
app.register_blueprint(blueprint)
app.app_context().push()

manager = Manager(app)


def before_request():
    """
    This function is intentionally empty because all necessary logic
    for token blacklisting checks is handled
    within the `decode_jwt` decorator.
    """
    pass


@manager.command
def create_schema():
    properties = [
        {
            "name": "document_id",
            "dataType": ["text"],
            "description": "Document identifier (custom 32-char uppercase hex)",
        },
        {
            "name": "chunk_index",
            "dataType": ["number"],
            "description": "Order of the chunk within the document",
        },
        {
            "name": "text",
            "dataType": ["text"],
            "description": "Chunk content",
        },
        {
            "name": "filename",
            "dataType": ["text"],
            "description": "Original filename",
        },
    ]
    try:
        WeaviateClient.create_schema(WeaviateClassEnum.APP_DOCUMENTS.value, properties)
        logger.info("Schema created successfully")
    except Exception as e:
        logger.error(f"Error creating schema: {e}")
        return {"status": "error", "message": "An error occurred while creating the schema."}, 500


@manager.command
def delete_schema():
    try:
        WeaviateClient.delete_schema(WeaviateClassEnum.APP_DOCUMENTS.value)
        logger.info("Schema deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting schema: {e}")
        return {"status": "error", "message": "An error occurred while deleting the schema."}, 500


@manager.command
def run():
    app.run(port=5008)


if __name__ == "__main__":
    manager.run()
