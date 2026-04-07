# Spec: AI Stock Agent on AWS Bedrock AgentCore

| Field | Value |
| --- | --- |
| **Status** | Draft |
| **Author** | Joao Thomaz Lemos |
| **Date** | 2026-04-07 |
| **PRD** | `docs/PRD-ai-stock-agent.md` |

---

## 1. Overview

Build a greenfield LangGraph ReAct agent deployed on AWS Bedrock AgentCore that answers real-time and historical stock price queries via SSE streaming. The agent exposes two yfinance tools and a FAISS-backed RAG tool over Amazon financial documents. Authentication flows through Cognito JWT via the AgentCore Gateway, observability through Langfuse Cloud callbacks, and conversation state persists via `AgentCoreMemorySaver`. All infrastructure is provisioned with Terraform. The deliverable is a running AgentCore endpoint plus a Jupyter notebook demonstrating 5 specific queries.

---

## 2. PRD Traceability

| PRD Requirement (Section / Item) | Spec Section | Notes |
| --- | --- | --- |
| P0-1: LangGraph ReAct agent with `.astream()` | 6.1, 6.3 (Graph), 7 Phase 3 | `StateGraph(MessagesState)` with `agent → tools_condition → tools → agent` loop |
| P0-2: `retrieve_realtime_stock_price` tool | 6.3 (Tools), 7 Phase 3 | yfinance `Ticker.info` for current price |
| P0-3: `retrieve_historical_stock_price` tool | 6.3 (Tools), 7 Phase 3 | yfinance `Ticker.history()` for date range |
| P0-4: RAG knowledge base with 3 Amazon PDFs | 6.3 (Tools), 7 Phase 4 | FAISS + Titan 512d embeddings, pre-built index |
| P0-5: SSE streaming responses | 6.3 (API), 7 Phase 5 | `text/event-stream` with `stream_mode="messages"` |
| P0-6: Cognito authentication | 6.2, 7 Phase 7 | User pool + app client; `CUSTOM_JWT` on Gateway |
| P0-7: FastAPI `/invocations` + `/ping` | 6.3 (API), 7 Phase 5 | Port 8080, AgentCore HTTP protocol contract |
| P0-8: `AgentCoreMemorySaver` for conversation state | 6.2, 6.3 (Graph), 7 Phase 3 | `langgraph-checkpoint-aws`, `actor_id` + `thread_id` |
| P0-9: Terraform infrastructure | 7 Phase 7 | `aws-ia/agentcore/aws` module + raw resources |
| P0-10: Jupyter notebook with 5 queries | 7 Phase 9 | Cognito auth → SSE invocations → trace display |
| P0-11: Langfuse observability | 6.2, 7 Phase 5 | `CallbackHandler` in `.astream()` config |
| P0-12: Docker ARM64 container | 7 Phase 8 | Multi-stage build, FAISS index bundled |
| P1-1: Langfuse trace screenshots in notebook | 7 Phase 9 | Screenshots in `notebooks/images/` |
| P1-2: Parameterized LLM model ID | 6.3 (Config), 7 Phase 1 | `BEDROCK_MODEL_ID` env var |
| P1-3: Parameterized embedding model + dims | 6.3 (Config), 7 Phase 1 | `EMBEDDING_MODEL_ID` + `EMBEDDING_DIMS` env vars |
| P1-4: FAISS index pre-build script | 7 Phase 4 | `scripts/build_index.py` |
| P1-5: Clear README | 7 Phase 9 | Step-by-step deployment instructions |
| P1-6: E2E acceptance tests | 7 Phase 6 | 5 UAC queries against live server |
| P1-7: LLM evaluation tests | 7 Phase 6 | LLM-as-judge with `@pytest.mark.llm` |
| P1-8: Integration tests for tools and retriever | 7 Phase 6 | yfinance + FAISS retrieval tests |
| P1-9: Notebook targets deployed endpoint | 7 Phase 9 | `BASE_URL` from Terraform output |
| P2-1: Makefile | 7 Phase 1 | Full workflow: install, dev, lint, test, build, push, apply |
| P2-2: Pre-commit hooks | Already exists | `.pre-commit-config.yaml` with Ruff + Terraform + gitleaks |

---

## 3. Background & Research

### Current State

The repository is greenfield documentation: PRD, assignment, architecture diagram (`.drawio`), cursor/claude rules and skills, and pre-commit configuration. There is no `src/`, `tests/`, `terraform/`, `pyproject.toml`, `Makefile`, or `Dockerfile`. Python version is pinned at `3.14.3` in `.python-version`. The `.gitignore` already covers Python, Terraform, `.env`, and PDF patterns.

### AgentCore HTTP Protocol

The container must implement two endpoints on `0.0.0.0:8080` (ARM64):

- **`POST /invocations`** — JSON request in, JSON or SSE (`text/event-stream`) response out. The container speaks SSE directly; AgentCore does not add framing.
- **`GET /ping`** — Returns JSON `{"status": "Healthy"}` with HTTP 200. Used for liveness/readiness.

### AgentCore Gateway + Cognito JWT

The Gateway validates JWTs using `CUSTOM_JWT` authorizer type with the Cognito user pool's OIDC discovery URL. Clients call with `Authorization: Bearer <jwt>`. At least one of `allowedAudiences`, `allowedClients`, `allowedScopes`, or `requiredCustomClaims` must be set.

