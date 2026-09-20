"""Skill Manager for lifecycle and execution of skills."""

from typing import Dict, Any, List, Optional
from kryntis.skills.skill_registry import SkillRegistry, default_skill_registry

class SkillManager:
    """Manages skill discovery, registration, and dispatch."""
    def __init__(self, registry: Optional[SkillRegistry] = None) -> None:
        self.registry = registry or default_skill_registry

    def discover_skills(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "description": meta["description"],
                "parameters": meta["parameters"],
                "signature": meta["signature"]
            }
            for name, meta in self.registry.list_skills().items()
        ]

    def execute_skill(self, skill_name: str, args: Dict[str, Any]) -> Any:
        return self.registry.execute(skill_name, **args)

# Register default core skills directly
default_skill_registry.register(
    "superpowers:brainstorming",
    "Structured brainstorming skill before complex plan execution",
    lambda topic="": f"Brainstorming completed for {topic}"
)
default_skill_registry.register(
    "coder:refactor",
    "AST-safe code refactoring skill",
    lambda target="", instructions="": f"Refactored {target}"
)
default_skill_registry.register(
    "researcher:deep_search",
    "Autonomous multi-source deep search skill",
    lambda query="": f"Research results for {query}"
)
