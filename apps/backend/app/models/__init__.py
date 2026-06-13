"""SQLAlchemy models.

هر model در فایل جدا برای ماژولاریتی.

برای اضافه کردن model جدید:
1. یه فایل جدید بساز
2. model رو تعریف کن
3. importش کن اینجا
4. اجرا: alembic revision --autogenerate -m "add model"
"""
from app.models.agent import Agent, LLMProvider
from app.models.conversation import Conversation, Message, MessageRole
from app.models.file import File, StorageBackend
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.models.workflow import Workflow
from app.models.workspace import Workspace

__all__ = [
    # User
    "User",
    "UserRole",
    # Workspace
    "Workspace",
    # Agent
    "Agent",
    "LLMProvider",
    # Workflow
    "Workflow",
    # Conversation
    "Conversation",
    "Message",
    "MessageRole",
    # File
    "File",
    "StorageBackend",
    # Task
    "Task",
    "TaskStatus",
]
