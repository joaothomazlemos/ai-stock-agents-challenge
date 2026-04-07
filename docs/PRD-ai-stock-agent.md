# PRD: AI Stock Agent on AWS Bedrock AgentCore

| Field | Value |
| --- | --- |
| **Status** | Draft |
| **Author** | Joao Thomaz Lemos |
| **Date** | 2026-04-07 |
| **Last Updated** | 2026-04-07 |

---

## Change History

| Date | Author | Description |
| --- | --- | --- |
| 2026-04-07 | Joao / Cursor | Initial draft based on assignment analysis, architecture design, and technology decisions |
| 2026-04-07 | Joao / Cursor | Added testing strategy (E2E + LLM eval), notebook local/deployed mode, screenshots directory |

---

## 1. Overview

Build an AI agent solution on AWS Bedrock AgentCore that answers real-time and historical stock price queries via SSE streaming. The agent uses a LangGraph ReAct pattern with yfinance tools and a RAG knowledge base over Amazon financial documents. Authentication is handled through AWS Cognito via the AgentCore native gateway, observability through Langfuse Cloud, and all infrastructure is provisioned with Terraform.

---

## 2. Problem Statement

This is a greenfield take-home assignment. The repository currently contains no application code (`src/` does not exist), no `pyproject.toml`, no `Makefile`, and no Terraform infrastructure. The deliverable is a fully functional AI agent deployed on AgentCore with a Jupyter notebook demonstrating 5 specific queries, Langfuse trace screenshots, and Cognito authentication.

The assignment requires specific technical choices (LangGraph, yfinance, SSE streaming, Cognito, Langfuse, Terraform) and specific acceptance criteria (5 queries answered correctly in a notebook). Every component must be built from scratch.

---

## 3. Goals & Success Metrics

### Goals

1. Deploy a LangGraph ReAct agent on AgentCore Runtime that answers stock price queries via SSE streaming
2. Implement Cognito-based user authentication via the AgentCore native gateway
3. Build a RAG knowledge base over 3 Amazon financial PDFs using FAISS + Titan Embeddings
4. Provide at least 2 yfinance tools (`retrieve_realtime_stock_price`, `retrieve_historical_stock_price`)
5. Integrate Langfuse Cloud for full trace observability
6. Provision all infrastructure with Terraform using the `aws-ia/agentcore/aws` module
7. Deliver a Jupyter notebook demonstrating all 5 required queries with traces and auth

### Success Metrics (SMART)

| Metric | Target | How to Measure |
| --- | --- | --- |
| All 5 notebook queries answered correctly | 5/5 pass | Notebook executed by evaluator team |
| SSE streaming visible in notebook | Every response streams token-by-token | Notebook cell output shows progressive rendering |
| Langfuse traces captured | 100% of agent invocations traced | Screenshots in notebook + Langfuse dashboard |
| Cognito auth working | Notebook authenticates before querying | `InitiateAuth` call visible in notebook |
| Terraform provisions all infra | Single `terraform apply` creates full stack | README documents deployment steps |
| Agent handles multi-turn via AgentCoreMemorySaver | Conversation state persists across calls | Notebook demo with follow-up questions in same thread |
| E2E acceptance tests pass | 5/5 UAC queries pass | `pytest -m e2e` green |
| LLM eval scores above threshold | >= 7/10 for each query | `pytest -m llm` with LLM-as-judge scoring |
| Integration tests pass without server | All pass | `pytest -m "not e2e and not llm"` green |

---

## 4. Target Users & Personas

| Persona | Description | Impact |
| --- | --- | --- |
| **Evaluator (hiring team)** | Reviews the submission: deploys infra, runs notebook, inspects code quality | Primary user. Must be able to deploy and run with minimal friction. |
| **End user (stock researcher)** | Queries real-time/historical stock prices and Amazon financial data | The persona the agent is designed for. Validates agent quality. |
| **Developer (maintainer)** | Future developer reading/extending the codebase | Clean architecture, parameterized config, and clear README matter. |

---

## 5. Proposed Solution

### 5.1 Architecture Overview

