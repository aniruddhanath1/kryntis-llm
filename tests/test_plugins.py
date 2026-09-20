"""Tests for kryntis.plugins subsystem."""

import pytest
from kryntis.plugins import PluginManager, BasePlugin
from kryntis.plugins.manifest import PluginManifest

class DummyPlugin(BasePlugin):
    name = "dummy_plugin"
    version = "1.0.0"

    def initialize(self, config: dict) -> None:
        self.initialized = True

    def manifest(self) -> PluginManifest:
        return PluginManifest(name="dummy_plugin", version="1.0.0", description="Dummy test plugin")

    def on_request(self, request_payload: dict) -> dict:
        request_payload["intercepted"] = True
        return request_payload

def test_plugin_lifecycle():
    pm = PluginManager()
    plugin = DummyPlugin()
    plugin.initialize({})
    pm.register_plugin(plugin)
    assert pm.get_plugin("dummy_plugin") is not None

    req = {"prompt": "test query"}
    processed = pm.intercept_request(req)
    assert processed.get("intercepted") is True
