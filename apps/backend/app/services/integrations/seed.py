"""Seed integrations registry from CONNECTOR_TEMPLATES + sample manifests."""

import json
import logging
from pathlib import Path

from magoco_core.integrations import get_integrations_registry
from magoco_core.integrations.models import (
    CONNECTOR_TEMPLATES, IntegrationManifest,
    IntegrationCategory, IntegrationStatus,
)

logger = logging.getLogger(__name__)


def seed_registry() -> dict:
    reg = get_integrations_registry()
    created, skipped = [], []
    for t in CONNECTOR_TEMPLATES:
        try:
            if reg.get(t.id):
                skipped.append(t.id)
                continue
            m = IntegrationManifest(
                id=t.id,
                name=t.id,
                display_name=t.name,
                description=t.description,
                version="1.0.0",
                category=t.category,
                tags=set(t.tags),
                author="MAGoCo Team",
                base_url=t.manifest_template.get("base_url", ""),
                status=IntegrationStatus.PUBLISHED,
                is_public=True,
                featured=True,
            )
            reg.create(m)
            created.append(t.id)
        except Exception as e:
            logger.warning(f"seed skip {t.id}: {e}")
            skipped.append(t.id)
    return {"created": created, "skipped": skipped, "total": len(created) + len(skipped)}