```text
+-------------------------------------------------------------------------+
|                              AWS Cloud                                   |
|                                                                          |
|  +------------------+    +---------------------+    +-----------------+  |
|  | AWS Cognito      |<---| AgentCore Gateway   |    | Terraform       |  |
|  | User Pool + JWT  |    | Cognito JWT Auth    |    | Terraform (aws) |  |
|  +------------------+    +---------------------+    +-----------------+  |
|                                  |                                       |
|                           4. Proxy to Runtime                            |
|                                  v                                       |
|  +---------------------------------------------------------------+      |
|  |              AgentCore Runtime (ARM64 container)               |      |
|  |                                                                |      |
|  |  +----------------------------------------------------------+ |      |
|  |  | FastAPI Server (port 8080)                                | |      |
|  |  | POST /invocations (JSON/SSE) + GET /ping                  | |      |
|  |  +----------------------------------------------------------+ |      |
|  |                          |                                     |      |
|  |                    .astream()                                  |      |
|  |                          v                                     |      |
|  |  +----------------------------------------------------------+ |      |
|  |  | LangGraph ReAct Agent                                     | |      |
|  |  |   llm_call -> should_continue -> tool_node -> loop        | |      |
|  |  +----------------------------------------------------------+ |      |
|  |       |              |              |              |           |      |
|  |       v              v              v              v           |      |
|  |  +---------+  +-----------+  +----------+  +--------------+  |      |
|  |  | yfinance|  | yfinance  |  | FAISS    |  | AgentCore    |  |      |
|  |  | realtime|  | historical|  | RAG tool |  | MemorySaver  |  |      |
|  |  +---------+  +-----------+  +----------+  +--------------+  |      |
|  |                                    |                          |      |
|  |                              Pre-built index                  |      |
|  |                              Titan 512d embeddings            |      |
|  |                              3 Amazon PDFs                    |      |
|  +---------------------------------------------------------------+      |
|                          |                                               |
|                    Traces via callback                                    |
|                          v                                               |
|                 +-------------------+                                     |
|                 | Langfuse Cloud    |                                     |
|                 | (free tier)       |                                     |
|                 +-------------------+                                     |
+-------------------------------------------------------------------------+

Client: Jupyter Notebook (boto3 / AgentCore SDK)
  1. Authenticate with Cognito -> get JWT
  2. POST /invocations via AgentCore Gateway with JWT
  3. Receive SSE stream response
```

### 5.2 Technology Stack

| Component | Technology | Notes |
| --- | --- | --- |
| Runtime | AWS Bedrock AgentCore | ARM64 container, port 8080 |
| Gateway + Auth | AgentCore Gateway + Cognito JWT | Native gateway, `CUSTOM_JWT` authorizer type |
| Agent framework | LangGraph (ReAct pattern) | `StateGraph(MessagesState)`, `.astream()` |
| LLM | Claude Sonnet via Bedrock | Parameterized: model ID from env var |
| Embeddings | Titan Embeddings via Bedrock | Parameterized: model ID + dims (default 512) from env var |
| Vector store | FAISS (in-memory) | Pre-built index bundled in container image |
| Stock data | yfinance | 2 tools: realtime + historical |
| Memory | `AgentCoreMemorySaver` | Persistent checkpointer, `actor_id` + `thread_id` |
| Observability | Langfuse Cloud (free tier) | `CallbackHandler` passed to `.astream()` config |
| IaC | Terraform | `aws-ia/agentcore/aws` module + `aws` provider (v6.17+) |
| Package manager | UV | `pyproject.toml` + `uv.lock` |
| Code quality | Ruff | line-length=100, target py312 |
| Container | Docker (ARM64) | Multi-stage build, `--platform linux/arm64` |

### 5.3 Endpoint Contract

AgentCore requires the container to implement:

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/invocations` | POST | Agent interaction. JSON request, SSE or JSON response. |
| `/ping` | GET | Health check. Returns `{"status": "Healthy"}`. |

Request schema for `/invocations`:

```json
{
  "prompt": "What is the stock price for Amazon right now?",
  "thread_id": "abc-123",
  "stream": true
}
```

- `prompt` (required): The user query.
- `thread_id` (optional): For multi-turn conversations via `AgentCoreMemorySaver`. Auto-generated if omitted.
- `stream` (optional, default `true`): If true, responds with `Content-Type: text/event-stream`. If false, returns full JSON.

### 5.4 Hexagonal Architecture

```text
src/ai_stock_agent/
├── domain/                     # Pure Python, no framework deps
│   ├── entities.py             # StockPrice, DocumentChunk value objects
│   ├── ports/
│   │   ├── inbound.py          # AgentPort (invoke agent use case interface)
│   │   └── outbound/
│   │       ├── llm.py          # ILLMProvider interface
│   │       ├── embedder.py     # IEmbedder interface
│   │       ├── stock.py        # IStockProvider interface
│   │       └── retriever.py    # IDocumentRetriever interface
│   └── use_cases/
│       └── invoke_agent.py     # Orchestrates graph invocation + streaming
│
├── adapters/
│   ├── inbound/
│   │   ├── api.py              # FastAPI routes: /invocations, /ping
│   │   └── schemas.py          # Pydantic request/response DTOs
│   └── outbound/
│       ├── bedrock_llm.py      # ChatBedrock adapter (implements ILLMProvider)
│       ├── bedrock_embedder.py # Titan embeddings adapter (implements IEmbedder)
│       ├── yfinance_stock.py   # yfinance adapter (implements IStockProvider)
│       └── faiss_retriever.py  # FAISS retriever adapter (implements IDocumentRetriever)
│
└── infrastructure/
    ├── app.py                  # FastAPI lifespan, DI wiring, composition root
    ├── config.py               # Pydantic Settings (env vars)
    ├── graph.py                # LangGraph StateGraph definition + compilation
    └── tools.py                # LangGraph tool definitions (wrappers around ports)
