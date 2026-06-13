"""File schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.file import StorageBackend


class FileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    path: str = Field(min_length=1, max_length=1000)
    mime_type: str = "application/octet-stream"
    is_folder: bool = False
    parent_id: uuid.UUID | None = None


class FileCreate(FileBase):
    workspace_id: uuid.UUID
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_key: str = Field(min_length=1, max_length=500)
    size: int = 0
    checksum: str | None = None


class FileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    path: str | None = None
    parent_id: uuid.UUID | None = None


class FileResponse(FileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    mime_type: str
    size: int
    storage_backend: StorageBackend
    storage_key: str
    checksum: str | None
    owner_id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
