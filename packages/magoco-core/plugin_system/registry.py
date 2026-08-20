"""
Plugin Registry System - Core of MAGoCo-Self-Evo Modular Architecture

This module provides the foundation for loading, registering, and executing
plugins dynamically. Each feature (Auto-Generation, IDE, Workflow, etc.)
is a plugin that can be independently maintained and upgraded.
"""

from typing import Dict, Any, Callable, Optional, Type
from abc import ABC, abstractmethod
import json
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PluginStatus(Enum):
    """Status of a plugin"""
    UNREGISTERED = "unregistered"
    REGISTERED = "registered"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    """Metadata about a plugin"""
    name: str
    version: str
    author: str
    description: str
    category: str  # "auto-gen", "ide", "workflow", "chat", "execution", "tasks", "evolution", "multi-model"
    dependencies: Optional[list] = None
    enabled: bool = True
    
    def to_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "category": self.category,
            "dependencies": self.dependencies or [],
            "enabled": self.enabled
        }


class MagocoPlugin(ABC):
    """Base class for all MAGoCo plugins"""
    
    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self.status = PluginStatus.REGISTERED
        self._config = {}
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the plugin's main functionality."""
        pass
    
    @abstractmethod
    def validate_input(self, *args, **kwargs) -> bool:
        """Validate input before execution."""
        pass
    
    def shutdown(self) -> bool:
        """Cleanup resources. Return True if successful."""
        return True
    
    def get_config(self) -> Dict:
        """Get plugin configuration"""
        return self._config.copy()
    
    def set_config(self, config: Dict) -> bool:
        """Set plugin configuration"""
        self._config.update(config)
        return True


