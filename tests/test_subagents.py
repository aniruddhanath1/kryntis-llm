"""Tests for kryntis.subagents subsystem."""

import pytest
import asyncio
from kryntis.subagents import SubagentManager, SubagentDefinition

@pytest.mark.asyncio
async def test_subagent_registration_and_delegation():
    mgr = SubagentManager()
    custom_agent = SubagentDefinition(
        name="tester",
        role="Unit Testing Agent",
        description="Executes test assertions",
        system_prompt="You are a test runner.",
        tools=["code_interpreter"]
    )
    mgr.register_subagent(custom_agent)
    assert mgr.get_subagent("tester") is not None
    
    result = await mgr.delegate("tester", "Run test suite", {"env": "test"})
    assert result["status"] == "completed"
    assert result["agent"] == "tester"
    assert "Run test suite" in result["output"]

def test_subagent_listing():
    mgr = SubagentManager()
    agents = mgr.list_subagents()
    names = [a["name"] for a in agents]
    assert "researcher" in names
    assert "coder" in names
