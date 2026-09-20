"""Tests for kryntis.skills subsystem."""

import pytest
from kryntis.skills import SkillRegistry, SkillManager

def test_skill_registry_and_execution():
    registry = SkillRegistry()
    registry.register(
        name="math:multiply",
        description="Multiply two integers",
        handler=lambda a, b: a * b
    )
    assert registry.get_skill("math:multiply") is not None
    res = registry.execute("math:multiply", a=6, b=7)
    assert res == 42

def test_skill_manager_discovery():
    registry = SkillRegistry()
    registry.register(
        name="test:ping",
        description="Ping handler",
        handler=lambda: "pong"
    )
    manager = SkillManager(registry=registry)
    discovered = manager.discover_skills()
    assert any(s["name"] == "test:ping" for s in discovered)
    assert manager.execute_skill("test:ping", {}) == "pong"
