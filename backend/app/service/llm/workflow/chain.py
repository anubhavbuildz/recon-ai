"""LangChain workflow: configured S3 context, base model invocation, response."""

import json
import logging
from time import perf_counter
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableLambda

from app.api.schemas import ChatResponse, ReconResponse
from app.core.config import get_settings
from app.service.agent.recon_agent import run_recon_agent
from app.service.llm.base import LLMClient, ModelError
from app.service.llm.role import load_system_prompt
from app.service.tools.call_s3 import create_call_s3_tool

logger = logging.getLogger(__name__)


async def run_workflow(target: str) -> ReconResponse:
    # Preserve the existing reconnaissance contract separately from cloud chat.
    return await RunnableLambda(run_recon_agent).ainvoke(target)


async def run_chat_workflow(question: str) -> ChatResponse:
    run_id = uuid4().hex[:12]
    started = perf_counter()
    logger.info("Chat workflow started run_id=%s", run_id)
    settings = get_settings()
    if not settings.s3_bucket_name or not (
        settings.s3_object_key or settings.s3_snapshot_prefix
    ):
        logger.warning("Chat configuration missing run_id=%s", run_id)
        raise ValueError(
            "Configure S3_BUCKET_NAME and S3_OBJECT_KEY or S3_SNAPSHOT_PREFIX"
        )
    try:
        client = LLMClient(settings)
    except Exception as exc:
        logger.error(
            "Model initialization failed run_id=%s error_type=%s",
            run_id,
            type(exc).__name__,
        )
        raise
    try:
        sources = []
        system_prompt = load_system_prompt()
        s3_tool = create_call_s3_tool(settings)
        tools_by_name = {s3_tool.name: s3_tool}
        model_with_tools = client.bind_tools([s3_tool], tool_choice="auto")
        # Some providers support only auto; validate calls and bound execution locally.
        final_model = model_with_tools

        async def answer(value: str) -> str:
            user_message = HumanMessage(content=value)
            messages = [SystemMessage(content=system_prompt), user_message]
            logger.info("Requesting model tool call run_id=%s", run_id)
            ai_response = await model_with_tools.ainvoke(messages)
            if ai_response.invalid_tool_calls or len(ai_response.tool_calls) != 1:
                raise ModelError("Model did not request a valid S3 tool call")
            messages.append(ai_response)

            for tool_call in ai_response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                if tool_name not in tools_by_name or tool_args != {} or not tool_id:
                    raise ModelError("Model supplied an unsupported tool call")
                logger.info("Executing tool=%s run_id=%s", tool_name, run_id)
                tool_output = await tools_by_name[tool_name].ainvoke(tool_args)
                if settings.s3_snapshot_prefix:
                    sources.extend(
                        item["source"] for item in json.loads(tool_output)["snapshots"]
                    )
                messages.append(
                    ToolMessage(content=str(tool_output), tool_call_id=tool_id)
                )
                logger.info("S3 tool completed run_id=%s", run_id)

            logger.info("Requesting final model answer run_id=%s", run_id)
            final_response = await final_model.ainvoke(messages)
            if (
                final_response.tool_calls
                or final_response.invalid_tool_calls
                or not isinstance(final_response.content, str)
                or not final_response.content.strip()
            ):
                raise ModelError("Model returned no final answer")
            return final_response.content

        message = await RunnableLambda(answer).ainvoke(question)
        logger.info(
            "Chat workflow completed run_id=%s duration_ms=%.1f",
            run_id,
            (perf_counter() - started) * 1000,
        )
        return ChatResponse(
            message=message,
            source=sources[0]
            if sources
            else f"s3://{settings.s3_bucket_name}/{settings.s3_object_key}",
            sources=sources,
        )
    except Exception as exc:
        logger.error(
            "Chat workflow failed run_id=%s error_type=%s reason=%s duration_ms=%.1f",
            run_id,
            type(exc).__name__,
            str(exc) if isinstance(exc, ModelError) else "upstream operation failed",
            (perf_counter() - started) * 1000,
        )
        raise
    finally:
        await client.close()