```

---

## 6. Features & Requirements (MoSCoW)

### Must-Have (P0)

| # | Requirement | Acceptance Criteria |
| --- | --- | --- |
| P0-1 | LangGraph ReAct agent with `.astream()` | Agent loops through llm_call -> should_continue -> tool_node |
| P0-2 | `retrieve_realtime_stock_price` tool | Returns current price for a given ticker via yfinance |
| P0-3 | `retrieve_historical_stock_price` tool | Returns historical prices for a date range via yfinance |
| P0-4 | RAG knowledge base tool with 3 Amazon PDFs | FAISS index with Titan 512d embeddings, pre-built and bundled |
| P0-5 | SSE streaming responses | `/invocations` returns `text/event-stream` with progressive tokens |
| P0-6 | Cognito authentication | User pool + app client; JWT validated by AgentCore Gateway |
| P0-7 | FastAPI `/invocations` + `/ping` endpoints | Meets AgentCore HTTP protocol contract (port 8080, ARM64) |
| P0-8 | `AgentCoreMemorySaver` for conversation state | Multi-turn conversations persist across requests via `thread_id` |
| P0-9 | Terraform infrastructure | AgentCore Runtime, Endpoint, Gateway, Cognito, Memory, IAM |
| P0-10 | Jupyter notebook with 5 queries | All 5 assignment queries answered correctly |
| P0-11 | Langfuse observability | Traces visible in Langfuse Cloud for every invocation |
| P0-12 | Docker ARM64 container | Builds and runs on AgentCore Graviton runtime |

### Should-Have (P1)

| # | Requirement | Notes |
| --- | --- | --- |
| P1-1 | Langfuse trace screenshots in notebook | Required by assignment UAC |
| P1-2 | Parameterized LLM model ID | Env var `BEDROCK_MODEL_ID`, default `anthropic.claude-sonnet-4-20250514` |
| P1-3 | Parameterized embedding model + dimensions | Env vars `EMBEDDING_MODEL_ID` + `EMBEDDING_DIMS` |
| P1-4 | FAISS index pre-build script | `scripts/build_index.py` that chunks PDFs and serializes `.faiss` |
| P1-5 | Clear README with deployment instructions | Step-by-step: prerequisites, Terraform, Docker build, notebook run |
| P1-6 | E2E acceptance tests for the 5 UAC queries | Tests run against live server, verify SSE streaming + response relevance |
| P1-7 | LLM evaluation tests | LLM-as-judge validates answer quality for each query; `@pytest.mark.llm` |
| P1-8 | Integration tests for tools and retriever | yfinance returns valid data, FAISS retrieves relevant chunks |
| P1-9 | Notebook targets deployed AgentCore endpoint | `BASE_URL` from Terraform output; full Cognito JWT auth flow |

### Could-Have (P2)

| # | Requirement | Notes |
| --- | --- | --- |
| P2-1 | Makefile for full workflow | `make install`, `make dev`, `make lint`, `make test`, `make build-index`, `make build`, `make push`, `make apply` -- README documents targets in execution order |
| P2-2 | Pre-commit hooks (ruff) | Already have `.pre-commit-config.yaml` in repo |
| P2-3 | CI/CD pipeline (GitHub Actions) | Lint, test, build ARM64 image, push to ECR |
| P2-4 | Agent system prompt optimization | Tuned prompt for financial analysis persona |

### Won't-Have (this iteration)

- Frontend / web UI (notebook-only client)
- Multiple user support / multi-tenancy
- Bedrock Knowledge Base (using FAISS instead)
- WebSocket `/ws` endpoint (SSE is sufficient)
- Long-term memory extraction (only session memory via checkpointer)

---

## 7. User Scenarios

### Scenario 1: Real-Time Stock Price

Evaluator opens the Jupyter notebook. They authenticate with Cognito, obtaining a JWT. They run the cell: "What is the stock price for Amazon right now?" The agent invokes `retrieve_realtime_stock_price` with ticker `AMZN`, streams the response token by token, and returns the current price with market context.

**Query:** What is the stock price for Amazon right now?
**Expected:** Agent calls yfinance for AMZN real-time price, streams result via SSE.

### Scenario 2: Historical Stock Prices

Evaluator asks: "What were the stock prices for Amazon in Q4 last year?" The agent determines Q4 2025 means October-December 2025, calls `retrieve_historical_stock_price` with appropriate date range, and presents the data.

**Query:** What were the stock prices for Amazon in Q4 last year?
**Expected:** Agent calls yfinance with `start=2025-10-01`, `end=2025-12-31`, streams formatted historical data.

### Scenario 3: Cross-Reference Stock + Reports

Evaluator asks: "Compare Amazon's recent stock performance to what analysts predicted in their reports." The agent uses both the yfinance historical tool AND the RAG retrieval tool to cross-reference actual prices with analyst commentary from the earnings releases.

**Query:** Compare Amazon's recent stock performance to what analysts predicted in their reports
**Expected:** Agent calls both yfinance (historical) and RAG (earnings reports), synthesizes a comparison.

### Scenario 4: Multi-Source Research

Evaluator asks: "I'm researching AMZN -- give me the current price and any relevant information about their AI business." The agent retrieves the real-time price AND searches the knowledge base for AI-related content from the annual report and earnings releases.

**Query:** I'm researching AMZN -- give me the current price and any relevant information about their AI business
**Expected:** Agent calls realtime tool + RAG tool, combines price data with AI business insights from documents.

### Scenario 5: Document-Only Query

Evaluator asks: "What is the total amount of office space Amazon owned in North America in 2024?" This is purely a document retrieval question -- no stock tools needed. The agent searches the annual report via RAG.

**Query:** What is the total amount of office space Amazon owned in North America in 2024?
**Expected:** Agent calls RAG tool only, retrieves specific data point from Amazon 2024 Annual Report.

---

## 8. Implementation Plan

### Phase 1: Project Scaffolding

**Goal:** Set up the project structure, dependencies, and dev tooling so we can start writing agent code.

- [ ] Create `pyproject.toml` with UV, Python 3.14, core deps (langgraph, langchain-aws, faiss-cpu, yfinance, fastapi, uvicorn, langfuse, pydantic-settings)
- [ ] Create hexagonal directory structure under `src/ai_stock_agent/`
- [ ] Create `Makefile` with targets: install, dev, lint, format, test, build
- [ ] Create `infrastructure/config.py` with Pydantic Settings (all env vars parameterized)
- [ ] Create `.env.example` documenting all environment variables
- [ ] Run `uv sync` to verify dependency resolution
- [ ] Verify `make lint` passes on empty project

### Phase 2: Agent Core (LangGraph + Tools + RAG)

**Goal:** Build the working ReAct agent locally with all 3 tools, streaming, and FAISS RAG.

- [ ] Implement `adapters/outbound/bedrock_llm.py` -- ChatBedrock wrapper implementing `ILLMProvider`
- [ ] Implement `adapters/outbound/bedrock_embedder.py` -- Titan embeddings implementing `IEmbedder`
- [ ] Implement `adapters/outbound/yfinance_stock.py` -- yfinance adapter implementing `IStockProvider`
- [ ] Implement `infrastructure/tools.py` -- LangGraph tool definitions: `retrieve_realtime_stock_price`, `retrieve_historical_stock_price`, `retrieve_documents`
- [ ] Create `scripts/build_index.py` -- download 3 PDFs, chunk with RecursiveCharacterTextSplitter, embed with Titan, serialize FAISS index to `data/faiss_index/`
- [ ] Implement `adapters/outbound/faiss_retriever.py` -- load pre-built FAISS index, implement `IDocumentRetriever`
- [ ] Implement `infrastructure/graph.py` -- StateGraph with `llm_call`, `should_continue`, `tool_node`, compiled with `AgentCoreMemorySaver`
- [ ] Implement `domain/use_cases/invoke_agent.py` -- orchestrate graph invocation + SSE streaming
- [ ] Implement `adapters/inbound/api.py` -- FastAPI routes for `/invocations` (POST) and `/ping` (GET)
- [ ] Implement `infrastructure/app.py` -- FastAPI lifespan, DI wiring
- [ ] Test locally: `uv run uvicorn src.ai_stock_agent.infrastructure.app:app --port 8080`
- [ ] Verify all 5 queries work locally with streaming

### Phase 3: Testing

**Goal:** Build the test suite that validates the agent works correctly before deployment. Tests act as a quality gate and living specification for the 5 UAC queries.

Tests follow the cost/latency pyramid from the test-guide skill:

| Layer | LLM Calls | Frequency | Purpose |
| --- | --- | --- | --- |
| Integration tests | None | Every commit | Tool execution, FAISS retrieval, API schema validation |
| E2E acceptance tests | Real model | Manual / PR | Full agent flow for all 5 UAC queries via SSE |
| LLM eval tests | Real model | Manual / merge | LLM-as-judge validates answer quality and completeness |

- [ ] Create `tests/conftest.py` -- shared fixtures, pytest config
- [ ] Create `tests/integration/test_tools.py` -- verify `retrieve_realtime_stock_price` returns valid price data, `retrieve_historical_stock_price` returns data for date range
- [ ] Create `tests/integration/test_retriever.py` -- verify FAISS retriever returns relevant chunks for each of the 5 queries; assert relevant doc ranks higher than irrelevant in top-k
- [ ] Create `tests/integration/test_api.py` -- verify `/ping` returns 200 + `{"status": "Healthy"}`; verify `/invocations` request schema validation (missing prompt -> 422)
- [ ] Create `tests/e2e/conftest.py` -- health check gate (`_require_server`), `e2e_client` fixture with `BASE_URL`, SSE helper `collect_sse_events`
- [ ] Create `tests/e2e/test_acceptance.py` -- run all 5 UAC queries against live server via SSE; assert streaming events received, response contains expected data (stock price present, document content present, etc.)
- [ ] Create `tests/e2e/test_streaming.py` -- verify SSE format: `Content-Type: text/event-stream`, progressive events, final event closes stream
- [ ] Create `tests/e2e/test_memory.py` -- send two messages with same `thread_id`, verify second response references first conversation
- [ ] Create `tests/e2e/test_llm_eval.py` -- LLM-as-judge for each of the 5 queries: feed the agent's response + the original question to an evaluator LLM, assert quality score >= threshold; mark with `@pytest.mark.llm`
- [ ] Add pytest markers to `pyproject.toml`: `e2e`, `llm`
- [ ] Verify: `pytest -m "not e2e and not llm"` passes (integration tests, no server needed)
- [ ] Verify: `pytest -m e2e` passes (requires `make dev` running)

### Phase 4: Infrastructure (Terraform)

**Goal:** Provision all AWS resources with Terraform so the agent can be deployed.

- [ ] Create `terraform/` directory structure
- [ ] Create Cognito user pool + app client resources
- [ ] Create AgentCore Memory resource
- [ ] Create AgentCore Runtime resource (CONTAINER type, ARM64)
- [ ] Create AgentCore Runtime Endpoint
- [ ] Create AgentCore Gateway with `CUSTOM_JWT` authorizer pointing to Cognito
- [ ] Create ECR repository for the Docker image
- [ ] Create IAM roles: AgentCore execution role (Bedrock invoke, Memory access, ECR pull)
- [ ] Create `terraform/variables.tf` with parameterized inputs (region, model IDs, etc.)
- [ ] Create `terraform/outputs.tf` (endpoint URL, Cognito pool ID, client ID)
- [ ] Test: `terraform plan` succeeds

### Phase 5: Deployment Integration

**Goal:** Build the ARM64 Docker image, push to ECR, deploy to AgentCore, and verify end-to-end.

- [ ] Create `Dockerfile` -- multi-stage ARM64 build, install deps, copy pre-built FAISS index, expose port 8080
- [ ] Build and test locally: `docker build --platform linux/arm64 -t ai-stock-agent .`
- [ ] Push image to ECR
- [ ] Deploy to AgentCore Runtime (update endpoint with new image)
- [ ] Configure Langfuse env vars (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`) as AgentCore Runtime environment variables
- [ ] Verify `/ping` returns healthy via AgentCore endpoint
- [ ] Verify `/invocations` returns SSE stream via AgentCore Gateway with Cognito JWT
- [ ] Verify Langfuse traces appear in dashboard
- [ ] Run E2E tests against deployed endpoint: `BASE_URL=<agentcore-url> pytest -m e2e`

