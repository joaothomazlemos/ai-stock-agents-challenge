from __future__ import annotations

from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.vectorstores import VectorStoreRetriever

from ai_stock_agent.domain.entities import DocumentChunk


class FAISSRetrieverAdapter:
    """Outbound adapter loading a pre-built FAISS index and exposing retrieval.

    Implements IDocumentRetriever protocol.
    """

    def __init__(self, index_path: str, embeddings: BedrockEmbeddings) -> None:
        self._vectorstore = FAISS.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True,
        )

    @property
    def vectorstore(self) -> FAISS:
        """Expose the underlying FAISS vectorstore for create_retriever_tool."""
        return self._vectorstore

    def as_retriever(self, k: int = 4) -> VectorStoreRetriever:
        return self._vectorstore.as_retriever(search_kwargs={"k": k})

    def retrieve(self, query: str, k: int = 4) -> list[DocumentChunk]:
        docs = self._vectorstore.similarity_search(query, k=k)
        return [
            DocumentChunk(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                page=doc.metadata.get("page"),
            )
            for doc in docs
        ]