### AgentCoreMemorySaver

Package `langgraph-checkpoint-aws`. Constructor takes `memory_id` (AgentCore Memory resource ARN) + `region_name`. At invoke time, `thread_id` and `actor_id` are passed via `configurable` in `RunnableConfig`. IAM requires `bedrock-agentcore:CreateEvent`, `ListEvents`, `RetrieveMemories`.

### LangGraph ReAct Pattern

Standard shape: `agent` node (LLM with bound tools) → `tools_condition` conditional edge → `tools` node (`ToolNode`) → loop back to `agent`. Streaming uses `graph.astream(..., stream_mode="messages", version="v2")` which yields `(message_chunk, metadata)` tuples for token-by-token output. The node should be `async def` and use `.ainvoke()` on the LLM (not `.invoke()`, which would block the event loop). Notably, you do **not** need `.astream()` on the LLM itself inside the node — LangGraph intercepts the callback system and emits token-by-token chunks even when the LLM is called with `.ainvoke()`.

### FAISS + LangChain

`FAISS.from_documents()` builds the index; `save_local()` / `load_local(..., allow_dangerous_deserialization=True)` for persistence. Wrap as retriever tool via `create_retriever_tool(vectorstore.as_retriever(), ...)`. Embeddings via `BedrockEmbeddings` from `langchain_aws` with Titan model.

### Langfuse Integration

`langfuse.langchain.CallbackHandler()` passed via `config={"callbacks": [handler]}` on `.astream()`. Traces all LLM calls, tool invocations, and graph transitions. Requires `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` env vars.

---

## 4. Goals

