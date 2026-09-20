"""Subagent Manager Subsystem."""

from typing import Dict, Any, List, Optional
from kryntis.subagents.agent_definition import SubagentDefinition
from kryntis.subagents.executor import SubagentExecutor

class SubagentManager:
    """Manages lifecycle, registry, and delegation to autonomous subagents."""
    def __init__(self) -> None:
        self._agents: Dict[str, SubagentDefinition] = {}
        self._executors: Dict[str, SubagentExecutor] = {}
        self._init_defaults()

    def register_subagent(self, definition: SubagentDefinition) -> None:
        self._agents[definition.name] = definition
        self._executors[definition.name] = SubagentExecutor(definition)

    def get_subagent(self, name: str) -> Optional[SubagentDefinition]:
        return self._agents.get(name)

    def list_subagents(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": agent.name,
                "role": agent.role,
                "description": agent.description,
                "tools": agent.tools
            }
            for agent in self._agents.values()
        ]

    async def delegate(self, agent_name: str, task_input: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        executor = self._executors.get(agent_name)
        if not executor:
            raise KeyError(f"Subagent '{agent_name}' not registered")
        return await executor.execute_task(task_input, context)

    def _init_defaults(self) -> None:
        self.register_subagent(
            SubagentDefinition(
                name="researcher",
                role="Codebase & Deep Research Specialist",
                description="Performs deep contextual search and doc lookup.",
                system_prompt="You are an autonomous research agent.",
                tools=["web_fetch", "fs_read_file", "sql_query"]
            )
        )
        self.register_subagent(
            SubagentDefinition(
                name="coder",
                role="Autonomous Code Refactoring Agent",
                description="Generates, refactors, and verifies Python code.",
                system_prompt="You are a senior pair-programming coding agent.",
                tools=["code_interpreter", "fs_read_file", "fs_list_dir"]
            )
        )

default_subagent_manager = SubagentManager()
