"""Feature flags — modularity-friendly toggles."""
from app.core.config import settings


def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled.

    فعلاً ساده — فقط env vars. در آینده میتونه از DB/Redis خونده بشه.
    """
    env_key = f"FEATURE_{feature.upper()}"
    # اگه env var ست شده باشه، از اون می‌خونیم
    return getattr(settings, env_key, True)
