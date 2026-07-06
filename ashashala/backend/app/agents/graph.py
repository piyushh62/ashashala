"""LangGraph wiring for the agent pipeline (Section 7).

    safety_in -> orchestrator -> {tutor | quiz_master | evaluator}
              -> safety_out -> progress -> END

This is the ONLY module that imports langgraph. Agents themselves are plain
async functions with no langgraph dependency, so routes can call them directly
and tests don't need the graph. `build_agent_graph()` composes them into a
StateGraph over SessionState; it degrades gracefully if langgraph isn't
installed (returns None), which keeps the rest of the app importable.

The graph operates on the read-only classification/orchestration parts of the
turn. Side-effecting work (persisting quizzes, grading attempts, writing
mastery) is done by the route handlers calling the same agent functions with a
DB session — the graph decides WHAT should happen; the routes execute it
transactionally. This keeps DB writes out of graph nodes (Separation of
Concerns) while still satisfying the spec's orchestration shape.
"""

from __future__ import annotations

import logging

from app.agents.orchestrator import classify_intent
from app.agents.safety import gemini_safety_check
from app.agents.state import SessionState, new_state
from app.services.lang_detect import detect_lang

logger = logging.getLogger(__name__)


async def _safety_in(state: SessionState) -> SessionState:
    """Harmful-content guard before any work. Sets safety_blocked instead of
    raising so the graph can short-circuit cleanly.

    Subject-relevance is deliberately NOT checked here — this node only sees the
    subject_id (a UUID), not the subject name. The nuanced "is this on-topic?"
    check lives in the tutor's safety_wrapper, which has the real subject name.
    """
    try:
        safe, reason = await gemini_safety_check(state["message"])
    except Exception as e:  # noqa: BLE001
        logger.warning("safety_in check failed, allowing: %s", e)
        safe, reason = True, None
    if not safe:
        state["safety_blocked"] = True
        state["safety_reason"] = reason or "harmful_content"
    return state


async def _orchestrate(state: SessionState) -> SessionState:
    if state.get("safety_blocked"):
        return state
    state["intent"] = await classify_intent(
        state["message"], school_id=state.get("school_id"),
        lang_hint=state.get("lang_detected", "en"),
    )
    return state


async def _safety_out(state: SessionState) -> SessionState:
    """Post-agent hook (Gemini's built-in filtering already ran on generation).
    Reserved for the deferred NVIDIA jailbreak classifier."""
    return state


def _route_after_orchestrator(state: SessionState) -> str:
    if state.get("safety_blocked"):
        return "safety_out"
    return state.get("intent", "explain")


def build_agent_graph():
    """Compile the LangGraph StateGraph, or return None if langgraph is absent."""
    try:
        from langgraph.graph import END, StateGraph
    except Exception as e:  # noqa: BLE001
        logger.warning("langgraph unavailable, graph disabled: %s", e)
        return None

    # Terminal passthrough nodes for the branch targets. The actual Tutor/Quiz/
    # Evaluator side effects run in the routes; here they mark the decided path.
    async def _mark(intent: str):
        async def _node(state: SessionState) -> SessionState:
            state["intent"] = intent
            return state
        return _node

    # Node names must not collide with SessionState keys (langgraph rule), so the
    # branch nodes are named for their agents (quiz_master/evaluator/progress_node)
    # rather than the intent words (quiz/grade/progress).
    graph = StateGraph(SessionState)
    graph.add_node("safety_in", _safety_in)
    graph.add_node("orchestrator", _orchestrate)
    graph.add_node("tutor", lambda s: s)
    graph.add_node("quiz_master", lambda s: s)
    graph.add_node("evaluator", lambda s: s)
    graph.add_node("progress_node", lambda s: s)
    graph.add_node("safety_out", _safety_out)

    graph.set_entry_point("safety_in")
    graph.add_edge("safety_in", "orchestrator")
    graph.add_conditional_edges(
        "orchestrator", _route_after_orchestrator,
        {"explain": "tutor", "quiz": "quiz_master", "grade": "evaluator",
         "progress": "progress_node", "safety_out": "safety_out"},
    )
    for node in ("tutor", "quiz_master", "evaluator", "progress_node"):
        graph.add_edge(node, "safety_out")
    graph.add_edge("safety_out", END)
    return graph.compile()


# Lazily-built singleton (None if langgraph missing).
_compiled = None


def get_agent_graph():
    global _compiled
    if _compiled is None:
        _compiled = build_agent_graph()
    return _compiled


async def run_orchestration(
    *,
    message: str,
    school_id: str,
    student_id: str,
    class_id: str,
    subject_id: str | None = None,
    input_mode: str = "text",
) -> SessionState:
    """Run the safety_in → orchestrator part of the graph for one turn.

    Executes the compiled LangGraph when langgraph is installed; otherwise runs
    the same nodes directly so orchestration behaves identically without the
    dependency. Returns the resolved SessionState (intent + safety flags), which
    the route then acts on (streams the tutor answer, starts a quiz, etc.).
    """
    state = new_state(
        student_id=student_id, school_id=school_id, class_id=class_id,
        message=message, subject_id=subject_id, input_mode=input_mode,  # type: ignore[arg-type]
    )
    state["lang_detected"] = detect_lang(message)

    graph = get_agent_graph()
    if graph is not None:
        try:
            result = await graph.ainvoke(state)
            return result  # type: ignore[return-value]
        except Exception as e:  # noqa: BLE001 — never let orchestration break the turn
            logger.warning("Graph invoke failed, running nodes directly: %s", e)

    state = await _safety_in(state)
    state = await _orchestrate(state)
    return state
