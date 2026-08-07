"""
Execution Engine hooks (Phase 2B/2C/3A).
"""

from .ui_loop import VisionAwareValidator, run_ui_validation_step, knowledge_context_for_goal

__all__ = ["VisionAwareValidator", "run_ui_validation_step", "knowledge_context_for_goal"]
