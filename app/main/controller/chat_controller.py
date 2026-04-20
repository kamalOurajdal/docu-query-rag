from flask import request
from flask_restx import Resource

from app.main.service.chat_service import generate_section
from app.main.util.dto import ChatDTO

api = ChatDTO.api


@api.route("")
class GenerateSection(Resource):
    @api.doc("Generate an answer for a given query title")
    @api.expect(ChatDTO.chat_request, validate=True)
    def post(self):
        return generate_section(request.json)
