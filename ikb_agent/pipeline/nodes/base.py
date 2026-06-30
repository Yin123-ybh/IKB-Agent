from __future__ import annotations

from ..state import ImportState
from ...settings import Settings


class BasePipelineNode:
    """Common callable wrapper for LangGraph import nodes."""

    name = "base_node"

    def __init__(self, settings: Settings):
        self.settings = settings

    def __call__(self, state: ImportState) -> ImportState:
        trace = list(state.get("trace", []))
        trace.append(self.name)
        state["trace"] = trace
        return self.process(state)

    def process(self, state: ImportState) -> ImportState:
        raise NotImplementedError

