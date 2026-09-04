"""Business logic services (ماژولار و مستقل).

هر service یه ماژول مستقل با interface واضح.
مثال: auth, agents, workflows, files, storage.
"""
from app.services.agents import register_builtin_tools
from app.services.browser_service import browser_service  # ← Agent Browser service

# Auto-register built-in tools on import
register_builtin_tools()
