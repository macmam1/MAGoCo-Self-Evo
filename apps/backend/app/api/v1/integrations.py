"""Integration management endpoints - connect 3rd party services."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.integration import Integration, IntegrationType, ConnectionStatus

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationCreate(BaseModel):
    integration_type: IntegrationType
    label: str
    credentials: Dict[str, Any] = Field(default_factory=dict)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class IntegrationUpdate(BaseModel):
    label: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None
    status: Optional[ConnectionStatus] = None


class IntegrationOut(BaseModel):
    id: UUID
    integration_type: IntegrationType
    label: str
    status: ConnectionStatus
    metadata_json: Dict[str, Any]
    created_at: str
    last_synced_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[IntegrationOut])
async def list_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Integration).where(Integration.owner_id == current_user.id)
    )
    items = result.scalars().all()
    return [
        IntegrationOut(
            id=i.id,
            integration_type=i.integration_type,
            label=i.label,
            status=i.status,
            metadata_json=i.metadata_json,
            created_at=i.created_at.isoformat() if i.created_at else "",
            last_synced_at=i.last_synced_at.isoformat() if i.last_synced_at else None,
        )
        for i in items
    ]


@router.post("/", response_model=IntegrationOut)
async def create_integration(
    payload: IntegrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    integration = Integration(
        owner_id=current_user.id,
        integration_type=payload.integration_type,
        label=payload.label,
        credentials=payload.credentials,
        metadata_json=payload.metadata_json,
        status=ConnectionStatus.CONNECTED,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    integration = await db.get(Integration, integration_id)
    if not integration or integration.owner_id != current_user.id:
        raise HTTPException(404, "Integration not found")
    await db.delete(integration)
    await db.commit()
    return {"ok": True}


@router.get("/types")
async def list_supported_types():
    return {
        "types": [
            {"id": t.value, "label": t.value.title()}
            for t in IntegrationType
        ]
    }