### Phase 6: Notebook & Deliverables

**Goal:** Create the demonstration notebook targeting the deployed AgentCore endpoint and finalize documentation.

- [ ] Create `notebooks/demo.ipynb`
- [ ] Cell 1: Configuration -- `BASE_URL` (AgentCore endpoint from Terraform output), AWS credentials, Cognito user pool ID + client ID
- [ ] Cell 2: Helper functions -- `invoke_agent(prompt, thread_id, stream)` with SSE parsing, JWT header injection
- [ ] Cell 3: Authenticate with Cognito (`InitiateAuth` via boto3), display JWT
- [ ] Cell 4: Query -- "What is the stock price for Amazon right now?"
- [ ] Cell 5: Query -- "What were the stock prices for Amazon in Q4 last year?"
- [ ] Cell 6: Query -- "Compare Amazon's recent stock performance to what analysts predicted in their reports"
- [ ] Cell 7: Query -- "I'm researching AMZN -- give me the current price and any relevant information about their AI business"
- [ ] Cell 8: Query -- "What is the total amount of office space Amazon owned in North America in 2024?"
- [ ] Cell 9: Multi-turn demo -- follow-up question in same `thread_id` to prove memory works
- [ ] Cell 10: Langfuse traces -- fetch traces via Langfuse API (`langfuse.get_client().get_traces()`) and display inline; also include screenshots from `notebooks/images/` as fallback
- [ ] Create `notebooks/images/` directory with Langfuse trace screenshots (captured during Phase 5 verification)
- [ ] Write comprehensive `README.md` with: prerequisites (AWS SSO login, Bedrock model access, Terraform, UV, Docker), AWS credentials setup (`aws sso login --profile <profile>`), `make` targets in execution order, architecture overview, notebook instructions
- [ ] Final review: run full E2E suite + LLM eval, verify all UAC are met

