"""Kryntis Skills Subsystem."""

from typing import Dict, Any, Callable, Optional
import inspect

class SkillRegistry:
    """Registry for autonomous agent skills."""
    def __init__(self) -> None:
        self._skills: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, handler: Callable[..., Any], parameters: Optional[Dict[str, Any]] = None) -> None:
        self._skills[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "parameters": parameters or {},
            "signature": str(inspect.signature(handler))
        }

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        return self._skills.get(name)

    def list_skills(self) -> Dict[str, Dict[str, Any]]:
        return self._skills

    def execute(self, name: str, **kwargs: Any) -> Any:
        skill = self._skills.get(name)
        if not skill:
            raise KeyError(f"Skill '{name}' not found")
        return skill["handler"](**kwargs)

default_skill_registry = SkillRegistry()

def skill(name: str, description: str, parameters: Optional[Dict[str, Any]] = None):
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        default_skill_registry.register(name, description, fn, parameters)
        return fn
    return decorator
