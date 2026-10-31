"""Minimal LangGraph with one placeholder agent node."""
from typing import NotRequired, TypedDict

from langgraph.graph import END, START, StateGraph

from app.api.schemas import ReconResponse
from app.service.agent.recon_agent import run_recon_agent


class ReconState(TypedDict):
    target: str
    result: NotRequired[ReconResponse]


async def recon_node(state: ReconState) -> dict[str, ReconResponse]:
    return {"result": await run_recon_agent(state["target"])}


builder = StateGraph(ReconState)
builder.add_node("recon", recon_node)
builder.add_edge(START, "recon")
builder.add_edge("recon", END)
workflow = builder.compile()


async def run_workflow(target: str) -> ReconResponse:
    state = await workflow.ainvoke({"target": target})
    return ReconResponse.model_validate(state["result"])
