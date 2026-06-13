"""Database init script.

استفاده:
    # ساخت همه جداول (برای dev)
    python -m scripts.init_db create

    # ساخت superuser
    python -m scripts.init_db createsuperuser
"""
import asyncio
import sys
import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.db import AsyncSessionLocal, Base, engine
from app.models import User, UserRole


async def create_tables() -> None:
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ همه جداول ساخته شدن")


async def create_superuser() -> None:
    """Create a default superuser."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        if result.scalar_one_or_none():
            print("⚠️  superuser 'admin' از قبل وجود داره")
            return

        admin = User(
            id=uuid.uuid4(),
            email="admin@magoco.dev",
            username="admin",
            full_name="Administrator",
            password_hash=hash_password("admin12345"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        session.add(admin)
        await session.commit()
        print("✅ superuser ساخته شد:")
        print("   username: admin")
        print("   password: admin12345")
        print("   ⚠️  حتماً بعدش password رو عوض کن!")


async def main() -> None:
    if len(sys.argv) < 2:
        print("استفاده: python -m scripts.init_db [create|createsuperuser]")
        return

    command = sys.argv[1]
    if command == "create":
        await create_tables()
    elif command == "createsuperuser":
        await create_superuser()
    else:
        print(f"❌ command ناشناس: {command}")


if __name__ == "__main__":
    asyncio.run(main())
