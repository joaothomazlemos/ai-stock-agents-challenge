"""LLM-as-judge evaluation tests for agent response quality.

Requires a running server AND AWS Bedrock access for the judge model.
"""

from __future__ import annotations

import os
import re

import pytest

from tests.e2e.conftest import collect_sse_events, extract_full_text

pytestmark = pytest.mark.llm

JUDGE_PROMPT_TEMPLATE = """\
You are an expert evaluator for an AI financial assistant. Rate the assistant's \
response to the given query on three dimensions: relevance, accuracy, and completeness.

## Query
{query}

## Assistant Response
{response}

## Instructions
- Relevance: Does the response address the query directly?
- Accuracy: Are the facts, figures, and data points correct or plausible?
- Completeness: Does the response fully answer the question?

Return your evaluation as JSON with this exact structure:
{{"score": <integer 1-10>, "reasoning": "<one paragraph>"}}

Return ONLY the JSON object, no other text.
"""

UAC_QUERIES = [
    {
        "query": "What is the stock price for Amazon right now?",
        "check": lambda text: any(t in text.lower() for t in ("amzn", "price", "$", "amazon")),
    },
    {
        "query": "What were Amazon's stock prices between October and December 2025?",
        "check": lambda text: any(t in text.lower() for t in ("price", "2025", "$", "stock")),
    },
    {
        "query": (
            "What is the total amount of office space "
            "Amazon owned in North America in 2024?"
        ),
        "check": lambda text: len(text) > 20,
    },
    {
        "query": "What was Amazon's net income in Q2 2025?",
        "check": lambda text: len(text) > 20,
    },
    {
        "query": "What were Amazon's AWS revenue numbers in Q3 2025?",
        "check": lambda text: len(text) > 20,
    },
]


def _get_judge_llm():
    """Create a ChatBedrock instance for the LLM judge."""
    try:
        from langchain_aws import ChatBedrock

        model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514")
        region = os.environ.get("AWS_REGION", "us-east-1")
        return ChatBedrock(
            model_id=model_id,
            region_name=region,
            model_kwargs={"temperature": 0.0, "max_tokens": 1024},
        )
    except Exception as exc:
        pytest.skip(f"Bedrock LLM not available for judge: {exc}")


def _parse_judge_score(judge_response: str) -> int:
    """Extract the integer score from the judge's JSON response."""
    match = re.search(r'"score"\s*:\s*(\d+)', judge_response)
    if match:
        return int(match.group(1))
    raise ValueError(f"Could not parse score from judge response: {judge_response[:200]}")


@pytest.mark.parametrize(
    "uac",
    UAC_QUERIES,
    ids=[f"uac_{i+1}" for i in range(len(UAC_QUERIES))],
)
async def test_agent_response_quality(e2e_client, uac):
    query = uac["query"]

    events = await collect_sse_events(
        e2e_client,
        "/invocations",
        json_body={"prompt": query},
        timeout=120,
    )
    response_text = extract_full_text(events)

    assert uac["check"](response_text), (
        f"Basic sanity check failed for query: {query}\nResponse: {response_text[:300]}"
    )

    judge = _get_judge_llm()
    judge_prompt = JUDGE_PROMPT_TEMPLATE.format(query=query, response=response_text)
    judge_result = await judge.ainvoke(judge_prompt)
    score = _parse_judge_score(judge_result.content)

    assert score >= 7, (
        f"LLM judge scored {score}/10 for query: {query}\n"
        f"Judge reasoning: {judge_result.content[:500]}"
    )
