from flask_restx import Resource
from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError

from app.db.connection import mongo
from app.main.components.weaviate_client import WeaviateClient
from app.main.util.dto import HealthCheckDTO

api = HealthCheckDTO.api


@api.route("")
class HealthCheck(Resource):
    @api.doc("Health Check")
    @api.marshal_with(HealthCheckDTO.healthcheck)
    def get(self):
        """Check connectivity to MongoDB and Weaviate."""
        errors = []

        try:
            mongo.db.command("ping")
        except (AutoReconnect, ServerSelectionTimeoutError):
            errors.append("MongoDB connection failed")

        try:
            WeaviateClient.ping()
        except Exception:
            errors.append("Weaviate connection failed")

        if errors:
            return {"status": "unhealthy", "message": "; ".join(errors)}, 500

        return {"status": "healthy", "message": "Docu-query service is UP"}, 200
