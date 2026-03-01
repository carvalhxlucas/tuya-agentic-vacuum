import os
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from agent.tools import (
    clean_specific_room,
    locate_robot,
    return_to_base,
    set_suction,
    start_cleaning,
    stop_cleaning,
)

ROBOT_TOOLS = [start_cleaning, stop_cleaning, return_to_base, locate_robot, set_suction, clean_specific_room]

def _friendly_message(action: str, params: dict) -> str:
    if action == "start_cleaning":
        return "Got it, starting cleaning now."
    if action == "stop_cleaning":
        return "Got it, pausing the robot."
    if action == "return_to_base":
        return "Got it, sending the robot back to base."
    if action == "locate_robot":
        return "Got it, sending locate command to the robot."
    if action == "set_suction":
        level = (params or {}).get("level") if isinstance(params, dict) else None
        if isinstance(level, str):
            return f"Got it, setting suction to {level}."
        return "Got it, suction adjusted."
    if action == "clean_specific_room":
        room = (params or {}).get("room_name") if isinstance(params, dict) else None
        if isinstance(room, str):
            return f"Got it, sending the robot to clean {room} now."
    return "Command executed."


SYSTEM_PROMPT = """You are the control assistant for a vacuum robot. The user gives commands in natural language.
Your task is to interpret the intent and use EXACTLY one of the available tools.
Respond in English, briefly and in a friendly way, confirming the action executed.
Use only the provided tools; do not invent other actions."""


def _fallback_intent(message: str) -> tuple[str, Optional[str], Optional[dict]]:
    text = message.lower().strip()
    if any(w in text for w in ["clean", "vacuum", "start", "sweep", "begin"]):
        if "kitchen" in text:
            return ("Got it, sending the robot to clean the kitchen now.", "clean_specific_room", {"room_name": "kitchen"})
        if "living" in text:
            return ("Got it, sending the robot to clean the living room now.", "clean_specific_room", {"room_name": "living room"})
        if "bedroom" in text or "bed room" in text:
            return ("Got it, sending the robot to clean the bedroom now.", "clean_specific_room", {"room_name": "bedroom"})
        if "bathroom" in text or "bath" in text:
            return ("Got it, sending the robot to clean the bathroom now.", "clean_specific_room", {"room_name": "bathroom"})
        return ("Got it, starting cleaning now.", "start_cleaning", None)
    if any(w in text for w in ["stop", "pause", "halt"]):
        return ("Got it, pausing the robot.", "stop_cleaning", None)
    if any(w in text for w in ["return", "base", "dock", "charge", "go back"]):
        return ("Got it, sending the robot back to base.", "return_to_base", None)
    if any(w in text for w in ["locate", "find", "where is"]):
        return ("Got it, sending locate command to the robot.", "locate_robot", None)
    if any(w in text for w in ["suction", "power", "strength"]):
        level = "normal"
        if "max" in text or "strong" in text or "high" in text:
            level = "strong"
        elif "min" in text or "gentle" in text or "low" in text:
            level = "gentle"
        elif "standby" in text or "eco" in text:
            level = "standby"
        return (f"Got it, setting suction to {level}.", "set_suction", {"level": level})
    room_match = re.search(r"clean\s+(?:the\s+)?(\w+(?:\s+\w+)?)", text)
    if room_match:
        room = room_match.group(1).strip()
        return (f"Got it, sending the robot to clean {room} now.", "clean_specific_room", {"room_name": room})
    return ("I didn't recognize a valid command. You can ask to start or pause cleaning, return to base, locate the robot, or clean a specific room.", None, None)


def create_agent() -> Any:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            llm_with_tools = llm.bind_tools(ROBOT_TOOLS)
            return {"type": "langchain", "llm": llm_with_tools}
        except Exception:
            pass
    return {"type": "fallback"}


def execute_agent(agent: Any, message: str) -> tuple[str, Optional[str], Optional[dict]]:
    if agent.get("type") == "fallback":
        return _fallback_intent(message)
    llm = agent.get("llm")
    if not llm:
        return _fallback_intent(message)
    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
        response = llm.invoke(messages)
        if hasattr(response, "tool_calls") and response.tool_calls:
            tc = response.tool_calls[0]
            name = tc.get("name") or (getattr(tc, "name", None))
            args = tc.get("args") or {}
            if hasattr(tc, "args"):
                args = tc.args or args
            tool_map = {t.name: t for t in ROBOT_TOOLS}
            if name in tool_map:
                tool_map[name].invoke(args)
                friendly = _friendly_message(name, args)
                return (friendly, name, args if isinstance(args, dict) else None)
        return (response.content or "Command processed.", None, None)
    except Exception:
        return _fallback_intent(message)
