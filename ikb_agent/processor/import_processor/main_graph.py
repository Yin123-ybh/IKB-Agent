"""Import graph entrypoint.

This module mirrors the original course project path:
`knowledge/processor/import_processor/main_graph.py`.
The concrete implementation lives in `ikb_agent.pipeline.import_pipeline`.
"""

from ...pipeline.import_pipeline import build_import_graph, run_import

__all__ = ["build_import_graph", "run_import"]

