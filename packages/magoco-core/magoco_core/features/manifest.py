"""
Feature Manifest Types
تعریف تایپ‌های اشتراکی برای manifest ویژگی‌ها
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class FeatureManifest:
    """Schema manifest یک ویژگی"""
    id: str
    name: str
    description: str
    version: str
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    category: str = "core"
    priority: int = 0
    enabledByDefault: bool = True
    minCoreVersion: str = ""
    entryPoints: Dict[str, str] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureManifest":
        return cls(**data)


@dataclass
class FeatureConfig:
    """تنظیمات runtime یک ویژگی"""
    enabled: bool = True
    userConfig: Dict[str, Any] = field(default_factory=dict)
    updatedAt: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureConfig":
        return cls(**data)


@dataclass
class FeatureState:
    """وضعیت کامل یک ویژگی در runtime"""
    # از FeatureManifest
    id: str
    name: str
    description: str
    version: str
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    category: str = "core"
    priority: int = 0
    enabledByDefault: bool = True
    minCoreVersion: str = ""
    entryPoints: Dict[str, str] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    
    # Runtime
    config: 'FeatureConfig' = field(default_factory=FeatureConfig)
    status: str = "unloaded"  # unloaded, loading, loaded, error, disabled
    error: Optional[str] = None
    loadedAt: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if isinstance(data.get("config"), FeatureConfig):
            data["config"] = data["config"].to_dict()
        return data