1. **Working ReAct agent** — LangGraph `StateGraph(MessagesState)` with tool loop, compiled with `AgentCoreMemorySaver`, streaming via `.astream()` (PRD Goals #1, #4)
2. **Three functional tools** — `retrieve_realtime_stock_price`, `retrieve_historical_stock_price`, and `retrieve_documents` backed by yfinance and FAISS (PRD Goals #3, #4)
3. **Correct SSE streaming** — Token-by-token via `text/event-stream` on `/invocations`, meeting AgentCore HTTP protocol contract (PRD Goal #1)
4. **Authenticated access** — Cognito user pool with JWT validation via AgentCore Gateway `CUSTOM_JWT` authorizer (PRD Goal #2)
5. **Full observability** — Every invocation traced in Langfuse Cloud with tool calls, LLM responses, and timing (PRD Goal #5)
6. **One-command infrastructure** — `terraform apply` provisions AgentCore Runtime, Endpoint, Gateway, Cognito, Memory, ECR, and IAM (PRD Goal #6)
7. **Demonstrable notebook** — 5 UAC queries answered with Cognito auth, SSE streaming, and Langfuse traces (PRD Goal #7)

---

## 5. Non-Goals (Out of Scope)

- Frontend / web UI — notebook is the only client
- Multi-tenancy or user management beyond a single Cognito test user
- Bedrock Knowledge Base managed service — using FAISS in-container instead
- WebSocket `/ws` endpoint — SSE is sufficient per assignment
- Long-term memory extraction — only session memory via `AgentCoreMemorySaver`
- CI/CD pipeline (P2-3) — document in README but don't implement
- Agent system prompt fine-tuning (P2-4) — functional prompt is sufficient

---

## 6. Technical Design

### 6.1 Architecture

```text
+--------------------------------------------------------------------------+
|                               AWS Cloud                                   |
|                                                                           |
|  +------------------+    +------------------------+    +----------------+ |
|  | Cognito          |<---| AgentCore Gateway      |    | Terraform      | |
|  | User Pool + JWT  |    | CUSTOM_JWT authorizer  |    | (provisions    | |
|  +------------------+    +------------------------+    |  everything)   | |
|                                   |                    +----------------+ |
|                            Proxy to Runtime                               |
|                                   v                                       |
|  +----------------------------------------------------------------+      |
|  |            AgentCore Runtime (ARM64 container)                  |      |
|  |                                                                 |      |
|  |  +-----------------------------------------------------------+ |      |
|  |  | FastAPI (port 8080)                                        | |      |
|  |  | POST /invocations  -> InvokeAgentUseCase -> graph.astream  | |      |
|  |  | GET  /ping         -> {"status": "Healthy"}                | |      |
|  |  +-----------------------------------------------------------+ |      |
|  |                          |                                      |      |
|  |                    .astream(stream_mode="messages")             |      |
|  |                          v                                      |      |
|  |  +-----------------------------------------------------------+ |      |
|  |  | LangGraph StateGraph(MessagesState)                        | |      |
|  |  |                                                            | |      |
|  |  |  START -> agent (ChatBedrock + bound tools)                | |      |
|  |  |            |                                               | |      |
|  |  |            v                                               | |      |
|  |  |      tools_condition                                       | |      |
|  |  |       /          \                                         | |      |
|  |  |    tools          END                                      | |      |
|  |  |   (ToolNode)                                               | |      |
|  |  |      |                                                     | |      |
|  |  |      +---> agent (loop)                                    | |      |
|  |  +-----------------------------------------------------------+ |      |
|  |       |              |              |              |             |      |
|  |       v              v              v              v             |      |
|  |  +---------+  +-----------+  +----------+  +---------------+   |      |
|  |  | yfinance|  | yfinance  |  | FAISS    |  | AgentCore     |   |      |
|  |  | realtime|  | historical|  | RAG tool |  | MemorySaver   |   |      |
|  |  +---------+  +-----------+  +----------+  +---------------+   |      |
|  |                                    |              |             |      |
|  |                           Pre-built index    Memory resource   |      |
|  |                           Titan 512d emb     (checkpointer)   |      |
|  +----------------------------------------------------------------+      |
|                          |                                                |
|                    Callbacks                                              |
|                          v                                                |
|                 +-------------------+                                      |
|                 | Langfuse Cloud    |                                      |
|                 +-------------------+                                      |
+--------------------------------------------------------------------------+

Client: Jupyter Notebook
  1. boto3 InitiateAuth -> Cognito JWT
  2. POST /invocations via Gateway with Bearer JWT
  3. Receive SSE stream
```

### 6.2 Key Decisions

| Decision | Choice | Rationale |
| --- | --- | --- |
| Agent framework | LangGraph `StateGraph(MessagesState)` | Assignment requirement; provides `tools_condition`, `ToolNode`, `.astream()` |
| LLM provider | `ChatBedrock` from `langchain-aws` | Direct Bedrock integration; avoids Converse API streaming issues (langchain-aws#763) |
| Embedding model | Titan Embeddings V2 (`amazon.titan-embed-text-v2:0`) at 512 dims | Assignment suggests Titan; 512d balances quality vs index size |
| Vector store | FAISS (in-memory, pre-built) | No managed infra needed; index bundled in container image; sub-second load |
| RAG tool creation | `create_retriever_tool()` from LangChain | Standard pattern for exposing retriever as LangGraph tool |
| Checkpointer | `AgentCoreMemorySaver` from `langgraph-checkpoint-aws` | Assignment requirement; persistent across container restarts; no external DB |
| SSE streaming | `stream_mode="messages"` with `version="v2"` | Token-by-token chunks; `version="v2"` gives unified `StreamPart` shape |
| API framework | Pure FastAPI (not `BedrockAgentCoreApp`) | Assignment says "Agentcore runtime hosted via FastAPI"; no SDK dependency |
| Auth | Cognito User Pool + AgentCore Gateway `CUSTOM_JWT` | Assignment requirement; Gateway handles JWT validation natively |
| IaC | Terraform with `aws-ia/agentcore/aws` module | Assignment requirement; module abstracts AgentCore resource creation |
| Observability | Langfuse Cloud `CallbackHandler` in `.astream()` config | Assignment requirement; captures full trace tree |
| Container platform | ARM64 (Graviton) | AgentCore Runtime requirement |
| Python version | 3.12 (local + container) | AgentCore SDK requires 3.12+; `.python-version` pinned to 3.12 |
| Package manager | UV | Already established in CLAUDE.md conventions |
| Tool wiring | App-level factory in `app.py` lifespan | Hex arch: tools created with adapter refs in composition root, passed to graph builder |
| SSE event shape | Typed JSON: `data: {"type": "token", "content": "..."}` | Explicit framing; easy to parse in notebook; `type: "end"` signals completion |
| Local dev memory | Conditional: `MemorySaver` if no `AGENTCORE_MEMORY_ID`, else `AgentCoreMemorySaver` | Best local DX; no AWS credentials needed for dev iteration |

### 6.3 API / Interface Changes

#### FastAPI Endpoints

```python
# POST /invocations — Agent interaction
class InvocationRequest(BaseModel):
    """Request body for agent invocation via POST /invocations."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, description="The user query to send to the agent")
    thread_id: str | None = Field(
        default=None,
        description="Conversation thread ID for multi-turn. Auto-generated if omitted.",
    )
    stream: bool = Field(
        default=True,
        description="If true, response is SSE text/event-stream. If false, full JSON.",
    )

# SSE response (stream=True):
# Content-Type: text/event-stream
# data: {"type": "token", "content": "The"}
# data: {"type": "token", "content": " current"}
# ...
# data: {"type": "end"}

# JSON response (stream=False):
class InvocationResponse(BaseModel):
    """JSON response returned when stream=false."""

    response: str = Field(description="The agent's full response text")
    thread_id: str = Field(description="The conversation thread ID used for this invocation")

# GET /ping — Health check
class PingResponse(BaseModel):
    """Health check response for GET /ping."""

    status: Literal["Healthy"] = Field(
        default="Healthy", description="Runtime health status"
    )
```

**Error responses** — precise HTTP status codes per failure mode:

| Status | When | Example |
| --- | --- | --- |
| `422 Unprocessable Entity` | Pydantic validation fails | Missing `prompt`, empty string |
| `500 Internal Server Error` | LLM invocation fails | Bedrock throttling, model error |
| `502 Bad Gateway` | Upstream service unreachable | Bedrock endpoint down, yfinance timeout |
| `503 Service Unavailable` | Agent not initialized | FAISS index not loaded, graph not compiled |

#### Domain Ports

```python
# ports/inbound.py — Use case interface
class AgentPort(Protocol):
    async def invoke(
        self, prompt: str, thread_id: str, stream: bool
    ) -> str | AsyncIterator[str]: ...

# ports/outbound/llm.py
class ILLMProvider(Protocol):
    def get_chat_model(self) -> BaseChatModel: ...

# ports/outbound/stock.py
class IStockProvider(Protocol):
    def get_realtime_price(self, ticker: str) -> StockPrice: ...
    def get_historical_prices(
        self, ticker: str, start: str, end: str
    ) -> list[StockPrice]: ...

# ports/outbound/retriever.py
class IDocumentRetriever(Protocol):
    def retrieve(self, query: str, k: int = 4) -> list[DocumentChunk]: ...

# ports/outbound/embedder.py
class IEmbedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
```

#### Domain Entities

```python
# domain/entities.py
@dataclass(frozen=True)
class StockPrice:
    ticker: str
    price: float
    currency: str
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class DocumentChunk:
    content: str
    source: str
    page: int | None = None
    score: float | None = None
```

#### LangGraph Tools

```python
# infrastructure/tools.py — Tool definitions for the ReAct graph

@tool
def retrieve_realtime_stock_price(ticker: str) -> str:
    """Get the current real-time stock price for a given ticker symbol."""
    ...

@tool
def retrieve_historical_stock_price(
    ticker: str, start_date: str, end_date: str
) -> str:
    """Get historical stock prices for a ticker within a date range."""
    ...

# RAG tool via create_retriever_tool()
retrieve_documents = create_retriever_tool(
    retriever,
    "retrieve_documents",
    "Search Amazon financial documents including annual reports and earnings releases.",
)
```

#### LangGraph Graph

```python
# infrastructure/graph.py

def build_agent_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    tool_node = ToolNode(tools)
    llm_with_tools = llm.bind_tools(tools)

    async def agent(state: MessagesState) -> dict:
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: MessagesState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=checkpointer)
```

#### Configuration

```python
# infrastructure/config.py

class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # AWS
    aws_region: str = Field(default="us-east-1", description="AWS region for Bedrock and AgentCore")

    # Bedrock LLM
    bedrock_model_id: str = Field(
        default="anthropic.claude-sonnet-4-20250514",
        description="Bedrock model ID for the chat LLM",
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
```

### 6.4 Data Model Changes

No database tables. All persistence is handled by:

- **`AgentCoreMemorySaver`** — Managed by AgentCore Memory service (AWS-managed, no schema)
- **FAISS index** — Pre-built binary file, read-only at runtime

---

## 7. Implementation Plan

### Phase 1: Project Scaffolding

**Goal:** Buildable project with dependency resolution, linting, and dev tooling.

Tasks:

- [ ] Create `pyproject.toml` with UV metadata, Python >=3.12, core deps: `langgraph`, `langchain-aws`, `langchain-community`, `langgraph-checkpoint-aws`, `faiss-cpu`, `yfinance`, `fastapi`, `uvicorn[standard]`, `langfuse`, `pydantic-settings`, `pypdf` (file: `pyproject.toml`)
- [ ] Create `Makefile` with targets: `install`, `dev-api`, `lint`, `format`, `test`, `build-index`, `build`, `push`, `apply` (file: `Makefile`)
- [ ] Create hexagonal directory structure with `__init__.py` files under `src/ai_stock_agent/` (file: `src/ai_stock_agent/`)
- [ ] Create `infrastructure/config.py` with `Settings` class — all env vars parameterized with defaults (file: `src/ai_stock_agent/infrastructure/config.py`)
- [ ] Create `.env.example` documenting all environment variables (file: `.env.example`)
- [ ] Run `uv sync` to verify dependency resolution

**Depends on:** None

**Verify:**

```text
uv sync && make lint
```

### Phase 2: Domain Layer

**Goal:** Pure Python domain — entities, port interfaces, use case contract. Zero framework dependencies.

Tasks:

- [ ] Create `domain/entities.py` with `StockPrice` and `DocumentChunk` frozen dataclasses (file: `src/ai_stock_agent/domain/entities.py`)
- [ ] Create `domain/ports/inbound.py` with `AgentPort` protocol (file: `src/ai_stock_agent/domain/ports/inbound.py`)
- [ ] Create `domain/ports/outbound/llm.py` with `ILLMProvider` protocol (file: `src/ai_stock_agent/domain/ports/outbound/llm.py`)
- [ ] Create `domain/ports/outbound/stock.py` with `IStockProvider` protocol (file: `src/ai_stock_agent/domain/ports/outbound/stock.py`)
- [ ] Create `domain/ports/outbound/retriever.py` with `IDocumentRetriever` protocol (file: `src/ai_stock_agent/domain/ports/outbound/retriever.py`)
- [ ] Create `domain/ports/outbound/embedder.py` with `IEmbedder` protocol (file: `src/ai_stock_agent/domain/ports/outbound/embedder.py`)
- [ ] Create `domain/use_cases/invoke_agent.py` with `InvokeAgentUseCase` implementing `AgentPort` — orchestrates graph invocation and SSE token iteration (file: `src/ai_stock_agent/domain/use_cases/invoke_agent.py`)

**Depends on:** Phase 1

**Verify:**

```text
make lint
python -c "from ai_stock_agent.domain.entities import StockPrice, DocumentChunk; print('OK')"
```

### Phase 3: Agent Core — LangGraph Graph + Tools + Adapters

**Goal:** Working ReAct agent with yfinance tools, runnable locally (without FAISS RAG yet).

Tasks:

- [ ] Create `adapters/outbound/bedrock_llm.py` — `ChatBedrock` wrapper implementing `ILLMProvider` (file: `src/ai_stock_agent/adapters/outbound/bedrock_llm.py`)
- [ ] Create `adapters/outbound/yfinance_stock.py` — yfinance adapter implementing `IStockProvider` with `get_realtime_price` (uses `Ticker.info`) and `get_historical_prices` (uses `Ticker.history()`) (file: `src/ai_stock_agent/adapters/outbound/yfinance_stock.py`)
- [ ] Create `infrastructure/tools.py` — `@tool` definitions for `retrieve_realtime_stock_price` and `retrieve_historical_stock_price` that delegate to `IStockProvider` (file: `src/ai_stock_agent/infrastructure/tools.py`)
- [ ] Create `infrastructure/graph.py` — `build_agent_graph()` function: `StateGraph(MessagesState)` with `agent` node, `tools_condition`, `ToolNode`, compiled with checkpointer param (file: `src/ai_stock_agent/infrastructure/graph.py`)
- [ ] Create agent system prompt in `prompts/system.md` — financial analysis assistant persona with tool usage guidelines (file: `prompts/system.md`)
- [ ] Test locally: invoke graph with yfinance tools, verify tool calls and responses

**Depends on:** Phase 2

**Verify:**

```text
make lint
python -c "
from ai_stock_agent.infrastructure.graph import build_agent_graph
print('Graph module imports OK')
"
```

### Phase 4: RAG — FAISS Index Build + Retriever

**Goal:** Pre-built FAISS index over 3 Amazon PDFs, exposed as a LangGraph tool.

Tasks:

- [ ] Create `adapters/outbound/bedrock_embedder.py` — `BedrockEmbeddings` wrapper implementing `IEmbedder` (file: `src/ai_stock_agent/adapters/outbound/bedrock_embedder.py`)
- [ ] Create `scripts/build_index.py` — Loads 3 PDFs, chunks with `RecursiveCharacterTextSplitter` using `CHUNK_SIZE` and `CHUNK_OVERLAP` from Settings (defaults: 1500 chars, 300 overlap), embeds with Titan, serializes FAISS index to `FAISS_INDEX_PATH` (file: `scripts/build_index.py`)
- [ ] Create `adapters/outbound/faiss_retriever.py` — Loads pre-built FAISS index via `FAISS.load_local()`, implements `IDocumentRetriever`, exposes as LangChain retriever (file: `src/ai_stock_agent/adapters/outbound/faiss_retriever.py`)
- [ ] Add `retrieve_documents` tool to `infrastructure/tools.py` via `create_retriever_tool()` (file: `src/ai_stock_agent/infrastructure/tools.py`)
- [ ] Run `scripts/build_index.py` to generate `data/faiss_index/` directory
- [ ] Add all 3 tools to graph, verify RAG tool returns relevant chunks

**Depends on:** Phase 3

**Verify:**

```text
make build-index
python -c "
from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings
vs = FAISS.load_local('data/faiss_index', BedrockEmbeddings(model_id='amazon.titan-embed-text-v2:0'), allow_dangerous_deserialization=True)
results = vs.similarity_search('Amazon AI business', k=3)
print(f'Retrieved {len(results)} chunks')
"
```

### Phase 5: FastAPI Server + SSE Streaming + Langfuse

**Goal:** Complete server meeting AgentCore HTTP protocol contract, with SSE streaming and Langfuse tracing.

Tasks:

- [ ] Create `adapters/inbound/schemas.py` — Pydantic DTOs: `InvocationRequest`, `InvocationResponse`, `PingResponse` (file: `src/ai_stock_agent/adapters/inbound/schemas.py`)
- [ ] Create `adapters/inbound/api.py` — FastAPI router with `POST /invocations` (SSE via `StreamingResponse` + JSON fallback) and `GET /ping` (file: `src/ai_stock_agent/adapters/inbound/api.py`)
- [ ] Implement SSE formatting: `data: {"type": "token", "content": "..."}` lines from `.astream()` chunks, terminated by `data: {"type": "end"}` (file: `src/ai_stock_agent/adapters/inbound/api.py`)
- [ ] Create `infrastructure/app.py` — FastAPI lifespan (init Settings, build adapters, build graph, store in `app.state`), DI wiring via `app.state` (file: `src/ai_stock_agent/infrastructure/app.py`)
- [ ] Wire Langfuse `CallbackHandler` — created per request, passed in `.astream()` `config["callbacks"]` (file: `src/ai_stock_agent/infrastructure/app.py`)
- [ ] Test locally: `uv run uvicorn ai_stock_agent.infrastructure.app:app --host 0.0.0.0 --port 8080`
- [ ] Verify all 5 queries work with SSE streaming via curl

**Depends on:** Phase 4

**Verify:**

```text
make dev-api
# In another terminal:
curl -N -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the stock price for Amazon right now?"}'
# Verify SSE events stream progressively
curl http://localhost:8080/ping
# Verify {"status": "Healthy"}
```

### Phase 6: Testing

**Goal:** Test suite validating tools, retriever, API, E2E acceptance, and LLM quality.

Tasks:

- [ ] Create `tests/conftest.py` — shared fixtures, pytest config, `anyio` backend (file: `tests/conftest.py`)
- [ ] Create `tests/integration/test_tools.py` — verify `retrieve_realtime_stock_price` returns valid price for "AMZN", `retrieve_historical_stock_price` returns data for a date range (file: `tests/integration/test_tools.py`)
- [ ] Create `tests/integration/test_retriever.py` — verify FAISS retriever returns relevant chunks for each of the 5 UAC queries (file: `tests/integration/test_retriever.py`)
- [ ] Create `tests/integration/test_api.py` — verify `/ping` returns 200 + `{"status": "Healthy"}`; verify `/invocations` missing prompt returns 422 (file: `tests/integration/test_api.py`)
- [ ] Create `tests/e2e/conftest.py` — health check gate (`_require_server`), `e2e_client` fixture with `BASE_URL`, SSE helper `collect_sse_events` (file: `tests/e2e/conftest.py`)
- [ ] Create `tests/e2e/test_acceptance.py` — 5 UAC queries against live server via SSE; assert streaming events received, responses contain expected data (file: `tests/e2e/test_acceptance.py`)
- [ ] Create `tests/e2e/test_streaming.py` — verify SSE format: `Content-Type: text/event-stream`, progressive events, final `end` event (file: `tests/e2e/test_streaming.py`)
- [ ] Create `tests/e2e/test_memory.py` — two messages with same `thread_id`, verify second response references first (file: `tests/e2e/test_memory.py`)
- [ ] Create `tests/e2e/test_llm_eval.py` — LLM-as-judge for each of the 5 queries; `@pytest.mark.llm`; assert quality score >= 7/10 (file: `tests/e2e/test_llm_eval.py`)
- [ ] Add pytest markers to `pyproject.toml`: `e2e` (requires running server), `llm` (requires LLM access) (file: `pyproject.toml`)

**Depends on:** Phase 5

**Verify:**

```text
pytest -m "not e2e and not llm" -v    # integration tests, no server needed
make dev-api                           # start server
pytest -m e2e -v                       # E2E against live server
pytest -m llm -v                       # LLM evaluation
```

### Phase 7: Terraform Infrastructure

**Goal:** Single `terraform apply` provisions all AWS resources.

Tasks:

- [ ] Create `terraform/providers.tf` — AWS + AWSCC providers, pin `aws` >= 6.17.0 (file: `terraform/providers.tf`)
- [ ] Create `terraform/variables.tf` — inputs: region, project name, model IDs, Langfuse keys, Cognito config (file: `terraform/variables.tf`)
- [ ] Create `terraform/cognito.tf` — User pool (password policy, no MFA for demo), app client with `ALLOW_USER_PASSWORD_AUTH` (file: `terraform/cognito.tf`)
- [ ] Create `terraform/ecr.tf` — ECR repository for Docker image (file: `terraform/ecr.tf`)
- [ ] Create `terraform/iam.tf` — AgentCore execution role with policies: Bedrock invoke, Memory access, ECR pull, CloudWatch logs (file: `terraform/iam.tf`)
- [ ] Create `terraform/main.tf` — AgentCore Runtime (CONTAINER, ARM64), Runtime Endpoint, Memory resource, Gateway with `CUSTOM_JWT` authorizer pointing to Cognito (file: `terraform/main.tf`)
- [ ] Create `terraform/outputs.tf` — endpoint URL, gateway URL, Cognito pool ID, client ID, ECR repo URL, Memory ARN (file: `terraform/outputs.tf`)
- [ ] Test: `terraform init && terraform plan` succeeds

**Depends on:** None (can be developed in parallel with Phases 2-6)

**Verify:**

```text
cd terraform && terraform init && terraform validate && terraform plan
```

### Phase 8: Docker + Deployment

**Goal:** ARM64 container image deployed to AgentCore, verified end-to-end.

Tasks:

- [ ] Create `Dockerfile` — multi-stage ARM64 build: UV install deps → copy source + FAISS index → `CMD uvicorn` on port 8080 (file: `Dockerfile`)
- [ ] Build locally: `docker build --platform linux/arm64 -t ai-stock-agent .`
- [ ] Push to ECR: `docker tag` + `docker push` (Makefile `push` target)
- [ ] `terraform apply` to deploy (creates/updates Runtime with new image)
- [ ] Configure Langfuse env vars on AgentCore Runtime
- [ ] Verify `/ping` returns healthy via AgentCore endpoint
- [ ] Verify `/invocations` streams SSE via Gateway with Cognito JWT
- [ ] Verify Langfuse traces appear in dashboard

**Depends on:** Phase 5 (working server), Phase 7 (Terraform resources)

**Verify:**

```text
make build && make push && make apply
curl https://<endpoint>/ping
# Create Cognito user and get JWT, then:
curl -N -X POST https://<gateway>/invocations \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the stock price for Amazon right now?"}'
```

### Phase 9: Notebook + Deliverables

**Goal:** Demonstration notebook and final documentation.

Tasks:

- [ ] Create `notebooks/demo.ipynb` with cells: config, helpers, Cognito auth, 5 UAC queries, multi-turn demo, Langfuse traces (file: `notebooks/demo.ipynb`)
- [ ] Cell 1: Configuration — `BASE_URL`, Cognito pool ID + client ID from Terraform outputs (file: `notebooks/demo.ipynb`)
- [ ] Cell 2: Helper functions — `authenticate()` (boto3 `InitiateAuth`), `invoke_agent()` (SSE parsing + JWT header) (file: `notebooks/demo.ipynb`)
- [ ] Cell 3: Authenticate with Cognito, display JWT (file: `notebooks/demo.ipynb`)
- [ ] Cells 4-8: Each of the 5 UAC queries with streamed output (file: `notebooks/demo.ipynb`)
- [ ] Cell 9: Multi-turn demo — follow-up question in same `thread_id` (file: `notebooks/demo.ipynb`)
- [ ] Cell 10: Langfuse traces — fetch via API + display screenshots from `notebooks/images/` (file: `notebooks/demo.ipynb`)
- [ ] Capture Langfuse trace screenshots into `notebooks/images/` (manual step during Phase 8 verification)
- [ ] Write `README.md` — prerequisites, AWS setup, `make` targets in order, architecture overview, notebook instructions (file: `README.md`)
- [ ] Run full E2E suite + LLM eval against deployed endpoint

**Depends on:** Phase 8 (deployed endpoint)

**Verify:**

```text
# Execute all notebook cells — all 5 queries return correct answers
# Langfuse traces visible in dashboard
BASE_URL=<gateway-url> pytest -m e2e -v
BASE_URL=<gateway-url> pytest -m llm -v
```

---

## 8. Testing Strategy

### Test Pyramid

| Layer | LLM Calls | External Services | Frequency | Purpose |
| --- | --- | --- | --- | --- |
| Integration | None | yfinance (real), FAISS (real) | Every commit | Tool execution, retrieval quality, API schema |
| E2E acceptance | Real model | Full stack (server running) | Manual / PR | Full agent flow for 5 UAC queries via SSE |
| LLM eval | Real model | Full stack | Manual / merge | LLM-as-judge validates answer quality |

### Integration Tests (no server, no LLM)

- **Tools**: `retrieve_realtime_stock_price("AMZN")` returns a positive float price; `retrieve_historical_stock_price("AMZN", "2025-10-01", "2025-12-31")` returns multiple price points
- **Retriever**: FAISS retriever returns chunks with `score > 0` for each UAC query; relevant doc ranks in top-3 for targeted queries (e.g., "office space" hits Annual Report)
- **API schema**: `/ping` returns 200; `/invocations` with missing `prompt` returns 422

### E2E Acceptance Tests (live server)

- Each of the 5 UAC queries produces SSE events with token content
- Response contains expected data markers (stock price present, document-sourced facts present)
- Final `end` event received for every query
- Memory test: second message in same thread references prior context

### LLM Evaluation Tests

- LLM-as-judge scores each of the 5 UAC responses on: relevance, accuracy, completeness
- Threshold: >= 7/10 per query
- Evaluator LLM: same Bedrock Claude model

### Acceptance Criteria (GIVEN/WHEN/THEN)

```text
GIVEN the agent is running with all tools registered
WHEN the user asks "What is the stock price for Amazon right now?"
THEN the agent calls retrieve_realtime_stock_price with ticker AMZN
AND returns the current price via SSE streaming

GIVEN the agent has FAISS index loaded with 3 Amazon PDFs
WHEN the user asks "What is the total amount of office space Amazon owned in North America in 2024?"
THEN the agent calls retrieve_documents
AND returns a specific data point from the Annual Report

GIVEN two messages sent with the same thread_id
WHEN the second message references the first conversation
THEN the agent response demonstrates awareness of prior context
AND AgentCoreMemorySaver persists the conversation state

GIVEN the server is running on port 8080
WHEN a POST to /invocations includes stream=true
THEN the response Content-Type is text/event-stream
AND events arrive progressively (not all at once)

GIVEN Langfuse is configured via env vars
WHEN any agent invocation completes
THEN a trace appears in Langfuse Cloud with tool calls and LLM responses
```

---

## 9. Risks & Open Questions

| # | Risk / Question | Status | Notes |
| --- | --- | --- | --- |
| 1 | `stream_mode="messages"` may not stream incrementally with some LangGraph versions (langchain-ai/langgraph#5249) | Mitigated | Pin LangGraph version; verify during Phase 3; fall back to `stream_mode="updates"` and extract content manually |
| 2 | `ChatBedrock` vs `ChatBedrockConverse` streaming behavior differs (langchain-aws#763) | Resolved | Use `ChatBedrock` (not Converse) to avoid missing `on_chat_model_stream` events |
| 3 | AgentCore Gateway may buffer SSE streams | Verify Phase 8 | SSE is documented in AgentCore HTTP contract; fallback: expose Runtime Endpoint directly or use API Gateway HTTP API |
| 4 | `AgentCoreMemorySaver` `memory_id` format | TBD | Likely the Memory resource ARN from Terraform output; resolve during Phase 3 |
| 5 | `aws-ia/agentcore/aws` module may not support Gateway with Cognito JWT | TBD | Fall back to raw `aws_bedrockagentcore_gateway` resource if needed |
| 6 | Bedrock model access not enabled in AWS account | Mitigated | Verify in Bedrock console before Phase 3; request access to Claude Sonnet + Titan Embeddings early |
| 7 | C extension compatibility (faiss-cpu) | Resolved | Both local dev and container use Python 3.12 |
| 8 | FAISS `load_local` distance strategy may not round-trip (langchain#14141) | Low | Build and load with same params; test during Phase 4 |
| 9 | Which AWS region has both AgentCore and Bedrock Claude available? | TBD | Likely `us-east-1`; verify before Phase 7 |

---

## 10. Files Affected

| Action | File | Changes |
| --- | --- | --- |
| Create | `pyproject.toml` | Project metadata, dependencies, pytest config, ruff config |
| Create | `Makefile` | Dev workflow targets |
| Create | `.env.example` | All env vars documented |
| Create | `Dockerfile` | ARM64 multi-stage build |
| Create | `src/ai_stock_agent/__init__.py` | Package init |
| Create | `src/ai_stock_agent/domain/__init__.py` | Package init |
| Create | `src/ai_stock_agent/domain/entities.py` | `StockPrice`, `DocumentChunk` value objects |
| Create | `src/ai_stock_agent/domain/ports/__init__.py` | Package init |
| Create | `src/ai_stock_agent/domain/ports/inbound.py` | `AgentPort` protocol |
| Create | `src/ai_stock_agent/domain/ports/outbound/__init__.py` | Package init |
| Create | `src/ai_stock_agent/domain/ports/outbound/llm.py` | `ILLMProvider` protocol |
| Create | `src/ai_stock_agent/domain/ports/outbound/stock.py` | `IStockProvider` protocol |
| Create | `src/ai_stock_agent/domain/ports/outbound/retriever.py` | `IDocumentRetriever` protocol |
| Create | `src/ai_stock_agent/domain/ports/outbound/embedder.py` | `IEmbedder` protocol |
| Create | `src/ai_stock_agent/domain/use_cases/__init__.py` | Package init |
| Create | `src/ai_stock_agent/domain/use_cases/invoke_agent.py` | Agent invocation + streaming orchestration |
| Create | `src/ai_stock_agent/adapters/__init__.py` | Package init |
| Create | `src/ai_stock_agent/adapters/inbound/__init__.py` | Package init |
| Create | `src/ai_stock_agent/adapters/inbound/api.py` | FastAPI routes (`/invocations`, `/ping`) |
| Create | `src/ai_stock_agent/adapters/inbound/schemas.py` | Pydantic DTOs |
| Create | `src/ai_stock_agent/adapters/outbound/__init__.py` | Package init |
| Create | `src/ai_stock_agent/adapters/outbound/bedrock_llm.py` | `ChatBedrock` adapter |
| Create | `src/ai_stock_agent/adapters/outbound/bedrock_embedder.py` | Titan embeddings adapter |
| Create | `src/ai_stock_agent/adapters/outbound/yfinance_stock.py` | yfinance stock data adapter |
| Create | `src/ai_stock_agent/adapters/outbound/faiss_retriever.py` | FAISS retriever adapter |
| Create | `src/ai_stock_agent/infrastructure/__init__.py` | Package init |
| Create | `src/ai_stock_agent/infrastructure/app.py` | FastAPI lifespan + DI wiring |
| Create | `src/ai_stock_agent/infrastructure/config.py` | `Settings` (Pydantic BaseSettings) |
| Create | `src/ai_stock_agent/infrastructure/graph.py` | LangGraph `StateGraph` definition |
| Create | `src/ai_stock_agent/infrastructure/tools.py` | LangGraph `@tool` wrappers |
| Create | `prompts/system.md` | Agent system prompt |
| Create | `scripts/build_index.py` | PDF ingestion → FAISS index builder |
| Create | `terraform/providers.tf` | AWS provider config |
| Create | `terraform/variables.tf` | Input variables |
| Create | `terraform/outputs.tf` | Output values |
| Create | `terraform/cognito.tf` | Cognito user pool + app client |
| Create | `terraform/main.tf` | AgentCore Runtime, Endpoint, Memory, Gateway |
| Create | `terraform/iam.tf` | IAM roles and policies |
| Create | `terraform/ecr.tf` | ECR repository |
| Create | `notebooks/demo.ipynb` | Demonstration notebook |
| Create | `notebooks/images/` | Langfuse trace screenshots |
| Create | `tests/conftest.py` | Shared fixtures, pytest config |
| Create | `tests/integration/test_tools.py` | yfinance tool tests |
| Create | `tests/integration/test_retriever.py` | FAISS retrieval tests |
| Create | `tests/integration/test_api.py` | API schema + health tests |
| Create | `tests/e2e/conftest.py` | E2E fixtures |
| Create | `tests/e2e/test_acceptance.py` | 5 UAC query acceptance tests |
| Create | `tests/e2e/test_streaming.py` | SSE format tests |
| Create | `tests/e2e/test_memory.py` | Multi-turn memory tests |
| Create | `tests/e2e/test_llm_eval.py` | LLM-as-judge evaluation |
| Modify | `README.md` | Full project documentation |
| Modify | `CLAUDE.md` | Update commands + architecture for this project |

---

## 11. References

- PRD: `docs/PRD-ai-stock-agent.md`
- Assignment: `docs/assignment.md`
- [AgentCore HTTP Protocol Contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html)
- [AgentCore Gateway Inbound Auth](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html)
- [Integrate AgentCore Memory with LangGraph](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-integrate-lang.html)
- [aws-ia/agentcore/aws Terraform Module](https://registry.terraform.io/modules/aws-ia/agentcore/aws/latest)
- [LangGraph Streaming Guide](https://docs.langchain.com/oss/python/langgraph/streaming)
- [Langfuse LangGraph Integration](https://langfuse.com/docs/integrations/langchain/example-python-langgraph)
- [FAISS LangChain Integration](https://docs.langchain.com/oss/python/integrations/vectorstores/faiss)
- [langgraph-checkpoint-aws (PyPI)](https://pypi.org/project/langgraph-checkpoint-aws/)
