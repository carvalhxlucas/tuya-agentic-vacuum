import logging
import os
import re
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

from agent.tools import (
    locate_robot,
    return_to_base,
    set_clean_mode,
    start_cleaning,
    stop_cleaning,
)

ROBOT_TOOLS = [start_cleaning, stop_cleaning, return_to_base, locate_robot, set_clean_mode]

SYSTEM_PROMPT = (
    "You are the control assistant for a vacuum robot. The user gives commands in natural language.\n"
    "Your task is to interpret the intent and use EXACTLY one of the available tools.\n"
    "Always respond in the same language the user wrote in — Portuguese if they write in Portuguese, English if in English.\n"
    "After calling a tool, confirm the action in a brief and friendly way.\n"
    "If the user refers to a previous command (e.g. 'do that again', 'faz de novo'), use the conversation history to infer the intent.\n"
    "Use only the provided tools; do not invent other actions."
)

# ---------------------------------------------------------------------------
# Fallback messages (no LLM available)
# ---------------------------------------------------------------------------

FALLBACK_MESSAGES_PT = {
    "start_cleaning": "Certo, iniciando a limpeza agora.",
    "stop_cleaning": "Certo, pausando o robô.",
    "return_to_base": "Certo, enviando o robô de volta para a base.",
    "locate_robot": "Certo, enviando o sinal de localização.",
    "set_clean_mode": "Certo, modo de limpeza alterado para {mode}.",
}

FALLBACK_MESSAGES_EN = {
    "start_cleaning": "Got it, starting cleaning now.",
    "stop_cleaning": "Got it, pausing the robot.",
    "return_to_base": "Got it, sending the robot back to base.",
    "locate_robot": "Got it, sending locate signal.",
    "set_clean_mode": "Got it, switching to {mode} mode.",
}


def _is_portuguese(text: str) -> bool:
    pt_words = {
        "limpar", "limpa", "limpeza", "iniciar", "inicia", "começa", "começar",
        "parar", "para", "pausar", "pausa", "voltar", "volta", "base", "carregar",
        "localizar", "localiza", "onde", "modo", "espiral", "aleatorio", "aleatório",
    }
    return bool(set(text.lower().split()) & pt_words)


def _friendly_message(action: str, params: dict, user_message: str) -> str:
    mode = (params or {}).get("mode", "") if isinstance(params, dict) else ""
    messages = FALLBACK_MESSAGES_PT if _is_portuguese(user_message) else FALLBACK_MESSAGES_EN
    template = messages.get(action, "Command executed.")
    return template.format(mode=mode) if "{mode}" in template else template


def _fallback_intent(message: str) -> tuple[str, Optional[str], Optional[dict]]:
    text = message.lower().strip()
    pt = _is_portuguese(text)

    if any(w in text for w in ["clean", "vacuum", "start", "sweep", "begin",
                                "limpar", "limpa", "aspirar", "iniciar", "começa", "começar", "limpeza"]):
        return (_friendly_message("start_cleaning", {}, message), "start_cleaning", None)
    if any(w in text for w in ["stop", "pause", "halt", "parar", "pausar", "para", "pausa"]):
        return (_friendly_message("stop_cleaning", {}, message), "stop_cleaning", None)
    if any(w in text for w in ["return", "base", "dock", "charge", "go back",
                                "voltar", "volta", "carregar", "carrega"]):
        return (_friendly_message("return_to_base", {}, message), "return_to_base", None)
    if any(w in text for w in ["locate", "find", "where is",
                                "localizar", "localiza", "onde", "encontrar"]):
        return (_friendly_message("locate_robot", {}, message), "locate_robot", None)
    if any(w in text for w in ["mode", "smart", "random", "spiral", "mop", "wall",
                                "modo", "espiral", "aleatorio", "aleatório", "esfregão"]):
        mode = "smart"
        if "random" in text or "aleatorio" in text or "aleatório" in text:
            mode = "random"
        elif "spiral" in text or "espiral" in text:
            mode = "spiral"
        elif "wall" in text:
            mode = "wall_follow"
        elif "mop" in text or "esfregão" in text:
            mode = "mop"
        return (_friendly_message("set_clean_mode", {"mode": mode}, message), "set_clean_mode", {"mode": mode})

    if pt:
        return ("Não entendi o comando. Você pode pedir para iniciar ou pausar a limpeza, voltar para a base, localizar o robô ou mudar o modo de limpeza.", None, None)
    return ("I didn't recognize a valid command. You can ask to start or pause cleaning, return to base, locate the robot, or change the cleaning mode.", None, None)


def _is_error(result: str) -> bool:
    return any(w in result.lower() for w in ("not configured", "failed", "rejected", "error", "invalid"))


def _extract_tool_call(messages: list) -> tuple[Optional[str], Optional[dict]]:
    """Extracts the last tool call name and args from a LangGraph messages list."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            tc = msg.tool_calls[0]
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
            args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
            return name, args if isinstance(args, dict) else None
    return None, None


# ---------------------------------------------------------------------------
# Agent creation
# ---------------------------------------------------------------------------

def _build_llm() -> Any:
    """Tries Ollama first, falls back to OpenAI. Returns None if neither is available."""
    try:
        from langchain_ollama import ChatOllama
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        llm = ChatOllama(model=model, base_url=base_url, temperature=0.3)
        llm.invoke("ping")
        logger.info("Using Ollama: %s", model)
        return llm
    except Exception as e:
        logger.info("Ollama unavailable (%s), trying OpenAI.", e)

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
            logger.info("Using OpenAI gpt-4o-mini.")
            return llm
        except Exception as e:
            logger.info("OpenAI unavailable (%s).", e)

    return None


def create_agent() -> Any:
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import create_react_agent

    llm = _build_llm()
    if llm is None:
        logger.warning("No LLM available — using regex fallback.")
        return {"type": "fallback"}

    memory = MemorySaver()
    graph = create_react_agent(
        model=llm,
        tools=ROBOT_TOOLS,
        prompt=SYSTEM_PROMPT,
        checkpointer=memory,
    )
    logger.info("LangGraph ReAct agent created with per-user memory.")
    return {"type": "langgraph", "graph": graph}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def execute_agent(
    agent: Any,
    message: str,
    user_id: str = "default",
) -> tuple[str, Optional[str], Optional[dict]]:
    if agent.get("type") == "fallback":
        return _fallback_intent(message)

    graph = agent.get("graph")
    if not graph:
        return _fallback_intent(message)

    config = {"configurable": {"thread_id": str(user_id)}}

    try:
        result = graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )
        last_msg = result["messages"][-1]
        response_text = last_msg.content if isinstance(last_msg.content, str) else str(last_msg.content)

        action_name, action_params = _extract_tool_call(result["messages"])
        logger.info("user=%s action=%s params=%s", user_id, action_name, action_params)

        return (response_text, action_name, action_params)

    except Exception as e:
        logger.error("Graph invocation error (user=%s): %s", user_id, e)
        return _fallback_intent(message)