---

## 9. Files Affected

### To Be Created

| File | Purpose |
| --- | --- |
| `pyproject.toml` | Python project config, dependencies (UV) |
| `Makefile` | Dev workflow targets |
| `.env.example` | Environment variable documentation |
| `Dockerfile` | ARM64 container build for AgentCore |
| `src/ai_stock_agent/__init__.py` | Package init |
| `src/ai_stock_agent/domain/entities.py` | StockPrice, DocumentChunk value objects |
| `src/ai_stock_agent/domain/ports/inbound.py` | AgentPort interface |
| `src/ai_stock_agent/domain/ports/outbound/llm.py` | ILLMProvider interface |
| `src/ai_stock_agent/domain/ports/outbound/embedder.py` | IEmbedder interface |
| `src/ai_stock_agent/domain/ports/outbound/stock.py` | IStockProvider interface |
| `src/ai_stock_agent/domain/ports/outbound/retriever.py` | IDocumentRetriever interface |
| `src/ai_stock_agent/domain/use_cases/invoke_agent.py` | Agent invocation + streaming orchestration |
| `src/ai_stock_agent/adapters/inbound/api.py` | FastAPI routes (/invocations, /ping) |
| `src/ai_stock_agent/adapters/inbound/schemas.py` | Pydantic request/response models |
| `src/ai_stock_agent/adapters/outbound/bedrock_llm.py` | ChatBedrock adapter |
| `src/ai_stock_agent/adapters/outbound/bedrock_embedder.py` | Titan embeddings adapter |
| `src/ai_stock_agent/adapters/outbound/yfinance_stock.py` | yfinance stock data adapter |
| `src/ai_stock_agent/adapters/outbound/faiss_retriever.py` | FAISS retriever adapter |
| `src/ai_stock_agent/infrastructure/app.py` | FastAPI lifespan + DI wiring |
| `src/ai_stock_agent/infrastructure/config.py` | Pydantic Settings (env-based config) |
| `src/ai_stock_agent/infrastructure/graph.py` | LangGraph StateGraph definition |
| `src/ai_stock_agent/infrastructure/tools.py` | LangGraph tool wrappers |
| `scripts/build_index.py` | PDF ingestion -> FAISS index builder |
| `data/faiss_index/` | Pre-built FAISS index (serialized) |
| `data/pdfs/` | Source Amazon financial PDFs |
| `terraform/main.tf` | Root module wiring aws-ia/agentcore module |
| `terraform/variables.tf` | Input variables (region, model IDs, etc.) |
| `terraform/outputs.tf` | Output values (endpoint URL, Cognito IDs) |
| `terraform/cognito.tf` | Cognito user pool + app client |
| `terraform/providers.tf` | AWS + AWSCC provider config |
| `terraform/iam.tf` | IAM roles and policies |
| `terraform/ecr.tf` | ECR repository for Docker image |
| `notebooks/demo.ipynb` | Demonstration notebook (local + deployed modes) |
| `notebooks/images/` | Langfuse trace screenshots for notebook display |
| `tests/conftest.py` | Shared test fixtures, pytest config |
| `tests/integration/test_tools.py` | yfinance tool integration tests |
| `tests/integration/test_retriever.py` | FAISS retrieval quality tests |
| `tests/integration/test_api.py` | API schema and health check tests |
| `tests/e2e/conftest.py` | E2E fixtures: health gate, SSE helper, client |
| `tests/e2e/test_acceptance.py` | 5 UAC query acceptance tests via SSE |
| `tests/e2e/test_streaming.py` | SSE format and streaming behavior tests |
| `tests/e2e/test_memory.py` | Multi-turn conversation memory tests |
| `tests/e2e/test_llm_eval.py` | LLM-as-judge evaluation of answer quality |
| `README.md` | Project documentation |

