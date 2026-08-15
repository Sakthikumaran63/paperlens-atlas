"""
Job Queue Abstraction
---------------------
Provides a lightweight async task queue interface for background pipeline execution.
"""
import asyncio
import logging
from typing import Callable, Coroutine

logger = logging.getLogger("paperlens")


class AsyncJobQueue:
    """Lightweight in-memory async job queue."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    def enqueue(self, task_func: Callable[..., Coroutine], *args, **kwargs) -> None:
        asyncio.create_task(task_func(*args, **kwargs))
        logger.info("Enqueued background job: %s", getattr(task_func, "__name__", str(task_func)))
