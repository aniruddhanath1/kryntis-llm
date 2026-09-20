"""Plugin Manager implementation for kryntis."""

from typing import Dict, List, Any, Optional
from kryntis.plugins.base_plugin import BasePlugin

class PluginManager:
    def __init__(self) -> None:
        self._plugins: Dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin, config: Optional[Dict[str, Any]] = None) -> None:
        plugin.initialize(config or {})
        self._plugins[plugin.name] = plugin

    def register_plugin(self, plugin: BasePlugin, config: Optional[Dict[str, Any]] = None) -> None:
        self.register(plugin, config)

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        return self._plugins.get(name)

    def list_plugins(self) -> List[str]:
        return list(self._plugins.keys())

    def intercept_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        for plugin in self._plugins.values():
            payload = plugin.on_request(payload)
        return payload

    def intercept_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        for plugin in self._plugins.values():
            response = plugin.on_response(response)
        return response

default_plugin_manager = PluginManager()
