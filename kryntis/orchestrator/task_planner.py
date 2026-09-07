"""Task planner — breaks complex queries into subtasks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SubTask:
    name: str
    description: str
    tool: str = "llm"   # llm | rag | internet | memory


@dataclass
class TaskPlan:
    original_query: str
    subtasks: list[SubTask] = field(default_factory=list)


class TaskPlanner:
    """
    Simple rule-based task planner.

    For MVP, single-step plans are generated based on intent.
    Can be upgraded to LLM-based planning for complex queries.
    """

    def plan(self, query: str, intent: str) -> TaskPlan:
        plan = TaskPlan(original_query=query)
        if intent == "document_qa":
            plan.subtasks = [
                SubTask("retrieve", "Find relevant document chunks", tool="rag"),
                SubTask("answer", "Generate answer from chunks", tool="llm"),
            ]
        elif intent == "internet_search":
            plan.subtasks = [
                SubTask("search", "Search the internet", tool="internet"),
                SubTask("answer", "Synthesise answer from web results", tool="llm"),
            ]
        else:
            plan.subtasks = [
                SubTask("retrieve", "Check knowledge base", tool="rag"),
                SubTask("answer", "Generate response", tool="llm"),
            ]
        return plan
