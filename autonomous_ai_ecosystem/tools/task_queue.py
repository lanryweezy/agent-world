import heapq
import uuid
from dataclasses import dataclass, field
from typing import Any, List, Tuple
from datetime import datetime

@dataclass(order=True)
class Task:
    """Represents a task to be executed by an agent."""
    priority: int
    task_id: str = field(compare=False)
    description: str = field(compare=False)
    payload: Any = field(compare=False)
    status: str = field(default="pending", compare=False) # pending, in_progress, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow, compare=False)
    dependencies: List[str] = field(default_factory=list, compare=False)

class TaskQueue:
    """A priority queue for managing tasks for the AI workforce."""

    def __init__(self):
        self._queue: List[Tuple[int, str, Task]] = []
        self._tasks = {}

    def add_task(self, description: str, payload: Any, priority: int = 10, dependencies: List[str] = None) -> str:
        """Adds a new task to the queue."""
        task_id = str(uuid.uuid4())
        task = Task(
            priority=priority,
            task_id=task_id,
            description=description,
            payload=payload,
            dependencies=dependencies or []
        )
        self._tasks[task_id] = task
        
        # Only add tasks with no dependencies to the queue
        if not task.dependencies:
            heapq.heappush(self._queue, (priority, task.created_at.isoformat(), task))
        
        return task_id

    def get_task(self) -> Task | None:
        """Retrieves the highest priority task from the queue."""
        if not self._queue:
            return None
        
        priority, _, task = heapq.heappop(self._queue)
        task.status = "in_progress"
        return task

    def complete_task(self, task_id: str):
        """Marks a task as completed and unlocks dependent tasks."""
        if task_id in self._tasks:
            self._tasks[task_id].status = "completed"
            self._unlock_dependencies(task_id)
        else:
            raise ValueError(f"Task with id {task_id} not found.")

    def fail_task(self, task_id: str):
        """Marks a task as failed."""
        if task_id in self._tasks:
            self._tasks[task_id].status = "failed"
        else:
            raise ValueError(f"Task with id {task_id} not found.")

    def _unlock_dependencies(self, completed_task_id: str):
        """Checks for tasks that were dependent on the completed task and adds them to the queue."""
        for task_id, task in self._tasks.items():
            if completed_task_id in task.dependencies:
                task.dependencies.remove(completed_task_id)
                if not task.dependencies and task.status == "pending":
                    heapq.heappush(self._queue, (task.priority, task.created_at.isoformat(), task))

    def get_task_status(self, task_id: str) -> str:
        """Returns the status of a specific task."""
        if task_id in self._tasks:
            return self._tasks[task_id].status
        return "not_found"

    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return not self._queue
