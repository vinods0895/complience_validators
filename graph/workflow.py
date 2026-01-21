from langgraph.graph import StateGraph, END
from functools import partial

from graph.state import ComplianceState
from graph.nodes import (
    extract_node,
    validate_node,
    stateful_node,
    resolver_node,
    human_review_node,
    report_node,
    route_decision,
)


def build_compliance_graph(
    extractor,
    validator,
    stateful_engine,
    resolver,
    reporter,
    human_review_store,
):
    graph = StateGraph(ComplianceState)

    # Bind dependencies explicitly (NO lambdas)
    graph.add_node("extract", partial(extract_node, extractor=extractor))
    graph.add_node("validate", partial(validate_node, validator=validator))
    graph.add_node("stateful", partial(stateful_node, stateful_engine=stateful_engine))
    graph.add_node("resolve", partial(resolver_node, resolver=resolver))
    graph.add_node(
        "human_review",
        partial(human_review_node, store=human_review_store),
    )
    graph.add_node("report", partial(report_node, reporter=reporter))

    graph.set_entry_point("extract")

    graph.add_edge("extract", "validate")
    graph.add_edge("validate", "stateful")
    graph.add_edge("stateful", "resolve")

    graph.add_conditional_edges(
        "resolve",
        route_decision,
        {
            "human_review": "human_review",
            "clarification": "report",
            "auto_approve": "report",
        },
    )

    graph.add_edge("human_review", END)
    graph.add_edge("report", END)

    return graph.compile()