### To Be Modified

| File | Changes |
| --- | --- |
| `CLAUDE.md` | Update commands and architecture sections for this project |
| `.gitignore` | Add `data/pdfs/`, `.env`, `terraform/.terraform/`, etc. |

### To Be Deleted

| File | Reason |
| --- | --- |
| (none) | Greenfield project; terraform/ was already cleaned up |

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| AgentCore ARM64 requirement breaks local dev | Medium | Medium | Develop and test locally with standard x86; ARM64 only needed for Docker build and deployment. Use `--platform linux/arm64` in Docker build. |
| FAISS cold start on container startup | Low | Low | Pre-build and serialize FAISS index at build time. Loading a serialized index is <1 second. |
| AgentCore Gateway does not support SSE passthrough | Low | High | AgentCore docs explicitly support SSE on `/invocations`. Verify early in Phase 4. Fallback: return full JSON response if SSE fails through gateway. |
| Bedrock model access not enabled in AWS account | Medium | High | Verify model access in Bedrock console before starting. Request access to Claude Sonnet + Titan Embeddings early. |
| `AgentCoreMemorySaver` requires specific IAM permissions | Medium | Medium | Terraform creates IAM role with `bedrock-agentcore:CreateEvent`, `ListEvents`, `RetrieveMemories` permissions. Test early. |
| Langfuse callback handler misses traces in streaming mode | Low | Medium | Langfuse `CallbackHandler` is passed via `config={"callbacks": [...]}` on `.astream()`. Verified in Langfuse docs for LangGraph. |
| yfinance rate limiting on rapid queries | Low | Low | yfinance is free and unthrottled for basic price queries. Only 2 tools, and the notebook runs queries sequentially. |
| Terraform `aws` provider AgentCore resources are new (v6.17+, Oct 2025) | Low | Medium | Use `aws-ia/agentcore/aws` module (v1.0.0, Feb 2026) which abstracts resource creation and handles edge cases. Pin provider version >= 6.17.0. |
| PDF document quality affects RAG answers | Medium | Medium | Use `RecursiveCharacterTextSplitter` with appropriate chunk size (1000 chars, 200 overlap). Test retrieval quality for the 5 specific queries during Phase 2. |

