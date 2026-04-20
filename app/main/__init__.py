import inject
from flask import Flask
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo

from app.db.connection import mongo
from app.main.config import config_by_name
from app.main.service.document_service import reset_processing_files

flask_bcrypt = Bcrypt()


def create_app(config_name: str) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    mongo.init_app(app)
    flask_bcrypt.init_app(app)

    def configure_injector(binder):
        binder.bind(PyMongo, mongo)

    inject.configure(configure_injector)

    with app.app_context():
        reset_processing_files()

    return app
