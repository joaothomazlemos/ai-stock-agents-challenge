from __future__ import annotations

from langchain_aws import BedrockEmbeddings


class BedrockEmbedderAdapter:
    """Outbound adapter providing Titan text embeddings via Bedrock.

    Implements IEmbedder protocol.
    """

    def __init__(self, model_id: str, region_name: str) -> None:
        self._embeddings = BedrockEmbeddings(
            model_id=model_id,
            region_name=region_name,
        )

    @property
    def langchain_embeddings(self) -> BedrockEmbeddings:
        """Expose the underlying LangChain embeddings object for FAISS integration."""
        return self._embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embeddings.embed_documents(texts)