---

## 11. Assumptions & Constraints

### Assumptions

- AWS account has Bedrock model access enabled for Claude Sonnet and Titan Embeddings in the target region
- AgentCore Runtime is available in the target AWS region (us-east-1 recommended)
- Langfuse Cloud free tier is sufficient for the demo (limited traces/month)
- The 3 Amazon PDF documents are publicly accessible and can be downloaded at build time
- `AgentCoreMemorySaver` works with the HTTP protocol contract (not just the SDK `@app.entrypoint` pattern)
- The evaluator team has AWS credentials (via SSO, IAM user, or environment variables) to run `terraform apply` and the notebook
- AWS SSO is the primary auth method for local development (`aws sso login --profile <profile>`)

### Constraints

- Container must be ARM64 (AgentCore runs on Graviton)
- Container must listen on port `0.0.0.0:8080`
- Must implement `POST /invocations` and `GET /ping` per AgentCore HTTP protocol contract
- Python 3.12+ (AgentCore SDK requirement)
- Must use LangGraph for agent orchestration (assignment requirement)
- Must use yfinance for stock data (assignment requirement)
- Must use Cognito for auth (assignment requirement)
- Must use Langfuse for observability (assignment requirement)
- Must use Terraform for IaC (assignment requirement)

---

## 12. Open Issues

