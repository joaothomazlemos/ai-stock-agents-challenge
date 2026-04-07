from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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


class InvocationResponse(BaseModel):
    """JSON response returned when stream=false."""

    response: str = Field(description="The agent's full response text")
    thread_id: str = Field(description="The conversation thread ID used for this invocation")


class PingResponse(BaseModel):
    """Health check response for GET /ping."""

    status: Literal["Healthy"] = Field(default="Healthy", description="Runtime health status")
