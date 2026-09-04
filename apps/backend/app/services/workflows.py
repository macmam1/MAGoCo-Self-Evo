"""Minimal workflow service — CRUD over the graph-based Workflow model."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import Workflow


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, *, name: str, description: str | None, graph: dict,
                     owner_id: uuid.UUID, workspace_id: uuid.UUID, is_public: bool = False) -> Workflow:
        wf = Workflow(name=name, description=description, graph=graph or {"nodes": [], "edges": []},
                      owner_id=owner_id, workspace_id=workspace_id, is_public=is_public)
        self.db.add(wf)
        await self.db.commit()
        await self.db.refresh(wf)
        return wf

    async def get(self, workflow_id: uuid.UUID) -> Workflow | None:
        return await self.db.get(Workflow, workflow_id)

    async def list_for_owner(self, owner_id: uuid.UUID) -> list[Workflow]:
        result = await self.db.execute(select(Workflow).where(Workflow.owner_id == owner_id))
        return list(result.scalars().all())
