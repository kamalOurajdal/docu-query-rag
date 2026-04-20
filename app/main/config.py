import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DEBUG = False
    MONGO_URI = os.getenv("MONGO_URI")
    WEAVIATE_URL = os.getenv("WEAVIATE_URL")

    # Standard OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o")

    OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "60.0"))
    OPENAI_MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2"))

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./uploads")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = dict(dev=DevelopmentConfig, prod=ProductionConfig)