class PluginRegistry:
    """
    Central registry for managing all plugins.
    
    Features:
    - Dynamic plugin registration/loading
    - Dependency resolution
    - Execution orchestration
    - Health monitoring
    - Configuration management
    """
    
    def __init__(self):
        self.plugins: Dict[str, MagocoPlugin] = {}
        self.plugin_metadata: Dict[str, PluginMetadata] = {}
        self.plugin_status: Dict[str, PluginStatus] = {}
        self._execution_history = []
    
    def register(self, metadata: PluginMetadata, plugin_class: Type[MagocoPlugin]) -> bool:
        """
        Register a new plugin.
        
        Args:
            metadata: Plugin metadata
            plugin_class: Plugin class (will be instantiated)
        
        Returns:
            True if registration successful
        """
        try:
            if metadata.name in self.plugins:
                logger.warning(f"Plugin {metadata.name} already registered. Overwriting.")
            
            # Check dependencies
            if metadata.dependencies:
                missing_deps = [d for d in metadata.dependencies if d not in self.plugins]
                if missing_deps:
                    logger.error(f"Plugin {metadata.name} has missing dependencies: {missing_deps}")
                    return False
            
            # Instantiate and initialize plugin
            plugin_instance = plugin_class(metadata)
            if not plugin_instance.initialize():
                logger.error(f"Failed to initialize plugin {metadata.name}")
                self.plugin_status[metadata.name] = PluginStatus.FAILED
                return False
            
            # Store plugin
            self.plugins[metadata.name] = plugin_instance
            self.plugin_metadata[metadata.name] = metadata
            self.plugin_status[metadata.name] = PluginStatus.LOADED
            
            logger.info(f"✅ Plugin registered: {metadata.name} v{metadata.version}")
            return True
        
        except Exception as e:
            logger.error(f"Error registering plugin {metadata.name}: {e}")
            self.plugin_status[metadata.name] = PluginStatus.FAILED
            return False
    
    def get_plugin(self, name: str) -> Optional[MagocoPlugin]:
        """Get a registered plugin by name"""
        return self.plugins.get(name)
    
    def execute_plugin(self, name: str, *args, **kwargs) -> Optional[Any]:
        """
        Execute a plugin.
        
        Args:
            name: Plugin name
            *args: Arguments to pass to plugin
            **kwargs: Keyword arguments to pass to plugin
        
        Returns:
            Plugin execution result
        """
        if name not in self.plugins:
            logger.error(f"Plugin {name} not found")
            return None
        
        plugin = self.plugins[name]
        
        # Validate input
        if not plugin.validate_input(*args, **kwargs):
            logger.error(f"Invalid input for plugin {name}")
            return None
        
        try:
            result = plugin.execute(*args, **kwargs)
            
            # Record execution
            self._execution_history.append({
                "plugin": name,
                "status": "success",
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })
            
            logger.info(f"✅ Plugin executed: {name}")
            return result
        
        except Exception as e:
            logger.error(f"Error executing plugin {name}: {e}")
            self._execution_history.append({
                "plugin": name,
                "status": "failed",
                "error": str(e)
            })
            return None
    
    def execute_pipeline(self, pipeline: list) -> Optional[Any]:
        """
        Execute a sequence of plugins (pipeline).
        
        Args:
            pipeline: List of tuples (plugin_name, args, kwargs)
        
        Returns:
            Result of the last plugin in pipeline
        """
        result = None
        
        for step in pipeline:
            if isinstance(step, str):
                plugin_name = step
                args, kwargs = (), {}
            elif isinstance(step, tuple) and len(step) == 3:
                plugin_name, args, kwargs = step
            else:
                logger.error(f"Invalid pipeline step: {step}")
                return None
            
            result = self.execute_plugin(plugin_name, *args, **kwargs)
            if result is None:
                logger.error(f"Pipeline failed at step: {plugin_name}")
                return None
        
        return result
    
    def list_plugins(self) -> Dict[str, Dict]:
        """List all registered plugins with their metadata"""
        return {
            name: {
                "metadata": self.plugin_metadata[name].to_dict(),
                "status": self.plugin_status.get(name, PluginStatus.UNREGISTERED).value
            }
            for name in self.plugins.keys()
        }
    
    def list_plugins_by_category(self, category: str) -> Dict[str, Dict]:
        """List plugins by category"""
        return {
            name: {
                "metadata": self.plugin_metadata[name].to_dict(),
                "status": self.plugin_status.get(name, PluginStatus.UNREGISTERED).value
            }
            for name, plugin in self.plugins.items()
            if self.plugin_metadata[name].category == category
        }
    
    def disable_plugin(self, name: str) -> bool:
        """Disable a plugin"""
        if name not in self.plugins:
            return False
        self.plugin_status[name] = PluginStatus.DISABLED
        logger.info(f"Plugin disabled: {name}")
        return True
    
    def enable_plugin(self, name: str) -> bool:
        """Enable a disabled plugin"""
        if name not in self.plugins:
            return False
        self.plugin_status[name] = PluginStatus.LOADED
        logger.info(f"Plugin enabled: {name}")
        return True
    
    def unregister_plugin(self, name: str) -> bool:
        """Unregister and shutdown a plugin"""
        if name not in self.plugins:
            return False
        
        try:
            plugin = self.plugins[name]
            plugin.shutdown()
            del self.plugins[name]
            del self.plugin_metadata[name]
            del self.plugin_status[name]
            logger.info(f"Plugin unregistered: {name}")
            return True
        except Exception as e:
            logger.error(f"Error unregistering plugin {name}: {e}")
            return False
    
    def get_execution_history(self, limit: int = 100) -> list:
        """Get recent execution history"""
        return self._execution_history[-limit:]
    
    def export_registry_config(self) -> Dict:
        """Export registry configuration as JSON"""
        return {
            "plugins": {
                name: {
                    "metadata": self.plugin_metadata[name].to_dict(),
                    "config": self.plugins[name].get_config(),
                    "status": self.plugin_status[name].value
                }
                for name in self.plugins.keys()
            },
            "execution_history_count": len(self._execution_history)
        }


# Global registry instance
_registry_instance = None


def get_registry() -> PluginRegistry:
    """Get or create global registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = PluginRegistry()
    return _registry_instance


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create a simple example plugin
    class ExamplePlugin(MagocoPlugin):
        def initialize(self) -> bool:
            logger.info(f"Initializing {self.metadata.name}")
            return True
        
        def execute(self, *args, **kwargs) -> Any:
            return {"result": f"Executed {self.metadata.name}", "args": args, "kwargs": kwargs}
        
        def validate_input(self, *args, **kwargs) -> bool:
            return True
    
    # Register and use
    registry = get_registry()
    
    metadata = PluginMetadata(
        name="example_plugin",
        version="1.0.0",
        author="MAGoCo Team",
        description="Example plugin",
        category="auto-gen"
    )
    
    registry.register(metadata, ExamplePlugin)
    result = registry.execute_plugin("example_plugin", "arg1", key="value")
    print(f"Result: {result}")
    print(f"Registry status: {json.dumps(registry.export_registry_config(), indent=2)}")
