"""
Feature Registry API Routes
REST API برای مدیریت ویژگی‌ها
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.features import get_registry, init_registry, FeatureConfig

router = APIRouter(prefix="/api/v1/features", tags=["features"])


class FeatureEnableRequest(BaseModel):
    feature_id: str


class FeatureConfigUpdate(BaseModel):
    feature_id: str
    config: Dict[str, Any]


class FeatureResponse(BaseModel):
    id: str
    name: str
    description: str
    version: str
    category: str
    enabled: bool
    status: str
    dependencies: List[str]
    entryPoints: Dict[str, str]


def get_feature_registry():
    """Dependency برای دریافت رجیستری"""
    return get_registry()


@router.get("/", response_model=List[FeatureResponse])
async def list_features(
    category: Optional[str] = None,
    enabled_only: bool = False,
    registry=Depends(get_feature_registry),
):
    """لیست تمام ویژگی‌ها"""
    if category:
        features = registry.get_features_by_category(category)
    elif enabled_only:
        features = registry.get_enabled_features()
    else:
        features = registry.get_all_features()
    
    return [
        FeatureResponse(
            id=fid,
            name=state.name,
            description=state.description,
            version=state.version,
            category=state.category,
            enabled=state.config.enabled,
            status=state.status,
            dependencies=state.dependencies,
            entryPoints=state.entryPoints,
        )
        for fid, state in features.items()
    ]


@router.get("/{feature_id}", response_model=FeatureResponse)
async def get_feature(
    feature_id: str,
    registry=Depends(get_feature_registry),
):
    """دریافت اطلاعات یک ویژگی"""
    state = registry.get_feature(feature_id)
    if not state:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    return FeatureResponse(
        id=state.id,
        name=state.name,
        description=state.description,
        version=state.version,
        category=state.category,
        enabled=state.config.enabled,
        status=state.status,
        dependencies=state.dependencies,
        entryPoints=state.entryPoints,
    )


@router.post("/{feature_id}/enable")
async def enable_feature(
    feature_id: str,
    registry=Depends(get_feature_registry),
):
    """فعال کردن یک ویژگی"""
    success = registry.enable_feature(feature_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot enable feature (dependency missing or not found)")
    
    return {"success": True, "feature_id": feature_id}


@router.post("/{feature_id}/disable")
async def disable_feature(
    feature_id: str,
    registry=Depends(get_feature_registry),
):
    """غیرفعال کردن یک ویژگی"""
    success = registry.disable_feature(feature_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot disable feature (required by other features or not found)")
    
    return {"success": True, "feature_id": feature_id}


@router.patch("/{feature_id}/config")
async def update_feature_config(
    feature_id: str,
    request: FeatureConfigUpdate,
    registry=Depends(get_feature_registry),
):
    """بروزرسانی تنظیمات یک ویژگی"""
    success = registry.update_user_config(feature_id, request.config)
    if not success:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    return {"success": True, "feature_id": feature_id}


@router.get("/load-order")
async def get_load_order(registry=Depends(get_feature_registry)):
    """دریافت ترتیب بارگذاری ویژگی‌ها"""
    order = registry.get_load_order()
    return {"load_order": order}


@router.post("/initialize")
async def initialize_registry():
    """مقداردهی اولیه مجدد رجیستری"""
    init_registry()
    return {"success": True, "message": "Registry reinitialized"}