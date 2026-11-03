"""Reusable LangChain chat model with tool binding."""

import logging
from time import perf_counter

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from openai import APIError, APITimeoutError

from app.core.config import Settings

logger = logging.getLogger(__name__)


class ModelError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, settings: Settings):
        if not settings.llm_api_key or not settings.llm_model:
            raise ModelError(
                "Configure LLM_API_KEY and LLM_MODEL before invoking a model"
            )
        self.http_client = httpx.Client()
        self.async_http_client = httpx.AsyncClient()
        self.model = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
            temperature=0.4,
            http_client=self.http_client,
            http_async_client=self.async_http_client,
        )

    def bind_tools(self, tools, **options):
        """Bind LangChain tools and return an async runnable with safe logging."""
        bound_model = self.model.bind_tools(tools, **options)

        async def invoke(messages):
            started = perf_counter()
            logger.info("Model request started messages=%d", len(messages))
            try:
                response = await bound_model.ainvoke(messages)
                logger.info(
                    "Model request completed tool_calls=%d duration_ms=%.1f",
                    len(response.tool_calls),
                    (perf_counter() - started) * 1000,
                )
                return response
            except APITimeoutError as exc:
                logger.warning("Model request timed out")
                raise ModelError("Model request timed out") from exc
            except APIError as exc:
                logger.error("Model request failed error_type=%s", type(exc).__name__)
                raise ModelError("Model request failed") from exc

        return RunnableLambda(invoke)

    async def invoke(self, prompt: str, system_prompt: str | None = None) -> str:
        messages = ([SystemMessage(content=system_prompt)] if system_prompt else []) + [
            HumanMessage(content=prompt)
        ]
        response = await self.bind_tools([], tool_choice="auto").ainvoke(messages)
        if not isinstance(response.content, str) or not response.content.strip():
            raise ModelError("Model returned an empty response")
        return response.content

    async def close(self) -> None:
        try:
            await self.async_http_client.aclose()
        finally:
            self.http_client.close()
