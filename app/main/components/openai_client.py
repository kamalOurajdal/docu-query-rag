from typing import Any, Dict, List, Optional, Union

from flask import current_app
from openai import OpenAI


class OpenAIClient:
    _instance: Optional['OpenAIClient'] = None
    _client: Optional[OpenAI] = None
    _embedding_model: Optional[str] = None
    _chat_model: Optional[str] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpenAIClient, cls).__new__(cls)
        return cls._instance

    @classmethod
    def _resolve_chat_model(cls, openai_model: Optional[str]) -> str:
        model_name = openai_model or current_app.config.get("OPENAI_CHAT_MODEL")
        if not model_name:
            raise ValueError(
                "No model name was provided (openai_model) and OPENAI_CHAT_MODEL "
                "is missing in config."
            )
        return model_name

    @classmethod
    def get_client(cls) -> OpenAI:
        if cls._client is not None:
            return cls._client

        cfg = current_app.config
        timeout_setting = cfg.get("OPENAI_TIMEOUT", 60.0)
        max_retries_setting = cfg.get("OPENAI_MAX_RETRIES", 2)

        api_key = cfg.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in Flask configuration")

        cls._client = OpenAI(
            api_key=api_key,
            timeout=timeout_setting,
            max_retries=max_retries_setting,
        )
        return cls._client

    @classmethod
    def get_embedding_model(cls) -> str:
        if cls._embedding_model is not None:
            return cls._embedding_model

        model = current_app.config.get("OPENAI_EMBEDDING_MODEL")
        if not model:
            raise ValueError(
                "OPENAI_EMBEDDING_MODEL not found in Flask configuration"
            )

        cls._embedding_model = model
        return cls._embedding_model

    @classmethod
    def get_chat_model(cls) -> str:
        if cls._chat_model is not None:
            return cls._chat_model

        model = current_app.config.get("OPENAI_CHAT_MODEL")
        if not model:
            raise ValueError(
                "OPENAI_CHAT_MODEL not found in Flask configuration"
            )

        cls._chat_model = model
        return cls._chat_model

    @classmethod
    def chat_completion(
        cls,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = 600,
        temperature: float = 0.3,
        openai_model: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        client = cls.get_client()
        model_name = cls._resolve_chat_model(openai_model=openai_model)

        params = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            **kwargs,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        response = client.chat.completions.create(**params)
        return response.choices[0].message.content

    @classmethod
    def create_response(
        cls,
        input_data: Union[str, List[Dict[str, Any]]],
        *,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        openai_model: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        client = cls.get_client()
        model_name = cls._resolve_chat_model(openai_model=openai_model)

        params: Dict[str, Any] = {
            "model": model_name,
            "input": input_data,
            **kwargs,
        }

        if max_output_tokens is not None:
            params["max_output_tokens"] = max_output_tokens

        if temperature is not None:
            params["temperature"] = temperature

        return client.responses.create(**params)

    @classmethod
    def embed_texts(cls, texts: List[str]) -> List[List[float]]:
        client = cls.get_client()
        model_name = cls.get_embedding_model()

        try:
            response = client.embeddings.create(
                input=texts,
                model=model_name,
            )
        except Exception as e:
            raise RuntimeError(
                f"Embedding creation failed with model '{model_name}': {e}"
            ) from e

        return [item.embedding for item in response.data]
