from __future__ import annotations

from langchain_aws import ChatBedrock
from langchain_core.language_models import BaseChatModel


class BedrockLLMProvider:
    """Outbound adapter providing a ChatBedrock LLM instance.

    Implements ILLMProvider protocol.
    """

    def __init__(self, model_id: str, region_name: str) -> None:
        self._model = ChatBedrock(
            model_id=model_id,
            region_name=region_name,
            streaming=True,
            model_kwargs={"temperature": 0.0, "max_tokens": 4096},
        )

    def get_chat_model(self) -> BaseChatModel:
        return self._model
