"""
Feature Registry Core
مدیریت ثبت، بارگذاری و مدیریت ویژگی‌ها (features)
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import logging

from .manifest import FeatureManifest, FeatureConfig, FeatureState

logger = logging.getLogger(__name__)


@dataclass
class FeatureRegistry:
    """
    رجیستری مرکزی ویژگی‌ها
    - اسکن پوشه‌های ویژگی‌ها
    - مدیریت manifestها
    - مدیریت config کاربران
    - API فعال/غیرفعال کردن
    """
    
    features_dir: Path
    config_file: Path
    _features: Dict[str, FeatureState] = field(default_factory=dict)
    _configs: Dict[str, FeatureConfig] = field(default_factory=dict)
    _initialized: bool = False
    
    def __post_init__(self):
        self.features_dir = Path(self.features_dir)
        self.config_file = Path(self.config_file)
        self._load_configs()
    
    def _load_configs(self):
        """بارگذاری تنظیمات ذخیره شده کاربران"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._configs = {
                        k: FeatureConfig(**v) if isinstance(v, dict) else v
                        for k, v in data.get("features", {}).items()
                    }
            except Exception as e:
                logger.warning(f"Failed to load feature configs: {e}")
                self._configs = {}
    
    def _save_configs(self):
        """ذخیره تنظیمات کاربران"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({
                    "features": {k: asdict(v) for k, v in self._configs.items()},
                    "updated_at": datetime.utcnow().isoformat(),
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save feature configs: {e}")
    
    def scan_features(self) -> List[FeatureManifest]:
        """اسکن پوشه‌های ویژگی‌ها و خواندن manifestها"""
        manifests = []
        
        if not self.features_dir.exists():
            logger.warning(f"Features directory not found: {self.features_dir}")
            return manifests
        
        for item in self.features_dir.iterdir():
            if not item.is_dir():
                continue
            
            manifest_path = item / "manifest.json"
            if not manifest_path.exists():
                logger.debug(f"No manifest.json in {item}")
                continue
            
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    manifest = FeatureManifest(**data)
                    manifests.append(manifest)
                    logger.debug(f"Loaded feature: {manifest.id} v{manifest.version}")
            except Exception as e:
                logger.error(f"Failed to load manifest from {manifest_path}: {e}")
        
        # مرتب‌سازی بر اساس priority (بالای‌تر اول)
        manifests.sort(key=lambda m: m.priority, reverse=True)
        return manifests
    
    def initialize(self) -> Dict[str, FeatureState]:
        """مقداردهی اولیه رجیستری - اسکن و بارگذاری همه ویژگی‌ها"""
        if self._initialized:
            return self._features
        
        manifests = self.scan_features()
        
        for manifest in manifests:
            config = self._configs.get(manifest.id, FeatureConfig(
                enabled=manifest.enabledByDefault,
                userConfig={},
                updatedAt=datetime.utcnow().isoformat()
            ))
            
            state = FeatureState(
                **asdict(manifest),
                config=config,
                status="unloaded",
            )
            self._features[manifest.id] = state
        
        self._initialized = True
        logger.info(f"Feature registry initialized with {len(self._features)} features")
        return self._features
    
    def get_feature(self, feature_id: str) -> Optional[FeatureState]:
        """دریافت وضعیت یک ویژگی"""
        return self._features.get(feature_id)
    
    def get_all_features(self) -> Dict[str, FeatureState]:
        """دریافت همه ویژگی‌ها"""
        return self._features.copy()
    
    def get_features_by_category(self, category: str) -> Dict[str, FeatureState]:
        """دریافت ویژگی‌ها بر اساس دسته‌بندی"""
        return {
            fid: state for fid, state in self._features.items()
            if state.category == category
        }
    
    def get_enabled_features(self) -> Dict[str, FeatureState]:
        """دریافت ویژگی‌های فعال"""
        return {
            fid: state for fid, state in self._features.items()
            if state.config.enabled and state.status != "error"
        }
    
    def enable_feature(self, feature_id: str) -> bool:
        """فعال کردن یک ویژگی"""
        if feature_id not in self._features:
            return False
        
        state = self._features[feature_id]
        
        # بررسی پیش‌نیازها
        for dep_id in state.dependencies:
            dep = self._features.get(dep_id)
            if not dep or not dep.config.enabled:
                logger.warning(f"Cannot enable {feature_id}: dependency {dep_id} not enabled")
                return False
        
        state.config.enabled = True
        state.config.updatedAt = datetime.utcnow().isoformat()
        self._configs[feature_id] = state.config
        self._save_configs()
        
        logger.info(f"Feature enabled: {feature_id}")
        return True
    
    def disable_feature(self, feature_id: str) -> bool:
        """غیرفعال کردن یک ویژگی"""
        if feature_id not in self._features:
            return False
        
        state = self._features[feature_id]
        
        # بررسی آیا ویژگی دیگر به این وابسته است
        for other_id, other_state in self._features.items():
            if other_state.config.enabled and feature_id in other_state.dependencies:
                logger.warning(f"Cannot disable {feature_id}: required by {other_id}")
                return False
        
        state.config.enabled = False
        state.config.updatedAt = datetime.utcnow().isoformat()
        self._configs[feature_id] = state.config
        self._save_configs()
        
        logger.info(f"Feature disabled: {feature_id}")
        return True
    
    def update_user_config(self, feature_id: str, config: Dict[str, Any]) -> bool:
        """بروزرسانی تنظیمات کاربر برای یک ویژگی"""
        if feature_id not in self._features:
            return False
        
        state = self._features[feature_id]
        state.config.userConfig = {**(state.config.userConfig or {}), **config}
        state.config.updatedAt = datetime.utcnow().isoformat()
        self._configs[feature_id] = state.config
        self._save_configs()
        
        return True
    
    def set_feature_status(self, feature_id: str, status: str, error: Optional[str] = None) -> bool:
        """تنظیم وضعیت runtime یک ویژگی"""
        if feature_id not in self._features:
            return False
        
        state = self._features[feature_id]
        state.status = status
        if error:
            state.error = error
        if status == "loaded":
            state.loadedAt = datetime.utcnow().isoformat()
        
        return True
    
    def get_load_order(self) -> List[str]:
        """ترتیب بارگذاری بر اساس dependencyها و priority"""
        # topological sort ساده
        enabled = self.get_enabled_features()
        visited = set()
        order = []
        
        def visit(fid: str):
            if fid in visited:
                return
            visited.add(fid)
            
            state = enabled.get(fid)
            if not state:
                return
            
            for dep_id in state.dependencies:
                if dep_id in enabled:
                    visit(dep_id)
            
            order.append(fid)
        
        for fid in enabled:
            visit(fid)
        
        return order


# Global registry instance
_registry: Optional[FeatureRegistry] = None


def get_registry() -> FeatureRegistry:
    """دریافت instance singleton رجیستری"""
    global _registry
    if _registry is None:
        # مسیر پیش‌فرض
        features_dir = Path(__file__).parent.parent.parent.parent / "features"
        config_file = Path(__file__).parent.parent.parent.parent / "data" / "feature_configs.json"
        _registry = FeatureRegistry(
            features_dir=features_dir,
            config_file=config_file,
        )
    return _registry


def init_registry(features_dir: Optional[Path] = None, config_file: Optional[Path] = None) -> FeatureRegistry:
    """مقداردهی اولیه رجیستری با مسیرهای سفارشی"""
    global _registry
    if features_dir is None:
        features_dir = Path(__file__).parent.parent.parent.parent / "features"
    if config_file is None:
        config_file = Path(__file__).parent.parent.parent.parent / "data" / "feature_configs.json"
    
    _registry = FeatureRegistry(
        features_dir=features_dir,
        config_file=config_file,
    )
    return _registry.initialize()