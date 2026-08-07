"""
Lumora Dev Multi-Agent Collaboration (v3 Phase 3B)

Coordinated team of specialized agents sharing Memory, Knowledge,
Planner, Vision, Browser, Execution, and Git/Terminal tools.
"""

from .agent_manager import AgentManager, get_agent_manager, AgentRole
from .coordinator import Coordinator
from .dispatcher import Dispatcher
from .shared_context import SharedContext
from .messaging import MessageBus
from .task_queue import TaskQueue, Task, TaskStatus

__all__ = [
    "AgentManager",
    "get_agent_manager",
    "AgentRole",
    "Coordinator",
    "Dispatcher",
    "SharedContext",
    "MessageBus",
    "TaskQueue",
    "Task",
    "TaskStatus",
]
