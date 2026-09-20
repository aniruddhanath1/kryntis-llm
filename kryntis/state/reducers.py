"""State Reducers."""

from typing import Dict, Any

def session_reducer(state: Dict[str, Any], action: Dict[str, Any]) -> Dict[str, Any]:
    action_type = action.get("type")
    new_state = state.copy()
    if action_type == "SET_ACTIVE_SESSION":
        new_state["active_session"] = action.get("payload")
    elif action_type == "SET_MODEL_STATUS":
        new_state["model_status"] = action.get("payload")
    return new_state
