"""
Kryntis AI — Sovereign Multi-Domain Autonomous LLM Platform.

A self-contained AI engine with RAG, memory, continual learning,
internet research, multi-format document ingestion, MCP, A2A, subagents, skills, and tools.
"""

from kryntis.QueryEngine import QueryEngine, default_query_engine
from kryntis.skills.skill_registry import SkillRegistry, default_skill_registry
from kryntis.skills.skill_manager import SkillManager
from kryntis.plugins.plugin_manager import PluginManager, default_plugin_manager
from kryntis.subagents.subagent_manager import SubagentManager, default_subagent_manager
from kryntis.mcp.server import MCPServer, default_mcp_server
from kryntis.a2a.protocol import AgentCard, A2AHandshake, A2APeerClient

__version__ = "4.0.0"
__author__ = "Kryntis AI"
__all__ = [
    "QueryEngine",
    "default_query_engine",
    "SkillRegistry",
    "default_skill_registry",
    "SkillManager",
    "PluginManager",
    "default_plugin_manager",
    "SubagentManager",
    "default_subagent_manager",
    "MCPServer",
    "default_mcp_server",
    "AgentCard",
    "A2AHandshake",
    "A2APeerClient",
    "__version__",
    "__author__",
]
