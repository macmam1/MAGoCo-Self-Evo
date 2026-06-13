"""SQLAlchemy models.

برای اضافه کردن model جدید:
1. یه فایل جدید بساز (مثلاً user.py)
2. model رو تعریف کن
3. importش کن اینجا
4. اجرا: alembic revision --autogenerate -m "add user model"
"""
from app.models.user import User, UserRole

__all__ = ["User", "UserRole"]
