"""
MAGoCo Plugin System - Modular Architecture Foundation

This package provides the core plugin system that allows MAGoCo-Self-Evo
to dynamically load and execute feature modules.
"""

from .registry import (
    PluginRegistry,
    MagocoPlugin,
    PluginMetadata,
    PluginStatus,
    get_registry
)

__all__ = [
    "PluginRegistry",
    "MagocoPlugin",
    "PluginMetadata",
    "PluginStatus",
    "get_registry"
]

__version__ = "1.0.0"
