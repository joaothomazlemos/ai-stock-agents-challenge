from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AWS
    aws_region: str = Field(
        default="us-east-1", description="AWS region for Bedrock and AgentCore"
    )

    # Bedrock LLM
    bedrock_model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-20250514-v1:0",
        description="Bedrock model ID or inference profile ID for the chat LLM",
    )

    # Bedrock Embeddings
    embedding_model_id: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Bedrock model ID for text embeddings",
    )
    embedding_dims: int = Field(default=512, ge=1, description="Embedding vector dimensions")

    # AgentCore Memory (empty = use in-memory MemorySaver for local dev)
    agentcore_memory_id: str = Field(
        default="",
        description="AgentCore Memory resource ARN. Empty uses in-memory checkpointer.",
    )

    # Langfuse (empty = tracing disabled)
    langfuse_public_key: str = Field(default="", description="Langfuse public API key")
    langfuse_secret_key: str = Field(default="", description="Langfuse secret API key")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse Cloud base URL"
    )

    # FAISS / RAG
    faiss_index_path: str = Field(
        default="data/faiss_index", description="Path to pre-built FAISS index directory"
    )
    chunk_size: int = Field(
        default=1500, ge=200, le=10000, description="Character size per document chunk"
    )
    chunk_overlap: int = Field(
        default=300, ge=0, le=5000, description="Overlap between consecutive chunks"
    )
    retriever_k: int = Field(
        default=5, ge=1, le=20, description="Number of chunks to retrieve per query"
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8080, ge=1, le=65535, description="Server bind port")

    # Agent
    agent_actor_id: str = Field(
        default="ai-stock-agent", description="Actor ID for AgentCoreMemorySaver"
    )