| # | Question | Status |
| --- | --- | --- |
| 1 | Can FastAPI replace `BedrockAgentCoreApp` for the `/invocations` endpoint, or must we use the SDK's Starlette wrapper? | **Resolved -- Pure FastAPI.** The assignment says "Agentcore runtime hosted via FastAPI." AgentCore docs confirm implementing `/invocations` POST + `/ping` GET directly is a valid alternative to `@app.entrypoint`. No SDK dependency needed. |
| 2 | Does the AgentCore Gateway pass SSE streams through without buffering? | **Verify in Phase 5.** SSE is non-negotiable. If the gateway buffers SSE, fallback: expose the Runtime Endpoint directly or use an AWS API Gateway HTTP API (known SSE support) instead. |
| 3 | What is the exact `memory_id` format for `AgentCoreMemorySaver`? Is it the ARN of the AgentCore Memory resource? | TBD -- resolve during Phase 2 implementation. Likely the Memory resource ARN from Terraform output. |
| 4 | Does the `aws-ia/agentcore/aws` Terraform module support Gateway creation with Cognito JWT auth? | TBD -- resolve during Phase 4. Fall back to raw `aws_bedrockagentcore_gateway` resource if needed. |
| 5 | Which AWS region has both AgentCore and Bedrock Claude Sonnet available? | TBD -- verify before Phase 4. Likely `us-east-1`. |
| 6 | ~~Can we use `bedrock-agentcore-sdk-python` alongside FastAPI?~~ | **Resolved -- Not applicable.** Using pure FastAPI (see #1). SDK is not a dependency. |

---

## 13. Research Sources

- [AgentCore HTTP Protocol Contract](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-http-protocol-contract.html) -- endpoint requirements, SSE format, container specs
- [AgentCore Runtime Direct Code Deployment](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy.html) -- deployment options, entrypoint patterns
- [Integrate AgentCore Memory with LangGraph](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-integrate-lang.html) -- `AgentCoreMemorySaver` setup, `actor_id` + `thread_id` config
- [AgentCore Gateway Inbound Auth](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-inbound-auth.html) -- Cognito JWT authorizer configuration
- [aws-ia/agentcore/aws Terraform Module](https://registry.terraform.io/modules/aws-ia/agentcore/aws/latest) -- v1.0.0, Runtime + Endpoint + Memory + Gateway resources
- [aws_bedrockagentcore_agent_runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime) -- `aws` provider resource reference (v6.17+)
- [bedrock-agentcore-sdk-python](https://github.com/aws/bedrock-agentcore-sdk-python) -- `BedrockAgentCoreApp`, `@app.entrypoint`, v1.4.8
- [LangGraph Streaming -- Filter by LLM Invocation](https://langchain-ai.github.io/langgraph/how-tos/streaming/#filter-by-llm-invocation) -- `.astream()` configuration
- [Langfuse LangGraph Integration](https://langfuse.com/docs/integrations/langchain/example-python-langgraph) -- `CallbackHandler` usage with LangGraph
- [Langfuse LangChain Tracing](https://langfuse.com/docs/integrations/langchain/tracing) -- env var setup, callback configuration
- [FAISS LangChain Integration](https://docs.langchain.com/oss/python/integrations/vectorstores/faiss) -- `FAISS.from_documents()`, `FAISS.load_local()`
- [AWS Vector Database Comparison](https://docs.aws.amazon.com/prescriptive-guidance/latest/choosing-an-aws-vector-database-for-rag-use-cases/vector-db-comparison.html) -- FAISS vs managed options trade-offs
### Knowledge Base Documents

These are the source PDFs for the FAISS RAG index (not research sources):

- [Amazon 2024 Annual Report (PDF)](https://s2.q4cdn.com/299287126/files/doc_financials/2025/ar/Amazon-2024-Annual-Report.pdf)
- [AMZN Q3 2025 Earnings Release (PDF)](https://s2.q4cdn.com/299287126/files/doc_financials/2025/q3/AMZN-Q3-2025-Earnings-Release.pdf)
- [AMZN Q2 2025 Earnings Release (PDF)](https://s2.q4cdn.com/299287126/files/doc_financials/2025/q2/AMZN-Q2-2025-Earnings-Release.pdf)
