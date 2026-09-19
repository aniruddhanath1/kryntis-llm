"""
Cognitive Reasoning and Simulation Subsystem.
"""

from kryntis.reasoning.counterfactual_simulator import (
    CausalCounterfactualSimulator,
    CounterfactualScenario,
    SimulationDomain,
    SimulationOutcome,
)
from kryntis.reasoning.self_falsifying_logic import (
    AuditScope,
    FalsificationAuditResult,
    FalsificationVulnerability,
    SelfFalsifyingLogicEngine,
)

__all__ = [
    "CausalCounterfactualSimulator",
    "CounterfactualScenario",
    "SimulationDomain",
    "SimulationOutcome",
    "SelfFalsifyingLogicEngine",
    "AuditScope",
    "FalsificationAuditResult",
    "FalsificationVulnerability",
]
