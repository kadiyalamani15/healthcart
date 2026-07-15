"""
LangGraph pipeline for HealthCart.

Graph topology:
  profile_analyzer → constraint_extractor → product_recommender
                   → compliance_validator → list_formatter → END

run_agent() is the public entry point. It is decorated with @observe() to
create the root Langfuse trace; each node's @observe() creates a child span.
"""

from langgraph.graph import StateGraph, END
from langfuse import observe

from agent.state import AgentState
from agent.nodes import (
    profile_analyzer_node,
    constraint_extractor_node,
    product_recommender_node,
    compliance_validator_node,
    list_formatter_node,
)


def _build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("profile_analyzer", profile_analyzer_node)
    workflow.add_node("constraint_extractor", constraint_extractor_node)
    workflow.add_node("product_recommender", product_recommender_node)
    workflow.add_node("compliance_validator", compliance_validator_node)
    workflow.add_node("list_formatter", list_formatter_node)

    workflow.set_entry_point("profile_analyzer")
    workflow.add_edge("profile_analyzer", "constraint_extractor")
    workflow.add_edge("constraint_extractor", "product_recommender")
    workflow.add_edge("product_recommender", "compliance_validator")
    workflow.add_edge("compliance_validator", "list_formatter")
    workflow.add_edge("list_formatter", END)

    return workflow.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


@observe(name="healthcart_agent")
def run_agent(health_profile: dict) -> dict:
    """
    Run the full HealthCart pipeline for a given health profile.
    Returns the final AgentState dict.

    This function is the root Langfuse trace. All node @observe() calls
    create child spans within it.
    """
    graph = get_graph()
    result = graph.invoke({"health_profile": health_profile})
    return result
