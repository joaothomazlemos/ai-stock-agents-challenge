# AI Stock Agent on AWS Bedrock AgentCore

A LangGraph ReAct agent deployed on AWS Bedrock AgentCore that answers real-time and historical stock price queries via SSE streaming. The agent exposes two yfinance tools and a FAISS-backed RAG tool over Amazon financial documents. Authentication flows through Cognito JWT via the AgentCore Gateway, observability through Langfuse Cloud, and infrastructure is provisioned with Terraform.

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                            AWS Cloud                                 │
│                                                                      │
│  ┌────────────┐    ┌───────────────────────┐    ┌──────────────┐    │
│  │ Cognito    │◄───│ AgentCore Gateway     │    │ Terraform    │    │
│  │ User Pool  │    │ CUSTOM_JWT authorizer │    │ (provisions  │    │
│  └────────────┘    └───────────┬───────────┘    │  everything) │    │
│                                │                 └──────────────┘    │
│                         Proxy to Runtime                             │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │           AgentCore Runtime (ARM64 container)                  │  │
│  │                                                                │  │
│  │  FastAPI (port 8080)                                           │  │
│  │  POST /invocations  →  LangGraph ReAct Agent  →  SSE stream   │  │
│  │  GET  /ping         →  {"status": "Healthy"}                   │  │
│  │                                                                │  │
│  │  Tools:                                                        │  │
│  │  ├── retrieve_realtime_stock_price   (yfinance)                │  │
│  │  ├── retrieve_historical_stock_price (yfinance)                │  │
│  │  └── retrieve_documents              (FAISS RAG)               │  │
│  │                                                                │  │
│  │  Memory: AgentCoreMemorySaver (multi-turn conversations)       │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                         │                                            │
│                   Langfuse callbacks                                 │
│                         ▼                                            │
│                ┌─────────────────┐                                   │
│                │ Langfuse Cloud  │                                   │
│                └─────────────────┘                                   │
└──────────────────────────────────────────────────────────────────────┘

Client: Jupyter Notebook
  1. boto3 InitiateAuth → Cognito JWT
  2. POST /invocations via Gateway with Bearer JWT
  3. Receive SSE stream
```

---

## Prerequisites

| Tool | Version | Purpose |
| --- | --- | --- |
| Python | >= 3.12 | Runtime |
| [UV](https://docs.astral.sh/uv/) | >= 0.7 | Package manager |
| [Terraform](https://www.terraform.io/) | >= 1.14 | Infrastructure provisioning |
| [Docker](https://www.docker.com/) | Latest | Container build (ARM64 support required) |
| AWS CLI | v2 | Authentication + ECR login |
| AWS Account | — | Bedrock model access enabled for Claude Sonnet + Titan Embeddings |

### AWS Model Access

Before deploying, ensure the following Bedrock models are enabled in your AWS account (region `us-east-1`):

- **Claude Sonnet** (`anthropic.claude-sonnet-4-20250514`) — Chat LLM
- **Titan Embeddings V2** (`amazon.titan-embed-text-v2:0`) — Document embeddings

Enable them in the [Bedrock Model Access console](https://console.aws.amazon.com/bedrock/home#/modelaccess).

---

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url>
cd ai-stock-agents-challenge
make install

# 2. Configure environment
cp .env.example .env
# Edit .env with your AWS region, Langfuse keys, etc.

# 3. Build the FAISS index (requires AWS credentials for Titan embeddings)
make build-index

# 4. Run locally
make dev-api
# Server at http://localhost:8080

# 5. Test
curl http://localhost:8080/ping
curl -N -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the stock price for Amazon right now?"}'
```

---

## Deployment

### Step 1: Bootstrap Terraform State (first time only)

```bash
# Creates the S3 bucket for Terraform remote state
bash terraform/bootstrap.sh
```

### Step 2: Initialize and Deploy Infrastructure

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

This provisions: Cognito User Pool, ECR Repository, IAM Roles, AgentCore Runtime, Endpoint, Memory, and Gateway.

Save the outputs — you'll need them for Docker push and the notebook:

```bash
terraform output
```

### Step 3: Build and Push Docker Image

```bash
# Build ARM64 image
make build

# Authenticate with ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $(terraform -chdir=terraform output -raw ecr_repository_url | cut -d/ -f1)

# Push to ECR
ECR_REPO=$(terraform -chdir=terraform output -raw ecr_repository_url) make push
```

### Step 4: Create a Cognito Test User

```bash
aws cognito-idp admin-create-user \
  --user-pool-id $(terraform -chdir=terraform output -raw cognito_user_pool_id) \
  --username testuser@example.com \
  --temporary-password "TempPass1!" \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id $(terraform -chdir=terraform output -raw cognito_user_pool_id) \
  --username testuser@example.com \
  --password "YourSecurePass1!" \
  --permanent
```

### Step 5: Verify Deployment

```bash
# Health check (via Runtime Endpoint)
curl https://<endpoint>/ping

# Authenticated invocation (via Gateway)
# First get a JWT token, then:
curl -N -X POST https://<gateway-url>/invocations \
  -H "Authorization: Bearer <jwt>" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the stock price for Amazon right now?"}'
```

---

## Running the Demo Notebook

