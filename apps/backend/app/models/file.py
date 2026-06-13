"""File model — file metadata + storage reference."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class StorageBackend(str, PyEnum):
    """Where the file is actually stored."""

    LOCAL = "local"
    HF_DATASETS = "hf_datasets"
    S3 = "s3"
    GCS = "gcs"


class File(Base):
    """A file in the file manager.

    The actual content is stored externally (per StorageBackend).
    """

    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)  # virtual path
    mime_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Storage info
    storage_backend: Mapped[StorageBackend] = mapped_column(
        String(20), default=StorageBackend.LOCAL, nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)  # key/path in storage
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)  # sha256

    # Tree structure (for folders)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    is_folder: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    # Ownership
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", lazy="joined")
    workspace: Mapped["Workspace"] = relationship("Workspace", lazy="joined")
    parent: Mapped["File | None"] = relationship(
        "File", remote_side="File.id", backref="children", lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<File {self.path}>"