```bash
# Set environment variables (from terraform output)
export GATEWAY_URL=$(terraform -chdir=terraform output -raw gateway_url)
export COGNITO_USER_POOL_ID=$(terraform -chdir=terraform output -raw cognito_user_pool_id)
export COGNITO_CLIENT_ID=$(terraform -chdir=terraform output -raw cognito_client_id)
export COGNITO_USERNAME="testuser@example.com"
export COGNITO_PASSWORD="YourSecurePass1!"

# Optional: Langfuse trace retrieval in the notebook
export LANGFUSE_PUBLIC_KEY="pk-..."
export LANGFUSE_SECRET_KEY="sk-..."

# Launch Jupyter
jupyter notebook notebooks/demo.ipynb
```

The notebook runs all 5 required queries:

1. **Real-time price** — "What is the stock price for Amazon right now?"
2. **Historical prices** — "What were the stock prices for Amazon in Q4 last year?"
3. **Cross-reference** — "Compare Amazon's recent stock performance to what analysts predicted in their reports"
4. **Multi-source** — "I'm researching AMZN -- give me the current price and any relevant information about their AI business"
5. **Document-only** — "What is the total amount of office space Amazon owned in North America in 2024?"

Plus a multi-turn conversation demo and Langfuse trace display.

---

## Makefile Targets

Run these in order for a full deployment workflow:

| Target | Command | Description |
| --- | --- | --- |
| `install` | `make install` | Install Python dependencies (UV) |
| `lint` | `make lint` | Run Ruff linter on `src/` |
| `format` | `make format` | Auto-format with Ruff |
| `test` | `make test` | Run integration tests (no server needed) |
| `build-index` | `make build-index` | Build FAISS index from PDFs |
| `dev-api` | `make dev-api` | Start local dev server (port 8080, hot reload) |
| `build` | `make build` | Build ARM64 Docker image |
| `push` | `make push` | Tag and push image to ECR |
| `apply` | `make apply` | Run `terraform apply` |

---

## Project Structure

```text
src/ai_stock_agent/
├── domain/                     # Pure Python, no framework dependencies
│   ├── entities.py             # StockPrice, DocumentChunk value objects
│   ├── ports/
│   │   ├── inbound.py          # AgentPort use case interface
│   │   └── outbound/           # Adapter interfaces (ILLMProvider, IStockProvider, etc.)
│   └── use_cases/
│       └── invoke_agent.py     # Orchestrates graph invocation + SSE streaming
├── adapters/
│   ├── inbound/
│   │   ├── api.py              # FastAPI routes: POST /invocations, GET /ping
│   │   └── schemas.py          # Pydantic request/response DTOs
│   └── outbound/
│       ├── bedrock_llm.py      # ChatBedrock adapter
│       ├── bedrock_embedder.py # Titan embeddings adapter
│       ├── yfinance_stock.py   # yfinance stock data adapter
│       └── faiss_retriever.py  # FAISS vector retriever adapter
└── infrastructure/
    ├── app.py                  # FastAPI lifespan, DI wiring (composition root)
    ├── config.py               # Pydantic Settings (env-based config)
    ├── graph.py                # LangGraph StateGraph definition
    └── tools.py                # LangGraph @tool wrappers

terraform/                      # IaC: AgentCore, Cognito, ECR, IAM
notebooks/demo.ipynb            # Demonstration notebook (5 queries + auth + traces)
scripts/build_index.py          # FAISS index builder from PDFs
prompts/system.md               # Agent system prompt
tests/
├── integration/                # Tool, retriever, API tests (no server)
└── e2e/                        # Acceptance, streaming, memory, LLM eval tests
```

---

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
| --- | --- | --- |
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock and AgentCore |
| `BEDROCK_MODEL_ID` | `anthropic.claude-sonnet-4-20250514` | Chat LLM model |
| `EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | Embedding model |
| `EMBEDDING_DIMS` | `512` | Embedding dimensions |
| `AGENTCORE_MEMORY_ID` | *(empty)* | AgentCore Memory ARN (empty = in-memory) |
| `LANGFUSE_PUBLIC_KEY` | *(empty)* | Langfuse public key (empty = tracing off) |
| `LANGFUSE_SECRET_KEY` | *(empty)* | Langfuse secret key |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse host URL |
| `FAISS_INDEX_PATH` | `data/faiss_index` | Path to pre-built FAISS index |
| `CHUNK_SIZE` | `1500` | Document chunk size (chars) |
| `CHUNK_OVERLAP` | `300` | Chunk overlap (chars) |
| `RETRIEVER_K` | `5` | Number of chunks to retrieve |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8080` | Server bind port |
| `AGENT_ACTOR_ID` | `ai-stock-agent` | Actor ID for memory checkpointer |

---

## Testing

```bash
# Integration tests (no server, no LLM — runs on every commit)
make test

# E2E acceptance tests (requires running server)
make dev-api  # in one terminal
pytest -m e2e -v  # in another terminal

# LLM evaluation tests (requires running server + Bedrock access)
pytest -m llm -v

# Against deployed endpoint
BASE_URL=https://<gateway-url> pytest -m e2e -v
```

---

## Technology Stack

| Component | Technology |
| --- | --- |
| Agent Framework | LangGraph (ReAct pattern) |
| LLM | Claude Sonnet via AWS Bedrock |
| Embeddings | Titan Embeddings V2 (512d) |
| Vector Store | FAISS (pre-built, in-container) |
| Stock Data | yfinance |
| Memory | AgentCoreMemorySaver |
| API | FastAPI (SSE streaming) |
| Auth | Cognito JWT via AgentCore Gateway |
| Observability | Langfuse Cloud |
| Infrastructure | Terraform (`aws-ia/agentcore/aws` module) |
| Container | Docker ARM64 (Graviton) |
| Package Manager | UV |
| Code Quality | Ruff |

---

## License

This project is part of a take-home assignment and is not licensed for redistribution.
